"""Tests for high-frequency GateFlow API wrappers added for real usage."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateflow.api import GateFlow


@pytest.mark.asyncio
async def test_report_wrappers_delegate_to_implementation_manager():
    gf = GateFlow()
    fake_manager = AsyncMock()
    fake_manager.get_drc_report.return_value = {"success": True, "report": "drc"}
    fake_manager.get_methodology_report.return_value = {"success": True, "report": "methodology"}
    fake_manager.get_power_report.return_value = {"success": True, "report": "power"}

    with patch.object(gf, "_get_implementation_manager", AsyncMock(return_value=fake_manager)):
        assert (await gf.get_drc_report())["report"] == "drc"
        assert (await gf.get_methodology_report())["report"] == "methodology"
        assert (await gf.get_power_report())["report"] == "power"


@pytest.mark.asyncio
async def test_simulation_wrappers_delegate_to_simulation_manager():
    gf = GateFlow()
    fake_manager = AsyncMock()
    fake_manager.create_simulation_set.return_value = {"success": True, "name": "sim_2"}
    fake_manager.add_wave.return_value = {"success": True, "signal": "dut.clk"}
    fake_manager.add_force.return_value = {"success": True, "signal": "dut.rst"}
    fake_manager.remove_force.return_value = {"success": True, "signal": "dut.rst"}
    fake_manager.get_signal_value.return_value = {"success": True, "value": "1"}

    with patch.object(gf, "_get_simulation_manager", AsyncMock(return_value=fake_manager)):
        assert (await gf.create_simulation_set("sim_2", ["tb.v"]))["name"] == "sim_2"
        assert (await gf.probe_signal("dut.clk"))["signal"] == "dut.clk"
        assert (await gf.add_force_signal("dut.rst", "1"))["signal"] == "dut.rst"
        assert (await gf.remove_force_signal("dut.rst"))["signal"] == "dut.rst"
        assert (await gf.get_signal_value("dut.done"))["value"] == "1"


@pytest.mark.asyncio
async def test_find_ip_returns_structured_error_when_registry_raises():
    gf = GateFlow()
    fake_registry = AsyncMock()
    fake_registry.query_ip.side_effect = RuntimeError("tcp mismatch")

    with patch.object(gf, "_get_ip_registry", AsyncMock(return_value=fake_registry)):
        result = await gf.find_ip("axi_gpio")

    assert result["success"] is False
    assert result["error"] == "tcp_protocol_error"


@pytest.mark.asyncio
async def test_find_ip_returns_multiple_candidates_structure():
    gf = GateFlow()
    fake_registry = AsyncMock()
    fake_registry.query_ip.return_value = type(
        "Query",
        (),
        {
            "success": False,
            "error": "multiple_candidates",
            "message": "too many candidates",
            "selected_vlnv": "xilinx.com:ip:axi_gpio:2.0",
            "candidates": [
                "xilinx.com:ip:axi_gpio:2.0",
                "xilinx.com:ip:axi_gpio:1.0",
            ],
            "details": None,
        },
    )()

    with patch.object(gf, "_get_ip_registry", AsyncMock(return_value=fake_registry)):
        result = await gf.find_ip("axi_gpio")

    assert result["success"] is True
    assert result["warning"] == "multiple_candidates"
    assert len(result["candidates"]) == 2


@pytest.mark.asyncio
async def test_build_standalone_elf_uses_non_project_provider():
    gf = GateFlow(vivado_path="C:/Xilinx/Vivado/2024.1")
    expected = {"success": True, "artifacts": {"elf_path": "demo.elf"}}

    with patch("gateflow.api.NonProjectProvider") as mock_provider_cls:
        mock_provider = mock_provider_cls.return_value
        mock_provider.build_standalone_elf.return_value = expected
        result = await gf.build_standalone_elf(
            workspace_path="F:/tmp/ws",
            app_name="demo_app",
            xsa_path="F:/tmp/design.xsa",
        )

    assert result == expected
    mock_provider.build_standalone_elf.assert_called_once()


@pytest.mark.asyncio
async def test_run_observability_api_wrappers_delegate_to_manager():
    gf = GateFlow()
    fake_manager = AsyncMock()
    fake_manager.launch_run.return_value = {"success": True, "run_name": "impl_1", "status": "Running"}
    fake_manager.wait_for_run.return_value = {"success": True, "run_name": "impl_1", "status": "Complete"}
    fake_manager.get_run_status.return_value = {"success": True, "run_name": "impl_1", "status": "Running"}
    fake_manager.get_run_progress.return_value = {"success": True, "progress_hint": "running"}
    fake_manager.get_run_messages.return_value = {"success": True, "messages": [{"severity": "info", "text": "ok"}]}

    with patch.object(gf, "_get_implementation_manager", AsyncMock(return_value=fake_manager)):
        assert (await gf.launch_run("impl_1"))["status"] == "Running"
        assert (await gf.wait_for_run("impl_1"))["status"] == "Complete"
        assert (await gf.get_run_status("impl_1"))["status"] == "Running"
        assert (await gf.get_run_progress("impl_1"))["progress_hint"] == "running"
        assert (await gf.get_run_messages("impl_1"))["messages"][0]["text"] == "ok"


@pytest.mark.asyncio
async def test_open_project_treats_already_open_as_success():
    gf = GateFlow()
    fake_engine = MagicMock()
    fake_engine.execute = AsyncMock(
        side_effect=[
            MagicMock(success=False, error=MagicMock(message="Project is already open.")),
        ]
    )

    with patch.object(gf, "_get_engine", AsyncMock(return_value=fake_engine)):
        result = await gf.open_project("F:/demo/demo.xpr")

    assert result["success"] is True
    assert "已在当前会话中打开" in result["message"]


@pytest.mark.asyncio
async def test_gateflow_gui_enabled_uses_gui_session_manager():
    fake_manager = MagicMock()
    fake_manager.is_initialized = False
    fake_manager.initialize = AsyncMock(return_value=True)
    fake_manager.ensure_gui_session = AsyncMock(return_value={"success": True, "shared_session": True})

    with patch("gateflow.api.get_engine_manager", return_value=fake_manager):
        gf = GateFlow(gui_enabled=True, gui_tcp_port=10124)
        engine = await gf._get_engine()

    assert engine is fake_manager
    fake_manager.initialize.assert_awaited_once()
    fake_manager.ensure_gui_session.assert_awaited_once()
