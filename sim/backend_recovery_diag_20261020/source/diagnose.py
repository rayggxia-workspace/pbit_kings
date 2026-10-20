"""Classify raw timing events; never turn reset transients into signoff PASS."""
import csv
import io
import json
from pathlib import Path
import re
from coverage_evidence import bind,runtime_errors,sha
from sync_policy import ALLOWED

OFFSETS={'phase0':0.0,'phase90':0.83,'phase180':1.67}
CHECKS=('fresh_reference_3200_bits_and_rng','busy_configuration_and_restart_rejected',
        'external_reset_and_startup_recovered','previously_affected_registers_fresh_known_write',
        'post_reset_3200_bits_and_rng_equal_reference','post_reset_core_and_test_clock_quality')


def intervals(text):
    windows=[]; start=None
    for row in csv.DictReader(io.StringIO(text)):
        if row['signal']!='core_rst_n': continue
        value=row['value'].lower()
        if 'x' in value or 'z' in value:
            if start is not None:
                windows.append((start,float(row['ns'])))
                start=None
            continue
        value=int(value,16); t=float(row['ns'])
        if value==0 and start is None: start=t
        elif value==1 and start is not None:
            windows.append((start,t));start=None
    if start is not None: windows.append((start,float('inf')))
    return windows


def timing(text,windows):
    events=[]
    blocks=re.split(r'(?m)^.*Timing violation in ',text)[1:]
    for block in blocks:
        lines=block.splitlines(); scope=lines[0].strip()
        call=next((s for s in lines[1:8] if re.search(r'\$\w+\(',s)),None)
        if call is None: raise ValueError('Unparseable timing event '+scope)
        check=re.search(r'\$(\w+)\(',call).group(1)
        stamps=[float(v)*0.01 for v in re.findall(r':\s*(\d+)',call)]
        if len(stamps)!=2: raise ValueError('Unparseable timing timestamps '+call)
        inside=any(start<=min(stamps) and max(stamps)<end for start,end in windows)
        allowed=ALLOWED.get(scope)
        reviewed=bool(allowed and check==allowed)
        events.append(dict(instance=scope,check=check,pin_event_ns=stamps,
                           definite_reset_window=inside,existing_first_stage_profile=reviewed))
    return events


def audit(root,case,build):
    root=Path(root); failures=[]
    text=(root/'simulation.log').read_text(errors='replace')
    result_path=root/'diagnostic_result.json'
    result=json.loads(result_path.read_text()) if result_path.is_file() else {}
    if not result: failures.append('Missing diagnostic_result.json')
    checks_path=root/'checks.jsonl'
    rows=[json.loads(l) for l in checks_path.read_text().splitlines() if l.strip()] if checks_path.is_file() else []
    if [r.get('name') for r in rows]!=list(CHECKS): failures.append('Missing/incorrect diagnostic assertion list')
    expected=dict(status='FUNCTIONAL_DIAGNOSTIC_PASS',release='20261020_recovery_diag_v1',case=case,
                  complete_runs=2,full_snapshots=2,snapshot_words_checked=200,
                  watched_registers=1575,refreshed_registers=1575,timing_signoff=False)
    if any(result.get(k)!=v for k,v in expected.items()): failures.append('Diagnostic result scope mismatch')
    if abs(result.get('reset_offset_ns',-999)-OFFSETS[case])>0.001: failures.append('Reset phase mismatch')
    if result.get('minimum_fresh_writes',0)<1: failures.append('Missing fresh pipeline writes')
    if not (1.5<=result.get('core_half_min_ns',0)<=result.get('core_half_max_ns',0)<=1.85):
        failures.append('Bad post-reset core clock quality')
    if not (45<=result.get('test_half_min_ns',0)<=result.get('test_half_max_ns',0)<=65):
        failures.append('Bad post-reset CKTST clock quality')
    if (root/'simulator_exit.txt').read_text().strip()!='0': failures.append('Nonzero simulator exit')
    if re.search(r'(?mi)^\s*(?:Fatal:|FATAL:|Error-|Error:)|timing checks disabled|\+notimingcheck|\+no_notifier',text):
        failures.append('Simulator fatal/error or disabled checks')
    for marker in ('[POSTLAYOUT_SDF_RETURNED]','[SYNC_HEALTH] PASS','[RECOVERY_DIAG_FUNCTIONAL] PASS',
                   '[SYNC_PROFILE] ACTIVE time=0 first_stage_notifiers=2'):
        if marker not in text: failures.append('Missing marker '+marker)
    trace_path=root/'reset_clock_trace.csv'
    windows=intervals(trace_path.read_text()) if trace_path.is_file() else []
    if len(windows)!=2 or any(end==float('inf') for _,end in windows): failures.append('Expected two completed definite reset windows')
    events=timing(text,windows)
    unexpected=[e for e in events if not e['existing_first_stage_profile']]
    reset=[e for e in unexpected if e['definite_reset_window']]
    outside=[e for e in unexpected if not e['definite_reset_window']]
    if outside: failures.append('Timing events outside definite reset windows')
    model_warnings=re.findall(r'(?m)^Warning-\[[^\]]+\][^\n]*',text)
    coverage=bind(build,root)
    rejected=runtime_errors(root,text)
    if rejected: failures.append('Rejected SDF binding messages')
    status='FAILED_VALID_OPERATION_OR_FUNCTION' if failures else (
        'RESET_TRANSIENTS_FUNCTIONALLY_CONTAINED_REVIEW_REQUIRED' if reset else
        'NO_UNEXPECTED_TIMING_IN_THIS_CASE_NOT_SIGNOFF')
    report=dict(status=status,case=case,functional_pass=not failures,failures=failures,
                result=result,raw_timing_event_count=len(events),reset_window_events=len(reset),
                outside_reset_events=len(outside),existing_profile_events=len(events)-len(unexpected),
                all_unexpected_timing_events_retained=len(unexpected),timing_signoff=False,
                chip_timing_pass=False,reset_windows_ns=windows,model_warnings=model_warnings,
                timing_events=events,sdf_coverage=coverage,
                additional_scope_note='Fresh-write checks cover 1575 previously affected flops; snapshot/RNG equality is functional evidence, not a formal proof for every future input',
                source_trace_sha256=sha(trace_path) if trace_path.is_file() else None)
    (root/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
