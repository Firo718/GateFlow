"""Release-gate snapshot tests for report parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gateflow.tools.build_tools import _summarize_lint_findings
from gateflow.utils.parser import ReportParser


SNAPSHOT_PATH = Path(__file__).with_name("snapshots") / "report_snapshots.json"


@pytest.mark.release_gate
def test_report_parser_snapshots():
    """Core report parsers must match stable snapshots."""
    snapshots = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))

    utilization_text = """Slice LUTs | 1234 | 203800 | 0.61
Slice Registers | 5678 | 407600 | 1.39
Block RAM Tile | 10 | 365 | 2.74
DSPs | 5 | 740 | 0.68
"""
    timing_text = """Setup Slack: 2.345 ns
Hold Slack: 0.567 ns
Timing Violations: 0
"""
    power_text = """Total On-Chip Power: 1.234 W
Dynamic Power: 0.856 W
Static Power: 0.378 W
"""
    drc_text = """ERROR: [DRC NSTD-1] Unspecified I/O Standard
WARNING: [DRC UCIO-1] Unconstrained Logical Port
"""
    methodology_text = """CRITICAL WARNING: clock interaction issue
WARNING: reset synchronizer issue
"""

    current = {
        "utilization": ReportParser.parse_utilization_report(utilization_text),
        "timing": ReportParser.parse_timing_report(timing_text),
        "power": ReportParser.parse_power_report(power_text),
        "drc": ReportParser.parse_drc_report(drc_text),
        "methodology": _summarize_lint_findings(methodology_text, "warning", 10),
    }

    assert current == snapshots
