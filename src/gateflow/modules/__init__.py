"""
GateFlow 模块封装库

提供常用 IP 模块的封装，参考 ADI hdl-main 项目的设计模式。
"""

from gateflow.modules.base import (
    IPCategory,
    IPInstanceInfo,
    IPModule,
    IPModuleRegistry,
    IPPort,
    IPProperty,
    register_module,
)

# 导入所有模块以触发注册
from gateflow.modules.interface.axi_gpio import AXIGPIO, create_axi_gpio
from gateflow.modules.interface.axi_uart import AXIUART, create_axi_uart
from gateflow.modules.clock.clk_wiz import ClockWizard, create_clock_wizard
from gateflow.modules.processing.processing_system7 import (
    ProcessingSystem7,
    create_processing_system7,
)
from gateflow.modules.memory.axi_dma import AXIDMA, create_axi_dma

__all__ = [
    # 基类
    "IPModule",
    "IPCategory",
    "IPProperty",
    "IPPort",
    "IPInstanceInfo",
    "IPModuleRegistry",
    "register_module",
    # 接口模块
    "AXIGPIO",
    "AXIUART",
    # 时钟模块
    "ClockWizard",
    # 处理系统模块
    "ProcessingSystem7",
    # 存储器模块
    "AXIDMA",
    # 便捷函数
    "create_axi_gpio",
    "create_axi_uart",
    "create_clock_wizard",
    "create_processing_system7",
    "create_axi_dma",
]


def get_module(name: str, tcl_engine=None):
    """
    获取 IP 模块实例
    
    Args:
        name: IP 名称
        tcl_engine: Tcl 执行引擎
    
    Returns:
        IP 模块实例
    
    Example:
        gpio = get_module("axi_gpio", engine)
        result = await gpio.create("gpio_0", {"gpio_width": 8})
    """
    return IPModuleRegistry.create_instance(name, tcl_engine)


def list_available_modules() -> list[str]:
    """
    列出所有可用的 IP 模块
    
    Returns:
        IP 名称列表
    """
    return IPModuleRegistry.list_modules()


def get_module_info(name: str) -> dict | None:
    """
    获取 IP 模块信息
    
    Args:
        name: IP 名称
    
    Returns:
        模块信息字典
    """
    module_class = IPModuleRegistry.get(name)
    if module_class:
        return {
            "name": module_class.ip_name,
            "display_name": module_class.ip_display_name,
            "category": module_class.ip_category.value,
            "version": module_class.ip_version,
            "description": module_class.ip_description,
            "documentation_url": module_class.ip_documentation_url,
            "vlnv": f"{module_class.ip_vlnv_base}:{module_class.ip_name}:{module_class.ip_version}",
        }
    return None
