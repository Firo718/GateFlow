"""Helpers for AI real-usage tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


class FakeResult:
    """Minimal engine result compatible with GateFlow API expectations."""

    def __init__(
        self,
        success: bool = True,
        data: str = "",
        error: str | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        self.success = success
        self.data = data
        self.warnings = warnings or []
        self.error = None if error is None else SimpleNamespace(message=error)


class FakeAiBuildEngine:
    """Fake engine that supports the common create/build/report flow."""

    def __init__(self) -> None:
        self.project_dir = ""
        self.top = "blink_led"

    async def execute_batch(self, commands, timeout=None):
        for cmd in commands:
            if cmd.startswith('create_project'):
                parts = cmd.split('"')
                if len(parts) >= 4:
                    self.project_dir = parts[3]
            if cmd.startswith("set_property top"):
                self.top = cmd.split()[2]
        return [FakeResult() for _ in commands]

    async def execute(self, command, timeout=None):
        if "get_property STATUS [get_runs synth_1]" in command:
            return FakeResult(data="synth_design Complete")
        if "get_property STATUS [get_runs impl_1]" in command:
            return FakeResult(data="write_bitstream Complete")
        if "get_property DIRECTORY [get_runs impl_1]" in command:
            base = self.project_dir or "F:/GateFlow/GateFlow_Prj/examples/blink_led/build_output"
            return FakeResult(data=f"{base}/impl_1")
        if "get_property top [current_fileset]" in command:
            return FakeResult(data=self.top)
        if "current_project" in command:
            return FakeResult(data=Path(self.project_dir).name if self.project_dir else "blink_led")
        if "report_utilization" in command:
            return FakeResult(data="Slice LUTs | 1234 | 203800 | 0.61")
        if "report_timing_summary" in command or "report_timing" in command:
            return FakeResult(data="Setup Slack: 2.345 ns\nHold Slack: 0.567 ns\nTiming Violations: 0")
        if "report_power" in command:
            return FakeResult(data="Total On-Chip Power: 1.234 W\nDynamic Power: 0.856 W\nStatic Power: 0.378 W")
        if "report_drc" in command:
            return FakeResult(data="ERROR: [DRC NSTD-1] Unspecified I/O Standard")
        if "report_methodology" in command:
            return FakeResult(data="CRITICAL WARNING: clock interaction issue")
        return FakeResult()
