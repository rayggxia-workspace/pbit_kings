"""Fail before simulation when SDF checks/cells cannot be matched."""
import json
from collections import Counter
from pathlib import Path
import re
import sys

# These remain visible and require review; none is a cell/check binding failure.
REVIEW_CODES={'SDFCOM_IWSBA','SDFCOM_NICD','SDFCOM_UHICD','SDFCOM_ANICD'}


def native_preview(root):
    preview=[]; paths=[]; zero=[]
    for path in sorted(root.glob('sdfAnnotateInfo*')):
        if not path.is_file(): continue
        paths.append(dict(name=path.name,bytes=path.stat().st_size))
        preview.append('FILE: '+path.name)
        with path.open(errors='replace') as stream:
            for index,line in enumerate(stream):
                if index>=300 or 'Design Not Annotated' in line: break
                preview.append(line.rstrip())
                match=re.search(r'No\. of (Pathdelays|Tchecks)\s*=\s*([\d,]+)\s+Annotated\s*=\s*([\d.]+)%',line)
                if match and int(match.group(2).replace(',',''))>0 and float(match.group(3))==0:
                    zero.append(match.group(1))
    (root/'sdf_native_coverage.txt').write_text('\n'.join(preview)+'\n')
    return paths,sorted(set(zero))


def check(root):
    path=root/'sdf_annotation.log'
    counts=Counter(); errors=[]; complete=False
    if not path.is_file():
        errors.append('Missing SDF annotation log')
    else:
        with path.open(errors='replace') as f:
            for line in f:
                if 'SDF annotation completed:' in line: complete=True
                match=re.search(r'Warning-\[([^\]]+)\]',line)
                if match: counts[match.group(1)]+=1
                if re.search(r'Error-\[|SDF Error|Total errors:\s*[1-9]',line,re.I):
                    if len(errors)<20: errors.append(line.strip())
    rejected={k:v for k,v in counts.items() if k not in REVIEW_CODES}
    if not complete: errors.append('SDF annotation completion missing')
    native_files,zero=native_preview(root)
    if zero: errors.append('Native SDF coverage is zero for '+', '.join(zero))
    result=dict(status='FAIL' if rejected or errors else ('REVIEW_REQUIRED' if counts else 'PASS'),
        warning_events=dict(counts),rejected_codes=rejected,errors=errors,
        native_coverage_files=native_files,native_coverage_preview='sdf_native_coverage.txt',
        note='Negative net delays/IO boundary warnings are not repaired or hidden; review is still required.')
    (root/'annotation_gate.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    result=check(Path('.')); print(json.dumps(result,indent=2))
    sys.exit(2 if result['status']=='FAIL' else 0)
