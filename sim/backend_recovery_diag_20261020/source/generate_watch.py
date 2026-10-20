"""Generate read-only pin monitors; no DUT source or model rewriting."""
import json
from pathlib import Path
import re


def generate(folder):
    folder=Path(folder)
    data=json.loads((folder/'affected_registers.json').read_text())
    items=data['instances']
    if not items or len(set(items))!=len(items): raise ValueError('Invalid monitor inventory')
    for name in items:
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',name):
            raise ValueError('Unsafe hierarchy path')
        if not ('u_mac_' in name and ('contrib_ff' in name or 'macsum_ff' in name)):
            raise ValueError('Unexpected monitor scope')
    lines=[]
    for i,name in enumerate(items):
        p='env.dut.'+name
        lines.append('ff_recovery_watch #(.INDEX({i})) watch_{i} (.ck({p}.CK),.en({p}.E),.d({p}.D),.q({p}.Q),.rst_n(env.dut.core_rst_n),.observe(observe_after_reset),.refreshed(refreshed[{i}]),.writes(write_count[{i}]));'.format(i=i,p=p))
    (folder/'affected_watch.svh').write_text('\n'.join(lines)+'\n')
    (folder/'affected_count.svh').write_text('localparam integer WATCH_COUNT={};\n'.format(len(items)))
    return len(items)


if __name__=='__main__': print('WATCH_MONITORS='+str(generate(Path(__file__).parent)))
