"""Streaming revision check of the vendor ZIPs; stdlib only, Python 3.6+."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import tempfile
import zipfile
from check_inputs import inspect
from sim_helpers import inspect_netlist

NET = 'sdf_261014/pt_netlist/pbit_io_wrapper_pt.vg'


def sdf_check(stream, leaves, corner):
    ref = None
    seen = set()
    bad = []
    headers = []
    counts = {'cells': 0, 'interconnect': 0, 'selected_negative_interconnect_values': 0,
              'selected_positive_interconnect_below_5ps': 0}
    for raw in stream:
        line = raw.decode('ascii') if isinstance(raw, bytes) else raw
        if len(headers) < 13:
            headers.append(line.strip())
        if '(INTERCONNECT ' in line:
            counts['interconnect'] += 1
            for triplet in re.findall(r'\(([-+0-9.eE:]+)\)', line):
                values = triplet.split(':')
                val = values[-1] if corner == 'WC' else values[0]
                if not val:
                    raise ValueError('Missing selected SDF triplet value')
                v = float(val)
                counts['selected_negative_interconnect_values'] += v < 0
                counts['selected_positive_interconnect_below_5ps'] += 0 < v < .005
        m = re.search(r'\(CELLTYPE\s+"([^"]+)"\)', line)
        if m:
            ref = m.group(1)
        m = re.search(r'\(INSTANCE\s*([^)]*)\)', line)
        if m:
            name = m.group(1).strip()
            if not name:
                if ref != 'pbit_io_wrapper':
                    raise ValueError('Unexpected root CELLTYPE')
                continue
            counts['cells'] += 1
            if leaves.get(name) != ref:
                if len(bad) < 30:
                    bad.append([name, ref, leaves.get(name)])
            seen.add(name)
    # These have no ordinary functional IOPATH; retain them in netlist/power.
    no_path_refs = {'TIEHIX1_9TSVT','TIELOX1_9TSVT','ANTENNAX1_9TSVT'}
    no_path = {n:r for n,r in leaves.items() if r in no_path_refs and n not in seen}
    expected = {n for n, r in leaves.items() if r.endswith('_9TSVT') and r not in no_path_refs}
    missing = expected - seen
    text = '\n'.join(headers)
    if '(DESIGN "pbit_io_wrapper")' not in text or '(TIMESCALE 1ns)' not in text:
        raise ValueError('Unexpected SDF design or time unit')
    token = 'ss_v1p08_125c' if corner == 'WC' else 'ff_v1p32_-40c'
    if token not in text:
        raise ValueError('SDF corner mismatch: ' + corner)
    return dict(header=headers, counts=counts, mismatched_examples=bad, no_functional_iopath_cell_records_absent=no_path,
                missing_standard_cell_records=len(missing), missing_examples=sorted(missing)[:30],
                status='PASS' if not bad and not missing else 'FAIL')


def spef_check(stream, leaves, corner):
    expected = {n for n, r in leaves.items() if r.endswith('_9TSVT')}
    missing = set(expected)
    header = []
    in_map = False
    entries = 0
    for raw in stream:
        line = raw.decode('ascii') if isinstance(raw, bytes) else raw
        s = line.strip()
        if s == '*NAME_MAP':
            in_map = True
            continue
        if not in_map:
            header.append(s)
            continue
        if s.startswith(('*PORTS', '*D_NET')):
            break
        m = re.match(r'^\*\d+\s+(\S+)\s*$', s)
        if m:
            entries += 1
            missing.discard(m.group(1).strip('"'))
    token = 'OPERATING_TEMPERATURE 125' if corner == 'WC' else 'OPERATING_TEMPERATURE -40'
    if '*DESIGN "pbit_io_wrapper"' not in header or token not in '\n'.join(header) or not entries:
        raise ValueError('SPEF header/corner mismatch')
    return dict(header=header, entries=entries, expected=len(expected), missing=len(missing),
                missing_examples=sorted(missing)[:30], status='PASS' if not missing else 'FAIL')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('sdf_zip', type=Path)
    p.add_argument('spef_zip', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    result = {'scope': 'Names/cell types only, not complete pin/RC or SDF annotation proof'}
    with zipfile.ZipFile(a.sdf_zip) as z, zipfile.ZipFile(a.spef_zip) as s, tempfile.TemporaryDirectory() as tmp:
        net = Path(tmp) / 'net.vg'
        h = hashlib.sha256()
        with z.open(NET) as src, net.open('wb') as dst:
            for block in iter(lambda: src.read(4 * 1024 * 1024), b''):
                h.update(block)
                dst.write(block)
        leaves, removed, refs = inspect(net)
        result.update(netlist_sha256=h.hexdigest(), leaf_instances=len(leaves),
                      removed_zero_port_physical=removed, references=dict(refs),
                      pll_interface=inspect_netlist(net), sdf={}, spef={})
        for corner, suffix in [('WC', 'cworst_T_125'), ('BC', 'cbest_T_m40')]:
            print('Checking SDF', corner, flush=True)
            with z.open('sdf_261014/{}/pbit_io_wrapper_{}.sdf'.format(corner, corner)) as stream:
                result['sdf'][corner] = sdf_check(stream, leaves, corner)
            print('Checking SPEF name map', corner, flush=True)
            with s.open('spef/pbit_{}.spef.gz'.format(suffix)) as packed:
                with gzip.GzipFile(fileobj=packed) as stream:
                    result['spef'][corner] = spef_check(stream, leaves, corner)
        with tarfile.open(fileobj=io.BytesIO(z.read('sdf_261014/pt_rpt/pt_rpt_261014.tar.gz')), mode='r:gz') as t:
            for m in t:
                if m.isfile():
                    # Only report bytes, with flattened basename, never archive paths.
                    (a.output / Path(m.name).name).write_bytes(t.extractfile(m).read())
    result['status'] = 'NAME_CELL_PRECHECK_PASS' if all(v['status']=='PASS' for group in ('sdf','spef') for v in result[group].values()) else 'FAIL'
    (a.output / 'input_audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'], 'leaves=', result['leaf_instances'], flush=True)
    return 0 if result['status']=='NAME_CELL_PRECHECK_PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
