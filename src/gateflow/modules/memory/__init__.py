"""
存储器模块

提供存储器相关的 IP 模块封装。
"""

from gateflow.modules.memory.axi_dma import AXIDMA, create_axi_dma

__all__ = [
    "AXIDMA",
    "create_axi_dma",
]
