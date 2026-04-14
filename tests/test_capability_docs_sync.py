"""Ensure committed capability docs stay in sync with runtime discovery."""

import json

from gateflow.capabilities import (
    build_capability_manifest,
    default_artifact_paths,
    render_capabilities_markdown,
)


def test_capability_docs_are_up_to_date():
    """docs/CAPABILITIES.md and docs/CAPABILITIES.json must match runtime output."""
    markdown_path, manifest_path = default_artifact_paths()

    assert markdown_path.exists(), f"Missing generated file: {markdown_path}"
    assert manifest_path.exists(), f"Missing generated file: {manifest_path}"

    expected_markdown = render_capabilities_markdown()
    expected_manifest = build_capability_manifest()

    actual_markdown = markdown_path.read_text(encoding="utf-8")
    actual_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert actual_markdown == expected_markdown
    assert actual_manifest == expected_manifest
