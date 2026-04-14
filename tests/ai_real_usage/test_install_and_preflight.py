"""AI real-usage tests for install and preflight flows."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from gateflow import __version__
from gateflow.cli import DiagnosticResult, cmd_capabilities, cmd_doctor, cmd_status, create_parser


@pytest.mark.ai_real_usage
def test_ai_can_check_version(capsys):
    """AI should be able to verify GateFlow installation through --version."""
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])
    assert f"GateFlow v{__version__}" in capsys.readouterr().out


@pytest.mark.ai_real_usage
def test_ai_can_run_doctor_json(capsys):
    """doctor --json should expose enough detail for AI reasoning."""
    args = SimpleNamespace(port=None, json=True)
    fake_results = [
        DiagnosticResult(name="Vivado 安装", passed=True, message="ok"),
        DiagnosticResult(name="TCP 协议", passed=False, message="mismatch", fix_suggestion="switch port"),
    ]

    with patch("gateflow.cli.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(tcp_port=9999)
        with patch("gateflow.cli.EnvironmentDiagnostics.run_all_diagnostics", return_value=fake_results):
            rc = cmd_doctor(args)

    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert payload["summary"]["failed"] == 1
    assert payload["results"][1]["fix_suggestion"] == "switch port"


@pytest.mark.ai_real_usage
def test_ai_can_run_status_and_capabilities(tmp_path, capsys):
    """status and capabilities must provide a full preflight picture."""
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tcl_server.tcl").write_text("# server", encoding="utf-8")
    (tmp_path / "start_server.bat").write_text("@echo off", encoding="utf-8")

    fake_settings = MagicMock(tcp_port=10099, vivado_path="C:/Xilinx/Vivado/2024.1", log_level="INFO")
    fake_vivado = MagicMock(
        version="2024.1",
        install_path="C:/Xilinx/Vivado/2024.1",
        executable="C:/Xilinx/Vivado/2024.1/bin/vivado.bat",
    )
    fake_engine = MagicMock()
    fake_engine.execute.return_value = MagicMock(success=True, execution_time=1.23, errors=[])

    with patch("gateflow.cli.CONFIG_DIR", tmp_path):
        with patch("gateflow.cli.get_settings", return_value=fake_settings):
            with patch("gateflow.cli.build_capability_manifest", return_value={"tool_count": 160}):
                with patch("gateflow.cli.VivadoDetector.detect_vivado", return_value=fake_vivado):
                    with patch("gateflow.cli.EnvironmentDiagnostics.check_port_listener", return_value=DiagnosticResult("l", True, "listener ok")):
                        with patch("gateflow.cli.EnvironmentDiagnostics.check_tcp_protocol", return_value=DiagnosticResult("p", True, "protocol ok")):
                            with patch("gateflow.cli.TclEngine", return_value=fake_engine):
                                status_rc = cmd_status(SimpleNamespace(port=None))

    status_output = capsys.readouterr().out
    assert status_rc == 0
    assert "MCP 工具数: 160" in status_output
    assert "protocol ok" in status_output

    cap_rc = cmd_capabilities(
        SimpleNamespace(
            json=False,
            write=True,
            markdown_path=str(tmp_path / "CAPABILITIES.md"),
            manifest_path=str(tmp_path / "CAPABILITIES.json"),
        )
    )
    assert cap_rc == 0
    assert (tmp_path / "CAPABILITIES.md").exists()
