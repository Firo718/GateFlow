"""Tests for Vivado run observability helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from gateflow.tools.build_tools import ImplementationManagerAdapter


class _Result:
    def __init__(self, success: bool = True, text: str = "", errors: list[str] | None = None):
        self.success = success
        self.data = text
        self.output = text
        self.result = text
        self.errors = errors or []
        self.error = None if success else SimpleNamespace(message="; ".join(self.errors))


class _RunEngine:
    def __init__(self, *, statuses: list[str], run_dir: str = "", progress: list[str] | None = None, direct_messages: str = ""):
        self.statuses = list(statuses)
        self.last_status = self.statuses[-1] if self.statuses else "unknown"
        self.progress = list(progress or [])
        self.last_progress = self.progress[-1] if self.progress else "unknown"
        self.direct_messages = direct_messages
        self.run_dir = run_dir
        self.commands: list[str] = []

    async def execute(self, command: str, timeout=None):
        self.commands.append(command)
        if command.startswith("launch_runs"):
            return _Result()
        if "get_property STATUS [get_runs" in command:
            status = self.statuses.pop(0) if self.statuses else self.last_status
            return _Result(text=status)
        if "get_property PROGRESS [get_runs" in command:
            progress = self.progress.pop(0) if self.progress else self.last_progress
            return _Result(text=progress)
        if "get_property CURRENT_STEP [get_runs" in command:
            return _Result(text="write_bitstream" if "Complete" in self.last_status else "route_design")
        if "get_property NEEDS_REFRESH [get_runs" in command:
            return _Result(text="0")
        if "get_property DIRECTORY [get_runs" in command:
            return _Result(text=self.run_dir)
        if "__GATEFLOW_MESSAGE__" in command or "get_messages -quiet" in command:
            return _Result(text=self.direct_messages)
        if "get_property top [current_fileset]" in command:
            return _Result(text="top")
        if command.startswith("reset_run"):
            return _Result()
        return _Result()


@pytest.mark.asyncio
async def test_launch_and_wait_run_success(tmp_path):
    run_dir = tmp_path / "impl_1"
    run_dir.mkdir()
    (run_dir / "runme.log").write_text("route_design\nwrite_bitstream\n", encoding="utf-8")
    engine = _RunEngine(
        statuses=["Running", "write_bitstream Complete"],
        progress=["50%", "100%"],
        run_dir=str(run_dir),
    )
    manager = ImplementationManagerAdapter(engine)

    result = await manager.launch_and_wait_run("impl_1", timeout=5, poll_interval=0.1)

    assert result["success"] is True
    assert result["is_complete"] is True
    assert result["current_step"] == "write_bitstream"
    assert result["last_known_step"] == "write_bitstream"
    assert result["progress"] == "100%"
    assert any(command.startswith("launch_runs impl_1") for command in engine.commands)


@pytest.mark.asyncio
async def test_launch_and_wait_run_timeout_keeps_last_status(tmp_path):
    run_dir = tmp_path / "synth_1"
    run_dir.mkdir()
    engine = _RunEngine(statuses=["Running", "Running"], progress=["25%", "25%"], run_dir=str(run_dir))
    manager = ImplementationManagerAdapter(engine)

    result = await manager.launch_and_wait_run("synth_1", timeout=0, poll_interval=0.1)

    assert result["success"] is False
    assert result["error"] == "run_wait_timeout"
    assert result["status"] == "Running"
    assert result["message"] == "run 已提交，但等待阶段超时: synth_1"


@pytest.mark.asyncio
async def test_get_run_messages_prefers_direct_query(tmp_path):
    run_dir = tmp_path / "impl_1"
    run_dir.mkdir()
    (run_dir / "runme.log").write_text(
        "INFO: started\nWARNING: routing warning\nERROR: route failed\n",
        encoding="utf-8",
    )
    engine = _RunEngine(
        statuses=["route_design Running"],
        progress=["42%"],
        run_dir=str(run_dir),
        direct_messages="__GATEFLOW_MESSAGE__|WARNING|direct warning\n__GATEFLOW_MESSAGE__|ERROR|direct error\n",
    )
    manager = ImplementationManagerAdapter(engine)

    result = await manager.get_run_messages("impl_1", limit=2)

    assert result["success"] is True
    assert result["matched_count"] == 2
    assert result["messages"][-1]["severity"] == "error"
    assert result["source"] == "vivado_messages"


@pytest.mark.asyncio
async def test_get_run_messages_falls_back_to_log(tmp_path):
    run_dir = tmp_path / "impl_1"
    run_dir.mkdir()
    (run_dir / "runme.log").write_text(
        "INFO: started\nWARNING: routing warning\nERROR: route failed\n",
        encoding="utf-8",
    )
    engine = _RunEngine(
        statuses=["route_design Running"],
        progress=["42%"],
        run_dir=str(run_dir),
        direct_messages="__GATEFLOW_MESSAGES_UNAVAILABLE__|unsupported\n",
    )
    manager = ImplementationManagerAdapter(engine)

    result = await manager.get_run_messages("impl_1", limit=2)

    assert result["success"] is True
    assert result["source"] == "run_log_fallback"
    assert result["details"] == "unsupported"


@pytest.mark.asyncio
async def test_get_run_status_not_found():
    class MissingEngine:
        async def execute(self, command: str, timeout=None):
            return _Result(success=False, errors=["No objects matched get_runs missing"])

    manager = ImplementationManagerAdapter(MissingEngine())
    result = await manager.get_run_status("missing")

    assert result["success"] is False
    assert result["error"] == "run_not_found"
