"""AI real-usage tests for simulation debug."""

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


@pytest.mark.ai_real_usage
@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_ai_can_run_simulation_debug_flow():
    """AI should be able to use the full simulation debug path."""
    module = _load_module(
        str(EXAMPLES_DIR / "simulation_debug_example.py"),
        "simulation_debug_example_ai_usage",
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
