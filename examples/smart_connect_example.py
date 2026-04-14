"""
智能连接 API 使用示例。

演示如何使用 GateFlow.smart_connect 方法进行智能连接。
"""

import asyncio
from gateflow import GateFlow


async def example_smart_connect():
    """智能连接示例"""
    gf = GateFlow()

    # 1. 自动检测并连接接口
    # 智能检测到这是 AXI 接口连接，自动使用 connect_bd_intf_net
    result = await gf.smart_connect(
        "axi_interconnect_0/M00_AXI",
        "axi_gpio_0/S_AXI"
    )
    print(f"接口连接: {result['message']}")
    print(f"连接类型: {result['connect_type']}")

    # 2. 自动检测并连接信号
    # 智能检测到这是普通信号连接，自动使用 connect_bd_net
    result = await gf.smart_connect(
        "clk_wiz_0/clk_out1",
        "axi_gpio_0/s_axi_aclk"
    )
    print(f"信号连接: {result['message']}")
    print(f"连接类型: {result['connect_type']}")

    # 3. 连接到 GND
    # 自动创建 xlconstant IP，值为 0，并连接到目标
    result = await gf.smart_connect("GND", "ip_0/reset_pin")
    print(f"GND 连接: {result['message']}")
    print(f"常量 IP: {result.get('constant_ip')}")
    print(f"常量宽度: {result.get('constant_width')}")

    # 4. 连接到 VCC
    # 自动创建 xlconstant IP，值为全 1，并连接到目标
    result = await gf.smart_connect("VCC", "ip_0/enable_pin")
    print(f"VCC 连接: {result['message']}")
    print(f"常量 IP: {result.get('constant_ip')}")

    # 5. 使用数字表示常量
    # "0" 等同于 GND，"1" 等同于 VCC
    result = await gf.smart_connect("0", "ip_0/reset")
    print(f"常量 0 连接: {result['message']}")

    # 6. 连接外部端口
    # 自动检测到这是端口连接
    result = await gf.smart_connect("clk", "gpio_0/s_axi_aclk")
    print(f"端口连接: {result['message']}")

    # 7. 强制指定连接类型
    # 即使自动检测可能不准确，也可以强制指定类型
    result = await gf.smart_connect(
        "clk_wiz_0/clk_out1",
        "gpio_0/s_axi_aclk",
        connect_type="signal"  # 强制使用信号连接
    )
    print(f"强制信号连接: {result['message']}")

    # 8. 反向常量连接
    # 目标为常量，自动反向处理
    result = await gf.smart_connect("ip_0/reset", "GND")
    print(f"反向 GND 连接: {result['message']}")


async def example_complete_bd_workflow():
    """完整的 Block Design 连接工作流示例"""
    gf = GateFlow()

    # 创建 Block Design
    await gf.create_bd_design("system")

    # 添加 IP 实例
    await gf.add_bd_ip("xilinx.com:ip:processing_system7:5.5", "ps7_0")
    await gf.add_bd_ip("xilinx.com:ip:axi_gpio:2.0", "gpio_0")
    await gf.add_bd_ip("xilinx.com:ip:axi_interconnect:2.1", "interconnect_0")

    # 智能连接 AXI 接口
    await gf.smart_connect("ps7_0/M_AXI_GP0", "interconnect_0/S00_AXI")
    await gf.smart_connect("interconnect_0/M00_AXI", "gpio_0/S_AXI")

    # 智能连接时钟
    await gf.smart_connect("ps7_0/FCLK_CLK0", "gpio_0/s_axi_aclk")
    await gf.smart_connect("ps7_0/FCLK_CLK0", "interconnect_0/ACLK")
    await gf.smart_connect("ps7_0/FCLK_CLK0", "interconnect_0/S00_ACLK")
    await gf.smart_connect("ps7_0/FCLK_CLK0", "interconnect_0/M00_ACLK")

    # 智能连接复位
    await gf.smart_connect("ps7_0/FCLK_RESET0_N", "gpio_0/s_axi_aresetn")
    await gf.smart_connect("ps7_0/FCLK_RESET0_N", "interconnect_0/ARESETN")

    # 连接未使用的引脚到 GND
    await gf.smart_connect("GND", "gpio_0/ip2intc_irpt")

    # 验证设计
    result = await gf.validate_bd_design()
    print(f"设计验证: {result['message']}")


async def example_error_handling():
    """错误处理示例"""
    gf = GateFlow()

    # 尝试连接不存在的对象
    result = await gf.smart_connect("invalid_source", "invalid_target")
    if not result["success"]:
        print(f"连接失败: {result['error']}")

    # 尝试连接类型不匹配的对象
    result = await gf.smart_connect(
        "interconnect_0/M00_AXI",  # 接口
        "gpio_0/s_axi_aclk",      # 信号
        connect_type="signal"  # 强制使用信号连接
    )
    if not result["success"]:
        print(f"连接失败: {result['error']}")


async def main():
    """主函数"""
    print("=== 智能连接 API 示例 ===\n")

    print("1. 基本连接示例:")
    await example_smart_connect()

    print("\n2. 完整工作流示例:")
    await example_complete_bd_workflow()

    print("\n3. 错误处理示例:")
    await example_error_handling()


if __name__ == "__main__":
    asyncio.run(main())
