"""Helpers for consistent tool-layer result models."""

from __future__ import annotations

from typing import Any


def join_errors(error: Any = None, errors: list[Any] | None = None) -> str | None:
    """Normalize tool-layer error text."""
    parts: list[str] = []
    if error:
        parts.append(str(error))
    if errors:
        parts.extend(str(item) for item in errors if item)

    if not parts:
        return None

    deduped: list[str] = []
    for part in parts:
        if part not in deduped:
            deduped.append(part)
    return "; ".join(deduped)


def clean_artifacts(artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Remove empty artifact entries."""
    if not artifacts:
        return {}
    return {key: value for key, value in artifacts.items() if value is not None}
