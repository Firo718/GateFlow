"""
AXI GPIO 模块封装

提供 AXI GPIO IP 核的封装，参考 ADI hdl-main 项目的设计模式。
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
class AXIGPIO(IPModule):
    """
    AXI GPIO 模块封装
    
    AXI GPIO 是一个通用输入输出接口 IP，支持单通道和双通道模式。
    
    Features:
        - 可配置 GPIO 位宽 (1-32 位)
        - 支持双通道模式
        - 支持输入、输出或双向模式
        - 支持中断输出
    
    Example:
        # 创建 AXI GPIO 实例
        gpio = AXIGPIO(tcl_engine)
        result = await gpio.create("axi_gpio_0", {
            "gpio_width": 8,
            "dual_channel": False,
            "all_outputs": True,
        })
        
        # 连接 GPIO
        await gpio.connect("axi_gpio_0", {
            "S_AXI": "axi_interconnect_0/M00_AXI",
            "GPIO": "external/gpio_pins",
        })
    """
    
    # IP 基本信息
    ip_name = "axi_gpio"
    ip_display_name = "AXI GPIO"
    ip_category = IPCategory.INTERFACE
    ip_version = "2.0"
    ip_description = "AXI General Purpose Input/Output"
    ip_documentation_url = "https://docs.xilinx.com/r/en-US/pg144-axi-gpio"
    
    def __init__(self, tcl_engine=None):
        """初始化 AXI GPIO 模块"""
        super().__init__(tcl_engine)
    
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 AXI GPIO 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典，支持以下参数：
                - gpio_width: GPIO 位宽 (1-32)，默认 32
                - dual_channel: 是否启用双通道，默认 False
                - gpio2_width: GPIO2 位宽 (1-32)，默认 32
                - all_inputs: 是否全部为输入，默认 False
                - all_outputs: 是否全部为输出，默认 False
                - input_default: 输入默认值，默认 0
                - output_default: 输出默认值，默认 0
                - enable_interrupt: 是否启用中断，默认 False
                - tri_default: 三态默认值，默认 0xFFFFFFFF
        
        Returns:
            创建结果字典
        
        Example:
            # 创建 8 位输出 GPIO
            result = await gpio.create("axi_gpio_0", {
                "gpio_width": 8,
                "all_outputs": True,
            })
            
            # 创建双通道 GPIO
            result = await gpio.create("axi_gpio_1", {
                "gpio_width": 16,
                "dual_channel": True,
                "gpio2_width": 8,
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
            logger.info(f"AXI GPIO 实例创建成功: {instance_name}")
        else:
            logger.error(f"AXI GPIO 实例创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "module_name": instance_name,
            "message": f"AXI GPIO 实例 {instance_name} 创建成功" if result.success else "创建失败",
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "gpio_width": 32,
            "dual_channel": False,
            "gpio2_width": 32,
            "all_inputs": False,
            "all_outputs": False,
            "input_default": 0,
            "output_default": 0,
            "enable_interrupt": False,
            "tri_default": 0xFFFFFFFF,
        }
    
    def get_available_properties(self) -> list[IPProperty]:
        """获取可配置属性列表"""
        return [
            IPProperty(
                name="gpio_width",
                value=32,
                description="GPIO 通道 1 位宽",
                value_type="int",
                default=32,
                min_value=1,
                max_value=32,
            ),
            IPProperty(
                name="dual_channel",
                value=False,
                description="是否启用双通道模式",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="gpio2_width",
                value=32,
                description="GPIO 通道 2 位宽",
                value_type="int",
                default=32,
                min_value=1,
                max_value=32,
            ),
            IPProperty(
                name="all_inputs",
                value=False,
                description="通道 1 全部为输入",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="all_outputs",
                value=False,
                description="通道 1 全部为输出",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="input_default",
                value=0,
                description="输入默认值",
                value_type="int",
                default=0,
            ),
            IPProperty(
                name="output_default",
                value=0,
                description="输出默认值",
                value_type="int",
                default=0,
            ),
            IPProperty(
                name="enable_interrupt",
                value=False,
                description="是否启用中断输出",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="tri_default",
                value=0xFFFFFFFF,
                description="三态控制默认值",
                value_type="int",
                default=0xFFFFFFFF,
            ),
        ]
    
    def get_ports(self) -> list[IPPort]:
        """获取端口列表"""
        ports = [
            # AXI 接口
            IPPort(
                name="S_AXI",
                direction="inout",
                description="AXI4-Lite 从接口",
                is_interface=True,
                interface_type="AXI4LITE",
            ),
            # 时钟和复位
            IPPort(
                name="s_axi_aclk",
                direction="input",
                width=1,
                description="AXI 时钟",
                is_clock=True,
            ),
            IPPort(
                name="s_axi_aresetn",
                direction="input",
                width=1,
                description="AXI 复位（低有效）",
                is_reset=True,
            ),
            # GPIO 通道 1
            IPPort(
                name="gpio_io_i",
                direction="input",
                width=32,
                description="GPIO 数据输入",
            ),
            IPPort(
                name="gpio_io_o",
                direction="output",
                width=32,
                description="GPIO 数据输出",
            ),
            IPPort(
                name="gpio_io_t",
                direction="output",
                width=32,
                description="GPIO 三态控制",
            ),
            # GPIO 通道 1 接口
            IPPort(
                name="GPIO",
                direction="inout",
                description="GPIO 通道 1 接口",
                is_interface=True,
                interface_type="GPIO",
            ),
            # GPIO 通道 2
            IPPort(
                name="gpio2_io_i",
                direction="input",
                width=32,
                description="GPIO2 数据输入",
            ),
            IPPort(
                name="gpio2_io_o",
                direction="output",
                width=32,
                description="GPIO2 数据输出",
            ),
            IPPort(
                name="gpio2_io_t",
                direction="output",
                width=32,
                description="GPIO2 三态控制",
            ),
            # GPIO 通道 2 接口
            IPPort(
                name="GPIO2",
                direction="inout",
                description="GPIO 通道 2 接口",
                is_interface=True,
                interface_type="GPIO",
            ),
            # 中断
            IPPort(
                name="ip2intc_irpt",
                direction="output",
                width=1,
                description="中断输出",
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
        
        # GPIO 位宽
        if "gpio_width" in config:
            tcl_config["C_GPIO_WIDTH"] = config["gpio_width"]
        
        # 双通道模式
        if "dual_channel" in config:
            tcl_config["C_IS_DUAL"] = 1 if config["dual_channel"] else 0
        
        # GPIO2 位宽
        if "gpio2_width" in config:
            tcl_config["C_GPIO2_WIDTH"] = config["gpio2_width"]
        
        # 输入/输出模式
        if "all_inputs" in config:
            tcl_config["C_ALL_INPUTS"] = 1 if config["all_inputs"] else 0
        
        if "all_outputs" in config:
            tcl_config["C_ALL_OUTPUTS"] = 1 if config["all_outputs"] else 0
        
        # 默认值
        if "input_default" in config:
            tcl_config["C_DIN_DEFAULT"] = config["input_default"]
        
        if "output_default" in config:
            tcl_config["C_DOUT_DEFAULT"] = config["output_default"]
        
        if "tri_default" in config:
            tcl_config["C_TRI_DEFAULT"] = config["tri_default"]
        
        # 中断
        if "enable_interrupt" in config:
            tcl_config["C_INTERRUPT_PRESENT"] = 1 if config["enable_interrupt"] else 0
        
        return tcl_config


# 便捷创建函数
async def create_axi_gpio(
    tcl_engine,
    instance_name: str,
    gpio_width: int = 32,
    dual_channel: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """
    创建 AXI GPIO 实例的便捷函数
    
    Args:
        tcl_engine: Tcl 执行引擎
        instance_name: 实例名称
        gpio_width: GPIO 位宽
        dual_channel: 是否双通道
        **kwargs: 其他配置参数
    
    Returns:
        创建结果字典
    
    Example:
        result = await create_axi_gpio(engine, "led_gpio", gpio_width=8, all_outputs=True)
    """
    gpio = AXIGPIO(tcl_engine)
    config = {
        "gpio_width": gpio_width,
        "dual_channel": dual_channel,
        **kwargs,
    }
    return await gpio.create(instance_name, config)
