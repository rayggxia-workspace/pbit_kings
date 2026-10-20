`timescale 1ns/10ps
module pll_clock_guard #(parameter integer ID=0)(
    input wire clk,rst_n,active,
    input realtime expected_half_ns
);
    realtime last_edge=-1,last_rise=-1,minimum=1.0e9,maximum=0;
    realtime high_min=1.0e9,high_max=0,low_min=1.0e9,low_max=0;
    realtime period_min=1.0e9,period_max=0;
    integer edges=0,periods=0;
    always @(posedge active) begin
        last_edge=-1; last_rise=-1; minimum=1.0e9; maximum=0; edges=0; periods=0;
        high_min=1.0e9; high_max=0; low_min=1.0e9; low_max=0;
        period_min=1.0e9; period_max=0;
    end
    always @(negedge rst_n)
        if (active) $fatal(1,"CLOCK_GUARD_UNEXPECTED_RESET id=%0d",ID);
    always @(clk) begin : EDGE_CHECK
        realtime delta;
        if (active && rst_n===1'b1) begin
            if (clk!==1'b0 && clk!==1'b1) $fatal(1,"CLOCK_GUARD_X id=%0d",ID);
            if (last_edge>=0) begin
                delta=$realtime-last_edge;
                // Frequency and duty distortion are different checks. This 10%
                // pulse budget is a diagnostic limit, not a library WIDTH rule.
                if (delta<expected_half_ns*0.9 || delta>expected_half_ns*1.1)
                    $fatal(1,"CLOCK_GUARD_PULSE id=%0d actual=%f half=%f",ID,delta,expected_half_ns);
                if (delta<minimum) minimum=delta;
                if (delta>maximum) maximum=delta;
                if (clk===0) begin
                    if (delta<high_min) high_min=delta;
                    if (delta>high_max) high_max=delta;
                end else begin
                    if (delta<low_min) low_min=delta;
                    if (delta>low_max) low_max=delta;
                end
                edges++;
            end
            if (clk===1) begin
                if (last_rise>=0) begin
                    delta=$realtime-last_rise;
                    if (delta<2*expected_half_ns-0.04 || delta>2*expected_half_ns+0.04)
                        $fatal(1,"CLOCK_GUARD_PERIOD id=%0d actual=%f period=%f",ID,delta,2*expected_half_ns);
                    if (delta<period_min) period_min=delta;
                    if (delta>period_max) period_max=delta;
                    periods++;
                end
                last_rise=$realtime;
            end
            last_edge=$realtime;
        end else begin last_edge=-1; last_rise=-1; end
    end
    initial forever begin
        #100;
        if (active && rst_n===1'b1 && last_edge>=0 &&
            $realtime-last_edge>2.0*expected_half_ns+0.1)
            $fatal(1,"CLOCK_GUARD_STOPPED id=%0d",ID);
    end
endmodule
