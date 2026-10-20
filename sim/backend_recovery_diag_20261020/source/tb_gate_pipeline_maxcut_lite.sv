`timescale 1ns/10ps
`include "ff_recovery_watch.sv"
module tb_gate_pipeline_maxcut_lite;
    `include "settings.svh"
    `include "affected_count.svh"
    gate_pipeline_env env();
    reg observe_after_reset=0;
    wire [WATCH_COUNT-1:0] refreshed;
    wire [31:0] write_count [0:WATCH_COUNT-1];
    `include "affected_watch.svh"
    string case_name,corner;
    real reset_offset_ns;
    integer trace_file,checks_file,stage=0,completed=0,busy_samples=0,last_cycles=0;
    integer full_snapshots=0,checked_words=0,refreshed_count=0,min_writes;
    reg was_busy=0,run_requested=0;
    reg [31:0] reference_words [0:99];
    reg [31:0] reference_rng,read_value;
    realtime last_core=-1,last_test=-1,trace_until=0;
    real min_core=1.0e9,max_core=0,min_test=1.0e9,max_test=0;
    integer active_core_edges=0,active_test_edges=0,short_core_during_reset=0;
    bit last_core_observe=0,last_test_observe=0;

    task automatic trace(input string name,input logic [31:0] value);
        if (trace_file) begin
            $fdisplay(trace_file,"%.3f,%s,%08h,%0d",$realtime,name,value,stage);
            $fflush(trace_file);
        end
    endtask
    always @(env.pad_rst_n) begin
        if (env.pad_rst_n===0) trace_until=$realtime+50;
        trace("pad_rst_n",{31'd0,env.pad_rst_n});
    end
    always @(env.dut.core_rst_n) begin
        trace_until=$realtime+50;
        trace("core_rst_n",{31'd0,env.dut.core_rst_n});
    end
    always @(env.dut.u_pll.EN) trace("pll_en",{31'd0,env.dut.u_pll.EN});
    always @(env.dut.u_pll.N) trace("pll_n",{24'd0,env.dut.u_pll.N});
    always @(env.dut.u_pll.OD) trace("pll_od",{30'd0,env.dut.u_pll.OD});
    always @(env.dut.core_clk) begin : CORE_CLOCK
        realtime delta;
        if (observe_after_reset && $isunknown(env.dut.core_clk))
            $fatal(1,"Unknown core clock after recovery");
        if (!$isunknown(env.dut.core_clk)) begin
            if (last_core>=0) begin
                delta=$realtime-last_core;
                if (observe_after_reset && last_core_observe) begin
                    if (delta<min_core) min_core=delta;
                    if (delta>max_core) max_core=delta;
                    active_core_edges++;
                end
                if (stage==3 && env.dut.core_rst_n===0 && delta<1.0) short_core_during_reset++;
            end
            last_core=$realtime; last_core_observe=observe_after_reset;
            if ($realtime<=trace_until) trace("core_clk",{31'd0,env.dut.core_clk});
        end
    end
    always @(env.dut.u_pll.CKTST) begin : TEST_CLOCK
        realtime delta;
        if (observe_after_reset && $isunknown(env.dut.u_pll.CKTST))
            $fatal(1,"Unknown CKTST clock after recovery");
        if (!$isunknown(env.dut.u_pll.CKTST)) begin
            if (last_test>=0 && observe_after_reset && last_test_observe) begin
                delta=$realtime-last_test;
                if (delta<min_test) min_test=delta;
                if (delta>max_test) max_test=delta;
                active_test_edges++;
            end
            last_test=$realtime; last_test_observe=observe_after_reset;
            if ($realtime<=trace_until) trace("cktst",{31'd0,env.dut.u_pll.CKTST});
        end
    end
    always @(negedge env.dut.core_clk or negedge env.dut.core_rst_n) begin
        if (env.dut.core_rst_n !== 1'b1) begin
            was_busy=0; busy_samples=0; run_requested=0;
        end else begin
            if ($isunknown({env.dut.u_pbit_top_run_busy_w,env.dut.u_pbit_top_run_done_w}))
                $fatal(1,"Unknown run control");
            if (env.dut.u_pbit_top_run_busy_w) begin
                if (!run_requested) $fatal(1,"Unrequested compute");
                busy_samples=was_busy ? busy_samples+1 : 1;
            end else if (was_busy) begin
                if (env.dut.u_pbit_top_run_done_w !== 1) $fatal(1,"No run completion");
                last_cycles=busy_samples; completed++;
            end
            was_busy=env.dut.u_pbit_top_run_busy_w;
        end
    end

    task automatic check(input string name);
        $fdisplay(checks_file,"{\"name\":\"%s\",\"sim_ns\":%.3f}",name,$realtime);
        $fflush(checks_file);
        $display("[RECOVERY_DIAG_CHECK] %s PASS ns=%.3f",name,$realtime);
    endtask
    task automatic configure;
        env.core_write(16'h0014,32'h1f1f1f1f);
        env.core_write(16'h0034,32'hffffffff);
        env.core_write(16'h0074,32'h1313);
        env.core_write(16'h0078,32'h0103);
        env.core_write(16'h007c,32'h0207);
        env.core_write(16'h0080,1);
        env.core_write(16'h0080,2);
        env.core_read_check(16'h0084,2);
        env.core_write(16'h0088,3);
        env.core_write(16'h008c,32'h13579bdf);
        env.core_write(16'h0090,3);
        env.core_read_check(16'h0094,32'h13579bdf);
    endtask
    task automatic run_two;
        integer before_count,polls;
        env.core_write(0,16);
        env.core_write(4,1); // Two sweeps, actual majority=1.
        env.core_write(0,1);
        before_count=completed; run_requested=1;
        env.core_write(0,4);
        polls=0;
        while (completed==before_count && polls<280) begin
            @(negedge env.dut.core_clk); #0.02; polls++;
        end
        run_requested=0;
        if (completed!=before_count+1 || last_cycles<22 || last_cycles>26)
            $fatal(1,"Run count/cadence mismatch count=%0d cycles=%0d",completed,last_cycles);
        env.core_read(8,read_value);
        if ((read_value&32'h147)!==5) $fatal(1,"Bad run status %h",read_value);
        env.core_read_check(12,0);
    endtask
    task automatic full_snapshot(input bit compare);
        logic [31:0] value,status;
        integer page,w,index;
        for (page=0;page<10;page++) begin
            env.core_write(16'h0010,32'(page));
            env.core_write(0,8);
            env.core_read(8,status);
            if (!status[5] || status[6] || status[1]) $fatal(1,"Snapshot not ready");
            env.core_read(8,status);
            if (status[5]) $fatal(1,"Snapshot valid did not clear");
            for (w=0;w<10;w++) begin
                index=page*10+w;
                env.core_read(16'h00a8+16'(4*w),value);
                if ($isunknown(value)) $fatal(1,"Unknown snapshot index=%0d",index);
                if (compare && value!==reference_words[index])
                    $fatal(1,"Post-reset snapshot differs word=%0d actual=%h reference=%h",index,value,reference_words[index]);
                if (!compare) reference_words[index]=value;
                checked_words++;
            end
        end
        full_snapshots++;
    endtask
    task automatic rng_read(output logic [31:0] value);
        env.core_write(16'h0074,32'h1313);
        env.core_write(16'h0088,3);
        env.core_write(16'h0090,2);
        env.core_read(16'h0094,value);
        if ($isunknown(value)) $fatal(1,"Unknown RNG readback");
    endtask
    task automatic reject_busy(input logic [15:0] addr,input logic [31:0] value);
        @(negedge env.launch_clk); env.fast_addr=addr; env.fast_data=value;
        @(posedge env.launch_clk); #0.30; env.fast_wr=1; env.fast_rd=0;
        @(posedge env.launch_clk); #0.30; env.fast_wr=0;
        repeat (3) @(negedge env.launch_clk);
        if (env.dut.u_pbit_top_u_uart_reg_subsystem_reg_access_error_w!==1)
            $fatal(1,"Busy request not rejected");
        env.fast_transactions++;
    endtask

    initial begin : TEST
        integer fd,i;
        trace_file=$fopen("reset_clock_trace.csv","w");
        checks_file=$fopen("checks.jsonl","w");
        if (!trace_file || !checks_file) $fatal(1,"Cannot open diagnostic traces");
        $fdisplay(trace_file,"ns,signal,value,stage");
        trace("pad_rst_n",{31'd0,env.pad_rst_n});
        trace("core_rst_n",{31'd0,env.dut.core_rst_n});
        if (!$value$plusargs("CASE=%s",case_name) || !$value$plusargs("RESET_OFFSET_NS=%f",reset_offset_ns))
            $fatal(1,"Missing diagnostic case/offset");
        if (!(reset_offset_ns==0.0 || reset_offset_ns==0.83 || reset_offset_ns==1.67)) $fatal(1,"Invalid reset offset");
        if (!$value$plusargs("SDF_CORNER=%s",corner) || corner!="WC") $fatal(1,"Require WC SDF");
        $printtimescale(tb_gate_pipeline_maxcut_lite);
        $printtimescale(env.dut);
        $display("[POSTLAYOUT_SDF_BEGIN] corner=WC path=simulation.sdf");
        $sdf_annotate("simulation.sdf",env.dut,,"sdf_annotation.log","MAXIMUM");
        $display("[POSTLAYOUT_SDF_RETURNED]");
        stage=1; env.initialize_fast(PLL_CFG); configure;
        run_two; full_snapshot(0); rng_read(reference_rng);
        check("fresh_reference_3200_bits_and_rng");
        stage=2;
        // Keep the existing busy-access/reset exercise, without waiting 65536 sweeps.
        env.core_write(0,16); env.core_write(4,32'h1f00ffff);
        run_requested=1; env.core_write(0,4);
        env.core_read(8,read_value);
        if (!read_value[1] || read_value[2]) $fatal(1,"Long run not busy");
        reject_busy(4,0); env.core_read_check(4,32'h1f00ffff);
        env.core_read_check(12,32'h80000);
        reject_busy(0,4); env.core_read_check(12,32'h80040);
        check("busy_configuration_and_restart_rejected");
        stage=3; env.reset_extra_ns=reset_offset_ns;
        env.end_fast_bus;
        env.initialize_fast(PLL_CFG);
        env.core_read_check(8,0); env.core_read_check(12,0); env.core_read_check(4,0);
        check("external_reset_and_startup_recovered");
        stage=4; observe_after_reset=1;
        configure; run_two;
        repeat (2) @(negedge env.dut.core_clk);
        min_writes=32'h7fffffff;
        for (i=0;i<WATCH_COUNT;i++) begin
            if (refreshed[i]!==1 || write_count[i]==0)
                $fatal(1,"Pipeline register not freshly overwritten index=%0d",i);
            refreshed_count++;
            if (write_count[i]<min_writes) min_writes=write_count[i];
        end
        check("previously_affected_registers_fresh_known_write");
        full_snapshot(1); rng_read(read_value);
        if (read_value!==reference_rng) $fatal(1,"Post-reset RNG differs %h vs %h",read_value,reference_rng);
        check("post_reset_3200_bits_and_rng_equal_reference");
        if (active_core_edges<20 || min_core<1.5 || max_core>1.85 ||
            active_test_edges<4 || min_test<45 || max_test>65)
            $fatal(1,"Post-reset clock quality failed core=%f/%f test=%f/%f",min_core,max_core,min_test,max_test);
        check("post_reset_core_and_test_clock_quality");
        observe_after_reset=0; stage=5;
        fd=$fopen("diagnostic_result.json","w");
        if (!fd) $fatal(1,"Cannot record diagnostic result");
        $fdisplay(fd,"{\"status\":\"FUNCTIONAL_DIAGNOSTIC_PASS\",\"release\":\"20261020_recovery_diag_v1\",\"case\":\"%s\",\"reset_offset_ns\":%.2f,\"complete_runs\":%0d,\"full_snapshots\":%0d,\"snapshot_words_checked\":%0d,\"watched_registers\":%0d,\"refreshed_registers\":%0d,\"minimum_fresh_writes\":%0d,\"core_half_min_ns\":%.3f,\"core_half_max_ns\":%.3f,\"test_half_min_ns\":%.3f,\"test_half_max_ns\":%.3f,\"short_core_edges_during_reset\":%0d,\"timing_signoff\":false}",case_name,reset_offset_ns,completed,full_snapshots,checked_words,WATCH_COUNT,refreshed_count,min_writes,min_core,max_core,min_test,max_test,short_core_during_reset);
        $fclose(fd); $fclose(checks_file); $fflush(trace_file);
        $display("[RECOVERY_DIAG_FUNCTIONAL] PASS case=%s snapshot_bits=3200 refreshed=%0d NOT_TIMING_SIGNOFF",case_name,refreshed_count);
        $finish;
    end
    initial begin #200us; $fatal(1,"Recovery diagnostic watchdog"); end
endmodule
