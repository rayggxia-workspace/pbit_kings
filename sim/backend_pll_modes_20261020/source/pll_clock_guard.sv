`timescale 1ns/10ps
module pll_clock_guard #(parameter integer ID=0)(
    input wire clk,rst_n,active,
    input realtime expected_half_ns
);
    realtime last_edge=-1,minimum=1.0e9,maximum=0;
    integer edges=0;
    always @(posedge active) begin
        last_edge=-1; minimum=1.0e9; maximum=0; edges=0;
    end
    always @(negedge rst_n)
        if (active) $fatal(1,"CLOCK_GUARD_UNEXPECTED_RESET id=%0d",ID);
    always @(clk) begin : EDGE_CHECK
        realtime delta;
        if (active && rst_n===1'b1) begin
            if (clk!==1'b0 && clk!==1'b1) $fatal(1,"CLOCK_GUARD_X id=%0d",ID);
            if (last_edge>=0) begin
                delta=$realtime-last_edge;
                if (delta<expected_half_ns-0.04 || delta>expected_half_ns+0.04)
                    $fatal(1,"CLOCK_GUARD_PULSE id=%0d actual=%f half=%f",ID,delta,expected_half_ns);
                if (delta<minimum) minimum=delta;
                if (delta>maximum) maximum=delta;
                edges++;
            end
            last_edge=$realtime;
        end else last_edge=-1;
    end
    initial forever begin
        #100;
        if (active && rst_n===1'b1 && last_edge>=0 &&
            $realtime-last_edge>2.0*expected_half_ns+0.1)
            $fatal(1,"CLOCK_GUARD_STOPPED id=%0d",ID);
    end
endmodule
