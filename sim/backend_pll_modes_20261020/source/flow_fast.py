"""Bounded fast-bus GLS and independently resumable PT power stages, Python 3.6."""
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from check_inputs import sha256
import workflow

ROOT=Path.cwd()
SOURCE=ROOT/'source'

def stage(name):
    Path('stage.txt').write_text(name+'\n')
    with Path('stage_times.tsv').open('a') as f: f.write('{}\t{}\n'.format(int(time.time()),name))
    print('STAGE={} TIME={}'.format(name,time.strftime('%Y-%m-%dT%H:%M:%S')),flush=True)

def command(args,cwd,log,timeout=None):
    args=[str(x) for x in args]; cwd=Path(cwd)
    (cwd/(log+'.command.json')).write_text(json.dumps(args,indent=2)+'\n')
    with (cwd/log).open('w') as out:
        rc=subprocess.call(args,cwd=str(cwd),stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
    if rc: raise RuntimeError('Exit {}: {}'.format(rc,cwd/log))
    # EDA tools can return zero after a command error; markers are checked too.

def parallel_flags(runtime=False):
    if os.environ['PARALLEL']=='serial': return []
    workers=int(os.environ['VCS_FGP_THREADS']); cpus=int(os.environ.get('SLURM_CPUS_PER_TASK',os.environ.get('CPUS','8')))
    if workers<1 or workers+1>cpus: raise ValueError('Invalid FGP CPU allocation')
    return ['-fgp=num_threads:{}'.format(workers)] if runtime else ['-fgp','-j{}'.format(cpus)]

def probe():
    stage('fgp_capability_probe')
    p=ROOT/'fgp_probe'; p.mkdir(exist_ok=True)
    command([os.environ.get('VCS_BIN','vcs'),'-full64','-sverilog',SOURCE/'fgp_probe.sv','-top','fgp_probe','-o','simv']+parallel_flags(),p,'compile.log',timeout=300)
    command(['./simv']+parallel_flags(True),p,'simulation.log',timeout=120)
    logs=(p/'compile.log').read_text(errors='replace')+(p/'simulation.log').read_text(errors='replace')
    if 'FGP_PROBE_PASS' not in logs or re.search(r'(?i)(unknown|unrecognized|ignored|unsupported).{0,100}fgp|fgp.{0,100}(not supported|unsupported|license.{0,40}(fail|denied))',logs):
        raise ValueError('FGP capability/license check did not pass; see fgp_probe logs. No silent serial fallback.')
    Path('FGP_PROBE_PASS.txt').write_text('parallel={} requested_threads={}\nActual utilization is measured separately.\n'.format(os.environ['PARALLEL'],os.environ['VCS_FGP_THREADS']))

def identity():
    return dict(checkpoint=json.loads(Path('checkpoint.json').read_text()),
                source={p.name:sha256(p) for p in SOURCE.iterdir() if p.is_file() and p.suffix in ('.py','.sv','.svh','.tcl')},
                precision=os.environ['PRECISION'],parallel=os.environ['PARALLEL'],fgp_threads=os.environ['VCS_FGP_THREADS'],
                diag_debug=os.environ.get('DIAG_DEBUG','minimal'),sdf_corner=os.environ.get('CORNER','WC'),
                settings_sha256=sha256('settings.svh'),sdf_setup_sha256=sha256('mode_sdf.svh'))

def inputs():
    stage('input_checks')
    parent=os.environ.get('CHECK_JOB','')
    fresh=parent=='fresh'
    if fresh: parent=''
    if not parent and not fresh:
        candidate=Path(os.environ['FAST_ROOT']).parent/'backend_261014/results/38042230'
        if (candidate/'INPUT_CHECK_COMPLETE.txt').is_file(): parent=str(candidate)
    if parent: workflow.reuse(parent)
    else: workflow.check()
    command([sys.executable,SOURCE/'settings.py'],ROOT,'settings.log')
    command([sys.executable,SOURCE/'sync_policy.py','--netlist',os.environ['ANALYSIS_NETLIST'],'--model',os.environ['STD_MODEL']],ROOT,'sync_preflight.log')
    Path('sync_policy_mode.txt').write_text(os.environ['SYNC_POLICY']+'\n')
    command([sys.executable,SOURCE/'precision.py',os.environ['PRECISION'],os.environ['STD_MODEL'],os.environ['IO_MODEL'],os.environ['PLL_MODEL']],ROOT,'precision.log')
    # The fast adapter is tied to inspected nets, widths and the actual launch CK.
    required={'req_valid':1,'req_write':1,'req_addr':8,'req_data':16,'resp_valid':1,'resp_status':2,'resp_data':16,
              'u_pbit_top_u_uart_reg_subsystem_reg_wr_en_w':1,'u_pbit_top_u_uart_reg_subsystem_reg_rd_en_w':1,
              'u_pbit_top_u_uart_reg_subsystem_reg_addr_w':16,'u_pbit_top_u_uart_reg_subsystem_reg_wdata_w':32,
              'u_pbit_top_u_uart_reg_subsystem_reg_rdata_w':32,'u_pbit_top_u_uart_reg_subsystem_reg_access_error_w':1}
    found={}; launch=False; active=False
    with Path(os.environ['ANALYSIS_NETLIST']).open() as f:
        for line in f:
            if re.match(r'\s*module\s+pbit_io_wrapper\b',line): active=True
            if not active: continue
            m=re.fullmatch(r'\s*wire\s+(?:\[(\d+):(\d+)\]\s+)?(\w+)\s*;\s*',line)
            if m and m.group(3) in required: found[m.group(3)]=int(m.group(1))-int(m.group(2))+1 if m.group(1) else 1
            if re.search(r'\bDFFRNQX0P5_9TSVT\s+u_pbit_top_u_uart_reg_subsystem_u_pbit_uart_reg_master_req_wr_en_ff_q_o_reg_0_\s*\(',line): launch=True
            if line.strip()=='endmodule': break
    if found!=required or not launch: raise ValueError('Fast bus netlist interface differs from reviewed 261014 adapter')
    manifest=json.loads(Path('inputs.json').read_text())
    manifest.update(transport='REGISTER_BUS_INJECTION',pll_transport='PLL_REGISTER_BUS_INJECTION',
                    force_scope='UART request-boundary nets held inactive during compute; first-stage notifier profile; PLL supply hookups. No array/register state or clock forced.',
                    full_uart_end_to_end=False,bus_stimulus_source_delay_ns=0.30,
                    bus_stimulus_clock='UART master write-enable register CK',
                    parallel=os.environ['PARALLEL'],fgp_requested_threads=int(os.environ['VCS_FGP_THREADS']))
    count=int(os.environ['SCALE_CELLS'])
    if count not in (1,4,16,64,100,400): raise ValueError('Unsupported scale')
    manifest.update(problem='replicated_clamped_K44_scale',configured_cells=count,
                    configured_nodes=8*count,free_nodes=4*count,configured_edges=16*count,
                    sweeps=200,majority=1,scale_side=int(count**0.5),
                    dense_array_power_representative=False,
                    unconfigured_nodes_assumed_inactive=False,
                    seed_policy='Same four reviewed nonzero seeds in every selected unit')
    if os.environ.get('FLOW_STAGE')=='config_smoke':
        manifest.update(problem='configuration_smoke_only',configured_nodes=1,free_nodes=0,
                        configured_edges=1,configured_seeds=1,sweeps=0,
                        power_window=False,compute_verified=False)
    Path('inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')

def bind_sdf():
    source=Path(os.environ['SDF_'+os.environ.get('CORNER','WC')]).resolve()
    with source.open('rb') as handle:
        if not handle.read(1): raise ValueError('Empty SDF file '+str(source))
    local=Path('simulation.sdf')
    if local.exists() or local.is_symlink():
        if not local.exists() or not os.path.samefile(str(source),str(local)):
            raise ValueError('Refuse mismatched simulation.sdf binding')
    else: workflow.link(source,local)


def build():
    stage('vcs_build')
    # VCS 2018 processes this literal $sdf_annotate during compilation.
    bind_sdf()
    parent=os.environ.get('BUILD_JOB','')
    if parent:
        parent=Path(parent).resolve()
        stamp=json.loads((parent/'BUILD_COMPLETE.json').read_text())
        if stamp!=identity(): raise ValueError('Build checkpoint source/config/library mismatch')
        for name in ('simv','simv.daidir'): workflow.link(parent/name,name)
        workflow.link(parent/'compile.log','compile.log')
        workflow.link(parent/'sdf_annotation.log','sdf_annotation.log')
    else:
        args=[os.environ.get('VCS_BIN','vcs'),'-full64','-sverilog','-timescale=1ns/'+os.environ['PRECISION'],
              '-diag=sdf:verbose','+sdfverbose','+allmtm','+neg_tchk','-negdelay','+delay_mode_path','+incdir+.', '+incdir+source',
              '-v','models/std.v','-v','models/io.v','models/pll.v',os.environ['ANALYSIS_NETLIST'],
              'source/uart_host.sv','source/gate_pipeline_env.sv','source/tb_gate_pipeline_maxcut_lite.sv',
              '-top','tb_gate_pipeline_maxcut_lite','-o','simv','-l','compile.log']+parallel_flags()
        if os.environ.get('DIAG_DEBUG','minimal')=='all': args.append('-debug_access+all')
        command(args,ROOT,'compile_console.log')
        if not Path('simv').is_file() or re.search(r'(?m)^Error-',Path('compile.log').read_text(errors='replace')):
            raise ValueError('VCS compile incomplete')
    command([sys.executable,SOURCE/'annotation_check.py'],ROOT,'build_annotation_check.log')
    Path('BUILD_COMPLETE.json').write_text(json.dumps(identity(),indent=2,sort_keys=True)+'\n')

def simulate(case):
    stage('simulate_'+case)
    bind_sdf()
    Path('simulation_corner.txt').write_text('WC\n')
    args=['./simv','+maxdelays','+sdfverbose','+SDF_CORNER=WC','+CASE='+case,
          '+SCALE_CELLS='+os.environ['SCALE_CELLS']]+parallel_flags(True)
    if os.environ['SYNC_POLICY']=='profile': args+=['+SYNC_NOTIFIER_PROFILE']
    Path('simulation_command.txt').write_text(json.dumps(args,indent=2)+'\n')
    Path('test_case.txt').write_text(case+'\n')
    command([sys.executable,'-u',SOURCE/'run_simulator.py']+args,ROOT,'simulation_console.log')
    command([sys.executable,SOURCE/'annotation_check.py'],ROOT,'annotation_check.log')
    command([sys.executable,SOURCE/'fast_audit.py'],ROOT,'fast_audit.log')
    if case=='power':
        result=json.loads(Path('scale_result.json').read_text())
        count=int(os.environ['SCALE_CELLS'])
        expected=dict(status='PASS',configured_cells=count,configured_nodes=8*count,
                      free_nodes=4*count,configured_edges=16*count,sweeps=200,majority=1,
                      score=16*count,target=16*count,snapshot_bits=3200)
        if any(result.get(k)!=v for k,v in expected.items()):
            raise ValueError('Scale test result/metadata mismatch')
        command([sys.executable,SOURCE/'window.py'],ROOT,'waveform_check.log')
        workflow_hash=sha256('active_window.vcd')
        Path('waveform_seal.json').write_text(json.dumps(dict(sha256=workflow_hash))+'\n')
        Path('SIMULATION_COMPLETE.txt').write_text('Fast register-bus K44 + full snapshot functional PASS. Not full UART or timing signoff.\n')
    elif case=='config':
        Path('CONFIG_SMOKE_COMPLETE.txt').write_text('SDF + real PLL startup + register-bus node/seed/edge configuration readback PASS. No compute, snapshot, pin UART or power claim.\n')
    else: Path('UART_SMOKE_COMPLETE.txt').write_text('Two pin UART transactions cross-checked against register bus; PLL UART not tested.\n')

def prepare():
    stage('pt_prepare')
    Path('pt_prepare').mkdir(exist_ok=True)
    command([os.environ.get('PT_BIN','pt_shell'),'-f',SOURCE/'prepare.tcl'],ROOT/'pt_prepare','pt.log')
    if not Path('pt_prepare/PREPARE_COMPLETE.txt').is_file(): raise ValueError('PT preparation incomplete; see RC/timing reports')

def power():
    stage('pt_power')
    sim=os.environ.get('SIM_JOB',''); prep=os.environ.get('PREPARE_JOB','')
    if sim:
        sim=Path(sim).resolve()
        workflow.same(json.loads(Path('checkpoint.json').read_text()),json.loads((sim/'checkpoint.json').read_text()))
        if not (sim/'SIMULATION_COMPLETE.txt').is_file(): raise ValueError('No passed simulation checkpoint')
        if (sim/'test_case.txt').read_text().strip()!='power': raise ValueError('UART smoke is not a power waveform')
        if sha256(sim/'active_window.vcd')!=json.loads((sim/'waveform_seal.json').read_text())['sha256']: raise ValueError('Waveform changed')
        workflow.link(sim/'active_window.vcd','active_window.vcd')
        for name in ('window.json','waveform_check.json','audit.json','annotation_gate.json'):
            shutil.copyfile(str(sim/name),name)
    elif not Path('SIMULATION_COMPLETE.txt').is_file(): raise ValueError('Missing simulation result')
    if prep:
        prep=Path(prep).resolve()
        workflow.same(json.loads(Path('checkpoint.json').read_text()),json.loads((prep/'checkpoint.json').read_text()))
        if not (prep/'pt_prepare/PREPARE_COMPLETE.txt').is_file(): raise ValueError('Cannot reuse failed PT preparation (including job 38042231)')
        os.environ['PREPARED_SESSION']=str(prep/'pt_prepare/prepared_session')
    else: os.environ['PREPARED_SESSION']=str(ROOT/'pt_prepare/prepared_session')
    Path('pt_power').mkdir(exist_ok=True)
    command([os.environ.get('PT_BIN','pt_shell'),'-f',SOURCE/'power.tcl'],ROOT/'pt_power','pt.log')
    command([sys.executable,SOURCE/'summarize.py'],ROOT,'summary.log')

def main(mode):
    if mode in ('probe','build','config_smoke','power_sim','uart','all'): probe()
    if mode=='probe': return
    inputs()
    if mode in ('build','config_smoke','power_sim','uart','all'): build()
    if mode in ('config_smoke','power_sim','uart','all'):
        simulate('config' if mode=='config_smoke' else ('uart' if mode=='uart' else 'power'))
    if mode in ('prepare','all'): prepare()
    if mode in ('power','all'): power()

if __name__=='__main__':
    try:
        main(sys.argv[1]); Path('STAGE_COMPLETE.txt').write_text(sys.argv[1]+'\n'); stage('complete_'+sys.argv[1])
    except Exception as error:
        import traceback
        Path('failure.txt').write_text(str(error)+'\n'+traceback.format_exc())
        raise
