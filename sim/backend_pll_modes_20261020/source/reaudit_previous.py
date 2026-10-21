"""Recheck frozen v2 evidence without rerunning EDA or changing its raw bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
from audit_modes import audit
from diagnose_suspects import summarize
from coverage_evidence import sha

CASES=('bypass','errors','bus_legacy','bus_safe','pin_only')
INDEX=Path(__file__).with_name('review_38230453_inputs.json')


def compact(report):
    keys=('case','status','functional_evidence_complete','failures','raw_timing_events',
          'reset_window_events','outside_reset_events','negative_control_reproduced',
          'historical_reaudit','serialization_notes','fatal_messages')
    return {k:report[k] for k in keys if k in report}


def review(previous,out):
    previous=Path(previous).resolve();out=Path(out).resolve()
    index=json.loads(INDEX.read_text())
    if out.exists():raise ValueError('Refuse to overwrite existing review '+str(out))
    if previous.is_dir() and (out==previous or previous in out.parents):
        raise ValueError('Review output must be outside the original result directory')
    archive=None
    if previous.is_file():
        if sha(previous)!=index['archive_sha256']:raise ValueError('Wrong previous archive SHA256')
        archive=tarfile.open(str(previous))
    elif not previous.is_dir():raise ValueError('Previous result not found')
    def read(name):
        if archive:
            member=archive.getmember(index['job']+'/'+name)
            if not member.isfile():raise ValueError('Nonregular review input '+name)
            return archive.extractfile(member).read()
        return (previous/name).read_bytes()
    try:
        for name,digest in index['files'].items():
            if hashlib.sha256(read(name)).hexdigest()!=digest:
                raise ValueError('Historical raw bytes changed: '+name)
        config=json.loads(read('run_config.json').decode('utf-8'))
        if config['release']!=index['release'] or config['sdf_corner']!='WC':
            raise ValueError('Historical release/corner differs')
        out.mkdir(parents=True)
        reports=[]
        # Materialize only the checked small reports, never the chip, SDF or IP.
        with tempfile.TemporaryDirectory(prefix='checked_raw.',dir=str(out)) as temporary:
            temp=Path(temporary)
            for name in index['files']:
                if name.startswith(('build/','cases/')):
                    dst=temp/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(read(name))
            for case in CASES:
                report=audit(temp/'cases'/case,case,'WC',temp/'build',historical=True)
                report.update(origin_job=index['job'],origin_release=index['release'],new_simulation=False)
                dst=out/'cases'/case;dst.mkdir(parents=True)
                saved=dict(report);saved.pop('timing_events',None)
                saved['raw_timing_reference']='Original cases/'+case+'/simulation.log; exact SHA256 in reaudit_summary.json'
                (dst/'audit.json').write_text(json.dumps(saved,indent=2)+'\n')
                reports.append(report)
        model=json.loads(read('model_probe/model_summary.json').decode('utf-8'))
        if len(model.get('variants',[]))!=2 or any(v['status']!='MODEL_PROBE_COMPLETE' for v in model['variants']):
            raise ValueError('Previous model probe is not complete')
        model.update(historical_reuse=True,origin_job=index['job'],new_simulation=False)
        diagnosis=summarize(out,reports,model)
        receipt=dict(origin_job=index['job'],origin_release=index['release'],verified_inputs=index['files'],
            previous_location=str(previous),cases=[compact(r) for r in reports],
            bus_handoff_verdict=diagnosis['bus_handoff_verdict'],new_simulation=False,
            raw_inputs_modified=False,timing_signoff=False,
            omitted_case='switch was incomplete; it must run with the corrected active-mode guard')
        (out/'reaudit_summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
        print('HISTORICAL_REAUDIT '+diagnosis['bus_handoff_verdict']+' OUT='+str(out),flush=True)
        return reports,model,index
    finally:
        if archive:archive.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    review(args.previous,args.out)
