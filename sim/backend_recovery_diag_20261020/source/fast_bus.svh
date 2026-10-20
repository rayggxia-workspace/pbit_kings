// Verification-only injection at the two UART masters' request boundaries.
// No array state, PLL output, clock, reset or computation result is forced.
logic fast_wr=0, fast_rd=0;
logic [15:0] fast_addr=0;
logic [31:0] fast_data=0;
logic pll_req=0, pll_write=0;
logic [7:0] pll_addr=0;
logic [15:0] pll_data=0;
bit fast_active=0;
integer fast_transactions=0;
realtime reset_extra_ns=0.0;
wire launch_clk = dut.u_pbit_top_u_uart_reg_subsystem_u_pbit_uart_reg_master_req_wr_en_ff_q_o_reg_0_.CK;

task automatic begin_fast_bus();
    fast_wr=0; fast_rd=0; fast_addr=0; fast_data=0;
    force dut.u_pbit_top_u_uart_reg_subsystem_reg_wr_en_w = fast_wr;
    force dut.u_pbit_top_u_uart_reg_subsystem_reg_rd_en_w = fast_rd;
    force dut.u_pbit_top_u_uart_reg_subsystem_reg_addr_w = fast_addr;
    force dut.u_pbit_top_u_uart_reg_subsystem_reg_wdata_w = fast_data;
    fast_active=1;
endtask

task automatic end_fast_bus();
    fast_wr=0; fast_rd=0;
    repeat (4) @(negedge launch_clk);
    release dut.u_pbit_top_u_uart_reg_subsystem_reg_wr_en_w;
    release dut.u_pbit_top_u_uart_reg_subsystem_reg_rd_en_w;
    release dut.u_pbit_top_u_uart_reg_subsystem_reg_addr_w;
    release dut.u_pbit_top_u_uart_reg_subsystem_reg_wdata_w;
    fast_active=0;
endtask

task automatic fast_access(input bit wr, input logic [15:0] addr,
                           input logic [31:0] data, output logic [31:0] value);
    if (!fast_active) $fatal(1,"Fast bus not acquired");
    @(negedge launch_clk);
    fast_addr=addr; fast_data=data;
    // Launch from the real UART-master clock branch, with an explicit 0.30 ns
    // source delay. A half-cycle launch would unnecessarily reduce setup margin.
    @(posedge launch_clk); #0.30;
    fast_wr=wr; fast_rd=!wr;
    @(posedge launch_clk); #0.30;
    fast_wr=0; fast_rd=0;
    // Register-block responses are registered, including pre-clear status.
    repeat (3) @(negedge launch_clk);
    if (dut.u_pbit_top_u_uart_reg_subsystem_reg_access_error_w !== 1'b0)
        $fatal(1,"Fast bus access error addr=%h wr=%b",addr,wr);
    value=dut.u_pbit_top_u_uart_reg_subsystem_reg_rdata_w;
    if (!wr && (^value === 1'bx)) $fatal(1,"Fast bus X read addr=%h data=%h",addr,value);
    fast_transactions++;
    $fdisplay(progress_file,"bus_pass,%.3f,%0d,%h",$realtime,fast_transactions,addr);
    $fflush(progress_file);
endtask

task automatic fast_cfg_wait(input logic [15:0] command_addr);
    logic [31:0] status;
    integer done_bit, polls;
    bit done;
    case (command_addr)
        16'h0080: done_bit=3;
        16'h0090: done_bit=7;
        16'h00a0: done_bit=4;
        default: $fatal(1,"Invalid configuration command");
    endcase
    polls=0; done=0;
    while (!done && polls<128) begin
        fast_access(0,16'h0008,0,status);
        if (status[6]) $fatal(1,"Configuration error status=%h",status);
        done=!status[8] && status[done_bit];
        polls++;
    end
    if (!done) $fatal(1,"Configuration completion timeout addr=%h status=%h",command_addr,status);
endtask

task automatic pll_bus_access(input bit wr, input logic [7:0] addr,
                              input logic [15:0] data, output logic [15:0] value);
    @(negedge dut.ref_clk);
    pll_addr=addr; pll_data=data; pll_write=wr;
    @(negedge dut.ref_clk); pll_req=1;
    @(negedge dut.ref_clk);
    if (dut.resp_valid !== 1'b1 || dut.resp_status !== 0)
        $fatal(1,"PLL bus response error addr=%h valid=%b status=%h",addr,dut.resp_valid,dut.resp_status);
    value=dut.resp_data;
    pll_req=0;
    repeat (2) @(negedge dut.ref_clk);
endtask

task automatic initialize_fast(input logic [15:0] cfg);
    logic [15:0] value;
    integer attempts;
    force dut.req_valid = pll_req;
    force dut.req_write = pll_write;
    force dut.req_addr = pll_addr;
    force dut.req_data = pll_data;
    #(2*REF_PERIOD_NS+reset_extra_ns); pad_rst_n=0;
    #(10*REF_PERIOD_NS);
    @(negedge ref_clk); pad_rst_n=1;
    repeat (25) @(negedge ref_clk);
    pll_bus_access(1,8'h00,cfg,value);
    pll_bus_access(0,8'h00,0,value);
    if (value !== cfg) $fatal(1,"PLL shadow readback mismatch %h",value);
    pll_bus_access(1,8'h02,16'h0001,value);
    attempts=0; value=0;
    while (value !== 16'h0072 && attempts<250) begin
        pll_bus_access(0,8'h04,0,value);
        if (value[11:8] != 0) $fatal(1,"PLL startup error status=%h",value);
        attempts++;
    end
    if (value !== 16'h0072) $fatal(1,"PLL startup timeout status=%h",value);
    pll_bus_access(0,8'h06,0,value);
    if (value !== cfg) $fatal(1,"PLL active readback mismatch %h",value);
    // Keep unused boundary inputs deterministic and inactive, outside storage.
    pll_req=0; pll_write=0; pll_addr=0; pll_data=0;
    repeat (16) @(negedge launch_clk);
    check_startup_health;
    begin_fast_bus;
    $display("[FAST_INIT] PLL configured through real register bank; core ready ns=%.3f",$realtime);
endtask
