/**
 * LED 闪烁模块
 *
 * 功能: 实现简单的 LED 闪烁效果
 * 平台: Xilinx Artix-7 (xc7a35tcpg236-1)
 *
 * 参数:
 *   CLK_FREQUENCY - 输入时钟频率 (Hz)
 *   BLINK_PERIOD  - LED 闪烁周期 (秒)
 *
 * 端口:
 *   clk   - 系统时钟输入
 *   rst_n - 异步复位，低电平有效
 *   led   - LED 输出
 */

module blink_led #(
    parameter CLK_FREQUENCY = 100_000_000,  // 默认 100MHz
    parameter BLINK_PERIOD  = 1             // 默认 1 秒闪烁周期
)(
    input  wire clk,      // 系统时钟
    input  wire rst_n,    // 异步复位 (低电平有效)
    output reg  led       // LED 输出
);

    // 计算计数器位宽和最大值
    localparam COUNTER_MAX = CLK_FREQUENCY * BLINK_PERIOD / 2 - 1;
    localparam COUNTER_WIDTH = $clog2(COUNTER_MAX + 1);

    // 计数器寄存器
    reg [COUNTER_WIDTH-1:0] counter;

    // 计数器逻辑
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            // 复位时计数器清零
            counter <= {COUNTER_WIDTH{1'b0}};
            led <= 1'b0;
        end else begin
            if (counter >= COUNTER_MAX) begin
                // 计数器达到最大值时翻转 LED
                counter <= {COUNTER_WIDTH{1'b0}};
                led <= ~led;
            end else begin
                // 正常计数
                counter <= counter + 1'b1;
            end
        end
    end

    // 仿真用: 显示当前状态
    `ifdef SIMULATION
    always @(posedge clk) begin
        if (counter == COUNTER_MAX) begin
            $display("[%0t] LED toggled to %b", $time, ~led);
        end
    end
    `endif

endmodule
