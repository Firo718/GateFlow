"""Minimal XSCT-backed provider helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from gateflow.embedded.providers import ProviderRunResult, ProviderStatus, ReservedProvider


class XSCTProvider(ReservedProvider):
    """Minimal XSCT provider for standalone app/BSP/ELF generation."""

    family = "xsct"

    def __init__(
        self,
        xsct_path: str | None = None,
        *,
        vitis_path: str | None = None,
        vivado_path: str | None = None,
    ):
        super().__init__(tool_path=xsct_path)
        self.vitis_path = vitis_path
        self.vivado_path = vivado_path

    def get_status(self) -> ProviderStatus:
        xsct_binary = self._resolve_xsct_binary()
        return ProviderStatus(
            tool_family=self.family,
            implemented=True,
            message="XSCT provider can create workspaces, standalone apps, BSPs and ELF artifacts",
            metadata={
                "xsct_binary": xsct_binary,
                "capabilities": [
                    "xsct_create_workspace",
                    "create_standalone_app",
                    "create_bsp",
                    "build_elf",
                ],
            },
        )

    def _resolve_xsct_binary(self) -> str | None:
        return self._resolve_binary(
            explicit_path=self.tool_path,
            env_var="GATEFLOW_XSCT_BINARY",
            candidates=["xsct.bat", "xsct"],
        )

    def _resolve_vitis_root(self) -> Path | None:
        """Infer the Vitis root from the XSCT binary or environment."""
        if self.vitis_path:
            candidate = Path(self.vitis_path).resolve()
            if candidate.exists():
                return candidate

        xsct_binary = self._resolve_xsct_binary()
        if xsct_binary:
            xsct_path = Path(xsct_binary).resolve()
            if xsct_path.parent.name.lower() == "bin":
                return xsct_path.parent.parent

        for env_var in ("XILINX_VITIS", "XILINX_XSCT"):
            env_value = os.environ.get(env_var)
            if env_value:
                candidate = Path(env_value).resolve()
                if candidate.exists():
                    return candidate

        if self.vivado_path:
            vivado_root = Path(self.vivado_path).resolve()
            if vivado_root.name.lower() == "bin":
                vivado_root = vivado_root.parent.parent
            elif (vivado_root / "bin").exists():
                vivado_root = vivado_root
            version_dir = vivado_root.name
            xilinx_root = vivado_root.parent.parent if vivado_root.parent.name.lower() == "vivado" else vivado_root.parent
            sibling = xilinx_root / "Vitis" / version_dir
            if sibling.exists():
                return sibling

        return None

    def _resolve_make_binary(self) -> str | None:
        vitis_root = self._resolve_vitis_root()
        if vitis_root:
            candidate = vitis_root / "gnuwin" / "bin" / "make.exe"
            if candidate.exists():
                return str(candidate)
        return shutil.which("make.exe") or shutil.which("make")

    def _resolve_size_binary(self) -> str | None:
        vitis_root = self._resolve_vitis_root()
        if vitis_root:
            candidate = vitis_root / "gnu" / "aarch32" / "nt" / "gcc-arm-none-eabi" / "bin" / "arm-none-eabi-size.exe"
            if candidate.exists():
                return str(candidate)
        return shutil.which("arm-none-eabi-size") or shutil.which("size")

    def create_workspace(self, *, workspace_path: str) -> dict[str, object]:
        """Create an XSCT workspace directory."""
        workspace = self._ensure_directory(workspace_path)
        return ProviderRunResult(
            success=True,
            message="XSCT workspace 已就绪",
            error=None,
            artifacts={"workspace_path": str(workspace)},
            metadata={},
        ).to_dict()

    @staticmethod
    def build_create_app_script(
        *,
        workspace_path: str,
        xsa_path: str,
        app_name: str,
        proc: str,
        template: str,
    ) -> str:
        """Generate the XSCT script that creates a standalone app."""
        workspace = Path(workspace_path).resolve().as_posix()
        xsa = Path(xsa_path).resolve().as_posix()
        return "\n".join(
            [
                f"setws {{{workspace}}}",
                f'app create -name {app_name} -hw {{{xsa}}} -proc {proc} -os standalone -template {{{template}}}',
                "exit",
            ]
        )

    def create_standalone_app(
        self,
        *,
        workspace_path: str,
        xsa_path: str,
        app_name: str,
        proc: str = "ps7_cortexa9_0",
        template: str = "Empty Application(C)",
    ) -> dict[str, object]:
        """Create a standalone XSCT app from an XSA."""
        xsct_binary = self._resolve_xsct_binary()
        if not xsct_binary:
            return ProviderRunResult(
                success=False,
                message="创建 standalone app 失败",
                error="xsct_not_found",
                artifacts={},
                metadata={},
            ).to_dict()

        workspace = self._ensure_directory(workspace_path)
        xsa = Path(xsa_path).resolve()
        if not xsa.exists():
            return ProviderRunResult(
                success=False,
                message="创建 standalone app 失败",
                error=f"missing_xsa: {xsa}",
                artifacts={"xsa_path": str(xsa), "workspace_path": str(workspace)},
                metadata={},
            ).to_dict()

        script_path = self._write_script(
            workspace / "gateflow_create_app.tcl",
            self.build_create_app_script(
                workspace_path=str(workspace),
                xsa_path=str(xsa),
                app_name=app_name,
                proc=proc,
                template=template,
            ),
        )
        command = [xsct_binary, str(script_path)]
        success, stdout, stderr = self._run_command(command, cwd=workspace)
        app_path = workspace / app_name

        return ProviderRunResult(
            success=success,
            message="standalone app 创建成功" if success else "standalone app 创建失败",
            error=None if success else (stderr.strip() or stdout.strip() or "xsct_app_create_failed"),
            artifacts={
                "workspace_path": str(workspace),
                "xsa_path": str(xsa),
                "app_path": str(app_path),
                "script_path": str(script_path),
            },
            metadata={
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
            },
        ).to_dict()

    def create_bsp(
        self,
        *,
        workspace_path: str,
        app_name: str,
    ) -> dict[str, object]:
        """Locate the BSP generated alongside the standalone application."""
        workspace = Path(workspace_path).resolve()
        bsp_candidates = sorted(
            {
                path.parent
                for path in workspace.rglob("*.mss")
                if app_name in path.as_posix() or "standalone" in path.as_posix().lower()
            }
        )
        if not bsp_candidates:
            return ProviderRunResult(
                success=False,
                message="BSP 创建失败",
                error="bsp_not_found",
                artifacts={"workspace_path": str(workspace)},
                metadata={},
            ).to_dict()

        return ProviderRunResult(
            success=True,
            message="BSP 已定位",
            error=None,
            artifacts={
                "workspace_path": str(workspace),
                "bsp_path": str(bsp_candidates[0]),
            },
            metadata={},
        ).to_dict()

    @staticmethod
    def build_build_elf_script(
        *,
        workspace_path: str,
        app_name: str,
        size_binary: str | None = None,
    ) -> str:
        """Generate an XSCT script that builds the application and emits size data."""
        workspace = Path(workspace_path).resolve()
        app_debug = workspace / app_name / "Debug"
        app_debug_posix = app_debug.as_posix()
        app_elf = app_debug / f"{app_name}.elf"
        app_size = app_debug / f"{app_name}.elf.size"
        size_command = ""
        if size_binary:
            normalized_size = Path(size_binary).resolve().as_posix()
            if os.name == "nt":
                size_command = f'if {{[file exists "{normalized_size}"]}} {{ puts [exec "{normalized_size}" "{app_elf.as_posix()}"] ; set fp [open "{app_size.as_posix()}" w] ; puts $fp [exec "{normalized_size}" "{app_elf.as_posix()}"] ; close $fp }}'
            else:
                size_command = f'if {{[file executable "{normalized_size}"]}} {{ puts [exec "{normalized_size}" "{app_elf.as_posix()}"] ; set fp [open "{app_size.as_posix()}" w] ; puts $fp [exec "{normalized_size}" "{app_elf.as_posix()}"] ; close $fp }}'
        return "\n".join(
            [
                f"setws {{{workspace.as_posix()}}}",
                f"app build -name {app_name}",
                f"set build_dir {{{app_debug_posix}}}",
                f"set elf_path {{{app_elf.as_posix()}}}",
                f"set size_path {{{app_size.as_posix()}}}",
                "if {![file exists $elf_path]} {",
                '    error "Missing ELF after app build: $elf_path"',
                "}",
                size_command,
                "exit",
            ]
        )

    def build_elf(self, *, workspace_path: str, app_name: str) -> dict[str, object]:
        """Build the standalone ELF inside the generated workspace."""
        xsct_binary = self._resolve_xsct_binary()
        if not xsct_binary:
            return ProviderRunResult(
                success=False,
                message="ELF 编译失败",
                error="xsct_not_found",
                artifacts={},
                metadata={},
            ).to_dict()

        workspace = self._ensure_directory(workspace_path)
        size_binary = self._resolve_size_binary()
        if size_binary is None:
            return ProviderRunResult(
                success=False,
                message="ELF 编译失败",
                error="size_tool_not_found",
                artifacts={
                    "workspace_path": str(workspace),
                    "elf_path": str((workspace / f"{app_name}.elf").resolve()),
                    "size_report_path": str((workspace / f"{app_name}.elf.size").resolve()),
                },
                metadata={},
            ).to_dict()
        script_path = self._write_script(
            workspace / "gateflow_build_elf.tcl",
            self.build_build_elf_script(
                workspace_path=str(workspace),
                app_name=app_name,
                size_binary=size_binary,
            ),
        )
        command = [xsct_binary, str(script_path)]
        success, stdout, stderr = self._run_command(command, cwd=workspace)

        debug_dir = workspace / app_name / "Debug"
        elf_path = debug_dir / f"{app_name}.elf"
        size_report_path = debug_dir / f"{app_name}.elf.size"
        success = success and elf_path.exists() and size_report_path.exists()
        if success:
            staged_elf = workspace / f"{app_name}.elf"
            shutil.copy2(elf_path, staged_elf)
            shutil.copy2(size_report_path, workspace / f"{app_name}.elf.size")

        return ProviderRunResult(
            success=success,
            message="ELF 编译成功" if success else "ELF 编译失败",
            error=None if success else (stderr.strip() or stdout.strip() or "xsct_build_failed"),
            artifacts={
                "workspace_path": str(workspace),
                "elf_path": str((workspace / f"{app_name}.elf").resolve()),
                "size_report_path": str((workspace / f"{app_name}.elf.size").resolve()),
                "script_path": str(script_path),
            },
            metadata={
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
            },
        ).to_dict()
