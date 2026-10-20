"""Local unit tests only; synthetic DUT is never a postlayout proof."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'));sys.path.insert(0,str(ROOT))
import plan
import audit_modes as a
import run
import build_driver
from precision import convert


class Tests(unittest.TestCase):
    def directory(self):
        p=ROOT/'tests/results';p.mkdir(exist_ok=True)
        return tempfile.TemporaryDirectory(dir=str(p))

    def compiler(self):
        base=Path(os.environ.get('PBIT_WORKSPACE',str(ROOT.parents[3])))
        p=base/'sc_weight_storage_or4_20261014/tools/iverilog/bin/iverilog.exe'
        if not p.is_file():self.skipTest('Local Icarus not bundled with server scripts')
        return p

    def settings(self,p):
        (p/'settings.svh').write_text('localparam integer CORE_MHZ=300,UART_DIVISOR=500,MAJORITY=1;\nlocalparam [15:0] PLL_CFG=16\'h0218;\nlocalparam SDF_CORNER="WC";\n')
        (p/'sync_profile.svh').write_text('task check_startup_health; endtask\n')
        (p/'mode_sdf.svh').write_text('// Syntax-only test: no SDF or full DUT exists.\n')

    def compile(self,p,top,extra,environment=False):
        exe=self.compiler()
        files=[ROOT/'tests/dut_syntax_stub.sv'] if environment else []
        if environment:files += [ROOT/'source/uart_host.sv',ROOT/'source/gate_pipeline_env.sv']
        args=[str(exe),'-g2012','-s',top,'-I',str(p),'-I',str(ROOT/'source'),'-o',str(p/'unit.vvp')]+[str(f) for f in files+extra]
        result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stdout)
        return exe

    def execute(self,p,exe):
        result=subprocess.run([str(exe.parent/'vvp.exe'),str(p/'unit.vvp')],cwd=str(p),
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=90)
        return result.stdout

    def xsim(self,p,top,extra,execute=False):
        base=Path(os.environ.get('XSIM_BIN','C:/Xilinx/vivado/Vivado/2018.3/bin'))
        if not (base/'xvlog.bat').is_file():self.skipTest('Local XSim not available')
        files=[ROOT/'tests/dut_syntax_stub.sv',ROOT/'source/uart_host.sv',ROOT/'source/gate_pipeline_env.sv']+extra
        def tool(name,args):
            result=subprocess.run([os.environ.get('COMSPEC','cmd.exe'),'/d','/c',str(base/(name+'.bat'))]+[str(x) for x in args],
                cwd=str(p),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,universal_newlines=True,timeout=180)
            self.assertEqual(result.returncode,0,result.stdout)
            return result.stdout
        tool('xvlog',['-sv','-i',p,'-i',ROOT/'source']+files)
        tool('xelab',[top,'-s','unit_snapshot'])
        return tool('xsim',['unit_snapshot','-runall']) if execute else ''

    def test_plan_selection(self):
        self.assertEqual(plan.cases('all'),['bypass','switch','errors'])
        for x in ('old_recovery','bypass,bypass',''):
            with self.assertRaises(ValueError):plan.cases(x)
        for x in ('WC','BC'):self.assertEqual(plan.corner(x),x)
        with self.assertRaises(ValueError):plan.corner('TT')
        self.assertEqual([f for _,f in plan.PLANS['switch']],[300,150,25,300,300])
        self.assertEqual(plan.MODES[25]&0x800,0x800)

    def test_python36_grammar(self):
        for p in ROOT.rglob('*.py'):
            if 'results' not in p.parts:ast.parse(p.read_text(),filename=str(p),feature_version=(3,6))

    def test_reset_windows_reject_unknown(self):
        trace='ns,signal,value,epoch\n1,core_rst_n,0,1\n2,core_rst_n,x,1\n4,core_rst_n,1,1\n'
        self.assertEqual(a.windows(trace),[(1,2)])
        with self.assertRaises(ValueError):a.windows('ns,signal,value,epoch\n1,core_rst_n,0,1\n')

    def test_timing_both_edges_and_exact_profile(self):
        def event(t1,t2,scope='array.ff',kind='setuphold'):
            return 'Timing violation in '+scope+'\n $'+kind+'(posedge CK:'+str(t1)+', negedge E:'+str(t2)+', limits:(2,3));\n'
        self.assertTrue(a.timing(event(150,145),[(1,2)])[0]['reset_window'])
        self.assertFalse(a.timing(event(150,99),[(1,2)])[0]['reset_window'])
        scope=next(iter(a.ALLOWED))
        self.assertTrue(a.timing(event(150,145,scope),[])[0]['existing_first_stage_profile'])
        self.assertFalse(a.timing(event(150,145,scope,'width'),[])[0]['existing_first_stage_profile'])
        with self.assertRaises(ValueError):a.timing('Timing violation in ff\nBad format\n',[])

    def fixture(self,p,case='bypass'):
        epochs=[];tx=[];checks=[];trace='ns,signal,value,epoch\n'
        for i,(name,f) in enumerate(plan.PLANS[case],1):
            h=round(500.0/f,2)
            epochs.append(dict(epoch=i,name=name,mhz=f,config=plan.MODES[f],core_baud=f*1000000//500,
                tiny_problem='two_node_maxcut',snapshot_mask=17,snapshot_expected=1,sweeps=2,actual_majority=1,
                core_pin_transactions=2,pll_pin_transactions=5,core_half_min_ns=h,core_half_max_ns=h,
                test_half_min_ns=53.33,test_half_max_ns=53.33,core_edges=100,test_edges=30,
                enable_to_release_ns=15010,reset_before_disable_ns=150))
            for n in ('startup_and_core_configuration_reset','dynamic_baud_pin_uart_read_write','tiny_maxcut_run_and_snapshot','mode_epoch_complete'):
                checks.append(dict(name=n,epoch=i))
            cfg=plan.MODES[f];ready=0x7a if f==25 else 0x72
            for req,resp in ((0x01000000|cfg,0),(0x02000000,cfg),(0x01020001,0x00020000),
                             (0x02040000,0x00040000|ready),(0x02060000,0x00060000|cfg)):
                tx.append(dict(transport='PLL_PIN_UART',epoch=i,request=format(req,'08x'),response=format(resp,'08x'),bit_ns=1000))
            for wr in (1,0):tx.append(dict(transport='CORE_PIN_UART',epoch=i,mhz=f,write=wr,address=4,data=1 if wr else 0,response=0 if wr else 1,bit_ns=500000.0/f))
            trace+='{},core_rst_n,0,{}\n{},core_rst_n,1,{}\n'.format(i*10,i,i*10+4,i)
        result=dict(release=plan.RELEASE,case=case,corner='WC',status='FUNCTIONAL_PASS',epochs=len(epochs),
            power_estimated=False,timing_signoff=False,checks=len(checks),pll_pin_transactions=len(epochs)*5,
            core_pin_transactions=len(epochs)*2,pll_directed_transactions=0)
        (p/'mode_result.json').write_text(json.dumps(result))
        for name,data in [('epochs',epochs),('transactions',tx),('checks',checks)]:
            (p/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
        (p/'mode_trace.csv').write_text(trace)
        (p/'simulation.log').write_text('[PLL_MODES_FUNCTIONAL] PASS\n[POSTLAYOUT_SDF_RETURNED]\n[SYNC_HEALTH] PASS\n[SYNC_PROFILE] ACTIVE time=0 first_stage_notifiers=2\n')
        (p/'simulator_exit.txt').write_text('0\n')
        return epochs,tx

    def audit(self,p,case='bypass'):
        with mock.patch.object(a,'bind',return_value={'MOCK':'not real SDF evidence'}):return a.audit(p,case,'WC',p/'mock_build')

    def test_complete_fixture_and_no_signoff(self):
        for case in ('bypass','switch'):
            with self.directory() as folder:
                p=Path(folder);self.fixture(p,case);r=self.audit(p,case)
                self.assertEqual(r['failures'],[]);self.assertFalse(r['timing_signoff'])

    def test_missing_uart_mode_and_wrong_baud_fail(self):
        for mutation in ('missing','baud','reply','no_mode','clock'):
            with self.directory() as folder:
                p=Path(folder);epochs,tx=self.fixture(p)
                if mutation=='missing':tx.pop()
                if mutation=='baud':tx[-1]['bit_ns']=16000 # Old divider 400 is WRONG for this netlist.
                if mutation=='reply':tx[3]['response']='00040072' # Bypass must report 0x7a.
                if mutation=='no_mode':epochs=[]
                if mutation=='clock':epochs[0]['core_half_min_ns']=1.67
                for name,data in [('epochs',epochs),('transactions',tx)]:
                    (p/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
                self.assertTrue(self.audit(p)['failures'],mutation)

    def error_fixture(self,p):
        epochs,tx=self.fixture(p,'errors')
        epochs[1]['pll_pin_transactions']=0
        tx=[t for t in tx if not(t['transport']=='PLL_PIN_UART' and t['epoch']==2)]
        for req,resp in ((0x01020008,0x02020000),(0x02040000,0x00040576),(0x01020002,0x00020000)):
            tx.append(dict(transport='PLL_PIN_UART',epoch=1,request=format(req,'08x'),response=format(resp,'08x'),bit_ns=1000))
        for factor in (.99,1.01):
            tx.append(dict(transport='CORE_PIN_UART',epoch=1,mhz=300,write=0,address=4,data=0,response=1,bit_ns=500000.0/300*factor))
        def append(epoch,data):
            for wr,addr,value,status,response in data:
                tx.append(dict(transport='PLL_REQUEST_BOUNDARY',epoch=epoch,write=wr,address=addr,data=value,status=status,response=response))
        for cfg,error in ((0xf218,2),(0x0200,3),(0x0018,4)):
            append(1,[(1,0,cfg,0,0),(1,2,1,2,0),(0,4,0,0,0x76|(error<<8)),
                      (0,6,0,0,0x218),(1,2,2,0,0),(0,4,0,0,0x72)])
        append(2,[(1,0,0x418,0,0),(1,2,1,0,0),(1,0,0x218,3,0),(1,2,1,3,0),
                  (0,0,0,0,0x418),(1,2,2,0,0),(0,4,0,0,0x11),(0,4,0,0,0x72),(0,6,0,0,0x418)])
        checks=a.rows(p/'checks.jsonl')
        for name in plan.ERROR_CHECKS:checks.append(dict(name=name,epoch=2 if name.startswith(('busy_','clear_','apply_')) else 1))
        for name,data in [('epochs',epochs),('transactions',tx),('checks',checks)]:
            (p/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in data))
        result=json.loads((p/'mode_result.json').read_text())
        result.update(checks=len(checks),pll_pin_transactions=8,core_pin_transactions=6,pll_directed_transactions=27)
        (p/'mode_result.json').write_text(json.dumps(result))
        return tx

    def test_error_case_complete_and_missing_busy_rejected(self):
        for bad in (False,True):
            with self.directory() as folder:
                p=Path(folder);tx=self.error_fixture(p)
                if bad:
                    next(t for t in tx if t['transport']=='PLL_REQUEST_BOUNDARY' and t['epoch']==2 and t['status']==3)['status']=0
                    (p/'transactions.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in tx))
                report=self.audit(p,'errors')
                self.assertEqual(bool(report['failures']),bad,report['failures'])

    def test_reset_only_events_not_silently_waived(self):
        with self.directory() as folder:
            p=Path(folder);self.fixture(p)
            with (p/'simulation.log').open('a') as f:f.write('Timing violation in array.ff\n $setuphold(posedge CK:1200,negedge E:1190,limits:(2,3));\nWarning-[STASKW_SDILTA64B] inf delay\n')
            r=self.audit(p);self.assertEqual(r['reset_window_events'],1)
            self.assertEqual(r['status'],'FUNCTIONAL_PASS_REVIEW_REQUIRED')
            self.assertEqual(len(r['model_and_runtime_warnings']),1)

    def test_active_event_and_short_pulse_fail(self):
        for pulse in (False,True):
            with self.directory() as folder:
                p=Path(folder);self.fixture(p)
                if pulse:
                    with (p/'mode_trace.csv').open('a') as f:f.write('20,core_clk,1,1\n20.01,core_clk,0,1\n')
                else:
                    with (p/'simulation.log').open('a') as f:f.write('Timing violation in ff\n $setuphold(posedge CK:2000,negedge E:1990,limits:(2,3));\n')
                self.assertTrue(self.audit(p)['failures'])

    def test_precision_keeps_units_and_dynamic_host(self):
        text=(ROOT/'source/gate_pipeline_env.sv').read_text()
        converted,_=convert(text,'10ps')
        self.assertIn('realtime CORE_BIT_NS =',converted)
        self.assertNotIn('localparam realtime CORE_BIT_NS',converted)
        self.assertIn('`timescale 1ns/10ps',converted)

    def test_build_corner_is_literal_and_separate(self):
        for selected,mtm in (('WC','MAXIMUM'),('BC','MINIMUM')):
            with self.directory() as folder:
                p=Path(folder);old=Path.cwd()
                def inputs():
                    (p/'inputs.json').write_text('{}');(p/'settings.svh').write_text('// unit fixture\n')
                try:
                    os.chdir(str(p))
                    with mock.patch.dict(os.environ,{'CORNER':selected,'CORE_MHZ':'300','PRECISION':'10ps',
                            'PARALLEL':'serial','SYNC_POLICY':'profile','BUILD_JOB':''}),\
                         mock.patch.object(build_driver.flow_fast,'inputs',side_effect=inputs),\
                         mock.patch.object(build_driver.flow_fast,'build'),mock.patch.object(build_driver,'native'):
                        build_driver.main()
                    self.assertIn('"'+mtm+'"',(p/'mode_sdf.svh').read_text())
                    self.assertIn('"'+selected+'"',(p/'settings.svh').read_text())
                    self.assertEqual(json.loads((p/'inputs.json').read_text())['corner'],selected)
                finally:os.chdir(str(old))

    def test_full_top_syntax_with_actual_environment(self):
        with self.directory() as folder:
            p=Path(folder);self.settings(p)
            self.xsim(p,'tb_gate_pipeline_maxcut_lite',[ROOT/'source/tb_gate_pipeline_maxcut_lite.sv'])
            # Deliberately not executed: declaration-only DUT is not a design model.

    def test_clock_guard_positive_and_negative(self):
        for mode,marker in [('ok','GUARD_TEST_PASS'),('pulse','CLOCK_GUARD_PULSE'),
                            ('reset','CLOCK_GUARD_UNEXPECTED_RESET'),('stop','CLOCK_GUARD_STOPPED')]:
            with self.directory() as folder:
                p=Path(folder)
                action={'ok':'','pulse':'#1;clk=0;#1;clk=1;','reset':'rst=0;','stop':'run_clock=0;'}[mode]
                (p/'tb.sv').write_text('''`timescale 1ns/10ps
module t;
reg clk=0,rst=1,active=0,run_clock=1;realtime half=5;
always #5 if(run_clock) clk=~clk;
pll_clock_guard guard(clk,rst,active,half);
initial begin #2;active=1;#20;ACTION #200;$display("GUARD_TEST_PASS");$finish;end
endmodule
'''.replace('ACTION',action))
                exe=self.compile(p,'t',[ROOT/'source/pll_clock_guard.sv',p/'tb.sv'])
                out=self.execute(p,exe);self.assertIn(marker,out)
                if mode!='ok':self.assertNotIn('GUARD_TEST_PASS',out)

    def test_real_host_codec_at_three_bauds(self):
        with self.directory() as folder:
            p=Path(folder);self.settings(p)
            (p/'tb.sv').write_text('''`timescale 1ns/10ps
module t;
gate_pipeline_env env();
realtime period;reg[31:0] result;
task automatic receive_byte(output reg[7:0] v);
 @(negedge env.core_rx);#(period/2);if(env.core_rx!==0)$fatal(1,"Bad request start");
 for(integer b=0;b<8;b++)begin #(period);v[b]=env.core_rx;end
 #(period);if(env.core_rx!==1)$fatal(1,"Bad request stop");
endtask
task automatic send_byte(input reg[7:0] v);
 env.dut.fake_tx=0;#(period);
 for(integer b=0;b<8;b++)begin env.dut.fake_tx=v[b];#(period);end
 env.dut.fake_tx=1;#(period);
endtask
task automatic transaction(input realtime bit_ns);
 reg[55:0] req,reply;reg[7:0] v;
 period=bit_ns;env.CORE_BIT_NS=bit_ns;
 fork
  begin
   for(integer i=6;i>=0;i--)begin receive_byte(v);req[i*8+:8]=v;end
   if(req!==56'h02000400000000)$fatal(1,"Bad UART byte order %h",req);
   reply=56'h00000400000001;
   for(integer i=6;i>=0;i--)send_byte(reply[i*8+:8]);
  end
  begin env.uart_access(2,4,0,result);if(result!==1)$fatal(1,"Bad host response");end
 join
endtask
initial begin #100;transaction(500000.0/300);transaction(500000.0/150);transaction(500000.0/25);
$display("DYNAMIC_UART_CODEC_TEST_PASS");$finish;end
endmodule
''')
            out=self.xsim(p,'t',[p/'tb.sv'],True);self.assertIn('DYNAMIC_UART_CODEC_TEST_PASS',out)

    def test_pll_uart_host_back_to_back(self):
        with self.directory() as folder:
            p=Path(folder);self.settings(p)
            (p/'tb.sv').write_text('''`timescale 1ns/10ps
module t;
wire host_tx;reg peer_tx=1;reg[31:0] result;
uart_host #(.BIT_NS(1000)) host(.tx(peer_tx),.rx(host_tx));
task automatic receive_byte(output reg[7:0] v);
 @(negedge host_tx);#500;
 for(integer b=0;b<8;b++)begin #1000;v[b]=host_tx;end
 #1000;if(host_tx!==1)$fatal(1,"Bad PLL request stop");
endtask
task automatic send_byte(input reg[7:0] v);
 peer_tx=0;#1000;
 for(integer b=0;b<8;b++)begin peer_tx=v[b];#1000;end
 peer_tx=1;#1000;
endtask
initial begin
 #100;
 fork
  begin
   reg[31:0] req;reg[7:0] v;
   for(integer i=3;i>=0;i--)begin receive_byte(v);req[i*8+:8]=v;end
   if(req!==32'h02060000)$fatal(1,"Bad PLL request order");
   send_byte(0);send_byte(6);send_byte(2);send_byte(24);
  end
  begin host.transfer4(32'h02060000,result);if(result!==32'h00060218)$fatal(1,"Bad PLL host reply");end
 join
 $display("PLL_UART_CODEC_TEST_PASS");$finish;
end
endmodule
''')
            out=self.xsim(p,'t',[p/'tb.sv'],True);self.assertIn('PLL_UART_CODEC_TEST_PASS',out)


if __name__=='__main__':unittest.main(verbosity=2)
