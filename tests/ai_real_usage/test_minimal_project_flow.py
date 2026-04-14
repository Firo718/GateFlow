"""AI real-usage tests for the minimal RTL project flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from gateflow import GateFlow
from tests.ai_real_usage.helpers import FakeAiBuildEngine


@pytest.mark.ai_real_usage
@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_ai_minimal_blink_led_flow():
    """AI should be able to complete the minimal blink_led build flow."""
    gf = GateFlow()
    fake_engine = FakeAiBuildEngine()
    here = Path("examples/blink_led")

    with patch.object(gf, "_get_engine", AsyncMock(return_value=fake_engine)):
        create = await gf.create_project("blink_led_gate", str(here / "build_ai_usage"), "xc7a35tcpg236-1")
        add_v = await gf.add_source_files([str(here / "blink_led.v")], file_type="verilog")
        set_top = await gf.set_top_module("blink_led")
        add_x = await gf.add_source_files([str(here / "blink_led.xdc")], file_type="xdc")
        synth = await gf.run_synthesis()
        impl = await gf.run_implementation()
        bit = await gf.generate_bitstream()

    assert create["success"] is True
    assert add_v["success"] is True
    assert set_top["success"] is True
    assert add_x["success"] is True
    assert synth["success"] is True
    assert impl["success"] is True
    assert bit["success"] is True
    assert bit["bitstream_path"].endswith("blink_led.bit")
