`timescale 1ns/10ps
module tb_vendor_stop;
    reg refclk=0,en=0,bp=0;
    wire ck1,ck2,testclk;
    tri high,low;
    integer fd,phase=0;
    realtime offset_ns;
    assign high=1'b1; assign low=1'b0;
    always #20 refclk=~refclk;
    PLL_TOP dut(.EN(en),.BP(bp),.N(8'd24),.SELECT(1'b0),.OD(2'b01),.REFCLK(refclk),
        .AVDD(high),.AVSS(low),.DVDD(high),.DVSS(low),.DVDD_DRV(high),.DVSS_DRV(low),
        .CKOUT1(ck1),.CKOUT2(ck2),.CKTST(testclk));
    always @(en) if(fd) $fdisplay(fd,"%.3f,en,%b,%0d",$realtime,en,phase);
    always @(ck1) if(fd) $fdisplay(fd,"%.3f,ckout,%b,%0d",$realtime,ck1,phase);
    always @(testclk) if(fd) $fdisplay(fd,"%.3f,cktst,%b,%0d",$realtime,testclk,phase);
    initial begin
        fd=$fopen("model_trace.csv","w");
        if(!fd) $fatal(1,"Cannot open model trace");
        $fdisplay(fd,"ns,signal,value,phase");
        for(phase=0;phase<5;phase++) begin
            #400; en=1; #4000;
            repeat(12) @(negedge ck1);
            if(^({ck1,ck2,testclk})===1'bx) $fatal(1,"Vendor clock X before stop");
            case(phase)
                0:offset_ns=0;
                1:offset_ns=0.83;
                2:offset_ns=1.67;
                3:offset_ns=20;
                4:offset_ns=53.33;
            endcase
            #(offset_ns); en=0;
            #200;
            if(ck1!==0 || ck2!==0 || testclk!==0) $fatal(1,"Vendor clock failed to stop");
            $display("[VENDOR_STOP_PHASE] complete phase=%0d offset=%f",phase,offset_ns);
        end
        $fflush(); $display("[VENDOR_STOP_COMPLETE] unchanged vendor behavior; not silicon proof");
        $finish;
    end
    initial begin #1ms; $fatal(1,"Vendor stop watchdog"); end
endmodule
