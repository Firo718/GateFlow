"""
Block Design 模块使用示例

本示例展示如何使用 BlockDesignManager 创建和管理 Vivado Block Design。
"""

from pathlib import Path
from gateflow.vivado import TclEngine
from gateflow.vivado.block_design import (
    BlockDesignManager,
    BlockDesignTclGenerator,
    BDIPInstance,
    BDPort,
    BDConnection,
    ZynqPSConfig,
    BDInterfaceType,
)


def example_create_simple_bd():
    """示例：创建简单的 Block Design"""
    print("=== 示例 1: 创建简单的 Block Design ===\n")

    # 创建 Tcl 引擎（需要 Vivado 环境）
    # engine = TclEngine()

    # 创建 Block Design 管理器
    # bd_manager = BlockDesignManager(engine)

    # 创建新的 Block Design
    # result = await bd_manager.create_design("my_design")
    # if not result['success']:
    #     print(f"创建失败: {result['errors']}")
    #     return

    # 添加 Zynq PS
    ps_config = ZynqPSConfig(
        enable_fabric_reset=True,
        enable_fabric_clock=True,
        enable_uart0=True,
        enable_enet0=True,
    )
    print("Zynq PS 配置:")
    print(f"  - Fabric Reset: {ps_config.enable_fabric_reset}")
    print(f"  - Fabric Clock: {ps_config.enable_fabric_clock}")
    print(f"  - UART0: {ps_config.enable_uart0}")
    print(f"  - ENET0: {ps_config.enable_enet0}")

    # 生成 Tcl 命令
    commands = BlockDesignTclGenerator.create_zynq_ps_tcl(
        "processing_system7_0", ps_config
    )
    print("\n生成的 Tcl 命令:")
    for cmd in commands:
        print(f"  {cmd}")


def example_create_axi_gpio():
    """示例：创建 AXI GPIO"""
    print("\n=== 示例 2: 创建 AXI GPIO ===\n")

    # 创建 AXI GPIO 实例配置
    gpio_instance = BDIPInstance(
        name="axi_gpio_0",
        ip_type="xilinx.com:ip:axi_gpio:2.0",
        config={
            "C_GPIO_WIDTH": 8,
            "C_IS_DUAL": 0,
            "C_GPIO2_WIDTH": 8,
        }
    )

    print(f"IP 实例: {gpio_instance.name}")
    print(f"IP 类型: {gpio_instance.ip_type}")
    print(f"配置参数: {gpio_instance.config}")

    # 生成 Tcl 命令
    commands = BlockDesignTclGenerator.create_bd_cell_with_config_tcl(gpio_instance)
    print("\n生成的 Tcl 命令:")
    for cmd in commands:
        print(f"  {cmd}")


def example_create_axi_interconnect():
    """示例：创建 AXI Interconnect"""
    print("\n=== 示例 3: 创建 AXI Interconnect ===\n")

    # 创建 AXI Interconnect（1 个主接口，2 个从接口）
    commands = BlockDesignTclGenerator.create_axi_interconnect_tcl(
        name="axi_interconnect_0",
        num_mi=2,  # 2 个主接口（连接 2 个外设）
        num_si=1,  # 1 个从接口（连接 PS）
    )

    print("生成的 Tcl 命令:")
    for cmd in commands:
        print(f"  {cmd}")


def example_connect_ports():
    """示例：连接端口"""
    print("\n=== 示例 4: 连接端口 ===\n")

    # 创建连接配置
    axi_connection = BDConnection(
        name=None,  # 自动命名
        source="processing_system7_0/M_AXI_GP0",
        destination="axi_interconnect_0/S00_AXI",
    )

    print(f"AXI 连接: {axi_connection.source} -> {axi_connection.destination}")

    # 生成接口连接 Tcl 命令
    cmd = BlockDesignTclGenerator.connect_bd_intf_net_tcl(axi_connection)
    print(f"\n接口连接命令:\n  {cmd}")

    # 创建时钟连接
    clock_cmd = BlockDesignTclGenerator.connect_bd_net_tcl(
        source="processing_system7_0/FCLK_CLK0",
        destinations=[
            "axi_interconnect_0/ACLK",
            "axi_interconnect_0/S00_ACLK",
            "axi_gpio_0/s_axi_aclk",
        ]
    )
    print(f"\n时钟连接命令:\n  {clock_cmd}")


def example_create_external_ports():
    """示例：创建外部端口"""
    print("\n=== 示例 5: 创建外部端口 ===\n")

    # 创建普通端口
    clk_port = BDPort(name="clk_in", direction="input", width=1)
    rst_port = BDPort(name="rst_n", direction="input", width=1)
    data_port = BDPort(name="data_out", direction="output", width=32)

    print("普通端口:")
    for port in [clk_port, rst_port, data_port]:
        cmd = BlockDesignTclGenerator.create_bd_port_tcl(port)
        print(f"  {cmd}")

    # 创建接口端口（AXI4-Lite 主接口）
    axi_port = BDPort(
        name="M_AXI",
        direction="output",  # 接口端口方向
        interface_type=BDInterfaceType.AXI4LITE,
    )
    print(f"\n接口端口:")
    cmd = BlockDesignTclGenerator.create_bd_port_tcl(axi_port)
    print(f"  {cmd}")


def example_build_zynq_system():
    """示例：快速构建 Zynq 系统"""
    print("\n=== 示例 6: 快速构建 Zynq 系统 ===\n")

    print("这个示例展示了如何快速构建一个完整的 Zynq Block Design")
    print("包括：")
    print("  1. Zynq Processing System")
    print("  2. Processor System Reset")
    print("  3. AXI Interconnect")
    print("  4. 自动连接时钟和复位")
    print("  5. 应用自动连接规则")
    print("  6. 验证设计")
    print("  7. 生成 HDL Wrapper")

    print("\n代码示例:")
    print("""
    # 创建 Tcl 引擎
    engine = TclEngine()
    bd_manager = BlockDesignManager(engine)

    # 创建 Block Design
    await bd_manager.create_design("zynq_system")

    # 配置 PS
    ps_config = ZynqPSConfig(
        enable_fabric_reset=True,
        enable_fabric_clock=True,
        enable_uart0=True,
    )

    # 快速构建 Zynq 系统
    result = await bd_manager.build_zynq_design(
        ps_config=ps_config,
        axi_peripherals=['axi_gpio', 'axi_uart'],
    )

    if result['success']:
        # 生成 HDL Wrapper
        await bd_manager.generate_wrapper()
        print("Zynq 系统构建成功！")
    """)


def example_create_clock_wizard():
    """示例：创建 Clock Wizard"""
    print("\n=== 示例 7: 创建 Clock Wizard ===\n")

    # 创建 Clock Wizard（输入 100MHz，输出 50MHz 和 200MHz）
    commands = BlockDesignTclGenerator.create_clock_wizard_tcl(
        name="clk_wiz_0",
        input_freq=100.0,
        output_freqs=[50.0, 200.0],
    )

    print("生成的 Tcl 命令:")
    for cmd in commands:
        print(f"  {cmd}")


def example_create_dma():
    """示例：创建 AXI DMA"""
    print("\n=== 示例 8: 创建 AXI DMA ===\n")

    # 创建 AXI DMA（包含 Scatter-Gather）
    commands = BlockDesignTclGenerator.create_axi_dma_tcl(
        name="axi_dma_0",
        include_sg=True,
    )

    print("生成的 Tcl 命令:")
    for cmd in commands:
        print(f"  {cmd}")


def example_export_import_bd():
    """示例：导出和导入 Block Design"""
    print("\n=== 示例 9: 导出和导入 Block Design ===\n")

    print("导出 Block Design 为 Tcl 脚本:")
    cmd = BlockDesignTclGenerator.export_bd_tcl(
        bd_name="my_design",
        output_path=Path("./my_design.tcl"),
    )
    print(f"  {cmd}")

    print("\n从 Tcl 脚本导入 Block Design:")
    cmd = BlockDesignTclGenerator.import_bd_tcl(
        tcl_path=Path("./my_design.tcl"),
    )
    print(f"  {cmd}")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("Block Design 模块使用示例")
    print("=" * 60)

    example_create_simple_bd()
    example_create_axi_gpio()
    example_create_axi_interconnect()
    example_connect_ports()
    example_create_external_ports()
    example_build_zynq_system()
    example_create_clock_wizard()
    example_create_dma()
    example_export_import_bd()

    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
