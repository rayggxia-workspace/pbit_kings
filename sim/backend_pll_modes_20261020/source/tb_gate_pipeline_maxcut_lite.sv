`timescale 1ns/10ps
`include "pll_clock_guard.sv"
module tb_gate_pipeline_maxcut_lite;
    `include "settings.svh"
    gate_pipeline_env env();
    string case_name,epoch_name,selected_corner;
    integer epoch=0,mhz=300,trace_fd,epoch_fd,uart_fd,check_fd,checks=0;
    integer pll_pin_count=0,core_pin_count=0,pll_fast_count=0;
    integer phase_pll_pins,phase_core_pins;
    bit stable=0,expect_reset=0,core_busy_before_apply=0;
    realtime core_half=1.666666667,test_half=53.333333333;
    realtime trace_until=0,t_reset=-1,t_off=-1,t_on=-1,t_release=-1;
    reg [31:0] value;
    pll_clock_guard #(.ID(0)) core_guard(env.dut.core_clk,env.dut.core_rst_n,stable,core_half);
    pll_clock_guard #(.ID(1)) test_guard(env.dut.u_pll.CKTST,env.dut.core_rst_n,stable,test_half);

    task automatic trace(input string name,input logic [31:0] v);
        if (trace_fd) begin
            $fdisplay(trace_fd,"%.3f,%s,%08h,%0d",$realtime,name,v,epoch);
            $fflush(trace_fd);
        end
    endtask
    always @(env.dut.core_rst_n) begin
        trace_until=$realtime+150;
        trace("core_rst_n",{31'd0,env.dut.core_rst_n});
        if (env.dut.core_rst_n===0 && epoch>0) t_reset=$realtime;
        if (env.dut.core_rst_n===1 && epoch>0) t_release=$realtime;
    end
    always @(env.dut.u_pll.EN) begin
        trace_until=$realtime+150;
        trace("pll_en",{31'd0,env.dut.u_pll.EN});
        if (epoch>0 && env.dut.u_pll.EN===0) t_off=$realtime;
        if (epoch>0 && env.dut.u_pll.EN===1) t_on=$realtime;
    end
    always @(env.dut.u_pll.BP) trace("pll_bp",{31'd0,env.dut.u_pll.BP});
    always @(env.dut.u_pll.N) trace("pll_n",{24'd0,env.dut.u_pll.N});
    always @(env.dut.u_pll.OD) trace("pll_od",{30'd0,env.dut.u_pll.OD});
    always @(env.dut.core_clk)
        if ($realtime<=trace_until) trace("core_clk",{31'd0,env.dut.core_clk});
    always @(env.dut.u_pll.CKTST)
        if ($realtime<=trace_until) trace("cktst",{31'd0,env.dut.u_pll.CKTST});

    function automatic logic [15:0] config_for(input integer f);
        case (f)
            300: config_for=16'h0218;
            150: config_for=16'h0418;
            25: config_for=16'h0a18;
            default: begin $fatal(1,"Unsupported mode"); config_for=0; end
        endcase
    endfunction
    function automatic logic [15:0] ready_status(input integer f);
        ready_status=(f==25)?16'h007a:16'h0072;
    endfunction
    task automatic check(input string name);
        checks++;
        $fdisplay(check_fd,"{\"name\":\"%s\",\"epoch\":%0d,\"ns\":%.3f}",name,epoch,$realtime);
        $fflush(check_fd);
        $display("[PLL_MODE_CHECK] %s PASS epoch=%0d ns=%.3f",name,epoch,$realtime);
    endtask
    task automatic pll_pin(input logic [31:0] req,input logic [31:0] expected);
        logic [31:0] reply;
        env.host.transfer4(req,reply);
        if (reply!==expected) $fatal(1,"PLL pin UART req=%h reply=%h expected=%h",req,reply,expected);
        pll_pin_count++;
        $fdisplay(uart_fd,"{\"transport\":\"PLL_PIN_UART\",\"epoch\":%0d,\"request\":\"%08h\",\"response\":\"%08h\",\"bit_ns\":1000.0}",epoch,req,reply);
        $fflush(uart_fd);
    endtask
    task automatic core_pin(input bit wr,input logic [15:0] addr,input logic [31:0] data,input logic [31:0] expected);
        logic [31:0] reply;
        if (env.fast_active) $fatal(1,"Core pin UART cannot run under bus injection");
        env.uart_access(wr?8'h01:8'h02,addr,data,reply);
        if (reply!==expected) $fatal(1,"Core pin UART data mismatch addr=%h",addr);
        core_pin_count++;
        $fdisplay(uart_fd,"{\"transport\":\"CORE_PIN_UART\",\"epoch\":%0d,\"mhz\":%0d,\"write\":%0d,\"address\":%0d,\"data\":%0d,\"response\":%0d,\"bit_ns\":%.6f}",epoch,mhz,wr,addr,data,reply,env.CORE_BIT_NS);
        $fflush(uart_fd);
    endtask
    task automatic pll_fast_begin;
        env.pll_req=0; env.pll_write=0; env.pll_addr=0; env.pll_data=0;
        force env.dut.req_valid=env.pll_req;
        force env.dut.req_write=env.pll_write;
        force env.dut.req_addr=env.pll_addr;
        force env.dut.req_data=env.pll_data;
    endtask
    task automatic pll_fast_end;
        env.pll_req=0;
        repeat (3) @(negedge env.dut.ref_clk);
        release env.dut.req_valid; release env.dut.req_write;
        release env.dut.req_addr; release env.dut.req_data;
    endtask
    task automatic pll_fast(input bit wr,input logic [7:0] addr,input logic [15:0] data,
                             input logic [1:0] status,output logic [15:0] reply);
        @(negedge env.dut.ref_clk);
        env.pll_addr=addr; env.pll_data=data; env.pll_write=wr;
        @(negedge env.dut.ref_clk); env.pll_req=1;
        @(negedge env.dut.ref_clk);
        if (env.dut.resp_valid!==1 || env.dut.resp_status!==status)
            $fatal(1,"PLL directed request status addr=%h actual=%h expected=%h",addr,env.dut.resp_status,status);
        reply=env.dut.resp_data; env.pll_req=0;
        repeat (2) @(negedge env.dut.ref_clk);
        pll_fast_count++;
        $fdisplay(uart_fd,"{\"transport\":\"PLL_REQUEST_BOUNDARY\",\"epoch\":%0d,\"write\":%0d,\"address\":%0d,\"data\":%0d,\"status\":%0d,\"response\":%0d}",epoch,wr,addr,data,status,reply);
        $fflush(uart_fd);
    endtask
    task automatic begin_epoch(input string name,input integer f,input bit resetting);
        stable=0; epoch++; epoch_name=name; mhz=f; expect_reset=resetting;
        t_reset=-1; t_off=-1; t_on=-1; t_release=-1;
        phase_pll_pins=pll_pin_count; phase_core_pins=core_pin_count;
        $display("[PLL_MODE_BEGIN] epoch=%0d name=%s mhz=%0d",epoch,name,f);
    endtask
    task automatic finish_startup(input bit cold);
        logic [15:0] cfg;
        cfg=config_for(mhz);
        repeat (12) @(negedge env.dut.core_clk);
        if (env.dut.core_rst_n!==1 || env.dut.u_pll.EN!==1 ||
            env.dut.u_pll.BP!==(mhz==25) || env.dut.u_pll.N!==8'd24 ||
            env.dut.u_pll.OD!==cfg[10:9]) $fatal(1,"PLL pins/reset disagree with selected mode");
        if (t_release<0 || t_on<0 || t_release-t_on<14920.0)
            $fatal(1,"Startup wait/reset sequence too short on=%f release=%f",t_on,t_release);
        if (!cold && (t_reset<0 || t_off<0 || t_off-t_reset<100.0))
            $fatal(1,"APPLY did not hold core reset before PLL disable reset=%f off=%f",t_reset,t_off);
        env.check_startup_health;
        core_half=500.0/mhz; env.CORE_BIT_NS=500000.0/mhz;
        stable=1;
        repeat (12) @(negedge env.dut.core_clk);
        env.begin_fast_bus;
        env.core_read_check(4,0); env.core_read_check(8,0); env.core_read_check(12,0);
        env.core_read_check(16'h0010,0);
        env.end_fast_bus;
        check("startup_and_core_configuration_reset");
    endtask
    task automatic start_pin_mode(input string name,input integer f,input bit cold);
        logic [15:0] cfg;
        begin_epoch(name,f,!cold); cfg=config_for(f);
        if (cold) begin
            #80; env.pad_rst_n=0; #400;
            @(negedge env.ref_clk); env.pad_rst_n=1;
            repeat (25) @(negedge env.ref_clk);
        end
        if (!cold) stable=1; // SHADOW writes must not disturb the old active clock.
        pll_pin({8'h01,8'h00,cfg},32'h00000000);
        pll_pin(32'h02000000,{16'h0000,cfg});
        stable=0;
        pll_pin(32'h01020001,32'h00020000);
        pll_pin(32'h02040000,{16'h0004,ready_status(f)});
        pll_pin(32'h02060000,{16'h0006,cfg});
        finish_startup(cold);
    endtask
    task automatic tiny_problem;
        logic [31:0] status,snapshot;
        integer n,polls;
        env.begin_fast_bus;
        env.core_write(16'h0014,32'h1f1f1f1f);
        env.core_write(16'h0034,32'hffffffff);
        env.core_write(16'h0074,0);
        env.core_write(16'h0078,0); env.core_write(16'h007c,32'h0703);
        env.core_write(16'h0080,1); env.core_write(16'h0080,2);
        env.core_read_check(16'h0084,7);
        env.core_write(16'h0078,32'h0100); env.core_write(16'h007c,32'h0101);
        env.core_write(16'h0080,1); env.core_write(16'h0080,2);
        env.core_read_check(16'h0084,1);
        env.core_write(16'h0088,0); env.core_write(16'h008c,32'h13579bdf);
        env.core_write(16'h0090,1); env.core_write(16'h0090,2);
        env.core_read_check(16'h0094,32'h13579bdf);
        env.core_write(16'h0098,0); env.core_write(16'h009c,32'h01fd);
        env.core_write(16'h00a0,1); env.core_write(16'h00a0,4);
        env.core_read_check(16'h00a4,32'h01fd);
        env.core_write(4,1); // Two sweeps; majority field zero means one trial.
        env.core_write(0,1); env.core_write(0,4);
        status=0; polls=0;
        while (!status[2] && polls<100) begin env.core_read(8,status); polls++; end
        if ((status&32'h147)!==5) $fatal(1,"Tiny run did not complete %h",status);
        env.core_read_check(12,0);
        env.core_write(16'h0010,0); env.core_write(0,8);
        env.core_read(8,status);
        if (!status[5] || status[6]) $fatal(1,"Snapshot not valid");
        env.core_read(16'h00a8,snapshot);
        if ((snapshot&32'h11)!==1 || (^snapshot===1'bx))
            $fatal(1,"Tiny MaxCut snapshot mismatch %h",snapshot);
        env.core_write(0,16);
        env.core_read_check(12,0);
        env.end_fast_bus;
        check("tiny_maxcut_run_and_snapshot");
    endtask
    task automatic exercise_epoch;
        core_pin(1,4,1,0); core_pin(0,4,0,1);
        check("dynamic_baud_pin_uart_read_write");
        tiny_problem;
        if (core_guard.edges<20 || test_guard.edges<4) $fatal(1,"Insufficient clock observations");
        $fdisplay(epoch_fd,"{\"epoch\":%0d,\"name\":\"%s\",\"mhz\":%0d,\"config\":%0d,\"core_baud\":%0d,\"core_pin_transactions\":%0d,\"pll_pin_transactions\":%0d,\"core_half_min_ns\":%.3f,\"core_half_max_ns\":%.3f,\"test_half_min_ns\":%.3f,\"test_half_max_ns\":%.3f,\"core_edges\":%0d,\"test_edges\":%0d,\"enable_to_release_ns\":%.3f,\"reset_before_disable_ns\":%.3f,\"tiny_problem\":\"two_node_maxcut\",\"snapshot_mask\":17,\"snapshot_expected\":1,\"sweeps\":2,\"actual_majority\":1}",epoch,epoch_name,mhz,config_for(mhz),mhz*1000000/500,core_pin_count-phase_core_pins,pll_pin_count-phase_pll_pins,core_guard.minimum,core_guard.maximum,test_guard.minimum,test_guard.maximum,core_guard.edges,test_guard.edges,t_release-t_on,t_off-t_reset);
        $fflush(epoch_fd);
        check("mode_epoch_complete");
    endtask
    task automatic bad_config(input logic [15:0] cfg,input logic [3:0] err,input string name);
        logic [15:0] r;
        pll_fast_begin;
        pll_fast(1,0,cfg,0,r); pll_fast(1,2,1,2,r);
        pll_fast(0,4,0,0,r);
        if (r!==(16'h0076 | (16'(err)<<8))) $fatal(1,"Unexpected illegal-config status %h",r);
        pll_fast(0,6,0,0,r); if (r!==16'h0218) $fatal(1,"Illegal config changed ACTIVE");
        pll_fast(1,2,2,0,r); pll_fast(0,4,0,0,r);
        if (r!==16'h0072) $fatal(1,"Sticky PLL error did not clear");
        pll_fast_end; check(name);
    endtask
    task automatic error_case;
        logic [15:0] r;
        integer polls;
        realtime nominal;
        start_pin_mode("start300",300,1); exercise_epoch;
        pll_pin(32'h01020008,32'h02020000);
        pll_pin(32'h02040000,32'h00040576);
        pll_pin(32'h01020002,32'h00020000);
        check("illegal_uart_command");
        bad_config(16'hf218,2,"reserved_config");
        bad_config(16'h0200,3,"invalid_n");
        bad_config(16'h0018,4,"invalid_output");
        nominal=env.CORE_BIT_NS;
        env.CORE_BIT_NS=nominal*0.99; core_pin(0,4,0,1); check("baud_margin_minus");
        env.CORE_BIT_NS=nominal*1.01; core_pin(0,4,0,1); check("baud_margin_plus");
        env.CORE_BIT_NS=nominal;
        env.begin_fast_bus;
        env.core_write(4,32'h1f00ffff); env.core_write(0,4);
        env.core_read(8,value);
        if (!value[1] || value[2]) $fatal(1,"Expected active long run before APPLY");
        core_busy_before_apply=1; env.end_fast_bus;
        begin_epoch("busy_apply150",150,1);
        pll_fast_begin;
        pll_fast(1,0,16'h0418,0,r); pll_fast(1,2,1,0,r);
        pll_fast(1,0,16'h0218,3,r); check("busy_shadow_rejected");
        pll_fast(1,2,1,3,r); check("busy_apply_rejected");
        pll_fast(0,0,0,0,r); if (r!==16'h0418) $fatal(1,"BUSY modified SHADOW");
        pll_fast(1,2,2,0,r); pll_fast(0,4,0,0,r);
        if (!r[0] || r[11:8]!=0 || r[2]) $fatal(1,"Cannot clear error while BUSY %h",r);
        check("clear_error_while_busy");
        polls=0;
        while (r!==16'h0072 && polls<250) begin pll_fast(0,4,0,0,r); polls++; end
        if (r!==16'h0072) $fatal(1,"Directed APPLY startup timeout");
        pll_fast(0,6,0,0,r); if (r!==16'h0418) $fatal(1,"Wrong ACTIVE after busy APPLY");
        pll_fast_end;
        finish_startup(0);
        if (!core_busy_before_apply) $fatal(1,"Missing abort exercise");
        check("apply_aborts_compute"); exercise_epoch;
    endtask

    initial begin : TEST
        integer fd;
        trace_fd=$fopen("mode_trace.csv","w"); epoch_fd=$fopen("epochs.jsonl","w");
        uart_fd=$fopen("transactions.jsonl","w"); check_fd=$fopen("checks.jsonl","w");
        if (!trace_fd || !epoch_fd || !uart_fd || !check_fd) $fatal(1,"Cannot open evidence files");
        $fdisplay(trace_fd,"ns,signal,value,epoch");
        trace("core_rst_n",{31'd0,env.dut.core_rst_n});
        if (!$value$plusargs("CASE=%s",case_name) || !$value$plusargs("SDF_CORNER=%s",selected_corner))
            $fatal(1,"Missing mode case/corner");
        if (selected_corner!=SDF_CORNER) $fatal(1,"Runtime/build SDF mismatch");
        $printtimescale(env.dut);
        $display("[POSTLAYOUT_SDF_BEGIN] corner=%s",selected_corner);
        `include "mode_sdf.svh"
        $display("[POSTLAYOUT_SDF_RETURNED]");
        case (case_name)
            "bypass": begin start_pin_mode("cold_bypass",25,1); exercise_epoch; end
            "switch": begin
                start_pin_mode("start300",300,1); exercise_epoch;
                start_pin_mode("down150",150,0); exercise_epoch;
                start_pin_mode("to_bypass",25,0); exercise_epoch;
                start_pin_mode("return300",300,0); exercise_epoch;
                start_pin_mode("same300_apply",300,0); exercise_epoch;
            end
            "errors": error_case;
            default: $fatal(1,"Unknown case");
        endcase
        stable=0;
        fd=$fopen("mode_result.json","w");
        if (!fd) $fatal(1,"Cannot write result");
        $fdisplay(fd,"{\"release\":\"20261020_pll_modes_v1\",\"case\":\"%s\",\"corner\":\"%s\",\"status\":\"FUNCTIONAL_PASS\",\"epochs\":%0d,\"checks\":%0d,\"pll_pin_transactions\":%0d,\"core_pin_transactions\":%0d,\"pll_directed_transactions\":%0d,\"power_estimated\":false,\"timing_signoff\":false}",case_name,selected_corner,epoch,checks,pll_pin_count,core_pin_count,pll_fast_count);
        $fclose(fd); $fflush();
        $display("[PLL_MODES_FUNCTIONAL] PASS case=%s epochs=%0d NOT_TIMING_SIGNOFF",case_name,epoch);
        $finish;
    end
    initial begin #100ms; $fatal(1,"PLL modes watchdog"); end
endmodule
