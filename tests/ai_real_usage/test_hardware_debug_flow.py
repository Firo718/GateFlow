"""AI real-usage tests for hardware debug flow."""

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
async def test_ai_can_run_hardware_debug_runtime_example():
    """AI should be able to follow the hardware debug runtime path."""
    module = _load_module(
        str(EXAMPLES_DIR / "hardware_debug_runtime_example.py"),
        "hardware_debug_runtime_example_ai_usage",
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
