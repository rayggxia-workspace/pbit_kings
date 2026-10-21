// TEST ONLY: declarations for local elaboration and host-codec tests, not RTL.
`timescale 1ns/10ps
module ff_stub(input wire CK);
    wire D=0,Q=0;
endmodule
module pll_stub(inout wire DVDD,DVSS,DVDD_DRV,DVSS_DRV);
    wire EN=0,BP=0,CKTST=0,CKOUT1=0;wire [7:0] N=24;wire[1:0] OD=1;
endmodule
module pbit_io_wrapper(input wire pad_clk_i,pad_rst_n_i,pad_uart_rx_i,pad_pll_cfg_rx_i,
                       output wire pad_uart_tx_o,pad_pll_cfg_tx_o,inout wire pll_avdd,pll_avss);
    reg fake_tx=1;
    assign pad_uart_tx_o=fake_tx;assign pad_pll_cfg_tx_o=1;
    wire ref_clk=pad_clk_i,core_clk=pad_clk_i,core_rst_n=pad_rst_n_i;
    wire req_valid,req_write,resp_valid;
    wire [7:0] req_addr;wire [15:0] req_data,resp_data;wire [1:0] resp_status;
    wire u_pbit_top_u_uart_reg_subsystem_reg_wr_en_w,u_pbit_top_u_uart_reg_subsystem_reg_rd_en_w;
    wire [15:0] u_pbit_top_u_uart_reg_subsystem_reg_addr_w;
    wire [31:0] u_pbit_top_u_uart_reg_subsystem_reg_wdata_w,u_pbit_top_u_uart_reg_subsystem_reg_rdata_w;
    wire u_pbit_top_u_uart_reg_subsystem_reg_access_error_w;
    pll_stub u_pll();
    ff_stub u_pbit_top_u_uart_reg_subsystem_u_pbit_uart_reg_master_req_wr_en_ff_q_o_reg_0_(pad_clk_i);
    ff_stub u_pbit_top_u_uart_reg_subsystem_u_pbit_uart_reg_master_req_addr_ff_q_o_reg_3_(pad_clk_i);
endmodule
