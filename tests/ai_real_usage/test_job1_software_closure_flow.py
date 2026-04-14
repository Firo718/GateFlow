"""AI real-usage smoke for the minimal job1 software closure."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from gateflow import GateFlow


def _detect_toolchain() -> dict[str, str]:
    """Locate the local Vivado/Vitis binaries needed for the smoke."""
    vivado = shutil.which("vivado.bat") or shutil.which("vivado")
    xsct = shutil.which("xsct.bat") or shutil.which("xsct")

    if xsct:
        xsct_path = Path(xsct).resolve()
        vitis_root = xsct_path.parent.parent if xsct_path.parent.name.lower() == "bin" else xsct_path.parent
    else:
        candidate = Path(r"F:\Xilinx2023p1\Vitis\2023.1\bin\xsct.bat")
        xsct = str(candidate) if candidate.exists() else ""
        vitis_root = candidate.parent.parent if candidate.exists() else None

    make_bin = ""
    size_bin = ""
    if vitis_root:
        make_candidate = vitis_root / "gnuwin" / "bin" / "make.exe"
        size_candidate = vitis_root / "gnu" / "aarch32" / "nt" / "gcc-arm-none-eabi" / "bin" / "arm-none-eabi-size.exe"
        if make_candidate.exists():
            make_bin = str(make_candidate)
        if size_candidate.exists():
            size_bin = str(size_candidate)

    return {
        "vivado": vivado or "",
        "xsct": xsct or "",
        "make": make_bin,
        "size": size_bin,
    }


@pytest.mark.ai_real_usage
@pytest.mark.release_gate
@pytest.mark.integration
@pytest.mark.vivado
@pytest.mark.asyncio
async def test_job1_xsa_to_elf_smoke(tmp_path, monkeypatch):
    """GateFlow should be able to continue job1 from .xpr to .elf delivery."""
    repo_root = Path(__file__).resolve().parents[3]
    job1_root = repo_root / "manual_runs" / "job1_zed_video"
    xpr_path = job1_root / "project" / "job1_zed_video.xpr"
    source_path = job1_root / "sw" / "ps_control_app_main.c"

    if not xpr_path.exists() or not source_path.exists():
        pytest.skip("job1_zed_video inputs not present")

    toolchain = _detect_toolchain()
    if not all([toolchain["vivado"], toolchain["xsct"], toolchain["make"], toolchain["size"]]):
        pytest.skip("Vivado/Vitis local toolchain not fully available for job1 software smoke")

    monkeypatch.setenv("GATEFLOW_XSCT_BINARY", toolchain["xsct"])
    monkeypatch.setenv(
        "PATH",
        str(Path(toolchain["make"]).parent)
        + os.pathsep
        + str(Path(toolchain["size"]).parent)
        + os.pathsep
        + os.environ.get("PATH", ""),
    )

    gf = GateFlow(vivado_path=str(Path(toolchain["vivado"]).resolve().parent.parent))
    xsa_path = tmp_path / "job1_smoke.xsa"
    workspace_path = tmp_path / "job1_ws"

    export_result = await gf.export_xsa(
        xpr_path=str(xpr_path),
        output_path=str(xsa_path),
    )
    assert export_result["success"] is True
    assert Path(export_result["artifacts"]["xsa_path"]).exists()

    build_result = await gf.build_standalone_elf(
        workspace_path=str(workspace_path),
        app_name="job1_smoke_app",
        xsa_path=str(xsa_path),
        source_path=str(source_path),
    )

    assert build_result["success"] is True
    assert Path(build_result["artifacts"]["xsa_path"]).exists()
    assert Path(build_result["artifacts"]["bsp_path"]).exists()
    assert Path(build_result["artifacts"]["elf_path"]).exists()
    assert Path(build_result["artifacts"]["size_report_path"]).exists()
