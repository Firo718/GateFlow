"""Runtime smoke tests for Phase 3 examples."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_report_checks_example_main():
    module = _load_module(
        str(EXAMPLES_DIR / "report_checks_example.py"),
        "report_checks_example",
    )

    fake_gf = MagicMock()
    fake_gf.get_utilization_report = AsyncMock(return_value={"success": True, "message": "ok"})
    fake_gf.get_timing_report = AsyncMock(return_value={"success": True, "message": "ok"})
    fake_gf.check_drc = AsyncMock(return_value={"success": True, "matched_findings": 1})
    fake_gf.check_methodology = AsyncMock(return_value={"success": True, "matched_findings": 1})
    fake_gf.get_power_report = AsyncMock(return_value={"success": True, "message": "ok"})

    with patch.object(module, "GateFlow", return_value=fake_gf):
        result = await module.main()

    assert result["utilization_success"] is True
    assert result["timing_success"] is True
    assert result["drc_findings"] >= 1
    assert result["methodology_findings"] >= 1
    assert result["power_success"] is True


@pytest.mark.asyncio
async def test_hardware_debug_runtime_example_main():
    module = _load_module(
        str(EXAMPLES_DIR / "hardware_debug_runtime_example.py"),
        "hardware_debug_runtime_example",
    )

    fake_manager = MagicMock()
    fake_manager.connect_server = AsyncMock(return_value={"success": True})
    fake_manager.program_fpga = AsyncMock(
        return_value=SimpleNamespace(success=True, device="xc7")
    )
    fake_manager.set_probe_file = AsyncMock(return_value={"success": True})

    with patch.object(module, "TclEngine", return_value=MagicMock()):
        with patch.object(module, "HardwareManager", return_value=fake_manager):
            result = await module.main()

    assert result["connect_success"] is True
    assert result["program_success"] is True
    assert result["probe_success"] is True


@pytest.mark.asyncio
async def test_build_zed_led_tcp_main(monkeypatch):
    module = _load_module(
        str(EXAMPLES_DIR / "build_zed_led_tcp.py"),
        "build_zed_led_tcp",
    )

    fake_gf = MagicMock()
    fake_gf.create_project = AsyncMock(return_value={"success": True})
    fake_gf.add_source_files = AsyncMock(return_value={"success": True})
    fake_gf.set_top_module = AsyncMock(return_value={"success": True})
    fake_gf.run_synthesis = AsyncMock(return_value={"success": True})
    fake_gf.run_implementation = AsyncMock(return_value={"success": True})
    fake_gf.generate_bitstream = AsyncMock(return_value={"success": True})

    monkeypatch.setattr(
        "sys.argv",
        ["build_zed_led_tcp.py", "--project-name", "smoke_proj"],
    )

    with patch.object(module, "ensure_engine_initialized", AsyncMock(return_value=MagicMock())):
        with patch.object(module, "GateFlow", return_value=fake_gf):
            rc = await module.main()

    assert rc == 0


@pytest.mark.asyncio
async def test_simulation_debug_example_main():
    module = _load_module(
        str(EXAMPLES_DIR / "simulation_debug_example.py"),
        "simulation_debug_example",
    )

    fake_gf = MagicMock()
    fake_gf.set_simulation_top = AsyncMock(return_value={"success": True})
    fake_gf.compile_simulation = AsyncMock(return_value={"success": True})
    fake_gf.elaborate_simulation = AsyncMock(return_value={"success": True})
    fake_gf.launch_simulation = AsyncMock(return_value={"success": True})
    fake_gf.probe_signal = AsyncMock(return_value={"success": True})
    fake_gf.add_force_signal = AsyncMock(return_value={"success": True})
    fake_gf.run_simulation = AsyncMock(return_value={"success": True})
    fake_gf.get_signal_value = AsyncMock(return_value={"success": True, "value": "8'h55"})
    fake_gf.remove_force_signal = AsyncMock(return_value={"success": True})

    with patch.object(module, "GateFlow", return_value=fake_gf):
        result = await module.main()

    assert result["compile_success"] is True
    assert result["run_success"] is True
    assert result["value_success"] is True


@pytest.mark.asyncio
async def test_ip_query_simulation_example_main():
    module = _load_module(
        str(EXAMPLES_DIR / "ip_query_simulation_example.py"),
        "ip_query_simulation_example",
    )

    fake_gf = MagicMock()
    fake_gf.find_ip = AsyncMock(return_value={"success": True, "vlnv": "xilinx.com:ip:axi_gpio:2.0"})
    fake_gf.list_available_ips = AsyncMock(return_value={"success": True, "count": 3, "ips": []})
    fake_gf.create_simulation_set = AsyncMock(return_value={"success": True})
    fake_gf.set_simulation_top = AsyncMock(return_value={"success": True})
    fake_gf.compile_simulation = AsyncMock(return_value={"success": True})
    fake_gf.elaborate_simulation = AsyncMock(return_value={"success": True})
    fake_gf.launch_simulation = AsyncMock(return_value={"success": True})
    fake_gf.probe_signal = AsyncMock(return_value={"success": True})
    fake_gf.add_force_signal = AsyncMock(return_value={"success": True})
    fake_gf.run_simulation = AsyncMock(return_value={"success": True})
    fake_gf.get_signal_value = AsyncMock(return_value={"success": True, "value": "1"})
    fake_gf.remove_force_signal = AsyncMock(return_value={"success": True})

    with patch.object(module, "GateFlow", return_value=fake_gf):
        result = await module.main()

    assert result["find_ip_success"] is True
    assert result["list_available_ips_success"] is True
    assert result["simulation_success"] is True


@pytest.mark.asyncio
async def test_zynq_template_example_main():
    module = _load_module(
        str(EXAMPLES_DIR / "zynq_template_example.py"),
        "zynq_template_example",
    )

    fake_manager = MagicMock()
    fake_manager.create_design = AsyncMock(return_value={"success": True})
    fake_manager.build_zynq_design = AsyncMock(return_value={"success": True})
    fake_manager.create_axi_gpio = AsyncMock(return_value={"success": True})
    fake_manager.create_axi_dma = AsyncMock(return_value={"success": True})
    fake_manager.save_design = AsyncMock(return_value={"success": True})
    fake_manager.generate_wrapper = AsyncMock(return_value={"success": True})

    with patch.object(module, "TclEngine", return_value=MagicMock()):
        with patch.object(module, "BlockDesignManager", return_value=fake_manager):
            result = await module.main()

    assert result["template_a"] is True
    assert result["template_b"] is True
