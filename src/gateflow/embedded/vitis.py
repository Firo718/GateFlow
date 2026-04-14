"""Minimal Vitis/Vivado-backed provider helpers."""

from __future__ import annotations

from pathlib import Path

from gateflow.embedded.providers import ProviderRunResult, ProviderStatus, ReservedProvider
from gateflow.vivado.tcl_engine import VivadoDetector


class VitisProvider(ReservedProvider):
    """Minimal Vitis provider for XSA export."""

    family = "vitis"

    def __init__(self, vivado_path: str | None = None):
        super().__init__(tool_path=vivado_path)

    def get_status(self) -> ProviderStatus:
        vivado_binary = self._resolve_vivado_binary()
        return ProviderStatus(
            tool_family=self.family,
            implemented=True,
            message="Vitis provider can export XSA artifacts from an existing .xpr",
            metadata={
                "vivado_binary": vivado_binary,
                "capabilities": ["export_xsa"],
            },
        )

    def _resolve_vivado_binary(self) -> str | None:
        if self.tool_path:
            candidate = Path(self.tool_path)
            if candidate.is_dir():
                for name in ("bin/vivado.bat", "bin/vivado"):
                    binary = candidate / name
                    if binary.exists():
                        return str(binary.resolve())
            elif candidate.exists():
                return str(candidate.resolve())

        vivado_info = VivadoDetector.detect_vivado(
            config_path=Path(self.tool_path) if self.tool_path and Path(self.tool_path).exists() else None
        )
        if vivado_info:
            return str(vivado_info.executable)

        return self._resolve_binary(
            explicit_path=None,
            env_var="GATEFLOW_VIVADO_BINARY",
            candidates=["vivado.bat", "vivado"],
        )

    @staticmethod
    def build_export_xsa_script(
        xpr_path: str,
        output_path: str,
        *,
        include_bit: bool = True,
    ) -> str:
        """Generate the Vivado Tcl script used to export an XSA."""
        normalized_xpr = Path(xpr_path).resolve().as_posix()
        normalized_output = Path(output_path).resolve().as_posix()
        include_bit_flag = "-include_bit" if include_bit else ""
        return "\n".join(
            [
                f'open_project "{normalized_xpr}"',
                "open_run impl_1",
                f"write_hw_platform -fixed -force {include_bit_flag} -file \"{normalized_output}\"".strip(),
                "close_project",
                "exit",
            ]
        )

    def export_xsa(
        self,
        *,
        xpr_path: str,
        output_path: str | None = None,
        include_bit: bool = True,
    ) -> dict[str, object]:
        """Export an XSA from a Vivado project."""
        vivado_binary = self._resolve_vivado_binary()
        if not vivado_binary:
            return ProviderRunResult(
                success=False,
                message="无法导出 XSA",
                error="vivado_not_found",
                artifacts={},
                metadata={"capabilities": ["export_xsa"]},
            ).to_dict()

        xpr = Path(xpr_path).resolve()
        if not xpr.exists():
            return ProviderRunResult(
                success=False,
                message="无法导出 XSA",
                error=f"missing_xpr: {xpr}",
                artifacts={"xpr_path": str(xpr)},
                metadata={"capabilities": ["export_xsa"]},
            ).to_dict()

        if output_path is None:
            output = xpr.with_suffix(".xsa")
        else:
            output = self._ensure_parent(output_path)

        script_path = self._write_script(
            output.parent / "gateflow_export_xsa.tcl",
            self.build_export_xsa_script(str(xpr), str(output), include_bit=include_bit),
        )
        command = [vivado_binary, "-mode", "batch", "-source", str(script_path)]
        success, stdout, stderr = self._run_command(command, cwd=xpr.parent)

        return ProviderRunResult(
            success=success,
            message="XSA 导出成功" if success else "XSA 导出失败",
            error=None if success else (stderr.strip() or stdout.strip() or "vivado_export_failed"),
            artifacts={
                "xpr_path": str(xpr),
                "xsa_path": str(output),
                "script_path": str(script_path),
            },
            metadata={
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
            },
        ).to_dict()
