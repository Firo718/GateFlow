"""
GateFlow MCP Server Entry Point.

This module provides the main entry point for the GateFlow MCP server,
which enables AI tools to interact with Vivado FPGA development software.
"""

import asyncio
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from gateflow.capabilities import build_runtime_tool_specs
from gateflow.tools.block_design_tools import register_block_design_tools
from gateflow.tools.bd_advanced_tools import register_bd_advanced_tools
from gateflow.tools.build_tools import register_build_tools
from gateflow.tools.constraint_tools import register_constraint_tools
from gateflow.tools.embedded_tools import register_embedded_tools
from gateflow.tools.file_tools import register_file_tools
from gateflow.tools.hardware_tools import register_hardware_tools
from gateflow.tools.ip_tools import register_ip_tools
from gateflow.tools.project_tools import register_project_tools
from gateflow.tools.simulation_tools import register_simulation_tools
from gateflow.tools.tcl_tools import register_tcl_tools
from gateflow.tools.registry import (
    ToolRegistry,
    ToolCategory,
    RiskLevel,
    get_registry,
)
from gateflow.settings import get_settings, GateFlowSettings
from gateflow.vivado.tcl_engine import TclEngine

logger = logging.getLogger(__name__)

_app_context: dict[str, Any] = {}


def create_registry() -> ToolRegistry:
    """
    创建并初始化工具注册表。

    Returns:
        已注册所有工具的 ToolRegistry 实例
    """
    registry = ToolRegistry()

    category_map = {category.value: category for category in ToolCategory}
    risk_map = {risk.value: risk for risk in RiskLevel}

    for spec in build_runtime_tool_specs():
        registry.register(
            name=spec.name,
            handler=None,
            category=category_map[spec.category],
            description=spec.short_description,
            risk_level=risk_map[spec.risk_level],
            requires_vivado=spec.requires_vivado,
            metadata={"module": spec.module},
        )

    logger.info(f"工具注册表初始化完成，共注册 {len(registry.list_all())} 个工具")
    return registry


def register_project_tools_to_registry(registry: ToolRegistry) -> None:
    """注册项目管理工具到注册表"""
    registry.register(
        name="create_project",
        handler=None,  # 占位，实际注册在 register_project_tools 中
        category=ToolCategory.PROJECT,
        description="创建新的 Vivado 项目",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="open_project",
        handler=None,
        category=ToolCategory.PROJECT,
        description="打开现有 Vivado 项目",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="add_source_files",
        handler=None,
        category=ToolCategory.PROJECT,
        description="添加源文件到当前项目",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="set_top_module",
        handler=None,
        category=ToolCategory.PROJECT,
        description="设置顶层模块",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="get_project_info",
        handler=None,
        category=ToolCategory.PROJECT,
        description="获取当前项目信息",
        risk_level=RiskLevel.SAFE,
        requires_vivado=True,
    )


def register_file_tools_to_registry(registry: ToolRegistry) -> None:
    """注册文件操作工具到注册表"""
    # 安全工具
    registry.register(
        name="read_file",
        handler=None,
        category=ToolCategory.FILE,
        description="读取文件内容",
        risk_level=RiskLevel.SAFE,
    )
    registry.register(
        name="list_files",
        handler=None,
        category=ToolCategory.FILE,
        description="列出目录中的文件",
        risk_level=RiskLevel.SAFE,
    )
    registry.register(
        name="file_exists",
        handler=None,
        category=ToolCategory.FILE,
        description="检查文件是否存在",
        risk_level=RiskLevel.SAFE,
    )
    registry.register(
        name="get_file_info",
        handler=None,
        category=ToolCategory.FILE,
        description="获取文件信息",
        risk_level=RiskLevel.SAFE,
    )

    # 正常工具
    registry.register(
        name="create_file",
        handler=None,
        category=ToolCategory.FILE,
        description="创建新文件",
        risk_level=RiskLevel.NORMAL,
    )
    registry.register(
        name="append_file",
        handler=None,
        category=ToolCategory.FILE,
        description="追加内容到文件",
        risk_level=RiskLevel.NORMAL,
    )
    registry.register(
        name="create_directory",
        handler=None,
        category=ToolCategory.FILE,
        description="创建目录",
        risk_level=RiskLevel.NORMAL,
    )
    registry.register(
        name="copy_file",
        handler=None,
        category=ToolCategory.FILE,
        description="复制文件",
        risk_level=RiskLevel.NORMAL,
    )

    # 危险工具
    registry.register(
        name="write_file",
        handler=None,
        category=ToolCategory.FILE,
        description="写入文件（覆盖）",
        risk_level=RiskLevel.DANGEROUS,
    )
    registry.register(
        name="delete_file",
        handler=None,
        category=ToolCategory.FILE,
        description="删除文件",
        risk_level=RiskLevel.DANGEROUS,
    )


def register_tcl_tools_to_registry(registry: ToolRegistry) -> None:
    """注册 Tcl 工具到注册表"""
    registry.register(
        name="execute_tcl",
        handler=None,
        category=ToolCategory.TCL,
        description="执行 Tcl 命令",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="execute_tcl_batch",
        handler=None,
        category=ToolCategory.TCL,
        description="批量执行 Tcl 命令",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_build_tools_to_registry(registry: ToolRegistry) -> None:
    """注册构建工具到注册表"""
    registry.register(
        name="run_synthesis",
        handler=None,
        category=ToolCategory.BUILD,
        description="运行综合",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="run_implementation",
        handler=None,
        category=ToolCategory.BUILD,
        description="运行实现",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="generate_bitstream",
        handler=None,
        category=ToolCategory.BUILD,
        description="生成比特流",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_constraint_tools_to_registry(registry: ToolRegistry) -> None:
    """注册约束工具到注册表"""
    registry.register(
        name="create_clock",
        handler=None,
        category=ToolCategory.CONSTRAINT,
        description="创建时钟约束",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="set_input_delay",
        handler=None,
        category=ToolCategory.CONSTRAINT,
        description="设置输入延迟约束",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="set_output_delay",
        handler=None,
        category=ToolCategory.CONSTRAINT,
        description="设置输出延迟约束",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_hardware_tools_to_registry(registry: ToolRegistry) -> None:
    """注册硬件工具到注册表"""
    registry.register(
        name="connect_hw_server",
        handler=None,
        category=ToolCategory.HARDWARE,
        description="连接硬件服务器",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="program_device",
        handler=None,
        category=ToolCategory.HARDWARE,
        description="编程 FPGA 设备",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_ip_tools_to_registry(registry: ToolRegistry) -> None:
    """注册 IP 工具到注册表"""
    registry.register(
        name="create_ip",
        handler=None,
        category=ToolCategory.IP,
        description="创建 IP 核",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="configure_ip",
        handler=None,
        category=ToolCategory.IP,
        description="配置 IP 核",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_block_design_tools_to_registry(registry: ToolRegistry) -> None:
    """注册 Block Design 工具到注册表"""
    registry.register(
        name="create_block_design",
        handler=None,
        category=ToolCategory.BLOCK_DESIGN,
        description="创建 Block Design",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="add_ip_to_bd",
        handler=None,
        category=ToolCategory.BLOCK_DESIGN,
        description="添加 IP 到 Block Design",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="connect_bd_cells",
        handler=None,
        category=ToolCategory.BLOCK_DESIGN,
        description="连接 Block Design 单元",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_bd_advanced_tools_to_registry(registry: ToolRegistry) -> None:
    """注册高级 Block Design 工具到注册表"""
    registry.register(
        name="create_smart_connect",
        handler=None,
        category=ToolCategory.BLOCK_DESIGN,
        description="创建智能连接",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="auto_connect_bd",
        handler=None,
        category=ToolCategory.BLOCK_DESIGN,
        description="自动连接 Block Design",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def register_simulation_tools_to_registry(registry: ToolRegistry) -> None:
    """注册仿真工具到注册表"""
    registry.register(
        name="run_simulation",
        handler=None,
        category=ToolCategory.SIMULATION,
        description="运行仿真",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )
    registry.register(
        name="add_testbench",
        handler=None,
        category=ToolCategory.SIMULATION,
        description="添加测试平台",
        risk_level=RiskLevel.NORMAL,
        requires_vivado=True,
    )


def apply_tool_config(registry: ToolRegistry, settings: GateFlowSettings) -> dict[str, Any]:
    """
    根据配置应用工具开关。

    Args:
        registry: 工具注册表
        settings: 配置实例

    Returns:
        应用结果统计
    """
    return registry.apply_config(
        enabled_tools=settings.enabled_tools,
        disabled_tools=settings.disabled_tools,
        disable_dangerous_tools=settings.disable_dangerous_tools,
    )


def create_server(name: str = "GateFlow", settings: GateFlowSettings | None = None) -> FastMCP:
    """
    Create and configure the GateFlow MCP server.

    Args:
        name: The name of the server instance.
        settings: Optional settings instance. If None, will use global settings.

    Returns:
        A configured FastMCP server instance.
    """
    # 获取配置
    if settings is None:
        settings = get_settings()

    mcp = FastMCP(
        name=name,
        instructions="""
GateFlow is an MCP server that enables AI tools to interact with Vivado FPGA development software.

Available capabilities:
- Project Management: Create, open, and manage Vivado projects
- Source Files: Add/remove Verilog/VHDL source files
- File Operations: Create, read, write, copy, and delete files
- Synthesis: Run synthesis and analyze results
- Implementation: Run implementation and generate bitstreams
- Constraints: Create timing constraints (clocks, IO delays, etc.)
- Hardware: Connect to hardware servers and program FPGAs
- IP Configuration: Create and configure IP cores (Clocking Wizard, FIFO, BRAM, etc.)
- Block Design: Create and manage Block Designs with IP integrations
- Simulation: Run behavioral simulation and manage testbenches
- Reports: Get utilization, timing, and other reports

The server executes Tcl commands through Vivado in batch mode, providing
a bridge between AI assistants and FPGA development workflows.
""",
    )

    # 创建工具注册表
    registry = create_registry()

    # 应用配置
    stats = apply_tool_config(registry, settings)
    logger.info(f"工具配置已应用: {stats}")

    # 保存注册表到应用上下文
    _app_context["registry"] = registry

    # 注册工具到 MCP（只注册启用的工具）
    # 注意：实际的工具处理函数在各自的 register_*_tools 中注册
    register_project_tools(mcp)
    register_build_tools(mcp)
    register_constraint_tools(mcp)
    register_embedded_tools(mcp)
    register_hardware_tools(mcp)
    register_ip_tools(mcp)
    register_block_design_tools(mcp)
    register_bd_advanced_tools(mcp)
    register_simulation_tools(mcp)
    register_tcl_tools(mcp)
    register_file_tools(mcp)

    return mcp


async def initialize_engine(vivado_path: str | None = None) -> TclEngine:
    """
    Initialize the Tcl execution engine.

    Args:
        vivado_path: Optional path to Vivado installation.

    Returns:
        An initialized TclEngine instance.
    """
    engine = TclEngine(vivado_path=vivado_path)
    await engine.initialize()
    _app_context["engine"] = engine
    return engine


def get_engine() -> TclEngine | None:
    """
    Get the current Tcl execution engine instance.

    Returns:
        The TclEngine instance or None if not initialized.
    """
    return _app_context.get("engine")


def main() -> None:
    """Main entry point for the GateFlow MCP server."""
    mcp = create_server()
    mcp.run()


if __name__ == "__main__":
    main()
