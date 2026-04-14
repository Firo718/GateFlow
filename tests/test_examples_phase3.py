"""Phase 3 example smoke tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateflow.vivado.simulation import SimulationManager, TestbenchConfig, TestbenchRunner


def test_blink_led_testbench_exists():
    """The blink_led example should include a runnable testbench."""
    tb_path = Path("examples/blink_led/tb_blink_led.v")
    assert tb_path.exists()
    text = tb_path.read_text(encoding="utf-8")
    assert "module tb_blink_led" in text
    assert "blink_led #(" in text


@pytest.mark.asyncio
async def test_blink_led_testbench_runner_smoke():
    """The blink_led example testbench should work with the TestbenchRunner flow."""
    mock_engine = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.errors = []
    mock_result.warnings = []
    mock_result.output = "completed\n"
    mock_engine.execute_async = AsyncMock(return_value=mock_result)

    manager = SimulationManager(mock_engine)
    runner = TestbenchRunner(manager)

    config = TestbenchConfig(
        name="tb_blink_led",
        dut_module="blink_led",
        source_files=[
            Path("examples/blink_led/blink_led.v"),
            Path("examples/blink_led/tb_blink_led.v"),
        ],
    )

    result = await runner.run_testbench(config, simulation_time="1us", log_wave=True)
    assert result.success is True
