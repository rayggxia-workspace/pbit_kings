"""Stream simulator output and retain wall-time progress through termination."""
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


def latest_progress():
    try:
        with open('progress.csv', 'rb') as handle:
            handle.seek(0, 2)
            handle.seek(max(0, handle.tell() - 4096))
            lines = handle.read().decode('utf-8', 'replace').splitlines()
        return lines[-1] if lines else 'no simulation progress yet'
    except OSError:
        return 'no simulation progress yet'


def thread_sample(pid, previous):
    rows=[]; now=time.monotonic(); hz=os.sysconf('SC_CLK_TCK')
    base=Path('/proc')/str(pid)/'task'
    try: tasks=list(base.iterdir())
    except OSError: return previous,rows
    for task in tasks:
        try:
            text=(task/'stat').read_text(); tail=text[text.rfind(')')+2:].split()
            ticks=int(tail[11])+int(tail[12]); old=previous.get(task.name)
            busy=(ticks-old[1])/hz/(now-old[0]) if old and now>old[0] else 0
            rows.append((task.name,tail[0],ticks,busy))
            previous[task.name]=(now,ticks)
        except (OSError,ValueError,IndexError): pass
    return previous,rows

def run(command, interval=10):
    requested = []
    def on_signal(number, frame):
        requested.append(number)
    for number in (signal.SIGTERM, signal.SIGINT):
        signal.signal(number, on_signal)
    start = time.monotonic()
    process = subprocess.Popen(command, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, universal_newlines=True,
                               errors='replace', bufsize=1,
                               start_new_session=(os.name == 'posix'))
    try:
        allowed=sorted(os.sched_getaffinity(process.pid)) if hasattr(os,'sched_getaffinity') else None
    except OSError:
        allowed=None
    Path('runtime_resources.json').write_text(json.dumps(dict(simulator_pid=process.pid,
        allowed_cpu_ids=allowed,allocated_cpus=os.environ.get('SLURM_CPUS_PER_TASK'),
        parallel=os.environ.get('PARALLEL'),fgp_requested=os.environ.get('VCS_FGP_THREADS')),indent=2)+'\n')
    def stream():
        with open('simulation.log', 'w', buffering=1) as log:
            for line in process.stdout:
                log.write(line)
                log.flush()
                sys.stdout.write(line)
                sys.stdout.flush()
    reader = threading.Thread(target=stream)
    reader.daemon = True
    reader.start()
    next_report = start
    deadline = None
    max_wall=float(os.environ.get('MAX_WALL_HOURS','12'))*3600
    thread_previous={}
    cpu_samples=[]
    Path('thread_usage.tsv').write_text('wall_seconds\ttid\tstate\tcpu_ticks\tcpu_cores_recent\n')
    with open('wall_progress.log', 'w', buffering=1) as wall:
        while process.poll() is None:
            now = time.monotonic()
            if max_wall>0 and now-start>=max_wall and not requested:
                Path('WALL_LIMIT_REACHED.txt').write_text('No pass implied. MAX_WALL_HOURS reached.\n')
                requested.append(signal.SIGTERM)
            if requested and deadline is None:
                if os.name == 'posix':
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                else:
                    process.terminate()
                deadline = now + 10
            if deadline is not None and now >= deadline:
                if os.name == 'posix':
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                else:
                    process.kill()
            if now >= next_report:
                message = '[WALL_PROGRESS] {} elapsed_s={:.0f} pid={} latest={}'.format(
                    datetime.datetime.now().isoformat(), now-start, process.pid, latest_progress())
                print(message, flush=True)
                wall.write(message + '\n')
                if os.name=='posix':
                    thread_previous,threads=thread_sample(process.pid,thread_previous)
                    if cpu_samples or now-start>=interval:
                        cpu_samples.append(dict(wall_seconds=now-start,threads=len(threads),
                                                busy_threads=sum(x[3]>.1 for x in threads),cpu_cores=sum(x[3] for x in threads)))
                    with Path('thread_usage.tsv').open('a') as usage:
                        for tid,state,ticks,busy in threads:
                            usage.write('{:.3f}\t{}\t{}\t{}\t{:.5f}\n'.format(now-start,tid,state,ticks,busy))
                next_report = now + interval
            time.sleep(0.2)
    rc = process.wait()
    reader.join(timeout=10)
    if requested:
        rc = 128 + requested[0]
    elif rc < 0:
        rc = 128 - rc
    if reader.is_alive() and rc == 0:
        rc = 2
    if not reader.is_alive():
        process.stdout.close()
    Path('simulator_exit.txt').write_text(str(rc) + '\n')
    Path('performance.json').write_text(json.dumps(dict(wall_seconds=time.monotonic()-start,
        requested_fgp_threads=os.environ.get('VCS_FGP_THREADS'),parallel=os.environ.get('PARALLEL'),
        mean_observed_cpu_cores=sum(x['cpu_cores'] for x in cpu_samples)/len(cpu_samples) if cpu_samples else None,
        max_busy_threads=max(x['busy_threads'] for x in cpu_samples) if cpu_samples else None,
        note='Linux thread accounting for simv PID only; requested thread count is not achieved speedup.'),indent=2)+'\n')
    return rc


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('Usage: run_simulator.py executable [arguments...]')
    sys.exit(run(sys.argv[1:]))
