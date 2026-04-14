"""Tests for runtime capability discovery."""

import json
from pathlib import Path

from gateflow.capabilities import (
    build_capability_manifest,
    build_runtime_tool_specs,
    default_artifact_paths,
    render_capabilities_markdown,
    write_capability_artifacts,
)
from gateflow.server import create_registry


def test_runtime_tool_specs_are_discovered():
    """The runtime probe should discover the real public tool surface."""
    specs = build_runtime_tool_specs()
    assert len(specs) >= 120
    names = {spec.name for spec in specs}
    assert "create_project" in names
    assert "run_synthesis_async" in names
    assert "get_power_report" in names
    assert "compile_simulation" in names
    assert "embedded_status" in names
    assert "vitis_status" in names
    assert "xsct_status" in names


def test_registry_matches_runtime_specs():
    """Registry count should match capability discovery count."""
    specs = build_runtime_tool_specs()
    registry = create_registry()
    assert len(registry.list_all()) == len(specs)


def test_manifest_and_markdown_include_runtime_count():
    """Manifest and markdown should be generated from the same source."""
    manifest = build_capability_manifest()
    markdown = render_capabilities_markdown()
    assert manifest["tool_count"] >= 120
    assert f"Total tools: `{manifest['tool_count']}`" in markdown


def test_default_artifact_paths_point_to_docs():
    """Default output paths should point to docs/CAPABILITIES.*."""
    markdown_path, manifest_path = default_artifact_paths()
    assert markdown_path.name == "CAPABILITIES.md"
    assert manifest_path.name == "CAPABILITIES.json"
    assert markdown_path.parent.name == "docs"
    assert manifest_path.parent.name == "docs"


def test_write_capability_artifacts():
    """Artifact writer should emit matching markdown/json files."""
    markdown_path, manifest_path = default_artifact_paths()
    output = write_capability_artifacts(
        markdown_path=markdown_path,
        manifest_path=manifest_path,
    )

    assert markdown_path.exists()
    assert manifest_path.exists()
    assert output["markdown_path"] == str(markdown_path)
    assert output["manifest_path"] == str(manifest_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert manifest["tool_count"] == output["tool_count"]
    assert f"Total tools: `{manifest['tool_count']}`" in markdown
