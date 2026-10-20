"""Build one selected SDF corner; never substitute ideal/vendor models."""
import json
import os
from pathlib import Path
import traceback
import flow_fast
from plan import RELEASE,MODES,PLANS,corner
from coverage_evidence import native


def main():
    selected=corner(os.environ['CORNER'])
    if (os.environ['CORE_MHZ']!='300' or os.environ['PRECISION']!='10ps' or
        os.environ['PARALLEL']!='serial' or os.environ['SYNC_POLICY']!='profile'):
        raise ValueError('Require baseline 300 MHz / 10 ps / serial / existing narrow profile')
    flow_fast.inputs()
    p=Path('inputs.json');data=json.loads(p.read_text())
    for k in ('seed_policy','configured_cells','configured_nodes','free_nodes','configured_edges',
              'sweeps','majority','scale_side','core_voltage_v','temperature_c','core_mhz'):
        data.pop(k,None)
    data.update(release=RELEASE,problem='PLL_modes_and_tiny_maxcut',corner=selected,
        actual_majority=1,sweeps_per_completed_run=2,configured_nodes_per_run=2,settings_baseline_mhz=300,
        seed='0x13579bdf lane 0 unit (0,0)',runtime_mode_mhz=[300,150,25],
        runtime_core_baud={str(f):f*1000000//500 for f in MODES},pll_uart_baud=1000000,
        mode_plans=PLANS,full_uart_end_to_end=False,transport='MIXED_EXPLICITLY_LOGGED',
        pll_transport='PIN_UART_NORMAL_MODES; REQUEST_BOUNDARY_SHORT_BUSY_AND_INVALID_CONFIG',
        core_transport='PIN_UART_PROBES; REQUEST_BOUNDARY_TINY_PROBLEM',
        safe_handoff_clock='UART req_addr[3] physical CK; falling edge +0.30ns; acquisition and release only',
        negative_control='bus_legacy retains the old immediate acquisition/release timing',
        DB_usage='Input identity only; VCS delays from chosen SDF and generic Verilog cells. No PT run.',
        timing_corner='SS 1.08 V 125 C WC SDF' if selected=='WC' else 'FF 1.32 V -40 C BC SDF',
        power_estimated=False,timing_signoff=False,analog_lock_verified=False,
        vendor_model_behavior_modified=False)
    p.write_text(json.dumps(data,indent=2)+'\n')
    with Path('settings.svh').open('a') as f:f.write('localparam SDF_CORNER="'+selected+'";\n')
    # VCS 2018 needs compile-time SDF filename and MTM strings.
    mtm='MAXIMUM' if selected=='WC' else 'MINIMUM'
    Path('mode_sdf.svh').write_text('$sdf_annotate("simulation.sdf",env.dut,,"sdf_annotation.log","'+mtm+'");\n')
    flow_fast.build()
    parent=os.environ.get('BUILD_JOB','')
    if parent:
        parent=Path(parent).resolve();native(parent)
        Path('sdf_native_coverage.txt').write_bytes((parent/'sdf_native_coverage.txt').read_bytes())
    native(Path.cwd())
    Path('NATIVE_ANNOTATION_COMPLETE.txt').write_text('Static SDF coverage, not timing signoff.\n')


if __name__=='__main__':
    try:main()
    except Exception as error:
        Path('failure.txt').write_text(str(error)+'\n'+traceback.format_exc())
        raise
