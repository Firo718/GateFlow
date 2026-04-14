"""Execution context primitives reserved for future non-project flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ExecutionContextKind:
    """Supported execution context kinds."""

    PROJECT = "project"
    NON_PROJECT = "non_project"
    EMBEDDED = "embedded"


@dataclass
class ExecutionContext:
    """Lightweight execution context carried by higher-level flows."""

    kind: str = ExecutionContextKind.PROJECT
    workspace: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize context for diagnostics and future persistence."""
        return {
            "kind": self.kind,
            "workspace": str(self.workspace) if self.workspace else None,
            "metadata": self.metadata,
        }
