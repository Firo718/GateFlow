"""
接口模块

提供接口相关的 IP 模块封装。
"""

from gateflow.modules.interface.axi_gpio import AXIGPIO, create_axi_gpio
from gateflow.modules.interface.axi_uart import AXIUART, create_axi_uart

__all__ = [
    "AXIGPIO",
    "AXIUART",
    "create_axi_gpio",
    "create_axi_uart",
]
