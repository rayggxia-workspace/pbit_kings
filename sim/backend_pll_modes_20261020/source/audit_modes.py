"""Fail closed on missing modes/serial evidence; retain reset transients."""
import csv
import io
import json
from pathlib import Path
import re
from collections import Counter
from coverage_evidence import bind,runtime_errors
from sync_policy import ALLOWED
from plan import RELEASE,PLANS,MODES,ERROR_CHECKS,PROBES


def rows(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def windows(text):
    result=[];start=None
    for r in csv.DictReader(io.StringIO(text)):
        if r['signal']!='core_rst_n':continue
        t=float(r['ns']);v=r['value'].lower()
        if 'x' in v or 'z' in v:
            if start is not None:result.append((start,t));start=None
        elif int(v,16)==0 and start is None:start=t
        elif int(v,16)==1 and start is not None:result.append((start,t));start=None
    if start is not None:raise ValueError('Core still in reset at end of test')
    return result


def timing(text,intervals):
    result=[]
    for block in re.split(r'(?m)^.*Timing violation in ',text)[1:]:
        lines=block.splitlines();scope=lines[0].strip()
        call=next((l for l in lines[1:8] if re.search(r'\$\w+\(',l)),None)
        if call is None:raise ValueError('Unparseable timing event '+scope)
        check=re.search(r'\$(\w+)\(',call).group(1)
        times=[int(v)*.01 for v in re.findall(r':\s*(\d+)',call)]
        if len(times) not in (1,2):raise ValueError('Unparseable timing stamps '+call)
        inside=any(a<=min(times) and max(times)<b for a,b in intervals)
        result.append(dict(instance=scope,check=check,pin_event_ns=times,
            reset_window=inside,existing_first_stage_profile=ALLOWED.get(scope)==check,raw=call.strip()))
    return result


def injection_evidence(trace,events):
    transitions=[];pins=[]
    for r in csv.DictReader(io.StringIO(trace)):
        if r['signal'] in ('fast_active','fast_addr'):
            transitions.append(float(r['ns']))
        if r['signal'].startswith('addr3_'):
            pins.append(r)
    details=[]
    for e in events:
        if e['reset_window'] or e['existing_first_stage_profile']:continue
        item=dict(e)
        item['nearest_bus_transition_ns']=min((abs(t-s) for t in e['pin_event_ns'] for s in transitions),default=None)
        item['address_feedback_candidate']=('req_addr_ff_q_o_reg_3_' in e['instance'] and e['check']=='setuphold')
        details.append(item)
    return dict(outside_details=details,address_pin_trace_rows=len(pins))


def partial(root,case,error):
    root=Path(root)
    text=(root/'simulation.log').read_text(errors='replace') if (root/'simulation.log').exists() else ''
    trace=(root/'mode_trace.csv').read_text() if (root/'mode_trace.csv').exists() else ''
    fail=[str(error)]
    try:intervals=windows(trace)
    except ValueError as ex:intervals=[];fail.append(str(ex))
    try:events=timing(text,intervals)
    except ValueError as ex:events=[];fail.append(str(ex))
    report=dict(case=case,status='DIAGNOSTIC_EXECUTION_FAILED',functional_evidence_complete=False,
        failures=fail,raw_timing_events=len(events),timing_events=events,
        fatal_messages=re.findall(r'(?m)^.*(?:Fatal:|CLOCK_GUARD_|BYPASS_REFERENCE_|Full snapshot X).*$',text),
        timing_signoff=False)
    report.update(injection_evidence(trace,events))
    (root/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def audit(root,case,selected_corner,build):
    root=Path(root);fail=[]
    result=json.loads((root/'mode_result.json').read_text())
    epochs=rows(root/'epochs.jsonl');tx=rows(root/'transactions.jsonl');checks=rows(root/'checks.jsonl')
    trace=(root/'mode_trace.csv').read_text();text=(root/'simulation.log').read_text(errors='replace')
    expected=PLANS[case]
    probe=case in PROBES
    for key,value in dict(release=RELEASE,case=case,corner=selected_corner,status='FUNCTIONAL_PASS',
                          epochs=len(expected),power_estimated=False,timing_signoff=False).items():
        if result.get(key)!=value:fail.append('Bad result '+key)
    if len(epochs)!=len(expected):fail.append('Missing mode epochs')
    for i,((name,f),row) in enumerate(zip(expected,epochs),1):
        fields=dict(epoch=i,name=name,mhz=f,config=MODES[f],core_baud=f*1000000//500,
                    tiny_problem='none' if probe else 'two_node_maxcut',snapshot_mask=0 if probe else 17,
                    snapshot_expected=0 if probe else 1,sweeps=0 if probe else 2,actual_majority=1,
                    snapshot_words_checked=0 if probe else 100,
                    core_pin_transactions=0 if probe else 2,pll_pin_transactions=0 if case=='errors' and i==2 else 5)
        if any(row.get(k)!=v for k,v in fields.items()):fail.append('Mode scope mismatch '+name)
        for prefix,half in (('core',500.0/f),('test',500.0/9.375)):
            low=row.get(prefix+'_half_min_ns',-1);high=row.get(prefix+'_half_max_ns',-1)
            if not half*.9<=low<=high<=half*1.1:fail.append('Bad clock pulse '+name+' '+prefix)
        if row.get('core_edges',0)<20 or row.get('test_edges',0)<4:fail.append('Insufficient clock samples '+name)
        if row.get('enable_to_release_ns',0)<14920:fail.append('Startup wait too short '+name)
        if i>1 and row.get('reset_before_disable_ns',0)<100:fail.append('Missing reset hold '+name)
        names=[c['name'] for c in checks if c['epoch']==i]
        required=(('startup_without_bus_override' if case=='pin_only' else 'startup_and_core_configuration_reset',
                   'bus_probe_complete') if probe else
                  ('startup_and_core_configuration_reset','dynamic_baud_pin_uart_read_write',
                   'tiny_maxcut_run_and_snapshot','mode_epoch_complete'))
        for item in required:
            if names.count(item)!=1:fail.append('Missing/duplicate mode check '+name+' '+item)
    metrics=rows(root/'clock_metrics.jsonl')
    if len(metrics)!=2*len(expected):fail.append('Missing clock metrics')
    for i,(_,f) in enumerate(expected,1):
        for signal,half in (('core',500.0/f),('test',500.0/9.375)):
            found=[r for r in metrics if r.get('epoch')==i and r.get('signal')==signal]
            if len(found)!=1:fail.append('Missing/duplicate clock metric');continue
            r=found[0]
            if not 2*half-.04<=r.get('period_min_ns',-1)<=r.get('period_max_ns',-1)<=2*half+.04:
                fail.append('Bad full clock period')
            for part in ('high','low'):
                if not half*.9<=r.get(part+'_min_ns',-1)<=r.get(part+'_max_ns',-1)<=half*1.1:
                    fail.append('Bad clock duty/pulse')
            if r.get('periods',0)<2:fail.append('Insufficient complete periods')
            if signal=='core' and f==25 and not 0<=r.get('bypass_lag_min_ns',-1)<=r.get('bypass_lag_max_ns',-1)<=2:
                fail.append('Bypass not tracking reference clock')
    if case=='errors':
        count=Counter(c['name'] for c in checks)
        if any(count[x]!=1 for x in ERROR_CHECKS):fail.append('Missing/duplicate directed error coverage')
    if result.get('checks')!=len(checks):fail.append('Check count mismatch')
    counts=Counter(t['transport'] for t in tx)
    for field,transport in (('pll_pin_transactions','PLL_PIN_UART'),('core_pin_transactions','CORE_PIN_UART'),
                             ('pll_directed_transactions','PLL_REQUEST_BOUNDARY')):
        if result.get(field)!=counts[transport]:fail.append('Transport count mismatch '+transport)
    if counts['PLL_PIN_UART']!=5*len(expected)+(3-5 if case=='errors' else 0):fail.append('PLL pin UART coverage count')
    if counts['CORE_PIN_UART']!=(0 if probe else 2*len(expected)+(2 if case=='errors' else 0)):fail.append('Core pin UART coverage count')
    if case=='errors':
        directed=[t for t in tx if t['transport']=='PLL_REQUEST_BOUNDARY']
        early=[t for t in directed if t['epoch']==1]
        expected_early=[]
        for cfg,error in ((0xf218,2),(0x0200,3),(0x0018,4)):
            expected_early += [(1,0,cfg,0,0),(1,2,1,2,0),(0,4,0,0,0x76|(error<<8)),
                              (0,6,0,0,0x218),(1,2,2,0,0),(0,4,0,0,0x72)]
        def fields(t):return tuple(t.get(k) for k in ('write','address','data','status','response'))
        if [fields(t) for t in early]!=expected_early:fail.append('Invalid-config directed evidence mismatch')
        late=[t for t in directed if t['epoch']==2]
        prefix=[(1,0,0x418,0,0),(1,2,1,0,0),(1,0,0x218,3,0),
                (1,2,1,3,0),(0,0,0,0,0x418),(1,2,2,0,0)]
        if [fields(t) for t in late[:6]]!=prefix or len(late)<9:fail.append('BUSY rejection evidence mismatch')
        elif (late[6].get('write')!=0 or late[6].get('address')!=4 or
              not late[6].get('response',0)&1 or late[6].get('response',0)&0xf04 or
              fields(late[-1])!=(0,6,0,0,0x418) or fields(late[-2])!=(0,4,0,0,0x72)):
            fail.append('BUSY clear/startup evidence mismatch')
    elif counts['PLL_REQUEST_BOUNDARY']:fail.append('Unexpected PLL request-boundary override')
    for t in tx:
        n=t.get('epoch',0)
        if not 1<=n<=len(expected):fail.append('Invalid transaction epoch');continue
        f=expected[n-1][1]
        if t['transport']=='CORE_PIN_UART':
            base=500000.0/f;ratio=t.get('bit_ns',0)/base
            allowed=(.99,1,1.01) if case=='errors' and n==1 else (1,)
            if not any(abs(ratio-x)<1e-6 for x in allowed):fail.append('Wrong dynamic UART bit period')
            if t.get('mhz')!=f or t.get('address')!=4 or t.get('response')!=(0 if t.get('write') else 1):
                fail.append('Wrong core UART response/scope')
        elif t['transport']=='PLL_PIN_UART':
            request=int(t['request'],16);response=int(t['response'],16)
            op=request>>24;addr=(request>>16)&255;data=request&65535
            error=case=='errors' and request==0x01020008
            exp=((2 if error else 0)<<24)|(addr<<16)
            if op==2:
                exp|={0:MODES[f],4:(0x0576 if case=='errors' and n==1 else (0x7a if f==25 else 0x72)),6:MODES[f]}.get(addr,0)
                # Normal startup STATUS precedes the intentional error; both are legitimate and ordered below.
                if addr==4 and case=='errors' and n==1:
                    if response not in (0x00040072,0x00040576):fail.append('Bad PLL STATUS reply')
                    exp=response
            if response!=exp or t.get('bit_ns')!=1000:fail.append('Bad PLL pin UART frame')
    # Match complete normal serial mode sequences, not merely a total transaction count.
    for i,(_,f) in enumerate(expected,1):
        pin=[t for t in tx if t['transport']=='PLL_PIN_UART' and t['epoch']==i]
        if case=='errors' and i==2:
            if pin:fail.append('Directed epoch mislabeled serial')
            continue
        cfg=MODES[f];rdy=0x7a if f==25 else 0x72
        sequence=[(0x01000000|cfg,0),(0x02000000,cfg),(0x01020001,0x00020000),
                  (0x02040000,0x00040000|rdy),(0x02060000,0x00060000|cfg)]
        if case=='errors':sequence += [(0x01020008,0x02020000),(0x02040000,0x00040576),(0x01020002,0x00020000)]
        if [(int(t['request'],16),int(t['response'],16)) for t in pin]!=sequence:fail.append('PLL serial sequence mismatch')
    if (root/'simulator_exit.txt').read_text().strip()!='0':fail.append('Simulator exit')
    if re.search(r'(?mi)^\s*(?:Fatal:|FATAL:|Error-|Error:)|timing checks disabled|\+notimingcheck|\+no_notifier',text):fail.append('Simulator error/disabled checks')
    for marker in ('[PLL_MODES_FUNCTIONAL] PASS','[POSTLAYOUT_SDF_RETURNED]','[SYNC_HEALTH] PASS',
                   '[SYNC_PROFILE] ACTIVE time=0 first_stage_notifiers=2'):
        if marker not in text:fail.append('Missing marker '+marker)
    functional_ok=not fail
    intervals=windows(trace)
    if len(intervals)!=len(expected):fail.append('Missing reset episodes')
    events=timing(text,intervals)
    unexpected=[e for e in events if not e['existing_first_stage_profile']]
    outside=[e for e in unexpected if not e['reset_window']]
    if outside:fail.append('Timing events outside definite reset windows')
    pulses=[];previous={}
    first_release=intervals[0][1] if intervals else float('inf')
    for r in csv.DictReader(io.StringIO(trace)):
        signal=r['signal']
        if signal not in ('core_clk','cktst'):continue
        now=float(r['ns']);v=r['value'].lower()
        if 'x' in v or 'z' in v:
            if now>=first_release and not any(a<=now<b for a,b in intervals):fail.append('Unknown clock outside reset')
            previous.pop(signal,None);continue
        if signal in previous:
            old=previous[signal];width=now-old
            if now>=first_release and 0<=width<1:
                inside=any(a<=old and now<b for a,b in intervals)
                pulses.append(dict(signal=signal,start_ns=old,end_ns=now,width_ns=round(width,3),reset_window=inside))
                if not inside:fail.append('Short clock pulse outside reset')
        previous[signal]=now
    warnings=re.findall(r'(?m)^Warning-\[[^\]]+\][^\n]*',text)
    rejected=runtime_errors(root,text)
    if rejected:fail.append('SDF binding errors')
    proof=bind(build,root)
    status='FAILURES_NEED_ACTION' if fail else ('FUNCTIONAL_PASS_REVIEW_REQUIRED' if unexpected or warnings else 'FUNCTIONAL_PASS_NOT_SIGNOFF')
    report=dict(status=status,case=case,corner=selected_corner,functional_evidence_complete=functional_ok,
        failures=fail,result=result,epochs=epochs,transport_counts=dict(counts),timing_events=events,
        raw_timing_events=len(events),reset_window_events=sum(e['reset_window'] for e in unexpected),
        outside_reset_events=len(outside),existing_profile_events=len(events)-len(unexpected),
        model_and_runtime_warnings=warnings,short_clock_pulses=pulses,reset_windows_ns=intervals,sdf_coverage=proof,
        clock_metrics=metrics,probe_only=probe,timing_signoff=False,analog_lock_verified=False,full_uart_end_to_end=False,
        clock_policy='Period +/-40ps; high/low +/-10%; bypass reference lag 0..2ns. Diagnostic limits, not foundry WIDTH signoff.')
    report.update(injection_evidence(trace,events))
    details=report['outside_details']
    report['negative_control_reproduced']=(case=='bus_legacy' and functional_ok and bool(details) and
        fail==['Timing events outside definite reset windows'] and all(
        d['address_feedback_candidate'] and d['nearest_bus_transition_ns'] is not None and
        d['nearest_bus_transition_ns']<=2 for d in details))
    (root/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
