"""
AXI UART 模块封装

提供 AXI UART Lite IP 核的封装，参考 ADI hdl-main 项目的设计模式。
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
class AXIUART(IPModule):
    """
    AXI UART 模块封装
    
    AXI UART Lite 是一个轻量级串口通信 IP，支持基本的 UART 功能。
    
    Features:
        - 可配置波特率 (110-921600)
        - 可配置数据位 (5-8)
        - 支持奇偶校验
        - 支持中断输出
    
    Example:
        # 创建 AXI UART 实例
        uart = AXIUART(tcl_engine)
        result = await uart.create("axi_uart_0", {
            "baud_rate": 115200,
            "data_bits": 8,
            "parity": "None",
        })
        
        # 连接 UART
        await uart.connect("axi_uart_0", {
            "S_AXI": "axi_interconnect_0/M01_AXI",
            "UART": "external/uart_rxd",
        })
    """
    
    # IP 基本信息
    ip_name = "axi_uartlite"
    ip_display_name = "AXI UART Lite"
    ip_category = IPCategory.INTERFACE
    ip_version = "2.0"
    ip_description = "AXI UART Lite - Lightweight Serial Communication Interface"
    ip_documentation_url = "https://docs.xilinx.com/r/en-US/pg142-axi-uartlite"
    
    def __init__(self, tcl_engine=None):
        """初始化 AXI UART 模块"""
        super().__init__(tcl_engine)
    
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 AXI UART 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典，支持以下参数：
                - baud_rate: 波特率，默认 9600
                - data_bits: 数据位 (5-8)，默认 8
                - parity: 校验类型 ("None", "Even", "Odd")，默认 "None"
                - stop_bits: 停止位 (1-2)，默认 1
                - enable_interrupt: 是否启用中断，默认 True
        
        Returns:
            创建结果字典
        
        Example:
            # 创建 115200 波特率的 UART
            result = await uart.create("axi_uart_0", {
                "baud_rate": 115200,
                "data_bits": 8,
                "parity": "None",
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
            logger.info(f"AXI UART 实例创建成功: {instance_name}")
        else:
            logger.error(f"AXI UART 实例创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "module_name": instance_name,
            "message": f"AXI UART 实例 {instance_name} 创建成功" if result.success else "创建失败",
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "baud_rate": 9600,
            "data_bits": 8,
            "parity": "None",
            "stop_bits": 1,
            "enable_interrupt": True,
        }
    
    def get_available_properties(self) -> list[IPProperty]:
        """获取可配置属性列表"""
        return [
            IPProperty(
                name="baud_rate",
                value=9600,
                description="波特率",
                value_type="int",
                default=9600,
                min_value=110,
                max_value=921600,
            ),
            IPProperty(
                name="data_bits",
                value=8,
                description="数据位",
                value_type="int",
                default=8,
                min_value=5,
                max_value=8,
            ),
            IPProperty(
                name="parity",
                value="None",
                description="校验类型",
                value_type="string",
                default="None",
                valid_values=["None", "Even", "Odd"],
            ),
            IPProperty(
                name="stop_bits",
                value=1,
                description="停止位",
                value_type="int",
                default=1,
                min_value=1,
                max_value=2,
            ),
            IPProperty(
                name="enable_interrupt",
                value=True,
                description="是否启用中断输出",
                value_type="bool",
                default=True,
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
            # UART 信号
            IPPort(
                name="rx",
                direction="input",
                width=1,
                description="UART 接收数据",
            ),
            IPPort(
                name="tx",
                direction="output",
                width=1,
                description="UART 发送数据",
            ),
            # UART 接口
            IPPort(
                name="UART",
                direction="inout",
                description="UART 接口",
                is_interface=True,
                interface_type="UART",
            ),
            # 中断
            IPPort(
                name="interrupt",
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
        
        # 波特率
        if "baud_rate" in config:
            tcl_config["C_BAUDRATE"] = config["baud_rate"]
        
        # 数据位
        if "data_bits" in config:
            tcl_config["C_DATA_BITS"] = config["data_bits"]
        
        # 校验类型
        if "parity" in config:
            parity_map = {
                "None": 0,
                "Even": 1,
                "Odd": 2,
            }
            tcl_config["C_USE_PARITY"] = parity_map.get(config["parity"], 0)
            if config["parity"] != "None":
                tcl_config["C_PARITY"] = config["parity"]
        
        # 停止位
        if "stop_bits" in config:
            tcl_config["C_STOP_BITS"] = config["stop_bits"]
        
        # 中断
        if "enable_interrupt" in config:
            tcl_config["C_HAS_INTERRUPT"] = 1 if config["enable_interrupt"] else 0
        
        return tcl_config


# 便捷创建函数
async def create_axi_uart(
    tcl_engine,
    instance_name: str,
    baud_rate: int = 115200,
    **kwargs,
) -> dict[str, Any]:
    """
    创建 AXI UART 实例的便捷函数
    
    Args:
        tcl_engine: Tcl 执行引擎
        instance_name: 实例名称
        baud_rate: 波特率
        **kwargs: 其他配置参数
    
    Returns:
        创建结果字典
    
    Example:
        result = await create_axi_uart(engine, "debug_uart", baud_rate=115200)
    """
    uart = AXIUART(tcl_engine)
    config = {
        "baud_rate": baud_rate,
        **kwargs,
    }
    return await uart.create(instance_name, config)
