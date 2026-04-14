"""Common provider helpers for embedded-oriented execution contexts."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProviderStatus:
    """Serializable provider status."""

    tool_family: str
    implemented: bool
    message: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert status to a plain dict."""
        return {
            "tool_family": self.tool_family,
            "implemented": self.implemented,
            "message": self.message,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class ProviderRunResult:
    """Serializable provider execution result."""

    success: bool
    message: str
    error: str | None
    artifacts: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert an execution result to a stable API/tool payload."""
        return {
            "success": self.success,
            "message": self.message,
            "error": self.error,
            "artifacts": self.artifacts,
            "metadata": self.metadata,
        }


class ReservedProvider:
    """Base class for embedded/Vitis/XSCT helpers."""

    family: str = "reserved"

    def __init__(self, tool_path: str | None = None):
        self.tool_path = tool_path

    def get_status(self) -> ProviderStatus:
        """Return provider status."""
        return ProviderStatus(
            tool_family=self.family,
            implemented=True,
            message=f"{self.family} provider exposes a minimal callable interface",
            metadata={},
        )

    @staticmethod
    def _normalize_path(path: str | Path | None) -> str | None:
        if path is None:
            return None
        return str(Path(path).resolve())

    @staticmethod
    def _ensure_parent(path: str | Path) -> Path:
        resolved = Path(path).resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _ensure_directory(path: str | Path) -> Path:
        resolved = Path(path).resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _write_script(path: str | Path, content: str) -> Path:
        script_path = Path(path).resolve()
        script_path.parent.mkdir(parents=True, exist_ok=True)
        script_path.write_text(content, encoding="utf-8")
        return script_path

    @staticmethod
    def _resolve_binary(
        explicit_path: str | None,
        env_var: str | None,
        candidates: list[str],
    ) -> str | None:
        if explicit_path:
            explicit = Path(explicit_path).expanduser().resolve()
            if explicit.exists():
                return str(explicit)

        if env_var:
            env_value = os.environ.get(env_var)
            if env_value:
                env_path = Path(env_value).expanduser().resolve()
                if env_path.exists():
                    return str(env_path)

        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found
        return None

    @staticmethod
    def _run_command(
        command: list[str],
        *,
        cwd: str | Path | None = None,
        timeout: int = 1800,
    ) -> tuple[bool, str, str]:
        completed = subprocess.run(
            command,
            cwd=str(Path(cwd).resolve()) if cwd is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        success = completed.returncode == 0
        return success, stdout, stderr
