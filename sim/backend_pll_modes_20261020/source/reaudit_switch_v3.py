"""Read-only review of the completed v3 switch run; never launch EDA tools."""
import argparse
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import zipfile

from audit_modes import audit
from coverage_evidence import sha
from precision import convert

JOB='38263376'
RELEASE='20261021_pll_modes_v3'
ARCHIVE_SHA='7b7c8143b935be976befb8a07486b0b2e77bf845925eb2c653c6051402b5afba'
PACKAGE_SHA='747eaebc6a763b42ba006a0234f362dadf2ac722c07027088d99845f629b03df'
BUILD_FILES=('annotation_gate.json','BUILD_COMPLETE.json','checkpoint.json','sdf_native_coverage.txt')
CASE_FILES=('mode_result.json','epochs.jsonl','transactions.jsonl','checks.jsonl',
            'clock_metrics.jsonl','mode_trace.csv','simulation.log','simulator_exit.txt',
            'coverage_binding.json','sdf_native_coverage.txt')


def review(archive,package,out):
    archive=Path(archive).resolve();package=Path(package).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Refuse to overwrite existing review '+str(out))
    if sha(archive)!=ARCHIVE_SHA:raise ValueError('Unexpected result archive SHA256')
    if sha(package)!=PACKAGE_SHA:raise ValueError('Unexpected original v3 script ZIP SHA256')
    verified={}
    with tarfile.open(str(archive)) as tar,zipfile.ZipFile(str(package)) as frozen:
        def read(name):
            member=tar.getmember(JOB+'/'+name)
            if not member.isfile():raise ValueError('Nonregular evidence '+name)
            data=tar.extractfile(member).read()
            verified[name]=hashlib.sha256(data).hexdigest()
            return data
        manifest=json.loads(read('source_manifest.json').decode('utf-8'))
        build_manifest=json.loads(read('build/source_manifest.json').decode('utf-8'))
        if manifest!=build_manifest:raise ValueError('Runtime/build manifest mismatch')
        config=json.loads(read('run_config.json').decode('utf-8'))
        precision=json.loads(read('build/precision.json').decode('utf-8'))
        if config['precision']!='10ps' or precision['precision']!='10ps' or not precision['units_preserved']:
            raise ValueError('Unexpected precision conversion')
        for name,digest in manifest.items():
            original=frozen.read('backend_pll_modes_20261020/'+name)
            if hashlib.sha256(original).hexdigest()!=digest:
                raise ValueError('Wrong original package member '+name)
            if name.startswith('source/'):
                expected=original
                if name in ('source/uart_host.sv','source/gate_pipeline_env.sv','source/tb_gate_pipeline_maxcut_lite.sv'):
                    expected=convert(original.decode('ascii'),'10ps')[0].encode('ascii')
                if read('build/'+name)!=expected:
                    raise ValueError('Build source differs '+name)
        if config['release']!=RELEASE or config['sdf_corner']!='WC' or config['performed_this_job']!=['switch']:
            raise ValueError('Wrong release/corner/new case scope')
        out.mkdir(parents=True)
        # Only small, validated metadata/logs are materialized, never chip/IP data.
        with tempfile.TemporaryDirectory(prefix='checked_raw.',dir=str(out)) as directory:
            temp=Path(directory)
            for name in ['build/'+n for n in BUILD_FILES]+['cases/switch/'+n for n in CASE_FILES]:
                path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(read(name))
            report=audit(temp/'cases/switch','switch','WC',temp/'build',
                         historical=True,historical_release=RELEASE)
        events=report['timing_events'];widths=[e for e in events if e['check']=='width']
        groups=Counter((e['width_ns'],e['limit_ns']) for e in widths)
        width_stats=[dict(width_ns=w,limit_ns=limit,shortfall_ns=round(limit-w,6),events=count)
                     for (w,limit),count in sorted(groups.items())]
        trace=list(csv.DictReader(io.StringIO(read('cases/switch/mode_trace.csv').decode('utf-8'))))
        bp=[dict(ns=float(r['ns']),value=r['value'],epoch=int(r['epoch']))
            for r in trace if r['signal']=='pll_bp']
        stats=dict(origin_job=JOB,origin_release=RELEASE,new_simulation=False,raw_inputs_modified=False,
            archive=str(archive),archive_sha256=ARCHIVE_SHA,original_package_sha256=PACKAGE_SHA,
            original_package_files_verified=len(manifest),verified_input_sha256=verified,
            corrected_parser_sha256=sha(Path(__file__).with_name('audit_modes.py')),
            readonly_reviewer_sha256=sha(Path(__file__)),
            raw_check_counts=dict(Counter(e['check'] for e in events)),width_distribution=width_stats,
            width_event_range_ns=[min(min(e['pin_event_ns']) for e in widths),
                                  max(max(e['pin_event_ns']) for e in widths)] if widths else [],
            width_distinct_instances=len({e['instance'] for e in widths}),bp_transitions=bp,
            former_failure='Scalar WIDTH limit was incorrectly parsed as a third event timestamp',
            no_new_waiver=True,timing_signoff=False,analog_lock_verified=False,
            power_estimated=False,live_executable_rechecked=False)
        saved=dict(report);saved.pop('timing_events')
        saved['timing_event_reference']='timing_events.csv; raw source stays in original archive'
        saved['origin_job']=JOB;saved['new_simulation']=False
        for name,data in (('audit.json',saved),('review_summary.json',stats)):
            (out/name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
        with (out/'timing_events.csv').open('w',encoding='utf-8',newline='') as file:
            writer=csv.writer(file,lineterminator='\n')
            writer.writerow(['check','instance','first_event_ns','second_event_ns','reset_window',
                             'existing_first_stage_profile','width_ns','limit_ns','raw'])
            for e in events:
                times=e['pin_event_ns']
                writer.writerow([e['check'],e['instance'],format(times[0],'.2f'),
                    format(times[1],'.2f') if len(times)>1 else '',e['reset_window'],
                    e['existing_first_stage_profile'],e.get('width_ns',''),e.get('limit_ns',''),e['raw']])
        print(json.dumps(dict(status=report['status'],failures=report['failures'],
            functional_evidence_complete=report['functional_evidence_complete'],
            raw_timing_events=report['raw_timing_events'],reset_window_events=report['reset_window_events'],
            existing_profile_events=report['existing_profile_events'],outside_reset_events=report['outside_reset_events'],
            width_distribution=width_stats,short_clock_pulses=report['short_clock_pulses'],out=str(out)),indent=2))
        return report,stats


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--original-package',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    review(args.archive,args.original_package,args.out)
