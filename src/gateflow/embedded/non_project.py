"""Minimal non-project embedded provider orchestration."""

from __future__ import annotations

from pathlib import Path

from gateflow.embedded.providers import ProviderRunResult, ProviderStatus, ReservedProvider
from gateflow.embedded.vitis import VitisProvider
from gateflow.embedded.xsct import XSCTProvider


class NonProjectProvider(ReservedProvider):
    """Minimal orchestration layer for XSA -> BSP -> ELF flows."""

    family = "embedded"

    def __init__(
        self,
        vivado_path: str | None = None,
        xsct_path: str | None = None,
    ):
        super().__init__(tool_path=None)
        self.vitis = VitisProvider(vivado_path=vivado_path)
        self.xsct = XSCTProvider(xsct_path=xsct_path, vivado_path=vivado_path)

    def get_status(self) -> ProviderStatus:
        vitis_status = self.vitis.get_status()
        xsct_status = self.xsct.get_status()
        return ProviderStatus(
            tool_family=self.family,
            implemented=True,
            message="Non-project embedded flow can export XSA and build a minimal standalone ELF",
            metadata={
                "capabilities": [
                    "export_xsa",
                    "create_standalone_app",
                    "create_bsp",
                    "build_elf",
                ],
                "vitis_binary": vitis_status.metadata.get("vivado_binary"),
                "xsct_binary": xsct_status.metadata.get("xsct_binary"),
            },
        )

    def export_xsa(
        self,
        *,
        xpr_path: str,
        output_path: str | None = None,
        include_bit: bool = True,
    ) -> dict[str, object]:
        """Delegate XSA export to the Vitis/Vivado provider."""
        return self.vitis.export_xsa(
            xpr_path=xpr_path,
            output_path=output_path,
            include_bit=include_bit,
        )

    def build_standalone_elf(
        self,
        *,
        workspace_path: str,
        app_name: str,
        xpr_path: str | None = None,
        xsa_path: str | None = None,
        source_path: str | None = None,
        proc: str = "ps7_cortexa9_0",
        template: str = "Empty Application(C)",
        platform_name: str = "gateflow_hw",
        domain_name: str = "standalone_domain",
    ) -> dict[str, object]:
        """Run the minimal embedded closure and return stable artifacts."""
        workspace = self._ensure_directory(workspace_path)
        artifacts: dict[str, object] = {
            "workspace_path": str(workspace),
            "xsa_path": None,
            "bsp_path": None,
            "elf_path": None,
            "size_report_path": None,
        }
        metadata: dict[str, object] = {
            "platform_name": platform_name,
            "domain_name": domain_name,
        }

        resolved_xsa_path = Path(xsa_path).resolve() if xsa_path else workspace / f"{app_name}.xsa"
        if xsa_path is None:
            if not xpr_path:
                return ProviderRunResult(
                    success=False,
                    message="最小软件闭环失败",
                    error="xpr_path_or_xsa_path_required",
                    artifacts=artifacts,
                    metadata=metadata,
                ).to_dict()
            export_result = self.export_xsa(
                xpr_path=xpr_path,
                output_path=str(resolved_xsa_path),
                include_bit=True,
            )
            metadata["export_xsa"] = export_result
            if not export_result.get("success", False):
                return ProviderRunResult(
                    success=False,
                    message="最小软件闭环失败：XSA 导出失败",
                    error=str(export_result.get("error")),
                    artifacts=artifacts,
                    metadata=metadata,
                ).to_dict()
        elif not resolved_xsa_path.exists():
            return ProviderRunResult(
                success=False,
                message="最小软件闭环失败",
                error=f"missing_xsa: {resolved_xsa_path}",
                artifacts=artifacts,
                metadata=metadata,
            ).to_dict()

        artifacts["xsa_path"] = str(resolved_xsa_path)
        metadata["workspace"] = self.xsct.create_workspace(workspace_path=str(workspace))

        app_result = self.xsct.create_standalone_app(
            workspace_path=str(workspace),
            xsa_path=str(resolved_xsa_path),
            app_name=app_name,
            proc=proc,
            template=template,
        )
        metadata["create_standalone_app"] = app_result
        if not app_result.get("success", False):
            return ProviderRunResult(
                success=False,
                message="最小软件闭环失败：standalone app 创建失败",
                error=str(app_result.get("error")),
                artifacts=artifacts,
                metadata=metadata,
            ).to_dict()

        if source_path:
            source = Path(source_path).resolve()
            if not source.exists():
                return ProviderRunResult(
                    success=False,
                    message="最小软件闭环失败：应用源码不存在",
                    error=f"missing_source: {source}",
                    artifacts=artifacts,
                    metadata=metadata,
                ).to_dict()
            app_source_dir = workspace / app_name / "src"
            app_source_dir.mkdir(parents=True, exist_ok=True)
            main_target = app_source_dir / "main.c"
            main_target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            source_variant = app_source_dir / source.name
            if source_variant.exists() and source_variant != main_target:
                source_variant.unlink()
            metadata["source_injected"] = str(main_target)

        bsp_result = self.xsct.create_bsp(workspace_path=str(workspace), app_name=app_name)
        metadata["create_bsp"] = bsp_result
        if not bsp_result.get("success", False):
            return ProviderRunResult(
                success=False,
                message="最小软件闭环失败：BSP 创建失败",
                error=str(bsp_result.get("error")),
                artifacts=artifacts,
                metadata=metadata,
            ).to_dict()
        artifacts["bsp_path"] = bsp_result["artifacts"].get("bsp_path")

        build_result = self.xsct.build_elf(workspace_path=str(workspace), app_name=app_name)
        metadata["build_elf"] = build_result
        if not build_result.get("success", False):
            return ProviderRunResult(
                success=False,
                message="最小软件闭环失败：ELF 编译失败",
                error=str(build_result.get("error")),
                artifacts=artifacts,
                metadata=metadata,
            ).to_dict()

        build_artifacts = build_result.get("artifacts", {})
        artifacts["elf_path"] = build_artifacts.get("elf_path")
        artifacts["size_report_path"] = build_artifacts.get("size_report_path")

        return ProviderRunResult(
            success=True,
            message="最小软件闭环完成",
            error=None,
            artifacts=artifacts,
            metadata=metadata,
        ).to_dict()
