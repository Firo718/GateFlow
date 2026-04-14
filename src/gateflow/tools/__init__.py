"""
MCP 工具模块。

提供 FastMCP 工具注册功能，将底层 Vivado 功能封装为 MCP 协议工具。
"""

from gateflow.tools.registry import (
    ToolCategory,
    ToolInfo,
    ToolRegistry,
    RiskLevel,
    get_registry,
    reset_registry,
    tool,
    register_decorated_tools,
)
from gateflow.tools.bd_advanced_tools import register_bd_advanced_tools
from gateflow.tools.block_design_tools import register_block_design_tools
from gateflow.tools.build_tools import register_build_tools
from gateflow.tools.constraint_tools import register_constraint_tools
from gateflow.tools.file_tools import register_file_tools
from gateflow.tools.hardware_tools import register_hardware_tools
from gateflow.tools.ip_tools import register_ip_tools
from gateflow.tools.project_tools import register_project_tools
from gateflow.tools.simulation_tools import register_simulation_tools
from gateflow.tools.tcl_tools import register_tcl_tools

__all__ = [
    # 注册表
    "ToolCategory",
    "ToolInfo",
    "ToolRegistry",
    "RiskLevel",
    "get_registry",
    "reset_registry",
    "tool",
    "register_decorated_tools",
    # 工具注册函数
    "register_project_tools",
    "register_build_tools",
    "register_constraint_tools",
    "register_hardware_tools",
    "register_ip_tools",
    "register_simulation_tools",
    "register_block_design_tools",
    "register_bd_advanced_tools",
    "register_tcl_tools",
    "register_file_tools",
]
