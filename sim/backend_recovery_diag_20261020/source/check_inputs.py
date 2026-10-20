"""Bounded Innovus Verilog/SPEF name-map precheck; Python 3.6, no packages.

This detects stale instance names, NOT complete RC topology correctness.
PrimeTime must subsequently validate pin/net annotation and RC completeness.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from baseline import old_baseline

PHYSICAL = {'PAD_P55_DUP_LINE_STAG_B', 'PCORNER', 'PVDDPOC', 'PVSS1',
            'PVDD1', 'PVSSANA1I', 'PVDDANA1I', 'PVSS2', 'PVDD2'}
INSTANCE = re.compile(r'^\s*(\w+)\s+(\S+)\s*\(')
KEYWORDS = {'module', 'input', 'output', 'inout', 'wire', 'reg', 'assign',
            'parameter', 'localparam', 'supply0', 'supply1'}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()


def inspect(path, derived=None):
    modules = {}; module = None; physical = []; refs = Counter()
    dst = Path(derived).open('w', encoding='ascii', newline='\n') if derived else None
    try:
        with Path(path).open(encoding='ascii') as src:
            pending = []
            for line in src:
                m = re.match(r'^\s*module\s+(\w+)\s*\(', line)
                if m:
                    module = m.group(1)
                    if module in modules: raise ValueError('Duplicate module: ' + module)
                    modules[module] = []
                if pending:
                    pending.append(line)
                    if ';' not in line: continue
                    text = ''.join(pending); pending = []
                    if not re.fullmatch(r'\s*\w+\s+\S+\s*\(\s*\)\s*;\s*', text):
                        raise ValueError('Physical allowlist cell has connected ports; do not delete: '+text)
                    if dst: dst.write('// Omitted zero-port physical-only instance: '+physical[-1]['instance']+'\n')
                    continue
                m = INSTANCE.match(line)
                if m and m.group(1) not in KEYWORDS:
                    ref, name = m.groups()
                    if not module: raise ValueError('Instance outside module')
                    refs[ref] += 1
                    if ref in PHYSICAL:
                        physical.append(dict(module=module, reference=ref, instance=name))
                        if ';' in line:
                            if not re.fullmatch(r'\s*\w+\s+\S+\s*\(\s*\)\s*;\s*', line):
                                raise ValueError('Connected physical instance must not be removed: '+line)
                            if dst: dst.write('// Omitted zero-port physical-only instance: '+name+'\n')
                        else: pending = [line]
                        continue
                    modules[module].append((ref, name))
                if dst: dst.write(line)
            if pending: raise ValueError('Unterminated physical instance')
    finally:
        if dst: dst.close()
    leaves = {}
    def expand(mod, prefix, stack):
        if mod in stack: raise ValueError('Recursive hierarchy')
        for ref, inst in modules[mod]:
            name = prefix + inst
            if ref in modules: expand(ref, name+'/', stack+[mod])
            else:
                if name in leaves: raise ValueError('Duplicate leaf: '+name)
                leaves[name] = ref
    if 'pbit_io_wrapper' not in modules: raise ValueError('Missing pbit_io_wrapper')
    expand('pbit_io_wrapper', '', [])
    return leaves, physical, refs


def compare_spef(path, leaves):
    expected = {n for n, r in leaves.items() if r.endswith('_9TSVT') and not r.startswith(('TIEHI','TIELO'))}
    missing = set(expected); header = []; in_map = False; entries = 0
    reset_names = []; found = set()
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(str(path), 'rt', encoding='ascii') as f:
        for line in f:
            s = line.strip()
            if s == '*NAME_MAP': in_map = True; continue
            if not in_map:
                header.append(s)
                if s.startswith('*D_NET'): break
                continue
            if s.startswith(('*PORTS', '*D_NET')): break
            m = re.match(r'^\*\d+\s+(\S+)\s*$', s)
            if not m: continue
            entries += 1; name = m.group(1).strip('"')
            if name in missing: missing.remove(name)
            if name.startswith('u_ref_reset_sync/'):
                reset_names.append(name)
            if name in expected: found.add(name)
    if not in_map or not entries: raise ValueError('Unsupported SPEF: nonempty NAME_MAP required')
    if '*DESIGN "pbit_io_wrapper"' not in header: raise ValueError('SPEF design mismatch')
    return dict(spef=str(path), header=header, name_map_entries=entries,
                expected_standard_instances=len(expected), found_standard_instances=len(found),
                missing_standard_instances=len(missing), missing_examples=sorted(missing)[:100],
                reset_sync_spef_names=reset_names,
                reset_sync_netlist_instances={n:r for n,r in leaves.items() if n.startswith('u_ref_reset_sync/')},
                status='NAME_PRECHECK_PASS' if not missing else 'NETLIST_SPEF_MISMATCH'), missing


def run(netlist, spefs, out, derive=False, require_old=False):
    out.mkdir(parents=True, exist_ok=True)
    digest=sha256(netlist)
    baseline=old_baseline(digest) if require_old else dict(id='unrestricted',sha256=digest)
    print('Reading netlist hierarchy:', netlist, flush=True)
    leaves, removed, refs = inspect(netlist, out/'analysis.vg' if derive else None)
    report = dict(netlist=str(netlist), netlist_sha256=digest,baseline=baseline,
                  leaf_instances=len(leaves), removed_zero_port_physical=removed,
                  retained_functional_io={n:r for n,r in leaves.items() if r in ('PDISDU','PDBSDU')},
                  spef_checks=[], limitation='Name presence is necessary, not proof of pin connectivity or complete RC annotation.')
    for i, path in enumerate(spefs):
        print('Checking SPEF:', path, flush=True)
        result, missing = compare_spef(path, leaves)
        result['sha256'] = sha256(path)
        report['spef_checks'].append(result)
        (out/('missing_instances_{}.txt'.format(i))).write_text('\n'.join(sorted(missing))+'\n')
        print(result['status'], 'missing=', len(missing), flush=True)
    report['status'] = 'NAME_PRECHECK_PASS' if all(x['status']=='NAME_PRECHECK_PASS' for x in report['spef_checks']) else 'NETLIST_SPEF_MISMATCH'
    (out/'input_check.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['status']=='NAME_PRECHECK_PASS' else 2


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--netlist', required=True, type=Path)
    p.add_argument('--spef', required=True, action='append', type=Path)
    p.add_argument('--out', default=Path('.'), type=Path)
    p.add_argument('--derive', action='store_true')
    p.add_argument('--require-old-backend', action='store_true')
    a=p.parse_args()
    sys.exit(run(a.netlist, a.spef, a.out, a.derive, a.require_old_backend))
