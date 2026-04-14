"""Execution-context helpers for tool-layer routing."""

from __future__ import annotations

from typing import Any

from gateflow.engine import get_engine_manager
from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.settings import get_settings


def get_active_execution_context() -> ExecutionContext:
    """Return the active execution context from engine or settings."""
    manager = get_engine_manager()
    try:
        return manager.execution_context
    except Exception:
        return get_settings().get_execution_context()


def project_context_error_message(tool_family: str) -> str | None:
    """Return a routing hint when project-only tools are used in another context."""
    context = get_active_execution_context()
    if context.kind == ExecutionContextKind.PROJECT:
        return None
    return (
        f"{tool_family} 工具仅支持 project execution_context。"
        f"当前上下文为 {context.kind}。"
        "请切回 project 上下文，或改用 embedded / vitis / xsct 预留工具族。"
    )


class AsyncContextBlockedProxy:
    """Async proxy returning a consistent routing failure payload."""

    def __init__(self, tool_family: str):
        self.tool_family = tool_family
        self.error = project_context_error_message(tool_family) or "execution_context blocked"

    def _payload(self, operation: str) -> dict[str, Any]:
        return {
            "success": False,
            "message": self.error,
            "error": self.error,
            "errors": [self.error],
            "warnings": [],
            "operation": operation,
        }

    def __getattr__(self, name: str):
        async def _blocked(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return self._payload(name)

        return _blocked
