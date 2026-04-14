"""Helpers for consistent manager return payloads."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def normalize_artifacts(artifacts: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a shallow-cleaned artifacts dictionary."""
    if not artifacts:
        return {}
    return {key: value for key, value in artifacts.items() if value is not None}


def format_result(
    *,
    success: bool,
    message: str,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
    raw_report: str | None = None,
    artifacts: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a consistent result payload used by high-frequency managers."""
    error = None
    if errors:
        error = "; ".join(str(item) for item in errors if item)

    payload: dict[str, Any] = {
        "success": success,
        "message": message,
        "error": error,
        "errors": errors or [],
        "warnings": warnings or [],
        "raw_report": raw_report,
        "artifacts": normalize_artifacts(artifacts),
    }
    payload.update(extra)
    return payload


def path_artifact(path: str | Path | None) -> dict[str, Any]:
    """Convenience helper for a single output path artifact."""
    if path is None:
        return {}
    return {"path": str(path)}
