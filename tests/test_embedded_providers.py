"""Tests for embedded / vitis / xsct providers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from gateflow.embedded import NonProjectProvider, VitisProvider, XSCTProvider


def test_non_project_provider_status():
    status = NonProjectProvider().get_status()
    assert status.tool_family == "embedded"
    assert status.implemented is True
    assert "export_xsa" in status.metadata["capabilities"]


def test_vitis_provider_status():
    status = VitisProvider().get_status()
    assert status.tool_family == "vitis"
    assert status.implemented is True
    assert "export_xsa" in status.metadata["capabilities"]


def test_xsct_provider_status():
    status = XSCTProvider().get_status()
    assert status.tool_family == "xsct"
    assert status.implemented is True
    assert "build_elf" in status.metadata["capabilities"]


def test_xsct_provider_can_infer_vitis_from_vivado_path(tmp_path):
    vivado_root = tmp_path / "Vivado" / "2024.1"
    vitis_root = tmp_path / "Vitis" / "2024.1"
    (vivado_root / "bin").mkdir(parents=True)
    (vitis_root / "bin").mkdir(parents=True)
    (vitis_root / "bin" / "xsct.bat").write_text("@echo off\n", encoding="utf-8")

    provider = XSCTProvider(vivado_path=str(vivado_root))

    assert provider._resolve_vitis_root() == vitis_root.resolve()


def test_build_elf_requires_size_report_tool(tmp_path):
    workspace = tmp_path / "ws"
    provider = XSCTProvider(xsct_path="F:/fake/xsct.bat")

    with patch.object(provider, "_resolve_xsct_binary", return_value="xsct.bat"):
        with patch.object(provider, "_resolve_size_binary", return_value=None):
            result = provider.build_elf(workspace_path=str(workspace), app_name="demo_app")

    assert result["success"] is False
    assert result["error"] == "size_tool_not_found"


def test_vitis_export_xsa_generates_script_and_artifacts(tmp_path):
    xpr_path = tmp_path / "demo.xpr"
    xpr_path.write_text("placeholder", encoding="utf-8")

    provider = VitisProvider()
    with patch.object(provider, "_resolve_vivado_binary", return_value="vivado.bat"):
        with patch.object(provider, "_run_command", return_value=(True, "ok", "")):
            result = provider.export_xsa(xpr_path=str(xpr_path))

    assert result["success"] is True
    artifacts = result["artifacts"]
    script_path = Path(artifacts["script_path"])
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert "write_hw_platform" in content
    assert artifacts["xsa_path"].endswith(".xsa")


def test_xsct_create_standalone_app_generates_script(tmp_path):
    workspace = tmp_path / "ws"
    xsa_path = tmp_path / "design.xsa"
    xsa_path.write_text("placeholder", encoding="utf-8")

    provider = XSCTProvider()
    with patch.object(provider, "_resolve_xsct_binary", return_value="xsct.bat"):
        with patch.object(provider, "_run_command", return_value=(True, "ok", "")):
            result = provider.create_standalone_app(
                workspace_path=str(workspace),
                xsa_path=str(xsa_path),
                app_name="demo_app",
            )

    assert result["success"] is True
    script_path = Path(result["artifacts"]["script_path"])
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")
    assert "app create" in content
    assert "demo_app" in content


def test_non_project_provider_orchestrates_minimal_elf_flow(tmp_path):
    workspace = tmp_path / "ws"
    source_path = tmp_path / "main.c"
    source_path.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    provider = NonProjectProvider()
    fake_xsa = tmp_path / "demo.xsa"
    fake_xsa.write_text("xsa", encoding="utf-8")
    fake_elf = workspace / "demo_app.elf"
    fake_size = workspace / "demo_app.elf.size"

    with patch.object(provider, "export_xsa", return_value={"success": True, "artifacts": {"xsa_path": str(fake_xsa)}}):
        with patch.object(provider.xsct, "create_workspace", return_value={"success": True, "artifacts": {"workspace_path": str(workspace)}}):
            with patch.object(provider.xsct, "create_standalone_app", return_value={"success": True, "artifacts": {"app_path": str(workspace / 'demo_app')}}):
                with patch.object(provider.xsct, "create_bsp", return_value={"success": True, "artifacts": {"bsp_path": str(workspace / 'bsp')}}):
                    with patch.object(provider.xsct, "build_elf", return_value={"success": True, "artifacts": {"elf_path": str(fake_elf), "size_report_path": str(fake_size)}}):
                        result = provider.build_standalone_elf(
                            workspace_path=str(workspace),
                            app_name="demo_app",
                            xpr_path=str(tmp_path / "demo.xpr"),
                            source_path=str(source_path),
                        )

    assert result["success"] is True
    assert result["artifacts"]["elf_path"] == str(fake_elf)
    assert result["artifacts"]["size_report_path"] == str(fake_size)
