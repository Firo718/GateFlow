"""
GateFlow capability discovery and rendering helpers.

This module makes the actual FastMCP tool surface the single source of truth
for registry metadata, generated manifests, and generated documentation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from gateflow.tools.bd_advanced_tools import register_bd_advanced_tools
from gateflow.tools.block_design_tools import register_block_design_tools
from gateflow.tools.build_tools import register_build_tools
from gateflow.tools.constraint_tools import register_constraint_tools
from gateflow.tools.embedded_tools import register_embedded_tools
from gateflow.tools.file_tools import register_file_tools
from gateflow.tools.hardware_tools import register_hardware_tools
from gateflow.tools.ip_tools import register_ip_tools
from gateflow.tools.project_tools import register_project_tools
from gateflow.tools.registry import RiskLevel, ToolCategory
from gateflow.tools.simulation_tools import register_simulation_tools
from gateflow.tools.tcl_tools import register_tcl_tools


@dataclass(frozen=True)
class ToolSpec:
    """Serializable description of a public MCP tool."""

    name: str
    description: str
    category: str
    risk_level: str
    requires_vivado: bool
    module: str

    @property
    def short_description(self) -> str:
        """Return the first non-empty line of the description."""
        for line in self.description.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""


_SAFE_NAMES = {
    "read_file",
    "list_files",
    "file_exists",
    "get_file_info",
    "get_project_info",
    "get_utilization_report",
    "get_timing_report",
    "get_power_report",
    "get_drc_report",
    "get_methodology_report",
    "get_run_status",
    "get_hw_devices",
    "get_hw_server_status",
    "hw_ila_list",
    "hw_vio_list",
}

_DANGEROUS_NAMES = {
    "write_file",
    "delete_file",
    "execute_tcl",
    "execute_tcl_batch",
    "execute_tcl_file",
}

_MODULE_CATEGORY_MAP = {
    "project_tools": ToolCategory.PROJECT,
    "file_tools": ToolCategory.FILE,
    "tcl_tools": ToolCategory.TCL,
    "build_tools": ToolCategory.BUILD,
    "constraint_tools": ToolCategory.CONSTRAINT,
    "embedded_tools": ToolCategory.TCL,
    "hardware_tools": ToolCategory.HARDWARE,
    "ip_tools": ToolCategory.IP,
    "block_design_tools": ToolCategory.BLOCK_DESIGN,
    "bd_advanced_tools": ToolCategory.BLOCK_DESIGN,
    "simulation_tools": ToolCategory.SIMULATION,
}


def _create_probe_mcp() -> FastMCP:
    """Create a temporary MCP server and register all public tools."""
    mcp = FastMCP(name="GateFlowCapabilityProbe")
    register_project_tools(mcp)
    register_build_tools(mcp)
    register_constraint_tools(mcp)
    register_embedded_tools(mcp)
    register_hardware_tools(mcp)
    register_ip_tools(mcp)
    register_block_design_tools(mcp)
    register_bd_advanced_tools(mcp)
    register_simulation_tools(mcp)
    register_tcl_tools(mcp)
    register_file_tools(mcp)
    return mcp


def _infer_category(module_name: str) -> ToolCategory:
    """Infer a ToolCategory from the source module."""
    short_name = module_name.rsplit(".", 1)[-1]
    return _MODULE_CATEGORY_MAP.get(short_name, ToolCategory.FILE)


def _infer_risk_level(tool_name: str, category: ToolCategory) -> RiskLevel:
    """Infer risk level from tool name and category."""
    if tool_name in _DANGEROUS_NAMES:
        return RiskLevel.DANGEROUS
    if tool_name in _SAFE_NAMES:
        return RiskLevel.SAFE

    if tool_name.startswith(("get_", "list_", "report_", "check_", "extract_", "analyze_")):
        if category not in {ToolCategory.TCL}:
            return RiskLevel.SAFE

    if tool_name.startswith(("create_", "open_", "set_", "add_", "run_", "generate_", "connect_", "program_", "refresh_", "upgrade_", "configure_", "export_", "save_", "append_", "copy_")):
        return RiskLevel.NORMAL

    return RiskLevel.NORMAL


def _infer_requires_vivado(category: ToolCategory) -> bool:
    """Infer whether the tool requires a Vivado backend."""
    return category not in {ToolCategory.FILE}


def build_runtime_tool_specs() -> list[ToolSpec]:
    """
    Collect the actual public tool surface from FastMCP registrations.

    Returns:
        Sorted list of ToolSpec entries for all registered tools.
    """
    mcp = _create_probe_mcp()
    specs: list[ToolSpec] = []

    for tool in mcp._tool_manager._tools.values():
        module_name = tool.fn.__module__
        category = _infer_category(module_name)
        risk_level = _infer_risk_level(tool.name, category)
        requires_vivado = _infer_requires_vivado(category)
        specs.append(
            ToolSpec(
                name=tool.name,
                description=tool.description.strip(),
                category=category.value,
                risk_level=risk_level.value,
                requires_vivado=requires_vivado,
                module=module_name,
            )
        )

    return sorted(specs, key=lambda spec: (spec.category, spec.name))


def build_capability_manifest() -> dict[str, Any]:
    """Build a machine-readable capability manifest."""
    specs = build_runtime_tool_specs()
    categories: dict[str, int] = {}
    risks: dict[str, int] = {}
    for spec in specs:
        categories[spec.category] = categories.get(spec.category, 0) + 1
        risks[spec.risk_level] = risks.get(spec.risk_level, 0) + 1

    return {
        "tool_count": len(specs),
        "categories": categories,
        "risk_levels": risks,
        "tools": [asdict(spec) for spec in specs],
    }


def render_capabilities_markdown() -> str:
    """Render the public capability manifest as markdown."""
    specs = build_runtime_tool_specs()
    lines = [
        "# GateFlow MCP Tools Capability Manifest",
        "",
        "This file is generated from the actual FastMCP tool registrations.",
        "Do not edit it manually; regenerate it from `gateflow.capabilities`.",
        "",
        f"- Total tools: `{len(specs)}`",
        "",
        "| Tool | Category | Risk | Vivado | Description |",
        "|------|----------|------|--------|-------------|",
    ]

    for spec in specs:
        vivado_flag = "Yes" if spec.requires_vivado else "No"
        lines.append(
            f"| `{spec.name}` | `{spec.category}` | `{spec.risk_level}` | {vivado_flag} | {spec.short_description} |"
        )

    return "\n".join(lines) + "\n"


def default_artifact_paths() -> tuple[Path, Path]:
    """Return default output paths for generated capability artifacts."""
    repo_root = Path(__file__).resolve().parents[2]
    docs_dir = repo_root / "docs"
    return docs_dir / "CAPABILITIES.md", docs_dir / "CAPABILITIES.json"


def write_capability_artifacts(
    markdown_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    Write generated capability markdown and machine-readable manifest to disk.

    Returns:
        Metadata for the generated artifacts.
    """
    default_markdown, default_manifest = default_artifact_paths()
    md_path = Path(markdown_path) if markdown_path is not None else default_markdown
    json_path = Path(manifest_path) if manifest_path is not None else default_manifest

    markdown = render_capabilities_markdown()
    manifest = build_capability_manifest()

    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    md_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "tool_count": manifest["tool_count"],
        "markdown_path": str(md_path),
        "manifest_path": str(json_path),
    }
