// Syntax-only fixture. Never simulate or use as functional evidence.
module pll_stub;
wire EN,CKTST;wire[7:0] N;wire[1:0] OD;
endmodule
module ff_stub;
wire CK,E,D,Q;
endmodule
module dut_stub;
wire core_clk,core_rst_n;
wire u_pbit_top_run_busy_w,u_pbit_top_run_done_w;
wire u_pbit_top_u_uart_reg_subsystem_reg_access_error_w;
pll_stub u_pll();ff_stub u_mac_contrib_ff();
endmodule
module gate_pipeline_env;
reg pad_rst_n=1,fast_wr=0,fast_rd=0;
reg[15:0]fast_addr=0;reg[31:0]fast_data=0;
real reset_extra_ns=0;
integer fast_transactions=0;
wire launch_clk;
dut_stub dut();
task automatic core_write(input logic[15:0]a,input logic[31:0]v);endtask
task automatic core_read(input logic[15:0]a,output logic[31:0]v);v=0;endtask
task automatic core_read_check(input logic[15:0]a,input logic[31:0]v);endtask
task automatic initialize_fast(input logic[15:0]c);endtask
task automatic end_fast_bus;endtask
endmodule
