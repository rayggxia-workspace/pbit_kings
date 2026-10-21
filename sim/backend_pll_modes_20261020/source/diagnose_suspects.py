"""Summarize causal controls separately from functional and signoff claims."""
import json
from pathlib import Path


def summarize(root,reports,model):
    root=Path(root);by_case={r['case']:r for r in reports}
    controls=[by_case.get(c) for c in ('bus_legacy','bus_safe','pin_only')]
    if all(controls):
        legacy,safe,pins=controls
        clean=lambda r:r.get('functional_evidence_complete') and not r.get('failures')
        if legacy.get('negative_control_reproduced') and clean(safe) and clean(pins):
            verdict='INJECTION_ARTIFACT_SUPPORTED_BY_AB_CONTROLS'
        elif clean(safe) and clean(pins) and clean(legacy):verdict='NOT_REPRODUCED_IN_THIS_RUN'
        else:verdict='UNRESOLVED_REVIEW_RAW_PIN_AND_TIMING_TRACES'
    else:verdict='CONTROLS_NOT_ALL_EXECUTED'
    resets=[]
    for r in reports:
        events=r.get('timing_events',[])
        selected=[e for e in events if e.get('reset_window') and not e.get('existing_first_stage_profile')]
        resets.append(dict(case=r['case'],reset_events=len(selected),
            mac_events=sum('u_mac_' in e['instance'] for e in selected),
            rng_events=sum('u_lfsr32_' in e['instance'] for e in selected),
            outside_events=r.get('outside_reset_events'),
            snapshot_words_checked=sum(e.get('snapshot_words_checked',0) for e in r.get('epochs',[]))))
    result=dict(bus_handoff_verdict=verdict,
        negative_control_raw_failure_retained=bool(by_case.get('bus_legacy',{}).get('negative_control_reproduced')),
        bypass=dict(status=by_case.get('bypass',{}).get('status','NOT_RUN'),
            policy='Full period +/-40ps, high/low diagnostic budget +/-10%, match actual REFCLK polarity with <=2ns edge lag. SDF WIDTH checks remain enabled.'),
        vendor_model_isolation=model,reset_events=resets,
        timing_signoff=False,analog_lock_verified=False,
        unresolved=['Foundry STA recovery/removal and WIDTH at physical sinks',
            'Vendor analog lock/start/stop/BP specification; digital model is not silicon',
            'Known internal pipeline X may be unobserved; full output snapshot is not all-register-state proof'])
    (root/'suspect_diagnosis.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
