`timescale 1ns/10ps
module ff_recovery_watch #(parameter integer INDEX=0)(
    input wire ck,en,d,q,rst_n,observe,
    output reg refreshed=0,
    output reg [31:0] writes=0
);
    reg pending=0, sampled_d=0;
    always @(posedge ck or negedge rst_n) begin
        if (rst_n !== 1'b1) pending=0;
        else begin
            pending=0;
            if (observe) begin
                if (en !== 1'b0 && en !== 1'b1) $fatal(1,"WATCH_UNKNOWN_ENABLE index=%0d",INDEX);
                if (en === 1'b1) begin
                    if (d !== 1'b0 && d !== 1'b1) $fatal(1,"WATCH_UNKNOWN_DATA index=%0d",INDEX);
                    sampled_d=d;
                    pending=1;
                end
            end
        end
    end
    // Check settled Q on the same physical clock branch, not an ideal root clock.
    always @(negedge ck or negedge rst_n) begin
        if (rst_n !== 1'b1) begin refreshed=0; writes=0; end
        else if (observe && pending) begin
            if (q !== sampled_d) $fatal(1,"WATCH_CAPTURE_MISMATCH index=%0d d=%b q=%b",INDEX,sampled_d,q);
            refreshed=1;
            writes=writes+1;
        end
    end
endmodule
