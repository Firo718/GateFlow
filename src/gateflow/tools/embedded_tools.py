"""Embedded / Vitis / XSCT tool registrations."""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.embedded import NonProjectProvider, VitisProvider, XSCTProvider

logger = logging.getLogger(__name__)


class EmbeddedStatusResult(BaseModel):
    """Status payload for embedded providers."""

    success: bool = Field(description="操作是否成功")
    tool_family: str = Field(description="工具族名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    metadata: dict = Field(default_factory=dict, description="状态元数据")


class EmbeddedOperationResult(BaseModel):
    """Stable payload for minimal embedded operations."""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict = Field(default_factory=dict, description="产物路径")
    metadata: dict = Field(default_factory=dict, description="附加元数据")


def register_embedded_tools(mcp: FastMCP) -> None:
    """Register minimal embedded / Vitis / XSCT tools."""

    embedded_provider = NonProjectProvider()
    vitis_provider = VitisProvider()
    xsct_provider = XSCTProvider()

    @mcp.tool()
    async def embedded_status() -> EmbeddedStatusResult:
        """查询 embedded 非工程软件闭环模块状态。"""
        logger.info("查询 embedded 模块状态")
        status = embedded_provider.get_status()
        return EmbeddedStatusResult(
            success=status.implemented,
            tool_family=status.tool_family,
            message=status.message,
            error=None,
            metadata=status.metadata,
        )

    @mcp.tool()
    async def vitis_status() -> EmbeddedStatusResult:
        """查询 Vitis/XSA 导出模块状态。"""
        logger.info("查询 vitis 模块状态")
        status = vitis_provider.get_status()
        return EmbeddedStatusResult(
            success=status.implemented,
            tool_family=status.tool_family,
            message=status.message,
            error=None,
            metadata=status.metadata,
        )

    @mcp.tool()
    async def xsct_status() -> EmbeddedStatusResult:
        """查询 XSCT 软件构建模块状态。"""
        logger.info("查询 xsct 模块状态")
        status = xsct_provider.get_status()
        return EmbeddedStatusResult(
            success=status.implemented,
            tool_family=status.tool_family,
            message=status.message,
            error=None,
            metadata=status.metadata,
        )

    @mcp.tool()
    async def vitis_export_xsa(
        xpr_path: str,
        output_path: str | None = None,
        include_bit: bool = True,
    ) -> EmbeddedOperationResult:
        """从已有 Vivado `.xpr` 导出最小 `.xsa`。"""
        logger.info("导出 XSA: %s", xpr_path)
        result = vitis_provider.export_xsa(
            xpr_path=xpr_path,
            output_path=output_path,
            include_bit=include_bit,
        )
        return EmbeddedOperationResult(**result)

    @mcp.tool()
    async def xsct_create_workspace(workspace_path: str) -> EmbeddedOperationResult:
        """创建或准备 XSCT workspace 目录。"""
        logger.info("创建 XSCT workspace: %s", workspace_path)
        result = xsct_provider.create_workspace(workspace_path=workspace_path)
        return EmbeddedOperationResult(**result)

    @mcp.tool()
    async def vitis_create_standalone_app(
        workspace_path: str,
        xsa_path: str,
        app_name: str,
        proc: str = "ps7_cortexa9_0",
        template: str = "Empty Application(C)",
    ) -> EmbeddedOperationResult:
        """基于 `.xsa` 创建 standalone app。"""
        logger.info("创建 standalone app: %s", app_name)
        result = xsct_provider.create_standalone_app(
            workspace_path=workspace_path,
            xsa_path=xsa_path,
            app_name=app_name,
            proc=proc,
            template=template,
        )
        return EmbeddedOperationResult(**result)

    @mcp.tool()
    async def vitis_create_bsp(
        workspace_path: str,
        app_name: str,
    ) -> EmbeddedOperationResult:
        """定位或创建 standalone app 对应 BSP。"""
        logger.info("定位 BSP: %s", app_name)
        result = xsct_provider.create_bsp(
            workspace_path=workspace_path,
            app_name=app_name,
        )
        return EmbeddedOperationResult(**result)

    @mcp.tool()
    async def vitis_build_elf(
        workspace_path: str,
        app_name: str,
    ) -> EmbeddedOperationResult:
        """编译 standalone app 并输出 `.elf`。"""
        logger.info("编译 ELF: %s", app_name)
        result = xsct_provider.build_elf(
            workspace_path=workspace_path,
            app_name=app_name,
        )
        return EmbeddedOperationResult(**result)
