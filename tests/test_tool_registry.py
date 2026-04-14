"""
工具注册表测试。

测试工具注册、启用/禁用和配置应用功能。
"""

import pytest

from gateflow.tools.registry import (
    ToolCategory,
    ToolInfo,
    ToolRegistry,
    RiskLevel,
    get_registry,
    reset_registry,
    tool,
    register_decorated_tools,
)


class TestToolCategory:
    """测试工具类别枚举"""

    def test_category_values(self):
        """测试类别值"""
        assert ToolCategory.PROJECT.value == "project"
        assert ToolCategory.FILE.value == "file"
        assert ToolCategory.TCL.value == "tcl"
        assert ToolCategory.BUILD.value == "build"
        assert ToolCategory.SIMULATION.value == "simulation"


class TestRiskLevel:
    """测试风险级别枚举"""

    def test_risk_level_values(self):
        """测试风险级别值"""
        assert RiskLevel.SAFE.value == "SAFE"
        assert RiskLevel.NORMAL.value == "NORMAL"
        assert RiskLevel.DANGEROUS.value == "DANGEROUS"


class TestToolInfo:
    """测试工具信息数据类"""

    def test_tool_info_creation(self):
        """测试创建工具信息"""
        info = ToolInfo(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.PROJECT,
            risk_level=RiskLevel.NORMAL,
        )
        assert info.name == "test_tool"
        assert info.description == "测试工具"
        assert info.category == ToolCategory.PROJECT
        assert info.risk_level == RiskLevel.NORMAL
        assert info.enabled is True
        assert info.requires_vivado is False

    def test_tool_info_to_dict(self):
        """测试转换为字典"""
        info = ToolInfo(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
            requires_vivado=True,
        )
        result = info.to_dict()
        assert result["name"] == "test_tool"
        assert result["category"] == "file"
        assert result["risk_level"] == "DANGEROUS"
        assert result["requires_vivado"] is True


class TestToolRegistry:
    """测试工具注册表"""

    def setup_method(self):
        """每个测试方法前重置注册表"""
        self.registry = ToolRegistry()

    def test_register_tool(self):
        """测试注册工具"""
        async def dummy_handler():
            pass

        self.registry.register(
            name="test_tool",
            handler=dummy_handler,
            category=ToolCategory.PROJECT,
            description="测试工具",
        )

        assert self.registry.exists("test_tool")
        tool = self.registry.get("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.category == ToolCategory.PROJECT

    def test_register_with_docstring(self):
        """测试使用 docstring 作为描述"""

        async def handler_with_doc():
            """这是文档字符串"""
            pass

        self.registry.register(
            name="doc_tool",
            handler=handler_with_doc,
            category=ToolCategory.FILE,
        )

        tool = self.registry.get("doc_tool")
        assert tool.description == "这是文档字符串"

    def test_unregister_tool(self):
        """测试注销工具"""
        self.registry.register(
            name="to_remove",
            handler=lambda: None,
            category=ToolCategory.TCL,
        )

        assert self.registry.exists("to_remove")
        result = self.registry.unregister("to_remove")
        assert result is True
        assert not self.registry.exists("to_remove")

    def test_unregister_nonexistent(self):
        """测试注销不存在的工具"""
        result = self.registry.unregister("nonexistent")
        assert result is False

    def test_enable_disable_tool(self):
        """测试启用/禁用工具"""
        self.registry.register(
            name="toggle_tool",
            handler=lambda: None,
            category=ToolCategory.BUILD,
        )

        # 禁用
        result = self.registry.disable("toggle_tool")
        assert result is True
        assert not self.registry.is_enabled("toggle_tool")

        # 启用
        result = self.registry.enable("toggle_tool")
        assert result is True
        assert self.registry.is_enabled("toggle_tool")

    def test_list_tools(self):
        """测试列出工具"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.PROJECT,
        )
        self.registry.register(
            name="tool2",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool3",
            handler=lambda: None,
            category=ToolCategory.PROJECT,
        )

        # 列出所有
        all_tools = self.registry.list_all()
        assert len(all_tools) == 3

        # 按类别筛选
        project_tools = self.registry.list_all(category=ToolCategory.PROJECT)
        assert len(project_tools) == 2

        file_tools = self.registry.list_all(category=ToolCategory.FILE)
        assert len(file_tools) == 1

    def test_list_enabled_disabled(self):
        """测试列出已启用/禁用的工具"""
        self.registry.register(
            name="enabled_tool",
            handler=lambda: None,
            category=ToolCategory.PROJECT,
        )
        self.registry.register(
            name="disabled_tool",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        self.registry.disable("disabled_tool")

        enabled = self.registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "enabled_tool"

        disabled = self.registry.list_disabled()
        assert len(disabled) == 1
        assert disabled[0].name == "disabled_tool"

    def test_list_by_risk_level(self):
        """测试按风险级别列出工具"""
        self.registry.register(
            name="safe_tool",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.SAFE,
        )
        self.registry.register(
            name="dangerous_tool",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
        )

        safe_tools = self.registry.list_by_risk_level(RiskLevel.SAFE)
        assert len(safe_tools) == 1

        dangerous_tools = self.registry.list_by_risk_level(RiskLevel.DANGEROUS)
        assert len(dangerous_tools) == 1

    def test_disable_by_risk_level(self):
        """测试按风险级别禁用工具"""
        self.registry.register(
            name="safe1",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.SAFE,
        )
        self.registry.register(
            name="dangerous1",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
        )
        self.registry.register(
            name="dangerous2",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
        )

        count = self.registry.disable_by_risk_level(RiskLevel.DANGEROUS)
        assert count == 2

        # 检查危险工具已禁用
        assert not self.registry.is_enabled("dangerous1")
        assert not self.registry.is_enabled("dangerous2")

        # 安全工具仍然启用
        assert self.registry.is_enabled("safe1")

    def test_apply_config_disable_dangerous(self):
        """测试应用配置：禁用危险工具"""
        self.registry.register(
            name="dangerous",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
        )
        self.registry.register(
            name="normal",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.NORMAL,
        )

        stats = self.registry.apply_config(disable_dangerous_tools=True)

        assert stats["dangerous_disabled"] == 1
        assert not self.registry.is_enabled("dangerous")
        assert self.registry.is_enabled("normal")

    def test_apply_config_disabled_list(self):
        """测试应用配置：禁用列表"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool2",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        stats = self.registry.apply_config(disabled_tools=["tool1"])

        assert not self.registry.is_enabled("tool1")
        assert self.registry.is_enabled("tool2")

    def test_apply_config_enabled_list(self):
        """测试应用配置：启用列表"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool2",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool3",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        stats = self.registry.apply_config(enabled_tools=["tool1", "tool2"])

        # 只有 tool1 和 tool2 启用
        assert self.registry.is_enabled("tool1")
        assert self.registry.is_enabled("tool2")
        assert not self.registry.is_enabled("tool3")

    def test_enable_all(self):
        """测试启用所有工具"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool2",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        self.registry.disable("tool1")
        self.registry.disable("tool2")

        self.registry.enable_all()

        assert self.registry.is_enabled("tool1")
        assert self.registry.is_enabled("tool2")

    def test_disable_all(self):
        """测试禁用所有工具"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )
        self.registry.register(
            name="tool2",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        self.registry.disable_all()

        assert not self.registry.is_enabled("tool1")
        assert not self.registry.is_enabled("tool2")

    def test_to_dict(self):
        """测试转换为字典"""
        self.registry.register(
            name="tool1",
            handler=lambda: None,
            category=ToolCategory.FILE,
        )

        result = self.registry.to_dict()
        assert "total_tools" in result
        assert "enabled_tools" in result
        assert "disabled_tools" in result
        assert "tools" in result


class TestGlobalRegistry:
    """测试全局注册表"""

    def setup_method(self):
        """每个测试方法前重置全局注册表"""
        reset_registry()

    def test_get_registry(self):
        """测试获取全局注册表"""
        registry1 = get_registry()
        registry2 = get_registry()

        # 应该是同一个实例
        assert registry1 is registry2

    def test_reset_registry(self):
        """测试重置全局注册表"""
        registry1 = get_registry()
        reset_registry()
        registry2 = get_registry()

        # 应该是不同的实例
        assert registry1 is not registry2


class TestToolDecorator:
    """测试工具装饰器"""

    def test_tool_decorator(self):
        """测试 @tool 装饰器"""
        @tool(
            name="decorated_tool",
            category=ToolCategory.PROJECT,
            description="装饰器工具",
            risk_level=RiskLevel.SAFE,
        )
        async def my_handler():
            pass

        assert hasattr(my_handler, "_tool_info")
        info = my_handler._tool_info
        assert info.name == "decorated_tool"
        assert info.category == ToolCategory.PROJECT
        assert info.description == "装饰器工具"
        assert info.risk_level == RiskLevel.SAFE

    def test_tool_decorator_with_docstring(self):
        """测试装饰器使用 docstring"""
        @tool("doc_tool", ToolCategory.FILE)
        async def handler():
            """这是文档描述"""
            pass

        info = handler._tool_info
        assert info.description == "这是文档描述"


class TestRegisterDecoratedTools:
    """测试注册装饰器标记的工具"""

    def test_register_decorated(self):
        """测试注册装饰器标记的工具"""
        import types

        # 创建一个模拟模块
        module = types.ModuleType("test_module")

        @tool("mod_tool1", ToolCategory.PROJECT)
        async def tool1():
            """工具1"""
            pass

        @tool("mod_tool2", ToolCategory.FILE)
        async def tool2():
            """工具2"""
            pass

        # 添加到模块
        module.tool1 = tool1
        module.tool2 = tool2

        registry = ToolRegistry()
        count = register_decorated_tools(registry, module)

        assert count == 2
        assert registry.exists("mod_tool1")
        assert registry.exists("mod_tool2")


class TestToolRegistryIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        registry = ToolRegistry()

        # 注册多个工具
        registry.register(
            name="create_project",
            handler=lambda: None,
            category=ToolCategory.PROJECT,
            risk_level=RiskLevel.NORMAL,
            requires_vivado=True,
        )
        registry.register(
            name="delete_file",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.DANGEROUS,
        )
        registry.register(
            name="read_file",
            handler=lambda: None,
            category=ToolCategory.FILE,
            risk_level=RiskLevel.SAFE,
        )

        # 应用配置
        stats = registry.apply_config(
            disabled_tools=["create_project"],
            disable_dangerous_tools=True,
        )

        # 验证结果
        assert not registry.is_enabled("create_project")  # 被禁用
        assert not registry.is_enabled("delete_file")  # 危险工具被禁用
        assert registry.is_enabled("read_file")  # 安全工具仍然启用

        # 验证统计
        assert stats["total_tools"] == 3
        assert stats["dangerous_disabled"] == 1
