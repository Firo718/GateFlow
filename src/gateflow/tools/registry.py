"""
工具注册表模块。

提供工具的注册、管理和开关控制功能，支持插件化架构。
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别枚举"""

    PROJECT = "project"
    BLOCK_DESIGN = "block_design"
    FILE = "file"
    TCL = "tcl"
    BUILD = "build"
    SIMULATION = "simulation"
    HARDWARE = "hardware"
    IP = "ip"
    CONSTRAINT = "constraint"


class RiskLevel(Enum):
    """风险级别枚举"""

    SAFE = "SAFE"  # 安全操作，无风险
    NORMAL = "NORMAL"  # 正常操作，一般风险
    DANGEROUS = "DANGEROUS"  # 危险操作，需要确认


@dataclass
class ToolInfo:
    """
    工具信息数据类。

    Attributes:
        name: 工具名称（唯一标识）
        description: 工具描述
        category: 工具类别
        risk_level: 风险级别
        enabled: 是否启用
        requires_vivado: 是否需要 Vivado 环境
        handler: 工具处理函数
        input_schema: 输入参数 JSON Schema（可选）
        metadata: 额外元数据
    """

    name: str
    description: str
    category: ToolCategory
    risk_level: RiskLevel = RiskLevel.NORMAL
    enabled: bool = True
    requires_vivado: bool = False
    handler: Callable | None = None
    input_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "enabled": self.enabled,
            "requires_vivado": self.requires_vivado,
            "metadata": self.metadata,
        }


class ToolRegistry:
    """
    工具注册表。

    管理所有工具的注册、注销、启用和禁用。

    Example:
        ```python
        registry = ToolRegistry()

        # 注册工具
        registry.register(
            name="create_project",
            handler=create_project_handler,
            category=ToolCategory.PROJECT,
            description="创建新的 Vivado 项目",
            risk_level=RiskLevel.NORMAL,
        )

        # 禁用工具
        registry.disable("delete_file")

        # 获取已启用的工具
        for tool in registry.list_enabled():
            print(tool.name)
        ```
    """

    def __init__(self):
        """初始化工具注册表"""
        self._tools: dict[str, ToolInfo] = {}
        self._handlers: dict[str, Callable] = {}
        logger.debug("工具注册表已初始化")

    def register(
        self,
        name: str,
        handler: Callable,
        category: ToolCategory,
        description: str = "",
        risk_level: RiskLevel = RiskLevel.NORMAL,
        requires_vivado: bool = False,
        input_schema: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        注册工具。

        Args:
            name: 工具名称（唯一标识）
            handler: 工具处理函数
            category: 工具类别
            description: 工具描述（默认使用 handler 的 docstring）
            risk_level: 风险级别
            requires_vivado: 是否需要 Vivado 环境
            input_schema: 输入参数 JSON Schema
            metadata: 额外元数据

        Raises:
            ValueError: 如果工具名称已存在
        """
        if name in self._tools:
            logger.warning(f"工具 '{name}' 已存在，将被覆盖")

        # 如果没有提供描述，使用函数的 docstring
        if not description and handler.__doc__:
            # 只取第一行作为描述
            description = handler.__doc__.strip().split("\n")[0]

        tool_info = ToolInfo(
            name=name,
            description=description,
            category=category,
            risk_level=risk_level,
            requires_vivado=requires_vivado,
            handler=handler,
            input_schema=input_schema,
            metadata=metadata or {},
        )

        self._tools[name] = tool_info
        self._handlers[name] = handler

        logger.info(
            f"已注册工具: {name} (类别: {category.value}, "
            f"风险: {risk_level.value}, Vivado: {requires_vivado})"
        )

    def unregister(self, name: str) -> bool:
        """
        注销工具。

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name not in self._tools:
            logger.warning(f"工具 '{name}' 不存在，无法注销")
            return False

        del self._tools[name]
        del self._handlers[name]
        logger.info(f"已注销工具: {name}")
        return True

    def enable(self, name: str) -> bool:
        """
        启用工具。

        Args:
            name: 工具名称

        Returns:
            是否成功启用
        """
        if name not in self._tools:
            logger.warning(f"工具 '{name}' 不存在，无法启用")
            return False

        self._tools[name].enabled = True
        logger.info(f"已启用工具: {name}")
        return True

    def disable(self, name: str) -> bool:
        """
        禁用工具。

        Args:
            name: 工具名称

        Returns:
            是否成功禁用
        """
        if name not in self._tools:
            logger.warning(f"工具 '{name}' 不存在，无法禁用")
            return False

        self._tools[name].enabled = False
        logger.info(f"已禁用工具: {name}")
        return True

    def get(self, name: str) -> ToolInfo | None:
        """
        获取工具信息。

        Args:
            name: 工具名称

        Returns:
            工具信息，如果不存在则返回 None
        """
        return self._tools.get(name)

    def get_handler(self, name: str) -> Callable | None:
        """
        获取工具处理函数。

        Args:
            name: 工具名称

        Returns:
            处理函数，如果不存在则返回 None
        """
        return self._handlers.get(name)

    def exists(self, name: str) -> bool:
        """
        检查工具是否存在。

        Args:
            name: 工具名称

        Returns:
            工具是否存在
        """
        return name in self._tools

    def is_enabled(self, name: str) -> bool:
        """
        检查工具是否启用。

        Args:
            name: 工具名称

        Returns:
            工具是否启用（不存在则返回 False）
        """
        tool = self._tools.get(name)
        return tool.enabled if tool else False

    def list_all(self, category: ToolCategory | None = None) -> list[ToolInfo]:
        """
        列出所有工具。

        Args:
            category: 可选，按类别筛选

        Returns:
            工具信息列表
        """
        if category is None:
            return list(self._tools.values())

        return [tool for tool in self._tools.values() if tool.category == category]

    def list_enabled(self, category: ToolCategory | None = None) -> list[ToolInfo]:
        """
        列出已启用的工具。

        Args:
            category: 可选，按类别筛选

        Returns:
            已启用的工具信息列表
        """
        tools = self.list_all(category)
        return [tool for tool in tools if tool.enabled]

    def list_disabled(self, category: ToolCategory | None = None) -> list[ToolInfo]:
        """
        列出已禁用的工具。

        Args:
            category: 可选，按类别筛选

        Returns:
            已禁用的工具信息列表
        """
        tools = self.list_all(category)
        return [tool for tool in tools if not tool.enabled]

    def list_by_risk_level(self, risk_level: RiskLevel) -> list[ToolInfo]:
        """
        按风险级别列出工具。

        Args:
            risk_level: 风险级别

        Returns:
            指定风险级别的工具列表
        """
        return [tool for tool in self._tools.values() if tool.risk_level == risk_level]

    def disable_by_risk_level(self, risk_level: RiskLevel) -> int:
        """
        禁用指定风险级别的所有工具。

        Args:
            risk_level: 风险级别

        Returns:
            禁用的工具数量
        """
        count = 0
        for tool in self._tools.values():
            if tool.risk_level == risk_level:
                tool.enabled = False
                count += 1
                logger.info(f"已禁用危险工具: {tool.name}")

        if count > 0:
            logger.info(f"共禁用 {count} 个 {risk_level.value} 级别的工具")
        return count

    def enable_all(self) -> None:
        """启用所有工具"""
        for tool in self._tools.values():
            tool.enabled = True
        logger.info("已启用所有工具")

    def disable_all(self) -> None:
        """禁用所有工具"""
        for tool in self._tools.values():
            tool.enabled = False
        logger.info("已禁用所有工具")

    def apply_config(
        self,
        enabled_tools: list[str] | None = None,
        disabled_tools: list[str] | None = None,
        disable_dangerous_tools: bool = False,
    ) -> dict[str, Any]:
        """
        应用配置到工具注册表。

        Args:
            enabled_tools: 启用的工具列表（None 表示不限制）
            disabled_tools: 禁用的工具列表
            disable_dangerous_tools: 是否禁用所有危险工具

        Returns:
            应用结果统计
        """
        stats = {
            "total_tools": len(self._tools),
            "enabled_count": 0,
            "disabled_count": 0,
            "dangerous_disabled": 0,
        }

        # 先禁用危险工具
        if disable_dangerous_tools:
            stats["dangerous_disabled"] = self.disable_by_risk_level(RiskLevel.DANGEROUS)

        # 应用禁用列表
        if disabled_tools:
            for name in disabled_tools:
                if self.disable(name):
                    stats["disabled_count"] += 1

        # 如果指定了启用列表，则只启用这些工具
        if enabled_tools is not None:
            # 先禁用所有工具
            self.disable_all()
            # 然后启用指定的工具
            for name in enabled_tools:
                if self.enable(name):
                    stats["enabled_count"] += 1
        else:
            # 统计已启用的工具
            stats["enabled_count"] = len(self.list_enabled())

        stats["disabled_count"] = len(self.list_disabled())

        logger.info(f"配置应用完成: {stats}")
        return stats

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_tools": len(self._tools),
            "enabled_tools": len(self.list_enabled()),
            "disabled_tools": len(self.list_disabled()),
            "tools": {name: tool.to_dict() for name, tool in self._tools.items()},
        }


# 全局注册表实例
_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """
    获取全局工具注册表实例。

    Returns:
        ToolRegistry 实例
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_registry() -> None:
    """
    重置全局注册表（主要用于测试）。
    """
    global _global_registry
    _global_registry = None


# ============================================================================
# 装饰器支持
# ============================================================================


def tool(
    name: str,
    category: ToolCategory,
    description: str = "",
    risk_level: RiskLevel = RiskLevel.NORMAL,
    requires_vivado: bool = False,
):
    """
    工具注册装饰器。

    用于将函数标记为工具，并附加工具元数据。

    Args:
        name: 工具名称
        category: 工具类别
        description: 工具描述
        risk_level: 风险级别
        requires_vivado: 是否需要 Vivado 环境

    Returns:
        装饰器函数

    Example:
        ```python
        @tool("create_project", ToolCategory.PROJECT, "创建新项目")
        async def create_project(name: str, path: str, part: str):
            ...
        ```
    """

    def decorator(func: Callable) -> Callable:
        # 将工具信息附加到函数
        func._tool_info = ToolInfo(
            name=name,
            description=description or (func.__doc__.strip().split("\n")[0] if func.__doc__ else ""),
            category=category,
            risk_level=risk_level,
            requires_vivado=requires_vivado,
            handler=func,
        )
        return func

    return decorator


def register_decorated_tools(registry: ToolRegistry, module: Any) -> int:
    """
    注册模块中所有使用 @tool 装饰器标记的函数。

    Args:
        registry: 工具注册表
        module: Python 模块对象

    Returns:
        注册的工具数量
    """
    count = 0
    for name in dir(module):
        obj = getattr(module, name)
        if callable(obj) and hasattr(obj, "_tool_info"):
            tool_info: ToolInfo = obj._tool_info
            registry.register(
                name=tool_info.name,
                handler=tool_info.handler,
                category=tool_info.category,
                description=tool_info.description,
                risk_level=tool_info.risk_level,
                requires_vivado=tool_info.requires_vivado,
            )
            count += 1

    logger.info(f"从模块注册了 {count} 个工具")
    return count
