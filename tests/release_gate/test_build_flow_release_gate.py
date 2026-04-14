"""Release-gate build flow tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateflow import GateFlow


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeResult:
    def __init__(self, success: bool = True, data: str = "", error: str | None = None, warnings: list[str] | None = None):
        self.success = success
        self.data = data
        self.warnings = warnings or []
        self.error = None if error is None else SimpleNamespace(message=error)


class _FakeBuildEngine:
    def __init__(self):
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
        return [_FakeResult() for _ in commands]

    async def execute(self, command, timeout=None):
        if "get_property STATUS [get_runs synth_1]" in command:
            return _FakeResult(data="synth_design Complete")
        if "get_property STATUS [get_runs impl_1]" in command:
            return _FakeResult(data="write_bitstream Complete")
        if "get_property DIRECTORY [get_runs impl_1]" in command:
            return _FakeResult(data=f"{self.project_dir}/{Path(self.project_dir).name}.runs/impl_1")
        if "get_property top [current_fileset]" in command:
            return _FakeResult(data=self.top)
        if "current_project" in command:
            return _FakeResult(data=Path(self.project_dir).name)
        return _FakeResult()


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_subprocess_build_flow_release_gate():
    """The core build flow must succeed on the blink_led example path."""
    gf = GateFlow()
    fake_engine = _FakeBuildEngine()
    here = Path("examples/blink_led")

    with patch.object(gf, "_get_engine", AsyncMock(return_value=fake_engine)):
        result = await gf.create_project("blink_led_gate", str(here / "build_release"), "xc7a35tcpg236-1")
        assert result["success"] is True

        result = await gf.add_source_files([str(here / "blink_led.v")], file_type="verilog")
        assert result["success"] is True

        result = await gf.set_top_module("blink_led")
        assert result["success"] is True

        result = await gf.add_source_files([str(here / "blink_led.xdc")], file_type="xdc")
        assert result["success"] is True

        synth = await gf.run_synthesis()
        impl = await gf.run_implementation()
        bit = await gf.generate_bitstream()

    assert synth["success"] is True
    assert impl["success"] is True
    assert bit["success"] is True
    assert bit["bitstream_path"].endswith("blink_led.bit")


@pytest.mark.release_gate
@pytest.mark.asyncio
async def test_tcp_build_flow_release_gate(release_gate_tcp_config, monkeypatch):
    """The TCP example must still run through its real example entrypoint."""
    module = _load_module(
        str(Path(__file__).resolve().parents[2] / "examples" / "build_zed_led_tcp.py"),
        "build_zed_led_tcp_release_gate",
    )

    fake_gf = MagicMock()
    fake_gf.create_project = AsyncMock(return_value={"success": True})
    fake_gf.add_source_files = AsyncMock(return_value={"success": True})
    fake_gf.set_top_module = AsyncMock(return_value={"success": True})
    fake_gf.run_synthesis = AsyncMock(return_value={"success": True})
    fake_gf.run_implementation = AsyncMock(return_value={"success": True})
    fake_gf.generate_bitstream = AsyncMock(return_value={"success": True})

    monkeypatch.setattr(
        "sys.argv",
        [
            "build_zed_led_tcp.py",
            "--project-name",
            "release_gate_tcp",
            "--tcp-port",
            release_gate_tcp_config["port"],
        ],
    )

    with patch.object(module, "ensure_engine_initialized", AsyncMock(return_value=MagicMock())):
        with patch.object(module, "GateFlow", return_value=fake_gf):
            rc = await module.main()

    assert rc == 0
