"""Version-bound checkpoints. Old revision waivers and binaries are never reused."""
import json
import os
from pathlib import Path
import shutil
import sys
from check_inputs import inspect, sha256
from input_audit import sdf_check, spef_check
import gzip

KEYS=('NETLIST','SDF_WC','SDF_BC','SPEF','SPEF_BC','STD_MODEL','IO_MODEL','PLL_MODEL','STD_DB','IO_DB','PLL_DB')
CONFIG=('CORE_MHZ','MAJORITY','UART_DIVISOR','PRECISION','SYNC_POLICY',
        'INPUT_SLEW_NS','PLL_SLEW_NS','OUTPUT_LOAD_PF')

def fingerprint():
    return dict(files={key:dict(path=str(Path(os.environ[key]).resolve()),sha256=sha256(os.environ[key])) for key in KEYS},
                config={key:os.environ[key] for key in CONFIG})

def same(a,b):
    if a['config'] != b['config'] or {k:v['sha256'] for k,v in a['files'].items()} != {k:v['sha256'] for k,v in b['files'].items()}:
        raise ValueError('Checkpoint differs in input/library hashes or precision/settings')

def link(src,dst):
    src=Path(src).resolve(); dst=Path(dst)
    if not src.exists(): raise ValueError('Missing checkpoint artifact '+str(src))
    if dst.exists() or dst.is_symlink(): raise ValueError('Refuse to overwrite '+str(dst))
    dst.symlink_to(src, target_is_directory=src.is_dir())

def check():
    fp=fingerprint()
    if fp['files']['NETLIST']['sha256']!='fa0f086141ef60616671ca0a061d487bef8a6997620db5d3313d24ba461fde98':
        raise ValueError('Not the locally reviewed 261014 PT netlist; stop before mixing revisions')
    leaves, removed, refs=inspect(os.environ['NETLIST'],Path('analysis.vg'))
    report=dict(netlist_sha256=fp['files']['NETLIST']['sha256'],leaf_instances=len(leaves),removed_zero_port_physical=removed,
                status='NAME_PRECHECK_PASS',spef_checks=[],sdf_checks={})
    for corner in ('WC','BC'):
        with open(os.environ['SDF_'+corner],'rb') as stream:
            report['sdf_checks'][corner]=sdf_check(stream,leaves,corner)
        with gzip.open(os.environ['SPEF' if corner=='WC' else 'SPEF_BC'],'rb') as stream:
            report['spef_checks'].append(spef_check(stream,leaves,corner))
    if any(x['status']!='PASS' for x in list(report['sdf_checks'].values())+report['spef_checks']):
        report['status']='FAIL'
    Path('input_check.json').write_text(json.dumps(report,indent=2)+'\n')
    if report['status']=='FAIL': raise ValueError('Input names/cell types do not match')
    fp['analysis_sha256']=sha256('analysis.vg')
    Path('checkpoint.json').write_text(json.dumps(fp,indent=2)+'\n')
    Path('INPUT_CHECK_COMPLETE.txt').write_text('Name/cell precheck only; VCS and PT coverage still required.\n')

def reuse(parent):
    parent=Path(parent)
    old=json.loads((parent/'checkpoint.json').read_text())
    same(old,fingerprint())
    if sha256(parent/'analysis.vg')!=old['analysis_sha256']: raise ValueError('Derived netlist changed')
    link(parent/'analysis.vg','analysis.vg')
    shutil.copy2(str(parent/'input_check.json'),'input_check.json')
    shutil.copy2(str(parent/'checkpoint.json'),'checkpoint.json')
    shutil.copy2(str(parent/'INPUT_CHECK_COMPLETE.txt'),'INPUT_CHECK_COMPLETE.txt')

def build_stamp():
    files=list(Path('source').glob('*.sv'))+list(Path('models').glob('*.v'))+[Path('settings.svh'),Path('sync_profile.svh')]
    stamp={str(p):sha256(p) for p in files}
    if os.environ.get('VCS_FGP_THREADS'):
        stamp['vcs_fgp_threads']=os.environ['VCS_FGP_THREADS']
    return stamp

def reuse_build(parent,corner):
    parent=Path(parent)
    same(json.loads(Path('checkpoint.json').read_text()),json.loads((parent/'checkpoint.json').read_text()))
    build=parent/corner
    if not (build/'ANNOTATION_COMPLETE.txt').exists(): raise ValueError('Missing annotation checkpoint')
    old=json.loads((build/'build_stamp.json').read_text())
    if old!=build_stamp(): raise ValueError('Testbench/model/settings changed; run annotate again')
    for name in ('simv','simv.daidir'):
        link(build/name,name)
    for name in ('compile.log','sdf_annotation.log'):
        shutil.copy2(str(build/name),name)

def power_reuse(sim,prep):
    current=json.loads(Path('checkpoint.json').read_text())
    for parent in (Path(sim),Path(prep)):
        same(current,json.loads((parent/'checkpoint.json').read_text()))
    sim=Path(sim); prep=Path(prep)
    if not (sim/'SIMULATION_COMPLETE.txt').exists() or not (prep/'pt_prepare/PREPARE_COMPLETE.txt').exists():
        raise ValueError('Missing successful simulation/PT checkpoint')
    if (sim/'simulation_corner.txt').read_text().strip()!='WC': raise ValueError('WC power requires WC waveform')
    for name in ('active_window.vcd',): link(sim/name,name)
    for name in ('window.json','waveform_check.json','audit.json','annotation_gate.json'):
        shutil.copy2(str(sim/name),name)
    # Verify waveform has not changed since the passed simulation stage.
    seal=json.loads((sim/'waveform_seal.json').read_text())
    if sha256('active_window.vcd')!=seal['sha256']: raise ValueError('Waveform checkpoint changed')
    link(prep/'pt_prepare/prepared_session','prepared_session')

if __name__=='__main__':
    mode=sys.argv[1]
    if mode=='check': check()
    elif mode=='reuse': reuse(sys.argv[2])
    elif mode=='stamp': Path(sys.argv[2]).write_text(json.dumps(build_stamp(),indent=2)+'\n')
    elif mode=='build': reuse_build(sys.argv[2],sys.argv[3])
    elif mode=='power': power_reuse(sys.argv[2],sys.argv[3])
    elif mode=='seal': Path('waveform_seal.json').write_text(json.dumps(dict(sha256=sha256('active_window.vcd')))+'\n')
    else: raise ValueError('Unknown mode')
