"""AI real-usage tests for recovery and actionable failures."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gateflow.cli import DiagnosticResult, cmd_doctor, cmd_status
from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.tools.block_design_tools import register_block_design_tools


@pytest.mark.ai_real_usage
def test_ai_gets_actionable_doctor_output_for_tcp_mismatch(capsys):
    """doctor should expose copyable recovery guidance for TCP mismatch."""
    args = SimpleNamespace(port=9999, json=True)
    fake_results = [
        DiagnosticResult(
            name="TCP 协议",
            passed=False,
            message="端口 9999 返回了非 GateFlow 响应",
            fix_suggestion="检查该端口是否连接到了其他 MCP/Tcl 服务，建议为 GateFlow 使用独立端口",
        )
    ]

    with patch("gateflow.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(tcp_port=9999)
        with patch("gateflow.cli.EnvironmentDiagnostics.run_all_diagnostics", return_value=fake_results):
            rc = cmd_doctor(args)

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert "独立端口" in payload["results"][0]["fix_suggestion"]


@pytest.mark.ai_real_usage
def test_ai_gets_actionable_status_output_for_missing_vivado(tmp_path, capsys):
    """status should clearly explain missing Vivado and missing scripts."""
    args = SimpleNamespace(port=None)
    fake_settings = MagicMock(tcp_port=9999, vivado_path=None, log_level="INFO")

    with patch("gateflow.cli.CONFIG_DIR", tmp_path):
        with patch("gateflow.cli.get_settings", return_value=fake_settings):
            with patch("gateflow.cli.build_capability_manifest", return_value={"tool_count": 160}):
                with patch("gateflow.cli.VivadoDetector.detect_vivado", return_value=None):
                    with patch("gateflow.cli.EnvironmentDiagnostics.check_port_listener", return_value=DiagnosticResult("l", False, "127.0.0.1:9999 未监听")):
                        with patch("gateflow.cli.EnvironmentDiagnostics.check_tcp_protocol", return_value=DiagnosticResult("p", False, "无法连接到端口 9999 进行协议探测", fix_suggestion="先启动 GateFlow tcl_server，再重试 status/doctor")):
                            rc = cmd_status(args)

    out = capsys.readouterr().out
    assert rc == 0
    assert "未检测到 Vivado 安装" in out
    assert "gateflow install" in out
    assert "GateFlow tcl_server" in out


@pytest.mark.ai_real_usage
@pytest.mark.asyncio
async def test_ai_sees_execution_context_routing_hint():
    """AI should get a routing hint when using project-only tools in the wrong context."""
    import gateflow.engine as engine_module

    manager = engine_module.EngineManager()
    previous = manager.execution_context
    manager._execution_context = ExecutionContext(kind=ExecutionContextKind.EMBEDDED)

    try:
        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = capture_tool
        register_block_design_tools(mock_mcp)
        result = await registered_tools["create_bd_design"]("system")
    finally:
        manager._execution_context = previous

    assert result.success is False
    assert result.error is not None
    assert "embedded / vitis / xsct" in result.error
