"""Record static native SDF binding of the exact executable used by each case."""
import hashlib
import json
import os
from pathlib import Path
import re
from annotation_check import REVIEW_CODES


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()


def load(path): return json.loads(Path(path).read_text())


def native(build):
    gate=load(build/'annotation_gate.json')
    if gate.get('status')=='FAIL' or gate.get('errors') or gate.get('rejected_codes'):
        raise ValueError('Compile-time SDF binding failed')
    text=(build/'sdf_native_coverage.txt').read_text()
    for label,count in (('Pathdelays',10574277),('Tchecks',2391706)):
        if not re.search(label+r'\s*=\s*'+str(count)+r'\s+Annotated\s*=\s*100\.00%',text):
            raise ValueError('Missing complete native compile-time coverage: '+label)
    return gate


def bind(build,case):
    build=Path(build).resolve(); case=Path(case).resolve()
    native(build)
    for name in ('simv','simv.daidir','simulation.sdf'):
        if not os.path.samefile(str(case/name),str(build/name)):
            raise ValueError('Runtime does not use the checked build: '+name)
    proof=dict(compiled_build=str(build),build_identity_sha256=sha(build/'BUILD_COMPLETE.json'),
               checkpoint_sha256=sha(build/'checkpoint.json'),
               native_report_sha256=sha(build/'sdf_native_coverage.txt'),
               source='Static compile-time native SDF report of the same executable/daidir/SDF',
               newly_measured_runtime_native_coverage=False,timing_signoff=False)
    (case/'sdf_native_coverage.txt').write_bytes((build/'sdf_native_coverage.txt').read_bytes())
    (case/'coverage_binding.json').write_text(json.dumps(proof,indent=2)+'\n')
    return proof


def runtime_errors(root,text):
    rejected=[]
    pattern=re.compile(r'Warning-\[(SDF[^\]]+)\]')
    path=root/'sdf_annotation.log'
    if path.is_file():
        with path.open(errors='replace') as f:
            for line in f:
                m=pattern.search(line)
                if (m and m.group(1) not in REVIEW_CODES) or re.search(r'Error-\[|SDF Error|Total errors:\s*[1-9]',line,re.I):
                    if len(rejected)<20: rejected.append(line.strip())
    for line in text.splitlines():
        m=pattern.search(line)
        if m and m.group(1) not in REVIEW_CODES:
            if len(rejected)<20: rejected.append(line.strip())
    return rejected


def historical_binding(build,case):
    build=Path(build);case=Path(case);native(build)
    proof=load(case/'coverage_binding.json')
    for field,name in (('build_identity_sha256','BUILD_COMPLETE.json'),('checkpoint_sha256','checkpoint.json'),
                       ('native_report_sha256','sdf_native_coverage.txt')):
        if proof.get(field)!=sha(build/name):raise ValueError('Historical coverage mismatch '+field)
    if sha(case/'sdf_native_coverage.txt')!=proof['native_report_sha256']:
        raise ValueError('Historical case coverage bytes mismatch')
    proof.update(historical_reaudit=True,live_executable_rechecked=False,
        historical_note='Rechecked recorded build/SDF provenance only; no EDA execution or fresh native coverage measurement.')
    return proof
