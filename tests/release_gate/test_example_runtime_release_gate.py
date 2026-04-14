"""Release-gate example runtime tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_report_checks_example_release_gate():
    module = _load_module(
        str(EXAMPLES_DIR / "report_checks_example.py"),
        "report_checks_example_release_gate",
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


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_simulation_debug_example_release_gate():
    module = _load_module(
        str(EXAMPLES_DIR / "simulation_debug_example.py"),
        "simulation_debug_example_release_gate",
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


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_hardware_debug_runtime_example_release_gate():
    module = _load_module(
        str(EXAMPLES_DIR / "hardware_debug_runtime_example.py"),
        "hardware_debug_runtime_example_release_gate",
    )

    fake_manager = MagicMock()
    fake_manager.connect_server = AsyncMock(return_value={"success": True})
    fake_manager.program_fpga = AsyncMock(return_value=MagicMock(success=True))
    fake_manager.set_probe_file = AsyncMock(return_value={"success": True})

    with patch.object(module, "TclEngine", return_value=MagicMock()):
        with patch.object(module, "HardwareManager", return_value=fake_manager):
            result = await module.main()

    assert result["connect_success"] is True
    assert result["program_success"] is True
    assert result["probe_success"] is True


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_zynq_template_example_release_gate():
    module = _load_module(
        str(EXAMPLES_DIR / "zynq_template_example.py"),
        "zynq_template_example_release_gate",
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
