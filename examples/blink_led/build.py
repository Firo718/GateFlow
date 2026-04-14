"""
GateFlow LED 闪烁项目构建脚本

本脚本演示如何使用 GateFlow MCP 工具自动化构建 LED 闪烁项目。
可以通过 AI 工具执行，也可以作为 Python 脚本参考。

使用方法:
1. 在 AI 工具中描述需求
2. 或直接运行此脚本 (需要 GateFlow 环境)

项目信息:
- 目标器件: xc7a35tcpg236-1 (Artix-7 35T)
- 功能: LED 闪烁，周期 1 秒
- 时钟: 100MHz
"""

import os
from pathlib import Path

# 项目配置
PROJECT_NAME = "blink_led"
PROJECT_PATH = Path(__file__).parent.absolute()
TARGET_PART = "xc7a35tcpg236-1"

# 源文件
VERILOG_SOURCES = [
    PROJECT_PATH / "blink_led.v"
]

CONSTRAINT_FILES = [
    PROJECT_PATH / "blink_led.xdc"
]


def build_project_workflow():
    """
    完整的项目构建工作流程。

    这个函数展示了使用 GateFlow 构建项目的完整步骤。
    在 AI 工具中，这些步骤会通过自然语言交互自动执行。
    """

    workflow = """
    ## GateFlow LED 闪烁项目构建流程

    ### 步骤 1: 创建项目

    用户: 创建一个名为 "blink_led" 的 Vivado 项目，
          目标器件是 xc7a35tcpg236-1，
          保存在 {project_path}

    AI 执行:
    - create_project(
        name="{project_name}",
        path="{project_path}",
        part="{target_part}"
      )

    ### 步骤 2: 添加源文件

    用户: 添加 blink_led.v 源文件

    AI 执行:
    - add_source_files(
        files=["{verilog_source}"],
        file_type="verilog"
      )

    ### 步骤 3: 设置顶层模块

    用户: 将 blink_led 设置为顶层模块

    AI 执行:
    - set_top_module(module_name="blink_led")

    ### 步骤 4: 添加约束文件

    用户: 添加约束文件 blink_led.xdc

    AI 执行:
    - add_source_files(
        files=["{constraint_file}"],
        file_type="xdc"
      )

    ### 步骤 5: 运行综合

    用户: 运行综合

    AI 执行:
    - run_synthesis()

    AI 响应: 综合完成，正在生成资源利用率报告...

    - get_utilization_report()

    AI 响应: 资源利用率:
             - LUT: 12 / 20800 (0.06%)
             - FF:  27 / 41600 (0.06%)
             - 设计非常小，资源充足

    ### 步骤 6: 运行实现

    用户: 运行实现

    AI 执行:
    - run_implementation()

    AI 响应: 实现完成，正在检查时序...

    - get_timing_report()

    AI 响应: 时序报告:
             - Setup Slack: 8.234ns (满足)
             - Hold Slack:  0.156ns (满足)
             - 时序满足要求

    ### 步骤 7: 生成比特流

    用户: 生成比特流

    AI 执行:
    - generate_bitstream()

    AI 响应: 比特流已生成:
             {project_path}/blink_led.runs/impl_1/blink_led.bit

    ### 步骤 8: 编程 FPGA (可选)

    用户: 连接硬件服务器并编程 FPGA

    AI 执行:
    - connect_hw_server(url="localhost:3121")

    AI 响应: 已连接到硬件服务器，发现 1 个设备

    - get_hw_devices()

    AI 响应: 设备列表:
             - 设备 0: xc7a35t_0

    - program_fpga(device_index=0)

    AI 响应: FPGA 编程成功！LED 应该开始闪烁。
    """.format(
        project_path=str(PROJECT_PATH),
        project_name=PROJECT_NAME,
        target_part=TARGET_PART,
        verilog_source=str(VERILOG_SOURCES[0]),
        constraint_file=str(CONSTRAINT_FILES[0])
    )

    return workflow


def quick_start_guide():
    """快速开始指南。"""

    guide = """
    ## 快速开始

    ### 方式 1: 使用 AI 工具 (推荐)

    在 Claude Desktop 或 Cursor 中:

    1. 确保 GateFlow MCP 服务器已配置
    2. 打开此目录
    3. 输入: "帮我构建这个 LED 闪烁项目"
    4. AI 会自动执行所有构建步骤

    ### 方式 2: 使用命令行

    如果你已经安装了 GateFlow:

    ```bash
    # 进入项目目录
    cd examples/blink_led

    # 在 AI 工具中打开并描述需求
    # 或使用 Vivado Tcl 控制台
    ```

    ### 方式 3: 使用 Vivado GUI

    1. 打开 Vivado
    2. 创建新项目
    3. 添加源文件和约束文件
    4. 运行综合和实现
    5. 生成比特流
    6. 编程 FPGA

    ## 项目参数

    可以通过修改 Verilog 参数来调整闪烁频率:

    - CLK_FREQUENCY: 时钟频率 (默认 100MHz)
    - BLINK_PERIOD:  闪烁周期 (默认 1 秒)

    示例: 修改为 0.5 秒闪烁周期

    在实例化时:
    ```verilog
    blink_led #(
        .CLK_FREQUENCY(100_000_000),
        .BLINK_PERIOD(0.5)  // 0.5 秒
    ) u_blink_led (
        .clk(clk),
        .rst_n(rst_n),
        .led(led)
    );
    ```
    """

    return guide


def simulation_guide():
    """仿真指南。"""

    guide = """
    ## 仿真指南

    ### 创建 Testbench

    创建文件: tb_blink_led.v

    ```verilog
    `timescale 1ns / 1ps

    module tb_blink_led;

        // 测试参数 (使用较短的闪烁周期以加快仿真)
        parameter CLK_FREQUENCY = 100_000_000;
        parameter BLINK_PERIOD = 0.001;  // 1ms for simulation

        // 输入
        reg clk;
        reg rst_n;

        // 输出
        wire led;

        // 实例化被测模块
        blink_led #(
            .CLK_FREQUENCY(CLK_FREQUENCY),
            .BLINK_PERIOD(BLINK_PERIOD)
        ) uut (
            .clk(clk),
            .rst_n(rst_n),
            .led(led)
        );

        // 时钟生成
        initial begin
            clk = 0;
            forever #5 clk = ~clk;  // 100MHz
        end

        // 测试流程
        initial begin
            // 初始化
            rst_n = 0;
            #100;
            rst_n = 1;

            // 等待几个闪烁周期
            #(BLINK_PERIOD * 1_000_000_000 * 5);

            // 结束仿真
            $display("Simulation completed successfully!");
            $finish;
        end

        // 监控 LED 变化
        always @(posedge led or negedge led) begin
            $display("[%0t] LED = %b", $time, led);
        end

    endmodule
    ```

    ### 使用 GateFlow 运行仿真

    用户: 创建仿真集并运行行为仿真

    AI 执行:
    - create_simulation_set(
        name="sim_1",
        sources=["tb_blink_led.v"]
      )
    - set_simulation_top(module="tb_blink_led")
    - launch_simulation(mode="behavioral", run_time="10ms")

    AI 响应: 仿真完成，LED 翻转了 5 次
    """

    return guide


def troubleshooting():
    """故障排除指南。"""

    guide = """
    ## 故障排除

    ### 问题 1: 时序违例

    症状: get_timing_report() 显示负的 Slack

    解决方案:
    - 检查时钟约束是否正确
    - 降低时钟频率
    - 添加流水线寄存器

    ### 问题 2: LED 不闪烁

    检查清单:
    1. 确认比特流已正确下载
    2. 检查引脚约束是否与开发板匹配
    3. 确认时钟信号是否正常
    4. 检查复位信号状态

    ### 问题 3: 资源利用率异常

    如果资源利用率过高:
    - 检查是否有意外的综合优化设置
    - 确认参数设置是否合理

    ### 问题 4: 无法连接硬件服务器

    解决方案:
    1. 确认 Vivado 硬件服务器正在运行
    2. 检查 JTAG 连接
    3. 确认驱动已正确安装

    用户: 连接硬件服务器失败

    AI 响应: 让我帮你检查问题...
    - get_hw_server_status()
    - 建议检查硬件服务器是否启动
    - 建议检查 JTAG 连接
    """

    return guide


def main():
    """主函数。"""

    print("=" * 70)
    print("GateFlow LED 闪烁项目构建脚本")
    print("=" * 70)
    print()

    print("项目信息:")
    print(f"  项目名称: {PROJECT_NAME}")
    print(f"  项目路径: {PROJECT_PATH}")
    print(f"  目标器件: {TARGET_PART}")
    print()

    print("源文件:")
    for src in VERILOG_SOURCES:
        print(f"  - {src}")
    print()

    print("约束文件:")
    for xdc in CONSTRAINT_FILES:
        print(f"  - {xdc}")
    print()

    print("=" * 70)
    print("构建工作流程")
    print("=" * 70)
    print(build_project_workflow())

    print("=" * 70)
    print("快速开始指南")
    print("=" * 70)
    print(quick_start_guide())

    print("=" * 70)
    print("仿真指南")
    print("=" * 70)
    print(simulation_guide())

    print("=" * 70)
    print("故障排除")
    print("=" * 70)
    print(troubleshooting())

    print("=" * 70)
    print("提示: 在 AI 工具中使用自然语言描述需求即可自动执行构建流程")
    print("=" * 70)


if __name__ == "__main__":
    main()
