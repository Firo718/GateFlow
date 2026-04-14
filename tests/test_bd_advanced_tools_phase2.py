"""Phase 2C/2D tests for advanced BD templates."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateflow.tools.bd_advanced_tools import register_bd_advanced_tools


@pytest.mark.asyncio
async def test_bd_create_zynq_gpio_uart_bram_system_success():
    """The common Zynq template tool should complete on a successful engine."""
    import gateflow.tools.bd_advanced_tools as bd_tools

    mock_engine = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.errors = []
    mock_result.warnings = []
    mock_result.output = ""
    mock_engine.execute_async = AsyncMock(return_value=mock_result)

    registered_tools = {}
    mock_mcp = MagicMock()

    def capture_tool():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    with patch.object(bd_tools, "_get_engine", return_value=mock_engine):
        register_bd_advanced_tools(mock_mcp)
        result = await registered_tools["bd_create_zynq_gpio_uart_bram_system"](
            generate_wrapper=False
        )

    assert result.success is True
    assert result.data is not None
    assert result.data["design_name"] == "system"
    assert "axi_gpio_0" in result.data["cells"]


@pytest.mark.asyncio
async def test_bd_create_zynq_gpio_uart_timer_dma_system_success():
    """The GPIO/UART/Timer/DMA template tool should complete on a successful engine."""
    import gateflow.tools.bd_advanced_tools as bd_tools

    mock_engine = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.errors = []
    mock_result.warnings = []
    mock_result.output = ""
    mock_engine.execute_async = AsyncMock(return_value=mock_result)

    registered_tools = {}
    mock_mcp = MagicMock()

    def capture_tool():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func

        return decorator

    mock_mcp.tool = capture_tool

    with patch.object(bd_tools, "_get_engine", return_value=mock_engine):
        register_bd_advanced_tools(mock_mcp)
        result = await registered_tools["bd_create_zynq_gpio_uart_timer_dma_system"](
            generate_wrapper=False
        )

    assert result.success is True
    assert result.data is not None
    assert result.data["design_name"] == "system_io"
    assert "axi_uartlite_0" in result.data["cells"]
