"""
Processing System7 模块封装

提供 Zynq-7000 Processing System IP 核的封装，参考 ADI hdl-main 项目的设计模式。
"""

import logging
from typing import Any

from gateflow.modules.base import (
    IPCategory,
    IPModule,
    IPPort,
    IPProperty,
    register_module,
)

logger = logging.getLogger(__name__)


@register_module
class ProcessingSystem7(IPModule):
    """
    Processing System7 模块封装
    
    Zynq-7000 Processing System 是 ARM Cortex-A9 双核处理系统 IP。
    
    Features:
        - ARM Cortex-A9 双核处理器
        - DDR 内存控制器
        - 多种外设接口 (UART, SPI, I2C, CAN, Ethernet, USB, SD, GPIO)
        - PL 时钟和复位输出
        - AXI 主从接口
    
    Example:
        # 创建 Processing System7 实例
        ps7 = ProcessingSystem7(tcl_engine)
        result = await ps7.create("processing_system7_0", {
            "preset": "ZedBoard",
            "enable_fabric_clock": True,
            "enable_fabric_reset": True,
            "enable_uart": True,
        })
        
        # 连接 PS7
        await ps7.connect("processing_system7_0", {
            "M_AXI_GP0": "axi_interconnect_0/S00_AXI",
            "FCLK_CLK0": "processing_clk",
        })
    """
    
    # IP 基本信息
    ip_name = "processing_system7"
    ip_display_name = "Processing System7"
    ip_category = IPCategory.PROCESSING
    ip_version = "5.5"
    ip_description = "Zynq-7000 Processing System - ARM Cortex-A9 Dual-Core"
    ip_documentation_url = "https://docs.xilinx.com/r/en-US/pg082-processing-system7"
    
    def __init__(self, tcl_engine=None):
        """初始化 Processing System7 模块"""
        super().__init__(tcl_engine)
    
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 Processing System7 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典，支持以下参数：
                - preset: 预设开发板配置名称 (如 "ZC702", "ZedBoard")
                - enable_fabric_clock: 是否启用 PL 时钟输出，默认 True
                - enable_fabric_reset: 是否启用 PL 复位输出，默认 True
                - enable_ddr: 是否启用 DDR 控制器，默认 True
                - enable_uart: 是否启用 UART，默认 True
                - enable_ethernet: 是否启用以太网，默认 False
                - enable_usb: 是否启用 USB，默认 False
                - enable_sd: 是否启用 SD 卡接口，默认 False
                - enable_gpio: 是否启用 GPIO，默认 False
                - enable_i2c: 是否启用 I2C，默认 False
                - enable_spi: 是否启用 SPI，默认 False
                - enable_can: 是否启用 CAN，默认 False
                - enable_ttc: 是否启用 TTC 定时器，默认 False
                - fclk_frequency: FCLK_CLK0 频率 (MHz)，默认 100
                - enable_m_axi_gp0: 是否启用 M_AXI_GP0，默认 True
                - enable_m_axi_gp1: 是否启用 M_AXI_GP1，默认 False
                - enable_s_axi_hp0: 是否启用 S_AXI_HP0，默认 False
                - enable_s_axi_hp1: 是否启用 S_AXI_HP1，默认 False
                - enable_s_axi_hp2: 是否启用 S_AXI_HP2，默认 False
                - enable_s_axi_hp3: 是否启用 S_AXI_HP3，默认 False
                - enable_s_axi_acp: 是否启用 S_AXI_ACP，默认 False
        
        Returns:
            创建结果字典
        
        Example:
            # 创建 ZedBoard 预设配置
            result = await ps7.create("processing_system7_0", {
                "preset": "ZedBoard",
                "enable_uart": True,
                "enable_ethernet": True,
            })
        """
        if not self._tcl_engine:
            return {
                "success": False,
                "error": "Tcl 引擎未初始化",
            }
        
        # 合并默认配置
        final_config = self.get_default_config()
        if config:
            final_config.update(config)
        
        # 验证配置
        valid, errors = self.validate_config(final_config)
        if not valid:
            return {
                "success": False,
                "error": "配置验证失败",
                "errors": errors,
            }
        
        # 生成创建命令
        commands = [self._generate_create_command(instance_name)]
        
        # 生成配置命令
        if final_config:
            tcl_config = self._convert_config_to_tcl(final_config)
            commands.append(self._generate_config_commands(instance_name, tcl_config))
        
        # 执行命令
        result = await self._tcl_engine.execute_async(commands)
        
        if result.success:
            # 注册实例
            self._register_instance(instance_name, instance_name, final_config)
            logger.info(f"Processing System7 实例创建成功: {instance_name}")
        else:
            logger.error(f"Processing System7 实例创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "module_name": instance_name,
            "message": f"Processing System7 实例 {instance_name} 创建成功" if result.success else "创建失败",
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "preset": None,
            "enable_fabric_clock": True,
            "enable_fabric_reset": True,
            "enable_ddr": True,
            "enable_uart": True,
            "enable_ethernet": False,
            "enable_usb": False,
            "enable_sd": False,
            "enable_gpio": False,
            "enable_i2c": False,
            "enable_spi": False,
            "enable_can": False,
            "enable_ttc": False,
            "fclk_frequency": 100,
            "enable_m_axi_gp0": True,
            "enable_m_axi_gp1": False,
            "enable_s_axi_hp0": False,
            "enable_s_axi_hp1": False,
            "enable_s_axi_hp2": False,
            "enable_s_axi_hp3": False,
            "enable_s_axi_acp": False,
        }
    
    def get_available_properties(self) -> list[IPProperty]:
        """获取可配置属性列表"""
        return [
            IPProperty(
                name="preset",
                value=None,
                description="预设开发板配置",
                value_type="string",
                valid_values=["ZC702", "ZC706", "ZedBoard", "MicroZed", "PYNQ"],
            ),
            IPProperty(
                name="enable_fabric_clock",
                value=True,
                description="启用 PL 时钟输出",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="enable_fabric_reset",
                value=True,
                description="启用 PL 复位输出",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="enable_ddr",
                value=True,
                description="启用 DDR 控制器",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="enable_uart",
                value=True,
                description="启用 UART",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="enable_ethernet",
                value=False,
                description="启用以太网",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="enable_usb",
                value=False,
                description="启用 USB",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="enable_sd",
                value=False,
                description="启用 SD 卡接口",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="enable_gpio",
                value=False,
                description="启用 GPIO",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="fclk_frequency",
                value=100,
                description="FCLK_CLK0 频率 (MHz)",
                value_type="int",
                default=100,
                min_value=10,
                max_value=250,
            ),
            IPProperty(
                name="enable_m_axi_gp0",
                value=True,
                description="启用 M_AXI_GP0 主接口",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="enable_s_axi_hp0",
                value=False,
                description="启用 S_AXI_HP0 从接口",
                value_type="bool",
                default=False,
            ),
        ]
    
    def get_ports(self) -> list[IPPort]:
        """获取端口列表"""
        ports = [
            # AXI 主接口
            IPPort(
                name="M_AXI_GP0",
                direction="inout",
                description="AXI 主接口 0",
                is_interface=True,
                interface_type="AXI4",
            ),
            IPPort(
                name="M_AXI_GP1",
                direction="inout",
                description="AXI 主接口 1",
                is_interface=True,
                interface_type="AXI4",
            ),
            # AXI 从接口 (高性能)
            IPPort(
                name="S_AXI_HP0",
                direction="inout",
                description="AXI 高性能从接口 0",
                is_interface=True,
                interface_type="AXI4",
            ),
            IPPort(
                name="S_AXI_HP1",
                direction="inout",
                description="AXI 高性能从接口 1",
                is_interface=True,
                interface_type="AXI4",
            ),
            IPPort(
                name="S_AXI_HP2",
                direction="inout",
                description="AXI 高性能从接口 2",
                is_interface=True,
                interface_type="AXI4",
            ),
            IPPort(
                name="S_AXI_HP3",
                direction="inout",
                description="AXI 高性能从接口 3",
                is_interface=True,
                interface_type="AXI4",
            ),
            # AXI 从接口 (ACP)
            IPPort(
                name="S_AXI_ACP",
                direction="inout",
                description="AXI ACP 从接口",
                is_interface=True,
                interface_type="AXI4",
            ),
            # PL 时钟输出
            IPPort(
                name="FCLK_CLK0",
                direction="output",
                width=1,
                description="PL 时钟 0",
                is_clock=True,
            ),
            IPPort(
                name="FCLK_CLK1",
                direction="output",
                width=1,
                description="PL 时钟 1",
                is_clock=True,
            ),
            IPPort(
                name="FCLK_CLK2",
                direction="output",
                width=1,
                description="PL 时钟 2",
                is_clock=True,
            ),
            IPPort(
                name="FCLK_CLK3",
                direction="output",
                width=1,
                description="PL 时钟 3",
                is_clock=True,
            ),
            # PL 复位输出
            IPPort(
                name="FCLK_RESET0_N",
                direction="output",
                width=1,
                description="PL 复位 0 (低有效)",
                is_reset=True,
            ),
            IPPort(
                name="FCLK_RESET1_N",
                direction="output",
                width=1,
                description="PL 复位 1 (低有效)",
                is_reset=True,
            ),
            IPPort(
                name="FCLK_RESET2_N",
                direction="output",
                width=1,
                description="PL 复位 2 (低有效)",
                is_reset=True,
            ),
            IPPort(
                name="FCLK_RESET3_N",
                direction="output",
                width=1,
                description="PL 复位 3 (低有效)",
                is_reset=True,
            ),
            # 中断
            IPPort(
                name="IRQ_F2P",
                direction="input",
                width=1,
                description="PL 到 PS 中断",
            ),
        ]
        return ports
    
    def _convert_config_to_tcl(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        将配置转换为 Tcl 属性格式
        
        Args:
            config: 用户配置字典
        
        Returns:
            Tcl 属性字典
        """
        tcl_config = {}
        
        # 预设配置
        if config.get("preset"):
            tcl_config["CONFIG.preset"] = config["preset"]
        
        # PL 时钟配置
        if "enable_fabric_clock" in config:
            if config["enable_fabric_clock"]:
                tcl_config["CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ"] = config.get("fclk_frequency", 100)
                tcl_config["CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ"] = config.get("fclk_frequency", 100)
                tcl_config["CONFIG.PCW_FPGA2_PERIPHERAL_FREQMHZ"] = config.get("fclk_frequency", 100)
                tcl_config["CONFIG.PCW_FPGA3_PERIPHERAL_FREQMHZ"] = config.get("fclk_frequency", 100)
        
        # PL 复位配置
        if "enable_fabric_reset" in config:
            tcl_config["CONFIG.PCW_USE_FABRIC_RESET"] = 1 if config["enable_fabric_reset"] else 0
        
        # DDR 配置
        if "enable_ddr" in config:
            if config["enable_ddr"]:
                tcl_config["CONFIG.PCW_DDR_RAM_HIGHADDR"] = "0x1FFFFFFF"
        
        # 外设配置
        peripheral_map = {
            "enable_uart": ("CONFIG.PCW_UART0_PERIPHERAL_ENABLE", "CONFIG.PCW_UART1_PERIPHERAL_ENABLE"),
            "enable_ethernet": ("CONFIG.PCW_ENET0_PERIPHERAL_ENABLE",),
            "enable_usb": ("CONFIG.PCW_USB0_PERIPHERAL_ENABLE",),
            "enable_sd": ("CONFIG.PCW_SD0_PERIPHERAL_ENABLE",),
            "enable_gpio": ("CONFIG.PCW_GPIO_MIO_GPIO_ENABLE",),
            "enable_i2c": ("CONFIG.PCW_I2C0_PERIPHERAL_ENABLE",),
            "enable_spi": ("CONFIG.PCW_SPI0_PERIPHERAL_ENABLE",),
            "enable_can": ("CONFIG.PCW_CAN0_PERIPHERAL_ENABLE",),
            "enable_ttc": ("CONFIG.PCW_TTC0_PERIPHERAL_ENABLE",),
        }
        
        for key, props in peripheral_map.items():
            if key in config:
                for prop in props:
                    tcl_config[prop] = 1 if config[key] else 0
        
        # AXI 接口配置
        axi_map = {
            "enable_m_axi_gp0": "CONFIG.PCW_USE_M_AXI_GP0",
            "enable_m_axi_gp1": "CONFIG.PCW_USE_M_AXI_GP1",
            "enable_s_axi_hp0": "CONFIG.PCW_USE_S_AXI_HP0",
            "enable_s_axi_hp1": "CONFIG.PCW_USE_S_AXI_HP1",
            "enable_s_axi_hp2": "CONFIG.PCW_USE_S_AXI_HP2",
            "enable_s_axi_hp3": "CONFIG.PCW_USE_S_AXI_HP3",
            "enable_s_axi_acp": "CONFIG.PCW_USE_S_AXI_ACP",
        }
        
        for key, prop in axi_map.items():
            if key in config:
                tcl_config[prop] = 1 if config[key] else 0
        
        return tcl_config


# 便捷创建函数
async def create_processing_system7(
    tcl_engine,
    instance_name: str = "processing_system7_0",
    preset: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """
    创建 Processing System7 实例的便捷函数
    
    Args:
        tcl_engine: Tcl 执行引擎
        instance_name: 实例名称
        preset: 预设开发板配置
        **kwargs: 其他配置参数
    
    Returns:
        创建结果字典
    
    Example:
        result = await create_processing_system7(
            engine, "ps7_0",
            preset="ZedBoard",
            enable_uart=True,
            enable_ethernet=True,
        )
    """
    ps7 = ProcessingSystem7(tcl_engine)
    config = {
        "preset": preset,
        **kwargs,
    }
    return await ps7.create(instance_name, config)
