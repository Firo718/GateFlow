"""
GateFlow - An open-source MCP server for AI-assisted Vivado FPGA development.

GateFlow enables AI coding tools to interact with AMD (Xilinx) Vivado through
the Model Context Protocol (MCP), allowing natural language control of FPGA
development workflows.
"""

__version__ = "0.1.0"
__author__ = "GateFlow Team"

from gateflow.api import GateFlow
from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.server import create_server
from gateflow.engine import (
    EngineManager,
    EngineMode,
    get_engine_manager,
    ensure_engine_initialized,
    execute_tcl,
    execute_tcl_batch,
)
# 模块封装库
from gateflow.modules import (
    IPModule,
    IPModuleRegistry,
    IPCategory,
    IPPort,
    IPProperty,
    register_module,
    get_module,
    list_available_modules,
    get_module_info,
    # 具体模块
    AXIGPIO,
    AXIUART,
    ClockWizard,
    ProcessingSystem7,
    AXIDMA,
    # 便捷函数
    create_axi_gpio,
    create_axi_uart,
    create_clock_wizard,
    create_processing_system7,
    create_axi_dma,
)

__all__ = [
    # 高级 API
    "GateFlow",
    "ExecutionContext",
    "ExecutionContextKind",
    # MCP 服务器
    "create_server",
    # 引擎管理
    "EngineManager",
    "EngineMode",
    "get_engine_manager",
    "ensure_engine_initialized",
    "execute_tcl",
    "execute_tcl_batch",
    # 模块封装库
    "IPModule",
    "IPModuleRegistry",
    "IPCategory",
    "IPPort",
    "IPProperty",
    "register_module",
    "get_module",
    "list_available_modules",
    "get_module_info",
    # 具体模块
    "AXIGPIO",
    "AXIUART",
    "ClockWizard",
    "ProcessingSystem7",
    "AXIDMA",
    # 便捷函数
    "create_axi_gpio",
    "create_axi_uart",
    "create_clock_wizard",
    "create_processing_system7",
    "create_axi_dma",
]
