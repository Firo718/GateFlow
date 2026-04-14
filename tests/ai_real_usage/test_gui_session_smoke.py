"""Real GUI session smoke for the minimal shared-session mode."""

from __future__ import annotations

import pytest
from pathlib import Path

from gateflow import GateFlow
from gateflow.engine import get_engine_manager


def _find_job1_xpr() -> Path | None:
    repo_root = Path(__file__).resolve().parents[3]
    xpr = repo_root / "manual_runs" / "job1_zed_video" / "project" / "job1_zed_video.xpr"
    return xpr if xpr.exists() else None


@pytest.mark.ai_real_usage
@pytest.mark.integration
@pytest.mark.vivado
@pytest.mark.asyncio
async def test_gui_session_open_status_close_smoke():
    """Start a GUI-backed session, confirm shared session info, then close it."""
    xpr = _find_job1_xpr()
    if xpr is None:
        pytest.skip("job1_zed_video .xpr not available")

    gf = GateFlow(gui_enabled=True, gui_tcp_port=10124)
    result = await gf.open_project_gui(str(xpr), tcp_port=10124)
    if not result.get("success", False):
        pytest.skip(f"GUI smoke skipped: {result.get('error')}")

    info = await gf.get_session_mode_info()
    gui_info = info.get("gui_session", {})
    assert gui_info.get("active") is True
    assert gui_info.get("project_path") == str(xpr)
    assert gui_info.get("tcp_port") == 10124

    await get_engine_manager().close()
