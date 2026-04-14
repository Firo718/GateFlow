"""Tests for execution context reservation hooks."""

from unittest.mock import AsyncMock, patch

import pytest

from gateflow.api import GateFlow
from gateflow.engine import EngineManager
from gateflow.execution_context import ExecutionContextKind
from gateflow.execution_context import ExecutionContext
from gateflow.settings import GateFlowSettings


def test_settings_get_execution_context_defaults():
    """Default execution context should stay project-oriented."""
    settings = GateFlowSettings()
    context = settings.get_execution_context()

    assert context.kind == ExecutionContextKind.PROJECT
    assert context.workspace is None


def test_settings_get_execution_context_custom_workspace():
    """Execution context should expose configured kind and workspace."""
    settings = GateFlowSettings(
        execution_context_kind=ExecutionContextKind.NON_PROJECT,
        execution_workspace="F:/GateFlow/non_project_workspace",
    )
    context = settings.get_execution_context()

    assert context.kind == ExecutionContextKind.NON_PROJECT
    assert str(context.workspace).replace("\\", "/").endswith("non_project_workspace")


def test_engine_mode_info_includes_execution_context():
    """Engine mode info should expose execution context reservation metadata."""
    manager = EngineManager()
    info = manager.get_mode_info()

    assert "execution_context" in info
    assert info["execution_context"]["kind"] in {
        ExecutionContextKind.PROJECT,
        ExecutionContextKind.NON_PROJECT,
        ExecutionContextKind.EMBEDDED,
    }


@pytest.mark.asyncio
async def test_gateflow_passes_execution_context_to_engine():
    """GateFlow should initialize engine using the provided execution context."""
    context = ExecutionContext(kind=ExecutionContextKind.NON_PROJECT)
    gf = GateFlow(execution_context=context)

    fake_engine = EngineManager()
    with patch("gateflow.api.ensure_engine_initialized_for_context", AsyncMock(return_value=fake_engine)) as init_mock:
        engine = await gf._get_engine()

    assert engine is fake_engine
    init_mock.assert_awaited_once()
    assert init_mock.await_args.args[0].kind == ExecutionContextKind.NON_PROJECT
