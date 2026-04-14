"""Real TCP/Vivado smoke for run observability queries."""

from __future__ import annotations

import asyncio
import os
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

from gateflow import GateFlow
from gateflow.engine import EngineMode, get_engine_manager
from gateflow.settings import reset_settings
from gateflow.vivado.tcl_server import TclServerInstaller


def _find_vivado() -> str | None:
    """Locate a local Vivado binary for the TCP smoke."""
    return shutil.which("vivado.bat") or shutil.which("vivado")


def _wait_for_gateflow_tcp(port: int, timeout: float = 30.0) -> None:
    """Wait until the local GateFlow TCP server answers the probe command."""
    deadline = time.time() + timeout
    last_error = ""
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as sock:
                sock.settimeout(2.0)
                sock.sendall(b"expr 1+2\n")
                data = sock.recv(4096).decode("utf-8", errors="replace")
                if "OK: 3" in data:
                    return
        except OSError as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise RuntimeError(f"GateFlow TCP server on port {port} did not become ready: {last_error}")


@pytest.mark.ai_real_usage
@pytest.mark.integration
@pytest.mark.vivado
@pytest.mark.asyncio
async def test_tcp_run_observability_smoke(tmp_path, monkeypatch):
    """Validate STATUS/PROGRESS/CURRENT_STEP/messages over a real TCP Vivado session."""
    vivado = _find_vivado()
    if not vivado:
        pytest.skip("Vivado binary not available")

    repo_root = Path(__file__).resolve().parents[3]
    xpr_path = repo_root / "manual_runs" / "job1_zed_video" / "project" / "job1_zed_video.xpr"
    if not xpr_path.exists():
        pytest.skip("job1_zed_video project not available")

    port = 10123
    server_script = tmp_path / "gateflow_tcp_smoke.tcl"
    server_script.write_text(TclServerInstaller().generate_script(port=port, blocking=True), encoding="utf-8")

    process = subprocess.Popen(
        [vivado, "-mode", "tcl", "-source", str(server_script), "-nolog", "-nojournal"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        _wait_for_gateflow_tcp(port)

        manager = get_engine_manager()
        await manager.close()
        reset_settings()
        monkeypatch.setenv("GATEFLOW_TCP_PORT", str(port))
        monkeypatch.delenv("GATEFLOW_VIVADO_PATH", raising=False)
        await manager.initialize(EngineMode.TCP)

        gf = GateFlow()
        gf._engine = manager

        opened = await gf.open_project(str(xpr_path))
        assert opened["success"] is True

        synth_status = await gf.get_run_status("synth_1")
        impl_status = await gf.get_run_status("impl_1")
        impl_progress = await gf.get_run_progress("impl_1")
        impl_messages = await gf.get_run_messages("impl_1", limit=10)

        assert synth_status["success"] is True
        assert synth_status["status_source"] == "vivado"
        assert synth_status["progress"] not in (None, "")
        assert synth_status["current_step"] not in (None, "")

        assert impl_status["success"] is True
        assert impl_status["status_source"] == "vivado"
        assert impl_status["progress"] not in (None, "")
        assert impl_status["current_step"] not in (None, "")

        assert impl_progress["success"] is True
        assert impl_progress["progress"] == impl_status["progress"]
        assert impl_progress["current_step"] == impl_status["current_step"]
        assert impl_progress["last_known_step"] == impl_status["last_known_step"]

        assert impl_messages["success"] is True
        assert impl_messages["source"] in {"vivado_messages", "run_log_fallback"}
        assert "matched_count" in impl_messages
    finally:
        try:
            await get_engine_manager().close()
        except Exception:
            pass
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
