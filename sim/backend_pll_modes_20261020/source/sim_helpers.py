"""Check the actual new netlist interface before compiling the pin-only TB."""
from pathlib import Path
import re


def inspect_netlist(path):
    top=[]; in_top=False; collecting=False; monitors=set(); pll=[]; in_pll=False
    required={'core_clk','u_pbit_top_run_busy_w','u_pbit_top_run_done_w'}
    with Path(path).open(encoding='ascii') as f:
        for line in f:
            if re.match(r'\s*module\s+pbit_io_wrapper\s*\(',line): in_top=collecting=True
            if not in_top: continue
            if collecting:
                top.append(line)
                if ');' in line: collecting=False
            for name in required:
                if re.search(r'\bwire\s+'+name+r'\s*;',line): monitors.add(name)
            if re.match(r'\s*PLL_TOP\s+u_pll\s*\(',line): in_pll=True
            if in_pll:
                pll.append(line)
                if ');' in line: in_pll=False
            if line.strip()=='endmodule': break
    ports=set(re.findall(r'\b\w+\b',''.join(top).split('(',1)[-1].split(')',1)[0]))
    expected={'pad_clk_i','pad_rst_n_i','pad_uart_rx_i','pad_uart_tx_o',
              'pad_pll_cfg_rx_i','pad_pll_cfg_tx_o','pll_avdd','pll_avss'}
    if ports!=expected or monitors!=required or not pll:
        raise ValueError('Netlist interface/monitor/PLL names do not match this testbench')
    pll_text=''.join(pll)
    if re.search(r'\.(?:DVDD|DVSS|DVDD_DRV|DVSS_DRV)\s*\(',pll_text):
        raise ValueError('PLL digital rails already connected; review TB supply hookup instead of adding drivers')
    return pll_text
