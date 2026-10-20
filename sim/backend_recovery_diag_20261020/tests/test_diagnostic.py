"""Local parser, monitor and syntax tests, not a real postlayout VCS run."""
import ast
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
sys.path.insert(0,str(ROOT))
import diagnose as d
from generate_watch import generate
import run


class Tests(unittest.TestCase):
    def directory(self):
        base=ROOT/'tests/results';base.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=str(base))

    def compiler(self):
        base=Path(os.environ.get('PBIT_WORKSPACE',str(ROOT.parents[3])))
        exe=base/'sc_weight_storage_or4_20261014/tools/iverilog/bin/iverilog.exe'
        if not exe.is_file():self.skipTest('Local Icarus not bundled in upload')
        return exe

    def event(self,first=150,second=145,scope='array.u_mac_contrib_ff',kind='setuphold'):
        return 'Timing violation in '+scope+'\n    $'+kind+'( posedge CK: '+str(first)+', negedge E: '+str(second)+', limits: (10,0) );\n\n'

    def fixture(self,p,events=''):
        value=dict(status='FUNCTIONAL_DIAGNOSTIC_PASS',release='20261020_recovery_diag_v1',case='phase0',
                   reset_offset_ns=0,complete_runs=2,full_snapshots=2,snapshot_words_checked=200,
                   watched_registers=1575,refreshed_registers=1575,minimum_fresh_writes=4,
                   core_half_min_ns=1.67,core_half_max_ns=1.67,test_half_min_ns=53.33,
                   test_half_max_ns=53.34,timing_signoff=False)
        (p/'diagnostic_result.json').write_text(json.dumps(value))
        (p/'checks.jsonl').write_text(''.join(json.dumps({'name':x})+'\n' for x in d.CHECKS))
        (p/'reset_clock_trace.csv').write_text('ns,signal,value,stage\n0,core_rst_n,00000000,1\n1,core_rst_n,00000001,1\n2,core_rst_n,00000000,3\n4,core_rst_n,00000001,4\n')
        (p/'simulator_exit.txt').write_text('0\n')
        (p/'simulation.log').write_text('[POSTLAYOUT_SDF_RETURNED]\n[SYNC_HEALTH] PASS\n[RECOVERY_DIAG_FUNCTIONAL] PASS\n[SYNC_PROFILE] ACTIVE time=0 first_stage_notifiers=2\n'+events)
        return value

    def audit(self,p):
        with mock.patch.object(d,'bind',return_value={'mock':'NOT REAL SDF PROOF'}):return d.audit(p,'phase0',p/'mock_build')

    def test_case_selection_and_no_old_reruns(self):
        self.assertEqual(run.cases('all'),['phase0','phase90','phase180'])
        self.assertEqual(run.cases('phase0'),['phase0'])
        for value in ('errors','recovery','uart','phase0,phase0'):
            with self.assertRaises(ValueError):run.cases(value)

    def test_definite_reset_windows(self):
        text='ns,signal,value,stage\n0,core_rst_n,xxxxxxxx,0\n1,core_rst_n,00000000,1\n3,core_rst_n,00000001,1\n4,core_clk,00000000,3\n5,core_rst_n,00000000,3\n6,core_rst_n,00000001,4\n'
        self.assertEqual(d.intervals(text),[(1,3),(5,6)])
        uncertain='ns,signal,value,stage\n1,core_rst_n,00000000,1\n2,core_rst_n,xxxxxxxx,1\n4,core_rst_n,00000001,1\n'
        self.assertEqual(d.intervals(uncertain),[(1,2)])
        self.assertFalse(d.timing(self.event(250,245),d.intervals(uncertain))[0]['definite_reset_window'])

    def test_both_pin_events_must_be_inside_same_reset(self):
        self.assertTrue(d.timing(self.event(150,145),[(1,2)])[0]['definite_reset_window'])
        self.assertFalse(d.timing(self.event(150,90),[(1,2)])[0]['definite_reset_window'])
        self.assertFalse(d.timing(self.event(200,195),[(1,2)])[0]['definite_reset_window'])
        with self.assertRaises(ValueError):d.timing('Timing violation in scope\nunknown format\n',[])

    def test_first_stage_scope_and_type_are_exact(self):
        scope=next(iter(d.ALLOWED))
        self.assertTrue(d.timing(self.event(scope=scope),[])[0]['existing_first_stage_profile'])
        self.assertFalse(d.timing(self.event(scope=scope,kind='hold'),[])[0]['existing_first_stage_profile'])
        self.assertFalse(d.timing(self.event(scope=scope+'other'),[])[0]['existing_first_stage_profile'])

    def test_reset_events_are_not_silently_waived(self):
        with self.directory() as folder:
            p=Path(folder);self.fixture(p,self.event(250,245))
            report=self.audit(p)
            self.assertEqual(report['status'],'RESET_TRANSIENTS_FUNCTIONALLY_CONTAINED_REVIEW_REQUIRED')
            self.assertEqual(report['all_unexpected_timing_events_retained'],1)
            self.assertFalse(report['chip_timing_pass'])
            self.assertFalse(report['timing_signoff'])

    def test_active_timing_is_a_failure(self):
        with self.directory() as folder:
            p=Path(folder);self.fixture(p,self.event(450,445))
            report=self.audit(p)
            self.assertEqual(report['outside_reset_events'],1)
            self.assertTrue(report['failures'])

    def test_missing_results_and_bad_clock_are_failures(self):
        for change in ('missing','clock','fresh'):
            with self.directory() as folder:
                p=Path(folder);value=self.fixture(p)
                if change=='missing':(p/'diagnostic_result.json').unlink()
                else:
                    value['core_half_min_ns' if change=='clock' else 'minimum_fresh_writes']=0
                    (p/'diagnostic_result.json').write_text(json.dumps(value))
                self.assertTrue(self.audit(p)['failures'])

    def test_model_warning_is_preserved(self):
        with self.directory() as folder:
            p=Path(folder);self.fixture(p,'Warning-[STASKW_SDILTA64B] Scaled delay exceeds 64 bit limit\n')
            self.assertEqual(len(self.audit(p)['model_warnings']),1)

    def test_generated_watches_are_read_only_and_complete(self):
        data=json.loads((ROOT/'source/affected_registers.json').read_text())
        self.assertEqual(len(data['instances']),1575)
        with self.directory() as folder:
            p=Path(folder);(p/'affected_registers.json').write_text(json.dumps(data))
            self.assertEqual(generate(p),1575)
            text=(p/'affected_watch.svh').read_text()
            self.assertEqual(text.count('ff_recovery_watch #'),1575)
            self.assertNotIn('force ',text)
            data['instances']=['bad; $finish;']
            (p/'affected_registers.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):generate(p)

    def test_python36_grammar_and_no_timing_disable(self):
        for path in ROOT.rglob('*.py'):
            if 'results' not in path.parts:ast.parse(path.read_text(),filename=str(path),feature_version=(3,6))
        tb=(ROOT/'source/tb_gate_pipeline_maxcut_lite.sv').read_text()
        self.assertNotIn('force ',tb)
        self.assertNotIn('$dump',tb)
        self.assertIn('full_snapshot(1)',tb)
        self.assertIn('env.reset_extra_ns=reset_offset_ns',tb)
        flow=(ROOT/'source/flow_fast.py').read_text()
        self.assertIn("if os.environ.get('DIAG_DEBUG','minimal')=='all'",flow)
        self.assertIn("'+neg_tchk'",flow)
        self.assertIn("'+delay_mode_path'",flow)

    def test_monitor_checks_fresh_writes_and_rejects_unknowns(self):
        exe=self.compiler()
        for mode in ('known','unknown_data','unknown_enable','wrong_capture'):
            with self.directory() as folder:
                p=Path(folder)
                tb='''`timescale 1ns/10ps
module t;
reg ck=0,en=0,d=0,q=1'bx,rst_n=0,observe=0;
wire fresh; wire[31:0] writes;
always #5 ck=~ck;
always @(posedge ck) if(en) q<=CAPTURE;
ff_recovery_watch w(ck,en,d,q,rst_n,observe,fresh,writes);
initial begin
#2; rst_n=1; en=1; d=0;
#10; rst_n=0; en=0; d=1'bx;
#10; rst_n=1; observe=1; en=ENABLE; d=VALUE;
#20;
if (!fresh || writes<1) $fatal(1,"No fresh write");
$display("WATCH_TEST_PASS");$finish;
end
endmodule
'''.replace('VALUE',"1'bx" if mode=='unknown_data' else "1'b1").replace(
    'ENABLE',"1'bx" if mode=='unknown_enable' else "1'b1").replace(
    'CAPTURE','~d' if mode=='wrong_capture' else 'd')
                (p/'tb.sv').write_text(tb)
                result=subprocess.run([str(exe),'-g2012','-s','t','-o',str(p/'test.vvp'),str(ROOT/'source/ff_recovery_watch.sv'),str(p/'tb.sv')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=60)
                self.assertEqual(result.returncode,0,result.stdout)
                result=subprocess.run([str(exe.parent/'vvp.exe'),str(p/'test.vvp')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=60)
                marker={'known':'WATCH_TEST_PASS','unknown_data':'WATCH_UNKNOWN_DATA',
                        'unknown_enable':'WATCH_UNKNOWN_ENABLE','wrong_capture':'WATCH_CAPTURE_MISMATCH'}[mode]
                self.assertIn(marker,result.stdout)
                if mode!='known':self.assertNotIn('WATCH_TEST_PASS',result.stdout)

    def test_top_syntax_only(self):
        exe=self.compiler()
        with self.directory() as folder:
            p=Path(folder)
            (p/'settings.svh').write_text("localparam integer CORE_MHZ=300,UART_DIVISOR=500,MAJORITY=1;\nlocalparam [15:0] PLL_CFG=16'h0218;\n")
            (p/'affected_registers.json').write_text(json.dumps({'instances':['u_mac_contrib_ff']}))
            generate(p)
            result=subprocess.run([str(exe),'-g2012','-s','tb_gate_pipeline_maxcut_lite','-I',str(p),'-I',str(ROOT/'source'),'-o',str(p/'syntax.vvp'),str(ROOT/'tests/syntax_env.sv'),str(ROOT/'source/tb_gate_pipeline_maxcut_lite.sv')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout)
            # Never executed: this fixture has no DUT behavior.

    def test_parser_against_prior_real_log(self):
        path=Path('C:/Users/86134/Documents/10月_MPW/APR_results/backend_functional_38215256.tar.gz')
        if not path.is_file():self.skipTest('Prior result not bundled with scripts')
        wanted=('simulation.log','startup_trace.csv');raw={}
        with tarfile.open(str(path),'r|gz') as tar:
            for m in tar:
                if m.name.startswith('38215256/cases/recovery/') and m.name.split('/')[-1] in wanted:
                    raw[m.name.split('/')[-1]]=tar.extractfile(m).read().decode()
        rows=list(csv.DictReader(io.StringIO(raw['startup_trace.csv'])))
        trace='ns,signal,value,stage\n'
        for row in rows:trace+=row['ns']+',core_rst_n,'+row['core_reset']+',0\n'
        events=d.timing(raw['simulation.log'],d.intervals(trace))
        self.assertEqual(len(events),1589)
        self.assertTrue(all(e['definite_reset_window'] and not e['existing_first_stage_profile'] for e in events))


if __name__=='__main__':unittest.main(verbosity=2)
