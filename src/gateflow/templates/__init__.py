"""
GateFlow 平台模板库

提供各种 FPGA 开发板的平台模板，支持快速创建项目。
"""

from gateflow.templates.platform_registry import (
    PlatformRegistry,
    get_platform,
    list_platforms,
    register_platform,
)
from gateflow.templates.common.base import (
    PlatformInfo,
    PlatformTemplate,
    PSType,
)

__all__ = [
    # 注册表
    "PlatformRegistry",
    "get_platform",
    "list_platforms",
    "register_platform",
    # 基类
    "PlatformInfo",
    "PlatformTemplate",
    "PSType",
]
