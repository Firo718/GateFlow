"""AI real-usage tests for reports and checks."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateflow.tools.build_tools import _summarize_lint_findings
from gateflow.utils.parser import ReportParser

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.ai_real_usage
@pytest.mark.release_gate
def test_ai_can_read_report_outputs():
    """AI-facing report outputs should stay structurally stable."""
    util = ReportParser.parse_utilization_report(
        "Slice LUTs | 1234 | 203800 | 0.61\nBlock RAM Tile | 10 | 365 | 2.74"
    )
    timing = ReportParser.parse_timing_report(
        "Setup Slack: 2.345 ns\nHold Slack: 0.567 ns\nTiming Violations: 0"
    )
    power = ReportParser.parse_power_report(
        "Total On-Chip Power: 1.234 W\nDynamic Power: 0.856 W\nStatic Power: 0.378 W"
    )
    drc = ReportParser.parse_drc_report(
        "ERROR: [DRC NSTD-1] Unspecified I/O Standard\nWARNING: [DRC UCIO-1] Unconstrained Logical Port"
    )
    methodology = _summarize_lint_findings(
        "CRITICAL WARNING: clock interaction issue\nWARNING: reset synchronizer issue",
        "warning",
        10,
    )

    assert util["Slice LUTs"]["used"] == 1234
    assert timing["timing_met"] is True
    assert power["total_power"] == 1.234
    assert drc["errors"] == 1
    assert methodology["matched_findings"] == 2


@pytest.mark.ai_real_usage
@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_ai_can_run_report_checks_example():
    """AI should be able to run the report-check example entrypoint."""
    module = _load_module(
        str(EXAMPLES_DIR / "report_checks_example.py"),
        "report_checks_example_ai_usage",
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
    assert result["power_success"] is True
