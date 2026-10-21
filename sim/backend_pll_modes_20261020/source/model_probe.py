"""Isolate EN-stop behavior in the actual vendor model, without the chip/SDF."""
import csv
import io
import json
import os
from pathlib import Path
import re
import subprocess
from coverage_evidence import sha
from precision import convert


def run(root,build,snapshot):
    root=Path(root);reports=[]
    for name,precision,model in (('native_1ps','1ps',Path(os.environ['PLL_MODEL'])),
                                 ('matched_10ps','10ps',Path(build)/'models/pll.v')):
        dst=root/name;dst.mkdir(parents=True)
        text=(Path(snapshot)/'source/tb_vendor_stop.sv').read_text()
        converted,_=convert(text,precision)
        (dst/'tb.sv').write_text(converted)
        commands=[[os.environ.get('VCS_BIN','vcs'),'-full64','-sverilog','-v',str(model.resolve()),
                   'tb.sv','-top','tb_vendor_stop','-o','simv'],['./simv']]
        ok=True
        for command,log in zip(commands,('compile.log','simulation.log')):
            with (dst/log).open('w') as out:
                rc=subprocess.call(command,cwd=str(dst),stdout=out,stderr=subprocess.STDOUT)
            (dst/(log+'.command.json')).write_text(json.dumps(command)+'\n')
            if log=='compile.log':
                (dst/'compile_tail.txt').write_text('\n'.join((dst/log).read_text(errors='replace').splitlines()[-80:])+'\n')
            if rc:ok=False;break
        text=(dst/'simulation.log').read_text(errors='replace') if (dst/'simulation.log').exists() else ''
        complete='[VENDOR_STOP_COMPLETE]' in text and text.count('[VENDOR_STOP_PHASE]')==5
        pulses=[];previous={};off={}
        if (dst/'model_trace.csv').exists():
            for row in csv.DictReader(io.StringIO((dst/'model_trace.csv').read_text())):
                t=float(row['ns']);p=int(row['phase']);s=row['signal'];key=(p,s)
                if row['value'] not in ('0','1'):previous.pop(key,None);continue
                if s=='en' and row['value']=='0':off[p]=t
                if s in ('ckout','cktst') and key in previous:
                    width=t-previous[key]
                    if 0<width<1:pulses.append(dict(phase=p,signal=s,width_ns=round(width,3),
                        start_ns=previous[key],end_ns=t,after_en_off_ns=t-off[p] if p in off else None))
                previous[key]=t
        warnings=re.findall(r'(?m)^Warning-\[[^\]]+\][^\n]*',text)
        report=dict(variant=name,precision=precision,model_sha256=sha(model),
            functional_behavior_modified=False,chip_netlist_or_sdf_used=False,
            status='MODEL_PROBE_COMPLETE' if ok and complete and 'Fatal:' not in text else 'MODEL_PROBE_FAILED',
            warnings=warnings,short_pulses=pulses,timing_signoff=False,
            silicon_failure_proven=False)
        (dst/'model_summary.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(report)
    summary=dict(variants=reports,isolated_vendor_warning_reproduced=any(r['warnings'] for r in reports),
                 isolated_vendor_short_pulse_reproduced=any(r['short_pulses'] for r in reports),
                 timing_signoff=False,silicon_failure_proven=False)
    (root/'model_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary
