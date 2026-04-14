"""
GateFlow 简单项目创建示例。

本示例演示如何使用 GateFlow MCP 工具创建一个基本的 Vivado FPGA 项目。
这个示例可以通过 AI 工具（如 Claude、Cursor）执行，也可以作为参考。

使用方法:
1. 在 AI 工具中直接描述需求，AI 会调用相应的 MCP 工具
2. 或参考此示例了解 GateFlow 的使用方式
"""

# ============================================================================
# 示例 1: 创建基本项目
# ============================================================================

"""
用户: 帮我创建一个 Artix-7 FPGA 项目

AI 将执行以下步骤:
"""

# 步骤 1: 创建项目
# create_project(
#     name="my_project",
#     path="D:/projects/my_project",
#     part="xc7a35tcpg236-1"  # Artix-7 35T
# )

# 步骤 2: 添加源文件
# add_source_files(
#     files=["D:/projects/my_project/src/top.v"],
#     file_type="verilog"
# )

# 步骤 3: 设置顶层模块
# set_top_module(module_name="top")

# 步骤 4: 添加约束文件
# add_source_files(
#     files=["D:/projects/my_project/constraints/top.xdc"],
#     file_type="xdc"
# )

# 步骤 5: 创建时钟约束
# create_clock(
#     name="clk",
#     period=10.0,  # 100MHz
#     target="clk"
# )

# ============================================================================
# 示例 2: 完整的构建流程
# ============================================================================

"""
用户: 运行综合和实现，生成比特流

AI 将执行以下步骤:
"""

# 步骤 1: 运行综合
# result = run_synthesis()
# if result.success:
#     print("综合完成")

# 步骤 2: 查看资源利用率
# report = get_utilization_report()
# print(f"LUT 使用率: {report.utilization['LUT']['percentage']}%")

# 步骤 3: 运行实现
# result = run_implementation()
# if result.success:
#     print("实现完成")

# 步骤 4: 检查时序
# timing = get_timing_report()
# if timing.timing.get("timing_met"):
#     print("时序满足要求")
# else:
#     print("时序违例!")

# 步骤 5: 生成比特流
# result = generate_bitstream()
# if result.success:
#     print(f"比特流已生成: {result.bitstream_path}")

# ============================================================================
# 示例 3: 硬件编程
# ============================================================================

"""
用户: 连接硬件服务器并编程 FPGA

AI 将执行以下步骤:
"""

# 步骤 1: 连接硬件服务器
# result = connect_hw_server(url="localhost:3121")
# if result.success:
#     print(f"连接成功，发现 {result.device_count} 个设备")

# 步骤 2: 获取设备列表
# devices = get_hw_devices()
# for device in devices.devices:
#     print(f"设备: {device['name']}")

# 步骤 3: 编程 FPGA
# result = program_fpga(device_index=0)
# if result.success:
#     print(f"设备 {result.device_name} 编程成功")

# ============================================================================
# 示例 4: 使用 IP 核
# ============================================================================

"""
用户: 创建一个时钟管理 IP，输入 100MHz，输出 50MHz 和 200MHz

AI 将执行以下步骤:
"""

# 步骤 1: 创建 Clocking Wizard IP
# result = create_clocking_wizard(
#     name="clk_wiz_0",
#     input_frequency=100.0,  # 100MHz 输入
#     output_clocks=[
#         {"name": "clk_out1", "frequency": 50.0},   # 50MHz 输出
#         {"name": "clk_out2", "frequency": 200.0},  # 200MHz 输出
#     ]
# )

# 步骤 2: 生成 IP 输出产品
# generate_ip_outputs(ip_name="clk_wiz_0")

# ============================================================================
# 示例 5: Block Design
# ============================================================================

"""
用户: 创建一个包含 Zynq PS 和 AXI GPIO 的 Block Design

AI 将执行以下步骤:
"""

# 步骤 1: 创建 Block Design
# create_bd_design(name="system")

# 步骤 2: 添加 Zynq PS IP
# add_bd_ip(
#     ip_type="xilinx.com:ip:processing_system7:5.7",
#     instance_name="processing_system7_0"
# )

# 步骤 3: 添加 AXI GPIO IP
# add_bd_ip(
#     ip_type="xilinx.com:ip:axi_gpio:2.0",
#     instance_name="axi_gpio_0",
#     config={"CONFIG.C_GPIO_WIDTH": "8"}
# )

# 步骤 4: 应用自动连接
# apply_bd_automation(rule="all")

# 步骤 5: 验证设计
# result = validate_bd_design()
# if result.success:
#     print("Block Design 验证通过")

# 步骤 6: 生成 HDL Wrapper
# generate_bd_wrapper()

# ============================================================================
# 示例 6: 仿真
# ============================================================================

"""
用户: 创建仿真集并运行行为仿真

AI 将执行以下步骤:
"""

# 步骤 1: 创建仿真集
# create_simulation_set(
#     name="sim_1",
#     sources=["D:/projects/my_project/sim/tb_top.v"]
# )

# 步骤 2: 设置仿真顶层
# set_simulation_top(module="tb_top", sim_set="sim_1")

# 步骤 3: 启动仿真
# launch_simulation(
#     mode="behavioral",
#     run_time="1ms",
#     gui=True  # 打开波形窗口
# )

# 步骤 4: 添加波形信号
# add_wave_signal(signal="tb_top/clk", radix="binary")
# add_wave_signal(signal="tb_top/data", radix="hex")

# ============================================================================
# 完整示例: LED 闪烁项目
# ============================================================================

"""
用户: 创建一个完整的 LED 闪烁项目，包含源文件、约束、综合和编程

以下是完整的交互示例:
"""

# 对话示例:
#
# 用户: 帮我创建一个 LED 闪烁项目，使用 Artix-7 FPGA
#
# AI: 好的，我将为您创建一个 LED 闪烁项目。
#
# [调用 create_project]
# [调用 add_source_files]
# [调用 set_top_module]
# [调用 add_source_files (约束)]
# [调用 create_clock]
#
# AI: 项目已创建完成。是否需要运行综合?
#
# 用户: 是的，运行综合并生成比特流
#
# AI: [调用 run_synthesis]
# AI: 综合完成，资源利用率: LUT 5%, FF 2%
# AI: [调用 run_implementation]
# AI: 实现完成，时序满足要求
# AI: [调用 generate_bitstream]
# AI: 比特流已生成
#
# 用户: 编程到 FPGA
#
# AI: [调用 connect_hw_server]
# AI: [调用 program_fpga]
# AI: FPGA 编程成功!

# ============================================================================
# 提示和最佳实践
# ============================================================================

"""
1. 项目命名规范:
   - 使用有意义的项目名称
   - 避免使用空格和特殊字符
   - 建议使用下划线分隔单词

2. 文件组织:
   - src/ - 源文件目录
   - constraints/ - 约束文件目录
   - sim/ - 仿真文件目录
   - ip/ - IP 核目录

3. 约束管理:
   - 先创建时钟约束
   - 再添加 IO 约束
   - 最后添加时序例外约束

4. 构建流程:
   - 综合后检查资源利用率
   - 实现后检查时序报告
   - 时序违例时分析关键路径

5. 调试技巧:
   - 使用行为仿真验证功能
   - 使用时序仿真验证时序
   - 使用 ILA 进行硬件调试
"""

if __name__ == "__main__":
    print(__doc__)
    print("\n本文件为示例文档，展示了如何通过自然语言与 GateFlow 交互。")
    print("请在 AI 工具（如 Claude、Cursor）中使用自然语言描述您的需求。")
