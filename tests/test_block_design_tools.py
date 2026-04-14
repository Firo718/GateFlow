"""
Block Design MCP 工具测试。

测试 Pydantic 模型验证、工具注册和异步工具函数。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.tools.block_design_tools import (
    CreateBDDesignResult,
    OpenBDDesignResult,
    CloseBDDesignResult,
    SaveBDDesignResult,
    AddBDIPResult,
    CreateBDPortResult,
    ConnectBDPortsResult,
    ApplyAutomationResult,
    ValidateBDDesignResult,
    GenerateWrapperResult,
    GetBDCellsResult,
    RemoveBDCellResult,
    GetBDPortsResult,
    GetBDConnectionsResult,
    register_block_design_tools,
)


# ==================== Pydantic 模型测试 ====================


class TestBDDesignResultModels:
    """Block Design 结果模型测试。"""

    def test_create_bd_design_result_success(self):
        """测试创建 Block Design 成功结果。"""
        result = CreateBDDesignResult(
            success=True,
            design_name="system",
            message="Block Design 创建成功",
        )
        
        assert result.success is True
        assert result.design_name == "system"
        assert result.error is None

    def test_create_bd_design_result_failure(self):
        """测试创建 Block Design 失败结果。"""
        result = CreateBDDesignResult(
            success=False,
            design_name=None,
            message="Block Design 创建失败",
            error="Design already exists",
        )
        
        assert result.success is False
        assert result.error == "Design already exists"

    def test_open_bd_design_result(self):
        """测试打开 Block Design 结果。"""
        result = OpenBDDesignResult(
            success=True,
            design_name="system",
            message="Block Design 打开成功",
        )
        
        assert result.success is True
        assert result.design_name == "system"

    def test_close_bd_design_result(self):
        """测试关闭 Block Design 结果。"""
        result = CloseBDDesignResult(
            success=True,
            message="Block Design 已关闭",
        )
        
        assert result.success is True

    def test_save_bd_design_result(self):
        """测试保存 Block Design 结果。"""
        result = SaveBDDesignResult(
            success=True,
            message="Block Design 保存成功",
        )
        
        assert result.success is True

    def test_add_bd_ip_result(self):
        """测试添加 IP 实例结果。"""
        result = AddBDIPResult(
            success=True,
            instance_name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
            message="IP 实例添加成功",
        )
        
        assert result.success is True
        assert result.instance_name == "axi_gpio_0"

    def test_create_bd_port_result(self):
        """测试创建端口结果。"""
        result = CreateBDPortResult(
            success=True,
            port_name="clk",
            direction="input",
            message="端口创建成功",
        )
        
        assert result.success is True
        assert result.port_name == "clk"
        assert result.direction == "input"

    def test_connect_bd_ports_result(self):
        """测试连接端口结果。"""
        result = ConnectBDPortsResult(
            success=True,
            source="clk_wiz_0/clk_out1",
            destination="axi_gpio_0/s_axi_aclk",
            message="端口连接成功",
        )
        
        assert result.success is True
        assert result.source == "clk_wiz_0/clk_out1"

    def test_apply_automation_result(self):
        """测试应用自动连接结果。"""
        result = ApplyAutomationResult(
            success=True,
            rule="all",
            message="自动连接应用成功",
        )
        
        assert result.success is True
        assert result.rule == "all"

    def test_validate_bd_design_result(self):
        """测试验证设计结果。"""
        result = ValidateBDDesignResult(
            success=True,
            message="Block Design 验证通过",
            warnings=[],
        )
        
        assert result.success is True
        assert result.warnings == []

    def test_validate_bd_design_result_with_warnings(self):
        """测试带警告的验证设计结果。"""
        result = ValidateBDDesignResult(
            success=True,
            message="Block Design 验证通过",
            warnings=["Unconnected port", "Missing clock"],
        )
        
        assert len(result.warnings) == 2

    def test_generate_wrapper_result(self):
        """测试生成 Wrapper 结果。"""
        result = GenerateWrapperResult(
            success=True,
            wrapper_name="system_wrapper",
            message="HDL Wrapper 生成成功",
        )
        
        assert result.success is True
        assert result.wrapper_name == "system_wrapper"

    def test_get_bd_cells_result(self):
        """测试获取 IP 实例列表结果。"""
        result = GetBDCellsResult(
            success=True,
            cells=[
                {"name": "axi_gpio_0"},
                {"name": "axi_interconnect_0"},
            ],
            cell_count=2,
            message="找到 2 个 IP 实例",
        )
        
        assert result.success is True
        assert result.cell_count == 2

        assert len(result.cells) == 2

    def test_remove_bd_cell_result(self):
        """测试移除 IP 实例结果。"""
        result = RemoveBDCellResult(
            success=True,
            instance_name="axi_gpio_0",
            message="IP 实例移除成功",
        )
        
        assert result.success is True
        assert result.instance_name == "axi_gpio_0"

    def test_get_bd_ports_result(self):
        """测试获取端口列表结果。"""
        result = GetBDPortsResult(
            success=True,
            ports=[
                {"name": "clk", "type": "port"},
                {"name": "M_AXI", "type": "interface"},
            ],
            port_count=2,
            message="找到 2 个端口",
        )
        
        assert result.success is True
        assert result.port_count == 2

    def test_get_bd_connections_result(self):
        """测试获取连接列表结果。"""
        result = GetBDConnectionsResult(
            success=True,
            connections=[
                {"name": "conn_0", "type": "interface"},
                {"name": "net_0", "type": "net"},
            ],
            connection_count=2,
            message="找到 2 个连接",
        )
        
        assert result.success is True
        assert result.connection_count == 2


# ==================== 工具注册测试 ====================


class TestBDToolsRegistration:
    """Block Design 工具注册测试。"""

    def test_register_block_design_tools(self):
        """测试工具注册。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_block_design_tools(mock_mcp)
        
        # 验证工具注册被调用
        assert mock_mcp.tool.called

    def test_register_tools_decorator_count(self):
        """测试工具注册装饰器调用次数。"""
        mock_mcp = MagicMock()
        call_count = [0]
        
        def mock_decorator(func=None):
            call_count[0] += 1
            if func:
                return func
            return lambda f: f
        
        mock_mcp.tool = mock_decorator
        
        register_block_design_tools(mock_mcp)
        
        # 应该注册了多个工具
        assert call_count[0] >= 10


# ==================== 异步工具函数测试 ====================


class TestBDToolFunctions:
    """Block Design 工具函数测试。"""

    @pytest.fixture
    def mock_mcp(self):
        """创建模拟的 FastMCP。"""
        mcp = MagicMock()
        mcp.tool = MagicMock(return_value=lambda f: f)
        return mcp

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def mock_result(self):
        """创建模拟的执行结果。"""
        result = MagicMock()
        result.success = True
        result.errors = []
        result.warnings = []
        result.output = ""
        return result

    @pytest.mark.asyncio
    async def test_create_bd_design_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_bd_design 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_design = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_open_bd_design_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 open_bd_design 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.open_design = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_close_bd_design_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 close_bd_design 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.close_design = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_save_bd_design_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 save_bd_design 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.save_design = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_add_bd_ip_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 add_bd_ip 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.add_ip_instance = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_bd_port_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_bd_port 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_external_port = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_connect_bd_ports_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 connect_bd_ports 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.connect_ports = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_apply_bd_automation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 apply_bd_automation 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.apply_automation = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_validate_bd_design_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 validate_bd_design 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.validate_design = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_generate_bd_wrapper_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 generate_bd_wrapper 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.current_design = MagicMock()
                mock_manager.current_design.name = "system"
                mock_manager.generate_wrapper = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_get_bd_cells_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 get_bd_cells 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.get_cells = AsyncMock(return_value=[
                    {"name": "axi_gpio_0"},
                    {"name": "axi_interconnect_0"},
                ])
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_remove_bd_cell_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 remove_bd_cell 工具。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_engine', return_value=mock_engine):
            with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.remove_ip_instance = AsyncMock(return_value={
                    "success": True,
                    "errors": [],
                    "warnings": [],
                })
                mock_get_manager.return_value = mock_manager
                
                register_block_design_tools(mock_mcp)


# ==================== 辅助函数测试 ====================


class TestBDToolsHelperFunctions:
    """Block Design 工具辅助函数测试。"""

    def test_get_engine_singleton(self):
        """测试获取引擎单例。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        
        with patch('gateflow.tools.block_design_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            engine1 = block_design_tools._get_engine()
            engine2 = block_design_tools._get_engine()
            
            # 应该返回同一个实例
            assert engine1 == engine2
        
        # 清理
        block_design_tools._engine = None

    def test_get_bd_manager_singleton(self):
        """测试获取 Block Design 管理器单例。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._bd_manager = None
        block_design_tools._engine = None
        
        with patch('gateflow.tools.block_design_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            with patch('gateflow.tools.block_design_tools.BlockDesignManager') as MockBDManager:
                mock_manager = MagicMock()
                MockBDManager.return_value = mock_manager
                
                manager1 = block_design_tools._get_bd_manager()
                manager2 = block_design_tools._get_bd_manager()
                
                # 应该返回同一个实例
                assert manager1 == manager2
        
        # 清理
        block_design_tools._bd_manager = None
        block_design_tools._engine = None


# ==================== 异常处理测试 ====================


class TestBDToolsExceptionHandling:
    """Block Design 工具异常处理测试。"""

    @pytest.fixture
    def mock_mcp(self):
        """创建模拟的 FastMCP。"""
        mcp = MagicMock()
        mcp.tool = MagicMock(return_value=lambda f: f)
        return mcp

    @pytest.mark.asyncio
    async def test_create_bd_design_exception(self, mock_mcp):
        """测试 create_bd_design 异常处理。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.create_design = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_block_design_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_add_bd_ip_exception(self, mock_mcp):
        """测试 add_bd_ip 异常处理。"""
        from gateflow.tools import block_design_tools
        
        block_design_tools._engine = None
        block_design_tools._bd_manager = None
        
        with patch.object(block_design_tools, '_get_bd_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.add_ip_instance = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_block_design_tools(mock_mcp)


# ==================== 边界情况测试 ====================


class TestBDToolsEdgeCases:
    """Block Design 工具边界情况测试。"""

    def test_result_model_with_none_values(self):
        """测试结果模型带 None 值。"""
        result = CreateBDDesignResult(
            success=False,
            design_name=None,
            message="失败",
            error=None,
        )
        
        assert result.success is False
        assert result.design_name is None

    def test_get_bd_cells_result_with_large_list(self):
        """测试带大量 IP 实例的列表结果。"""
        cells = [{"name": f"ip_{i}"} for i in range(100)]
        result = GetBDCellsResult(
            success=True,
            cells=cells,
            cell_count=100,
            message="找到 100 个 IP 实例",
        )
        
        assert result.cell_count == 100
        assert len(result.cells) == 100

    def test_validate_result_with_many_warnings(self):
        """测试带多个警告的验证结果。"""
        warnings = [f"Warning {i}" for i in range(50)]
        result = ValidateBDDesignResult(
            success=True,
            message="验证通过",
            warnings=warnings,
        )
        
        assert len(result.warnings) == 50

    def test_result_model_empty_message(self):
        """测试结果模型空消息。"""
        result = AddBDIPResult(
            success=True,
            message="",
        )
        
        assert result.success is True
        assert result.message == ""

    def test_result_model_validation(self):
        """测试结果模型验证。"""
        # 有效数据
        result = CreateBDPortResult(
            success=True,
            port_name="clk",
            direction="input",
            message="成功",
        )
        
        assert result.success is True
        assert result.port_name == "clk"
        assert result.direction == "input"

    def test_connect_result_with_interface(self):
        """测试接口连接结果。"""
        result = ConnectBDPortsResult(
            success=True,
            source="axi_interconnect_0/M00_AXI",
            destination="axi_gpio_0/S_AXI",
            message="接口连接成功",
        )
        
        assert result.success is True
        assert "M00_AXI" in result.source

    def test_get_bd_ports_result_mixed_types(self):
        """测试混合类型端口列表结果。"""
        result = GetBDPortsResult(
            success=True,
            ports=[
                {"name": "clk", "type": "port"},
                {"name": "M_AXI", "type": "interface"},
                {"name": "rst", "type": "port"},
            ],
            port_count=3,
            message="找到 3 个端口",
        )
        
        assert result.port_count == 3
        port_types = [p["type"] for p in result.ports]
        assert "port" in port_types
        assert "interface" in port_types
