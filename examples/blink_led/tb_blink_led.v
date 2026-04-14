`timescale 1ns / 1ps

module tb_blink_led;

    localparam CLK_FREQUENCY = 8;
    localparam BLINK_PERIOD = 1;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    wire led;

    integer toggle_count = 0;

    blink_led #(
        .CLK_FREQUENCY(CLK_FREQUENCY),
        .BLINK_PERIOD(BLINK_PERIOD)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .led(led)
    );

    always #5 clk = ~clk;

    initial begin
        $display("tb_blink_led: start");
        #20;
        rst_n = 1'b1;
        #200;
        $display("tb_blink_led: toggles=%0d", toggle_count);
        $finish;
    end

    always @(posedge led or negedge led) begin
        if (rst_n) begin
            toggle_count = toggle_count + 1;
        end
    end

endmodule
