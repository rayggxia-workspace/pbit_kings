"""Freeze input provenance and simulation settings, without touching originals."""
import json
import os
import math
from pathlib import Path
from check_inputs import sha256
from sim_helpers import inspect_netlist
from baseline import old_baseline


def measurement_sdc(path, mhz, input_slew, output_load):
    if mhz not in (300,450,500) or not all(math.isfinite(v) and v>0 for v in (input_slew,output_load)):
        raise ValueError('Invalid measurement constraints')
    path.write_text(
        '# Measurement-only constraints; not the backend signoff SDC.\n'
        '# Root input slew and output load are assumptions (ns and pF).\n'
        'create_clock -name ref_clk -period 40 [get_ports pad_clk_i]\n'
        'create_clock -name core_clk -period %.12f [get_pins u_pll/CKOUT1]\n'
        'set_input_transition %.12g [all_inputs]\n'
        'set_load %.12g [get_ports {pad_uart_tx_o pad_pll_cfg_tx_o}]\n'
        '# No case analysis, false paths, timing waivers or forced internal clock slews.\n'
        % (1000.0/mhz,input_slew,output_load))


def main():
    mhz=int(os.environ['CORE_MHZ']); majority=int(os.environ['MAJORITY'])
    divisor=int(os.environ['UART_DIVISOR'])
    if mhz not in (300,450,500) or not 1<=majority<=32 or divisor<2:
        raise ValueError('CORE_MHZ=300/450/500; MAJORITY actual count 1..32; UART_DIVISOR>=2')
    mode=os.environ.get('SDC_MODE','backend')
    if mode not in ('backend','measurement'): raise ValueError('SDC_MODE must be resolved by submit.sh')
    assumptions={}
    if mode=='measurement':
        assumptions=dict(input_slew_ns=float(os.environ.get('INPUT_SLEW_NS','0.1')),
                         pll_root_slew_ns=float(os.environ.get('PLL_SLEW_NS','0.1')),
                         output_load_pf=float(os.environ.get('OUTPUT_LOAD_PF','0.01')))
        if not all(math.isfinite(v) and v>0 for v in assumptions.values()): raise ValueError('Invalid boundary assumptions')
        measurement_sdc(Path(os.environ['SDC']),mhz,assumptions['input_slew_ns'],assumptions['output_load_pf'])
    paths={key:Path(os.environ[key]).resolve() for key in
           ('NETLIST','ANALYSIS_NETLIST','SPEF','SDC','STD_DB','IO_DB','PLL_DB','STD_MODEL','IO_MODEL','PLL_MODEL')}
    for key,path in paths.items():
        if not path.is_file(): raise ValueError('Missing '+key+': '+str(path))
        if any(c in str(path) for c in '\n\r{}'): raise ValueError('Unsupported path: '+str(path))
    Path('pll_instance.txt').write_text(inspect_netlist(paths['ANALYSIS_NETLIST']))
    check=json.loads(Path('input_check.json').read_text())
    if check['status']!='NAME_PRECHECK_PASS': raise ValueError('Precheck failed')
    baseline=dict(id='backend_261014_DRC_SI',sha256=check['netlist_sha256'])
    if sha256(paths['NETLIST'])!=check['netlist_sha256']: raise ValueError('Netlist changed after precheck')
    header='\n'.join(check['spef_checks'][0]['header'])
    if 'OPERATING_TEMPERATURE 125' not in header:
        raise ValueError('This power experiment is fixed at SS / 1.08 V / 125 C; need 125 C SPEF')
    precision=os.environ.get('PRECISION','10ps')
    if precision not in ('1ps','10ps'): raise ValueError('PRECISION must be 1ps or 10ps')
    manifest=dict(baseline=baseline,constraint_mode=mode,boundary_assumptions=assumptions,
                  precision=precision,power_library_note='User-selected DB; default NLDM differs from vendor CCS SDF. Not a reproduced SI signoff.',
                  pll_digital_supply_model='TB connects omitted DVDD/DVDD_DRV to logic 1 and DVSS/DVSS_DRV to logic 0; always-on core; not analog power',
                  sta_signoff=False,core_mhz=mhz, majority=majority, majority_code=majority-1,uart_divisor=divisor,
                  core_voltage_v=1.08,temperature_c=125,physical_nodes=3200,
                  configured_nodes=8,free_nodes=4,sweeps=200,problem='clamped_K44_smoke',
                  paths={k:str(v) for k,v in paths.items()},
                  sha256={k:sha256(v) for k,v in paths.items()})
    Path('inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
    Path('settings.svh').write_text(
        'localparam integer CORE_MHZ={}, UART_DIVISOR={}, MAJORITY={};\n'
        "localparam logic [15:0] PLL_CFG=16'h{:04x};\n".format(mhz,divisor,majority,{300:0x218,450:0x224,500:0x228}[mhz]) +
        'localparam realtime TIME_PRECISION_NS={};\n'.format('0.01' if precision=='10ps' else '0.001'))


if __name__=='__main__': main()
