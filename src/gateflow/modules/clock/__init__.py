"""
时钟管理模块

提供时钟相关的 IP 模块封装。
"""

from gateflow.modules.clock.clk_wiz import ClockWizard, create_clock_wizard

__all__ = [
    "ClockWizard",
    "create_clock_wizard",
]
