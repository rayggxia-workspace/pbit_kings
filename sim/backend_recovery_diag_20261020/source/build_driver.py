"""Use audited inputs, but build only the reset diagnostic testbench."""
import json
import os
from pathlib import Path
import traceback
import flow_fast
from generate_watch import generate
from coverage_evidence import native,sha


def main():
    if (os.environ['CORE_MHZ']!='300' or os.environ['PRECISION']!='10ps' or
            os.environ['PARALLEL']!='serial' or os.environ['SYNC_POLICY']!='profile'):
        raise ValueError('Require 300 MHz, 10 ps, serial and the existing narrow profile')
    if os.environ.get('DIAG_DEBUG','minimal') not in ('minimal','all'): raise ValueError('DIAG_DEBUG=minimal|all')
    generate(Path('source'))
    flow_fast.inputs()
    p=Path('inputs.json'); data=json.loads(p.read_text())
    for key in ('seed_policy','configured_cells','configured_nodes','free_nodes','configured_edges','sweeps','majority','scale_side'):
        data.pop(key,None)
    data.update(problem='reset_recovery_phase_diagnostic',seed_policy='One shared seed lane 3 at unit (19,19), nonzero 0x13579bdf; other nodes keep reset defaults',
                observed_registers=1575,actual_majority=1,completed_run_sweeps=2,
                diagnostic_offsets_ns=[0.0,0.83,1.67],full_snapshot_bits=3200,
                power_window=False,power_estimated=False,timing_signoff=False,
                global_debug=os.environ.get('DIAG_DEBUG','minimal'),
                diagnostic_note='Raw reset-window events retained, not silently waived; no vendor model changes')
    p.write_text(json.dumps(data,indent=2)+'\n')
    flow_fast.build()
    parent=os.environ.get('BUILD_JOB','')
    if parent:
        parent=Path(parent).resolve()
        if sha(parent/'BUILD_COMPLETE.json')!=sha('BUILD_COMPLETE.json'): raise ValueError('Stale build')
        native(parent)
        Path('sdf_native_coverage.txt').write_bytes((parent/'sdf_native_coverage.txt').read_bytes())
    native(Path.cwd())
    Path('NATIVE_ANNOTATION_COMPLETE.txt').write_text('Static native coverage only; not chip timing signoff.\n')


if __name__=='__main__':
    try: main()
    except Exception as e:
        Path('failure.txt').write_text(str(e)+'\n'+traceback.format_exc())
        raise
