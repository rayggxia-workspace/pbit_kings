"""Change precision only in job-local source copies; preserve time units."""
import json
from pathlib import Path
import re
import sys
from check_inputs import sha256

NS = {'s':1e9,'ms':1e6,'us':1e3,'ns':1,'ps':.001,'fs':.000001}
def convert(text, precision):
    target = .01 if precision=='10ps' else .001
    if re.search(r'pragma\s+protect|`protect',text):
        raise ValueError('Encrypted model: precision cannot be audited')
    found=[]
    def scale(m):
        unit=m.group(1)
        n,u=re.fullmatch(r'(\d+)\s*(s|ms|us|ns|ps|fs)',unit).groups()
        if int(n)*NS[u] < target: raise ValueError('Time unit smaller than requested precision: '+unit)
        found.append(m.group(0))
        return '`timescale '+unit+'/'+precision
    text=re.sub(r'`timescale\s+(\d+\s*(?:ms|us|ns|ps|fs|s))\s*/\s*\d+\s*(?:ms|us|ns|ps|fs|s)',scale,text)
    for m in re.finditer(r'\btimeunit\s+(\d+)\s*(ms|us|ns|ps|fs|s)',text):
        if int(m.group(1))*NS[m.group(2)] < target: raise ValueError('SV timeunit smaller than precision')
    text=re.sub(r'(\btimeunit\s+\d+\s*(?:ms|us|ns|ps|fs|s)\s*/\s*)\d+\s*(?:ms|us|ns|ps|fs|s)',lambda m:m.group(1)+precision,text)
    text=re.sub(r'\btimeprecision\s+\d+\s*(?:ms|us|ns|ps|fs|s)\s*;', 'timeprecision '+precision+';',text)
    return text,found

if __name__=='__main__':
    precision=sys.argv[1]
    if precision not in ('1ps','10ps'): raise ValueError('Unsupported precision')
    out=Path('models'); out.mkdir(exist_ok=True)
    records=[]
    for label,path in zip(('std.v','io.v','pll.v'),sys.argv[2:]):
        p=Path(path); text,found=convert(p.read_text(encoding='ascii'),precision)
        (out/label).write_text(text,encoding='ascii')
        records.append(dict(original=str(p),sha256=sha256(p),copy=str(out/label),directives=sorted(set(found))))
    if len(records)!=3: raise ValueError('Need three library models')
    for name in ('uart_host.sv','gate_pipeline_env.sv','tb_gate_pipeline_maxcut_lite.sv'):
        p=Path('source')/name
        text,_=convert(p.read_text(),precision); p.write_text(text)
    Path('precision.json').write_text(json.dumps(dict(precision=precision,units_preserved=True,models=records),indent=2)+'\n')
