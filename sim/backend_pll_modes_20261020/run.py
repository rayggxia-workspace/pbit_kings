"""Immutable, one-build PLL mode suite; no timing-signoff claim."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'source'))
from plan import cases,corner,PLANS,RELEASE
from audit_modes import audit
from coverage_evidence import sha,native,bind


def save(path,value): Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')


def verify(root):
    manifest=json.loads((root/'manifest.json').read_text())
    for name,digest in manifest.items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or sha(root/p)!=digest: raise ValueError('Package SHA mismatch: '+name)
    return manifest


def command(args,folder,env):
    save(folder/'command.json',[str(x) for x in args])
    with (folder/'driver.log').open('w') as out:
        p=subprocess.Popen([str(x) for x in args],cwd=str(folder),env=env,stdout=out,stderr=subprocess.STDOUT)
        while True:
            try: rc=p.wait(timeout=30);break
            except subprocess.TimeoutExpired: print('DIAGNOSTIC_RUNNING '+str(folder),flush=True)
    (folder/'driver_exit.txt').write_text(str(rc)+'\n')
    if rc: raise RuntimeError('Exit {}: {}'.format(rc,folder/'driver.log'))


def main():
    snapshot=Path(os.environ['MODE_SNAPSHOT']).resolve(); root=Path.cwd()
    manifest=verify(snapshot); selected=cases(os.environ.get('MODE_CASES','all')); sdf_corner=corner(os.environ['CORNER'])
    save(root/'source_manifest.json',manifest)
    save(root/'run_config.json',dict(release=RELEASE,cases=selected,mode_plans={c:PLANS[c] for c in selected},
        settings_baseline_mhz=300,supported_mode_mhz=[300,150,25],precision='10ps',sdf_corner=sdf_corner,parallel='serial',
        full_uart_end_to_end=False,power_estimated=False,timing_signoff=False,
        old_passed_tests_rerun=False))
    build=root/'build'; build.mkdir()
    shutil.copytree(str(snapshot/'source'),str(build/'source'))
    save(build/'source_manifest.json',manifest)
    env=dict(os.environ,ANALYSIS_NETLIST=str(build/'analysis.vg'),SDC=str(build/'measurement.sdc'))
    (root/'stage.txt').write_text('build\n')
    command([sys.executable,'-u','source/build_driver.py'],build,env)
    native(build)
    reports=[]
    for case in selected:
        (root/'stage.txt').write_text(case+'\n')
        dst=root/'cases'/case;dst.mkdir(parents=True)
        for name in ('simv','simv.daidir','simulation.sdf'):
            source=(build/name).resolve()
            if not source.exists(): raise ValueError('Missing build artifact '+str(source))
            (dst/name).symlink_to(source,target_is_directory=source.is_dir())
        bind(build,dst)
        (dst/'sync_policy_mode.txt').write_text('profile\n')
        args=[sys.executable,'-u',snapshot/'source/run_simulator.py','./simv',
              '+maxdelays' if sdf_corner=='WC' else '+mindelays','+sdfverbose',
              '+SDF_CORNER='+sdf_corner,'+SYNC_NOTIFIER_PROFILE','+CASE='+case]
        try:
            command(args,dst,env)
            report=audit(dst,case,sdf_corner,build)
            reports.append(dict(case=case,status=report['status'],failures=report['failures'],
                timing_events=report['raw_timing_events'],reset_window_events=report['reset_window_events'],
                outside_reset_events=report['outside_reset_events'],model_warnings=report['model_and_runtime_warnings']))
        except Exception as error:
            (dst/'diagnostic_failure.txt').write_text(str(error)+'\n'+traceback.format_exc())
            reports.append(dict(case=case,status='DIAGNOSTIC_EXECUTION_FAILED',failures=[str(error)]))
        save(root/'diagnostic_progress.json',reports)
    failed=any(r['failures'] for r in reports)
    save(root/'diagnostic_summary.json',dict(status='FAILURES_NEED_ACTION' if failed else 'DIAGNOSTICS_COMPLETE_REVIEW_REQUIRED',
         cases=reports,diagnostic_complete=True,chip_timing_pass=False,timing_signoff=False,
         note='Reset-window events are retained, not blanket-waived. Backend review is still required.'))
    (root/'DIAGNOSTICS_COMPLETE.txt').write_text('PLL modes execution completed; not chip timing PASS.\n')
    (root/'stage.txt').write_text('complete\n')
    if failed: raise RuntimeError('One or more diagnostic cases failed; see diagnostic_summary.json')
    print('DIAGNOSTICS_COMPLETE_REVIEW_REQUIRED NOT_CHIP_TIMING_PASS',flush=True)


if __name__=='__main__':
    try:
        if len(sys.argv)>1 and sys.argv[1]=='verify':print('PACKAGE_OK files='+str(len(verify(Path(sys.argv[2]).resolve()))))
        elif len(sys.argv)>1 and sys.argv[1]=='validate':print('CASES_OK '+','.join(cases(sys.argv[2]))+' CORNER='+corner(sys.argv[3]))
        else: main()
    except Exception as e:
        Path('failure.txt').write_text(str(e)+'\n'+traceback.format_exc())
        raise
