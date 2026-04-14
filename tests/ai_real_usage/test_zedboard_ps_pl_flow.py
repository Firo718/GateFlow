"""AI real-usage tests for ZedBoard PS+PL template flows."""

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
async def test_ai_can_build_zedboard_ps_pl_templates():
    """AI should be able to use both ZedBoard PS+PL template routes."""
    module = _load_module(
        str(EXAMPLES_DIR / "zynq_template_example.py"),
        "zynq_template_example_ai_usage",
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
