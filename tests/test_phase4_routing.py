"""Phase 4 routing tests."""

from unittest.mock import MagicMock

import pytest

from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.tools.block_design_tools import register_block_design_tools
from gateflow.tools.build_tools import register_build_tools
from gateflow.tools.constraint_tools import register_constraint_tools
from gateflow.tools.project_tools import register_project_tools


def _capture_tools(register_fn):
    mock_mcp = MagicMock()
    registered_tools = {}

    def capture_tool():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    register_fn(mock_mcp)
    return registered_tools


@pytest.mark.asyncio
async def test_project_tool_rejects_non_project_context():
    """Project tools should reject non-project execution contexts."""
    import gateflow.engine as engine_module

    manager = engine_module.EngineManager()
    previous = manager.execution_context
    manager._execution_context = ExecutionContext(kind=ExecutionContextKind.NON_PROJECT)

    tools = _capture_tools(register_project_tools)
    try:
        result = await tools["create_project"]("demo", "/tmp/demo", "xc7a35tcpg236-1")
    finally:
        manager._execution_context = previous

    assert result.success is False
    assert "project execution_context" in result.message


@pytest.mark.asyncio
async def test_build_tool_rejects_embedded_context():
    """Build tools should reject embedded execution contexts."""
    import gateflow.engine as engine_module

    manager = engine_module.EngineManager()
    previous = manager.execution_context
    manager._execution_context = ExecutionContext(kind=ExecutionContextKind.EMBEDDED)

    tools = _capture_tools(register_build_tools)
    try:
        result = await tools["run_synthesis"]()
    finally:
        manager._execution_context = previous

    assert result.success is False
    assert result.error is not None
    assert "embedded" in result.error


@pytest.mark.asyncio
async def test_constraint_tool_rejects_non_project_context():
    """Constraint tools should reject non-project execution contexts."""
    import gateflow.engine as engine_module

    manager = engine_module.EngineManager()
    previous = manager.execution_context
    manager._execution_context = ExecutionContext(kind=ExecutionContextKind.NON_PROJECT)

    tools = _capture_tools(register_constraint_tools)
    try:
        result = await tools["create_clock"]("clk", 10.0, "clk")
    finally:
        manager._execution_context = previous

    assert result.success is False
    assert result.error is not None
    assert "non_project" in result.error


@pytest.mark.asyncio
async def test_block_design_tool_rejects_embedded_context():
    """Block design tools should reject embedded execution contexts."""
    import gateflow.engine as engine_module

    manager = engine_module.EngineManager()
    previous = manager.execution_context
    manager._execution_context = ExecutionContext(kind=ExecutionContextKind.EMBEDDED)

    tools = _capture_tools(register_block_design_tools)
    try:
        result = await tools["create_bd_design"]("system")
    finally:
        manager._execution_context = previous

    assert result.success is False
    assert result.error is not None
    assert "embedded" in result.error
