"""Narrow notifier-only policy for the inspected backend synchronizers."""
import argparse
import hashlib
import json
import re
from pathlib import Path

RX1 = ('u_pbit_top_u_uart_reg_subsystem_u_pbit_uart_reg_master_'
       'u_uart_rx_8n1_rx_sync_dly1_ff_q_o_reg_0_')
RX2 = RX1.replace('dly1_', 'dly2_')
RST1 = 'u_reset_sync.rst_sync_ff_reg_0_'
RST2 = 'u_reset_sync.rst_sync_ff_reg_1_'
PREFIX = 'tb_gate_pipeline_maxcut_lite.env.dut.'
ALLOWED = {PREFIX+RX1: 'setuphold', PREFIX+RST1: 'recrem'}


def read_modules(path, wanted):
    result = {}; current = None; lines = []; digest = hashlib.sha256()
    with path.open('rb') as f:
        for raw in f:
            digest.update(raw)
            line = raw.decode('ascii')
            match = re.match(r'\s*module\s+(\w+)\b', line)
            if match:
                current = match.group(1) if match.group(1) in wanted else None
                lines = []
            if current:
                lines.append(line)
                if re.search(r'\bendmodule\b', line):
                    if current in result:
                        raise ValueError('Duplicate module '+current)
                    result[current] = ''.join(lines)
                    current = None
    if set(result) != set(wanted):
        raise ValueError('Missing modules: '+str(set(wanted)-set(result)))
    return result, digest.hexdigest()


def instances(text):
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    result = {}
    for match in re.finditer(r'^\s*(\w+)\s+(\w+)\s*\((.*?)\);', text, re.M|re.S):
        cell, name, ports = match.groups()
        if cell == 'module':
            continue
        pairs = re.findall(r'\.(\w+)\s*\(\s*([^()]+?)\s*\)', ports)
        remainder = re.sub(r'\.\w+\s*\([^()]*\)', '', ports)
        if remainder.strip(' \r\n\t,'):
            continue
        if name in result:
            raise ValueError('Duplicate instance '+name)
        result[name] = (cell, dict(pairs))
    return result


def check_chain(cells, first, second, reset_pin):
    a, b = cells[first], cells[second]
    for cell, pins in (a,b):
        if not re.fullmatch(r'DFF(?:RNQ|SNQ)X(?:0P5|1|2|4)_9TSVT', cell):
            raise ValueError('Unexpected synchronizer cell '+cell)
        if set(pins) != {'D','Q','CK',reset_pin}:
            raise ValueError('Unexpected synchronizer ports')
    # P&R may add non-inverting hold buffers between the two stages.
    drivers = {}
    for cell, pins in cells.values():
        if re.fullmatch(r'(?:BUF|DEL\d+)X\w+_9TSVT', cell) and set(pins)=={'A','Y'}:
            if pins['Y'] in drivers:
                raise ValueError('Multiple buffer drivers')
            drivers[pins['Y']] = pins['A']
    net = b[1]['D']; visited = set()
    while net != a[1]['Q']:
        if net in visited or net not in drivers:
            raise ValueError('Cannot prove first-Q to second-D synchronizer chain')
        visited.add(net); net = drivers[net]
    if a[1][reset_pin] != b[1][reset_pin]:
        raise ValueError('Different synchronizer reset branches')
    return a[0], b[0]


def notifier(body, check):
    calls = []
    for match in re.finditer(r'\$'+check+r'\s*\(', body):
        depth=1; start=match.end(); args=[]
        for i in range(start,len(body)):
            ch=body[i]
            if ch=='(': depth+=1
            elif ch==')':
                depth-=1
                if depth==0:
                    args.append(body[start:i].strip()); calls.append(args); break
            elif ch==',' and depth==1:
                args.append(body[start:i].strip()); start=i+1
        else: raise ValueError('Unclosed timing check')
    names={args[4] for args in calls if len(args)>=5}
    if not calls or len(names)!=1 or any(len(args)<5 for args in calls):
        raise ValueError('Ambiguous notifier for '+check)
    name=next(iter(names))
    if not re.fullmatch(r'\w+',name) or not re.search(r'\breg\s+'+name+r'\s*;',body):
        raise ValueError('Notifier is not a scalar reg')
    expected = ('CK','D') if check=='setuphold' else ('RN','CK')
    for args in calls:
        for arg,pin in zip(args[:2],expected):
            if not re.match(r'(?:pos|neg)edge\s+'+pin+r'\b',arg):
                raise ValueError('Unexpected timing check pins')
    return name


def prepare(netlist, model, output):
    modules, net_hash = read_modules(netlist, {'pbit_io_wrapper','reset_sync_async_assert_0'})
    top=instances(modules['pbit_io_wrapper'])
    reset=instances(modules['reset_sync_async_assert_0'])
    if top['u_reset_sync'][0]!='reset_sync_async_assert_0' or top[RX1][1]['D']!='core_uart_rx':
        raise ValueError('Unexpected asynchronous input binding')
    rcells=check_chain(reset,'rst_sync_ff_reg_0_','rst_sync_ff_reg_1_','RN')
    ucells=check_chain(top,RX1,RX2,'SN')
    if reset['Tie_LTIEHI'][0]!='TIEHIX1_9TSVT' or reset['Tie_LTIEHI'][1]['Y']!=reset['rst_sync_ff_reg_0_'][1]['D']:
        raise ValueError('Reset synchronizer first D is not tied high')
    lib, model_hash=read_modules(model,{rcells[0],ucells[0]})
    targets=[(RX1,ucells[0],'setuphold'),(RST1,rcells[0],'recrem')]
    info=[]; forces=[]
    for path,cell,check in targets:
        name=notifier(lib[cell],check)
        forces.append("        force dut.{}.{} = 1'b0;".format(path,name))
        info.append(dict(instance=PREFIX+path,cell=cell,notifier=name,allowed_check=check))
    text='''// Generated from validated backend connectivity and actual vendor models.
bit sync_profile_active=0;
bit [3:0] sync_reset_seen=0;
integer startup_file, startup_events=0;
always @(negedge dut.RX1.SN) sync_reset_seen[0]=1;
always @(negedge dut.RX2.SN) sync_reset_seen[1]=1;
always @(negedge dut.RST1.RN) sync_reset_seen[2]=1;
always @(negedge dut.RST2.RN) sync_reset_seen[3]=1;
initial begin
    if ($test$plusargs("SYNC_NOTIFIER_PROFILE")) begin
FORCES
        sync_profile_active=1;
        $display("[SYNC_PROFILE] ACTIVE time=0 first_stage_notifiers=2 NOT_TIMING_SIGNOFF");
    end
    startup_file=$fopen("startup_trace.csv","w");
    if (!startup_file) $fatal(1,"Cannot open startup_trace.csv");
    $fdisplay(startup_file,"ns,reset_seen,core_reset,rx_pad,rx1_d,rx1_q,rx2_q,reset1_q,reset2_q,core_tx");
end
always @(core_rx or core_tx or dut.core_rst_n or dut.RX1.D or dut.RX1.Q or dut.RX2.Q or dut.RST1.Q or dut.RST2.Q) begin
    if (startup_file && core_transactions==0 && startup_events<20000) begin
        $fdisplay(startup_file,"%.3f,%b,%b,%b,%b,%b,%b,%b,%b,%b",$realtime,sync_reset_seen,
            dut.core_rst_n,core_rx,dut.RX1.D,dut.RX1.Q,dut.RX2.Q,dut.RST1.Q,dut.RST2.Q,core_tx);
        $fflush(startup_file);
        startup_events++;
    end
end
task check_startup_health;
    $display("[SYNC_HEALTH] seen=%b reset=%b rx=%b/%b resetQ=%b/%b",sync_reset_seen,
        dut.core_rst_n,dut.RX1.Q,dut.RX2.Q,dut.RST1.Q,dut.RST2.Q);
    if (sync_reset_seen !== 4'b1111 ||
        {dut.core_rst_n,dut.RX1.SN,dut.RX2.SN,dut.RST1.RN,dut.RST2.RN,
         dut.RX1.Q,dut.RX2.Q,dut.RST1.Q,dut.RST2.Q} !== 9'b111111111)
        $fatal(1,"Startup synchronizer reset/idle health failed; see startup_trace.csv");
    $display("[SYNC_HEALTH] PASS");
endtask
'''.replace('FORCES','\n'.join(forces))
    for key,value in [('RX1',RX1),('RX2',RX2),('RST1',RST1),('RST2',RST2)]:
        text=text.replace(key,value)
    output.mkdir(parents=True,exist_ok=True)
    (output/'sync_profile.svh').write_text(text,encoding='ascii')
    (output/'sync_profile.json').write_text(json.dumps(dict(targets=info,
        netlist_sha256=net_hash,model_sha256=model_hash,
        policy='Notifier-only, first stages only. All SDF and checks retained; second stages untouched. Not timing/CDC signoff.'),indent=2)+'\n')


def timing_events(text, active=False):
    headers=list(re.finditer(r'Timing violation in\s+(\S+)',text))
    checks=list(re.finditer(r'\$(setuphold|setup|hold|recrem|recovery|removal|width|period|skew|timeskew|fullskew|nochange)\s*\(',text))
    events=[]; accounted=set()
    for i,h in enumerate(headers):
        end=headers[i+1].start() if i+1<len(headers) else len(text)
        local=[c for c in checks if h.end()<=c.start()<end]
        waived=(active and len(local)==1 and ALLOWED.get(h.group(1))==local[0].group(1))
        events.append(dict(instance=h.group(1),checks=[c.group(1) for c in local],waived=bool(waived)))
        accounted.update(c.start() for c in local)
    for c in checks:
        if c.start() not in accounted:
            events.append(dict(instance='UNBOUND',checks=[c.group(1)],waived=False))
    return events


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--netlist',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('.'))
    a=p.parse_args(); prepare(a.netlist,a.model,a.output)
