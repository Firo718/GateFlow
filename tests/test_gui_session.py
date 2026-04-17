"""Tests for the minimal GUI session mode."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gateflow import GateFlow
from gateflow.engine import EngineManager, EngineMode


def _mock_result(*, success: bool, data=None, result=None, output: str | None = None):
    mock = MagicMock()
    mock.success = success
    mock.data = data
    mock.result = result
    mock.output = "" if output is None else output
    return mock


@pytest.fixture(autouse=True)
def _isolated_gui_state_root(request):
    root = Path.cwd() / ".pytest-gui-state" / request.node.name
    root.mkdir(parents=True, exist_ok=True)
    state_file = root / "gui_session.json"
    with patch("gateflow.engine.CONFIG_DIR", root):
        with patch("gateflow.engine.GUI_SESSION_STATE_FILE", state_file):
            with patch("gateflow.engine.Path.home", return_value=root):
                yield root


@pytest.mark.asyncio
async def test_api_open_project_gui_delegates_to_engine_manager():
    gf = GateFlow()
    fake_manager = MagicMock()
    fake_manager.is_initialized = False
    fake_manager.initialize = AsyncMock(return_value=True)
    fake_manager.ensure_gui_session = AsyncMock(
        return_value={
            "success": True,
            "message": "GUI 会话已启动",
            "error": None,
            "project_path": "F:/demo/demo.xpr",
            "tcp_port": 10099,
            "gui_process_started": True,
            "shared_session": True,
        }
    )

    with patch("gateflow.api.get_engine_manager", return_value=fake_manager):
        result = await gf.open_project_gui("F:/demo/demo.xpr", tcp_port=10099)

    assert result["success"] is True
    fake_manager.initialize.assert_awaited_once_with(EngineMode.GUI_SESSION)
    fake_manager.ensure_gui_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_api_attach_gui_session_delegates_to_engine_manager():
    gf = GateFlow()
    fake_manager = MagicMock()
    fake_manager.is_initialized = False
    fake_manager.initialize = AsyncMock(return_value=True)
    fake_manager.attach_gui_session = AsyncMock(
        return_value={
            "success": True,
            "message": "已附着到现有 GUI 会话",
            "error": None,
            "project_path": "F:/demo/demo.xpr",
            "tcp_port": 10124,
            "gui_process_started": False,
            "shared_session": True,
            "attached": True,
        }
    )

    with patch("gateflow.api.get_engine_manager", return_value=fake_manager):
        result = await gf.attach_gui_session(10124, project_path="F:/demo/demo.xpr")

    assert result["success"] is True
    fake_manager.initialize.assert_awaited_once_with(EngineMode.GUI_SESSION)
    fake_manager.attach_gui_session.assert_awaited_once()


def test_engine_mode_info_includes_gui_session():
    manager = EngineManager()
    info = manager.get_mode_info()
    assert "gui_session" in info


@pytest.mark.asyncio
async def test_engine_ensure_gui_session_without_vivado_returns_error(monkeypatch):
    manager = EngineManager()
    await manager.close()

    with patch("gateflow.engine.VivadoDetector.detect_vivado", return_value=None):
        result = await manager.ensure_gui_session(project_path="F:/demo/demo.xpr", tcp_port=10099)

    assert result["success"] is False
    assert result["error"] == "vivado_not_found"


@pytest.mark.asyncio
async def test_engine_ensure_gui_session_success():
    manager = EngineManager()
    await manager.close()
    fake_vivado = MagicMock(
        version="2024.1",
        install_path=Path("C:/Xilinx/Vivado/2024.1"),
        executable=Path("C:/Xilinx/Vivado/2024.1/bin/vivado.bat"),
    )
    fake_process = MagicMock()
    fake_process.poll.return_value = None
    current_project_missing = _mock_result(success=False)
    open_project_ok = _mock_result(success=True)

    with patch("gateflow.engine.VivadoDetector.detect_vivado", return_value=fake_vivado):
        with patch("gateflow.engine.subprocess.Popen", return_value=fake_process):
            with patch.object(manager, "_wait_for_tcp_ready", AsyncMock(return_value=True)):
                with patch("gateflow.engine.TcpClientManager.reset"):
                        with patch("gateflow.engine.TcpClientManager.get_client", return_value=MagicMock()):
                            with patch("gateflow.engine.TcpClientManager.ensure_connected", AsyncMock(return_value=True)):
                                with patch.object(
                                    manager,
                                    "execute",
                                    AsyncMock(side_effect=[current_project_missing, open_project_ok]),
                                ):
                                    result = await manager.ensure_gui_session(
                                        project_path="F:/demo/demo.xpr",
                                        tcp_port=10099,
                                    )

    assert result["success"] is True
    assert result["shared_session"] is True
    assert result["project_path"] == "F:/demo/demo.xpr"


@pytest.mark.asyncio
async def test_engine_ensure_gui_session_timeout_keeps_pending_process(_isolated_gui_state_root):
    manager = EngineManager()
    await manager.close()
    fake_vivado = MagicMock(
        version="2024.1",
        install_path=Path("C:/Xilinx/Vivado/2024.1"),
        executable=Path("C:/Xilinx/Vivado/2024.1/bin/vivado.bat"),
    )
    fake_process = MagicMock()
    fake_process.poll.return_value = None
    fake_process.pid = 4321
    state_file = _isolated_gui_state_root / "gui_session.json"

    with patch("gateflow.engine.VivadoDetector.detect_vivado", return_value=fake_vivado):
        with patch("gateflow.engine.subprocess.Popen", return_value=fake_process):
            with patch.object(manager, "_wait_for_tcp_ready", AsyncMock(return_value=False)):
                result = await manager.ensure_gui_session(
                    project_path="F:/demo/demo.xpr",
                    tcp_port=10099,
                )

    assert result["success"] is False
    assert result["error"] == "gui_tcp_not_ready"
    assert result["gui_process_started"] is True
    assert result["shared_session"] is True
    fake_process.terminate.assert_not_called()
    persisted = json.loads(state_file.read_text(encoding="utf-8"))
    assert persisted["tcp_port"] == 10099
    assert persisted["startup_pending"] is True


def test_engine_get_mode_info_uses_persisted_gui_state(_isolated_gui_state_root):
    state_file = _isolated_gui_state_root / "gui_session.json"
    state_file.write_text(
        json.dumps(
            {
                "project_path": "F:/demo/demo.xpr",
                "tcp_port": 10124,
                "server_script": str(_isolated_gui_state_root / "gui_session_10124.tcl"),
                "owned_process": False,
                "pid": None,
                "startup_pending": False,
            }
        ),
        encoding="utf-8",
    )

    manager = EngineManager()
    manager._initialized = False
    manager.__init__()
    info = manager.get_mode_info()

    gui_info = info["gui_session"]
    assert gui_info["active"] is True
    assert gui_info["tcp_port"] == 10124
    assert gui_info["project_path"] == "F:/demo/demo.xpr"


@pytest.mark.asyncio
async def test_engine_auto_mode_prefers_gui_when_enabled():
    manager = EngineManager()
    await manager.close()

    with patch("gateflow.engine.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(
            gui_enabled=True,
            gui_tcp_port=10124,
            get_execution_context=MagicMock(return_value=manager.execution_context),
            get_timeout_config=MagicMock(return_value=manager._timeout_config),
        )
        with patch.object(manager, "ensure_gui_session", AsyncMock(return_value={"success": True})):
            ok = await manager.initialize(EngineMode.AUTO)

    assert ok is True
    assert manager.mode == EngineMode.GUI_SESSION


@pytest.mark.asyncio
async def test_engine_attach_gui_session_does_not_own_process():
    manager = EngineManager()
    await manager.close()

    with patch.object(manager, "_wait_for_tcp_ready", AsyncMock(return_value=True)):
        with patch("gateflow.engine.TcpClientManager.reset"):
            with patch("gateflow.engine.TcpClientManager.get_client", return_value=MagicMock()):
                with patch("gateflow.engine.TcpClientManager.ensure_connected", AsyncMock(return_value=True)):
                    with patch.object(
                        manager,
                        "execute",
                        AsyncMock(
                            side_effect=[
                                _mock_result(success=True, data="demo"),
                                _mock_result(success=True, data="F:/demo"),
                            ]
                        ),
                    ):
                        result = await manager.attach_gui_session(tcp_port=10124)

    assert result["success"] is True
    assert manager._gui_owned_process is False


@pytest.mark.asyncio
async def test_engine_attach_gui_session_reuses_same_project_without_reopen():
    manager = EngineManager()
    await manager.close()
    execute = AsyncMock(
        side_effect=[
            _mock_result(success=True, data="demo"),
            _mock_result(success=True, data="F:/demo"),
        ]
    )

    with patch.object(manager, "_wait_for_tcp_ready", AsyncMock(return_value=True)):
        with patch("gateflow.engine.TcpClientManager.reset"):
            with patch("gateflow.engine.TcpClientManager.get_client", return_value=MagicMock()):
                with patch("gateflow.engine.TcpClientManager.ensure_connected", AsyncMock(return_value=True)):
                    with patch.object(manager, "execute", execute):
                        result = await manager.attach_gui_session(
                            tcp_port=10124,
                            project_path="F:/demo/demo.xpr",
                        )

    assert result["success"] is True
    assert [call.args[0] for call in execute.await_args_list] == [
        "current_project",
        "get_property directory [current_project]",
    ]
    assert result["project_path"] == "F:/demo/demo.xpr"


@pytest.mark.asyncio
async def test_engine_attach_gui_session_rejects_project_mismatch():
    manager = EngineManager()
    await manager.close()
    execute = AsyncMock(
        side_effect=[
            _mock_result(success=True, data="other"),
            _mock_result(success=True, data="F:/other"),
        ]
    )

    with patch.object(manager, "_wait_for_tcp_ready", AsyncMock(return_value=True)):
        with patch("gateflow.engine.TcpClientManager.reset"):
            with patch("gateflow.engine.TcpClientManager.get_client", return_value=MagicMock()):
                with patch("gateflow.engine.TcpClientManager.ensure_connected", AsyncMock(return_value=True)):
                    with patch.object(manager, "execute", execute):
                        result = await manager.attach_gui_session(
                            tcp_port=10124,
                            project_path="F:/demo/demo.xpr",
                        )

    assert result["success"] is False
    assert result["error"] == "gui_project_mismatch"
    assert result["project_path_requested"] == "F:/demo/demo.xpr"
    assert Path(result["project_path_actual"]) == Path("F:/other/other.xpr")
    assert [call.args[0] for call in execute.await_args_list] == [
        "current_project",
        "get_property directory [current_project]",
    ]


@pytest.mark.asyncio
async def test_engine_attach_gui_session_serializes_concurrent_calls():
    manager = EngineManager()
    await manager.close()
    active = 0
    max_active = 0

    async def fake_attach_gui_session_impl(*, tcp_port: int, project_path: str | None = None):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0)
        active -= 1
        return {"success": True, "tcp_port": tcp_port, "project_path": project_path}

    with patch.object(manager, "_attach_gui_session_impl", side_effect=fake_attach_gui_session_impl):
        await asyncio.gather(
            manager.attach_gui_session(tcp_port=10124),
            manager.attach_gui_session(tcp_port=10124),
        )

    assert max_active == 1
