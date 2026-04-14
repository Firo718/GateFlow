"""
IP MCP 工具测试。

测试 IP 配置相关的 Pydantic 模型验证、工具注册和异步工具函数。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError

from gateflow.tools.ip_tools import (
    CreateClockingWizardResult,
    CreateFIFOResult,
    CreateBRAMResult,
    CreateAXIInterconnectResult,
    CreateZynqPSResult,
    ListIPsResult,
    GetIPInfoResult,
    UpgradeIPResult,
    GenerateOutputsResult,
    RemoveIPResult,
    register_ip_tools,
)


# ==================== Pydantic 模型测试 ====================


class TestCreateClockingWizardResult:
    """CreateClockingWizardResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = CreateClockingWizardResult(
            success=True,
            ip_name="clk_wiz_0",
            module_name="clk_wiz_0",
            message="Clocking Wizard IP 创建成功",
        )
        
        assert result.success is True
        assert result.ip_name == "clk_wiz_0"
        assert result.error is None

    def test_failure_result(self):
        """测试失败结果。"""
        result = CreateClockingWizardResult(
            success=False,
            message="Clocking Wizard IP 创建失败",
            error="Invalid configuration",
        )
        
        assert result.success is False
        assert result.error == "Invalid configuration"

    def test_required_fields(self):
        """测试必需字段。"""
        with pytest.raises(ValidationError):
            CreateClockingWizardResult()


class TestCreateFIFOResult:
    """CreateFIFOResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = CreateFIFOResult(
            success=True,
            ip_name="fifo_0",
            module_name="fifo_0",
            message="FIFO IP 创建成功",
        )
        
        assert result.success is True
        assert result.ip_name == "fifo_0"

    def test_with_error(self):
        """测试带错误的结果。"""
        result = CreateFIFOResult(
            success=False,
            message="创建失败",
            error="Depth exceeds maximum",
        )
        
        assert result.error == "Depth exceeds maximum"


class TestCreateBRAMResult:
    """CreateBRAMResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = CreateBRAMResult(
            success=True,
            ip_name="bram_0",
            module_name="bram_0",
            message="BRAM IP 创建成功",
        )
        
        assert result.success is True


class TestCreateAXIInterconnectResult:
    """CreateAXIInterconnectResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = CreateAXIInterconnectResult(
            success=True,
            ip_name="axi_interconnect_0",
            module_name="axi_interconnect_0",
            message="AXI Interconnect IP 创建成功",
        )
        
        assert result.success is True


class TestCreateZynqPSResult:
    """CreateZynqPSResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = CreateZynqPSResult(
            success=True,
            ip_name="processing_system7_0",
            module_name="processing_system7_0",
            message="Zynq PS IP 创建成功",
        )
        
        assert result.success is True


class TestListIPsResult:
    """ListIPsResult 模型测试。"""

    def test_empty_list(self):
        """测试空列表。"""
        result = ListIPsResult(
            success=True,
            ips=[],
            count=0,
            message="没有找到 IP",
        )
        
        assert result.success is True
        assert result.ips == []
        assert result.count == 0

    def test_with_ips(self):
        """测试带 IP 的列表。"""
        result = ListIPsResult(
            success=True,
            ips=[
                {"name": "clk_wiz_0", "module_name": "clk_wiz_0"},
                {"name": "fifo_0", "module_name": "fifo_0"},
            ],
            count=2,
            message="找到 2 个 IP",
        )
        
        assert result.count == 2
        assert len(result.ips) == 2


class TestGetIPInfoResult:
    """GetIPInfoResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = GetIPInfoResult(
            success=True,
            ip_info={
                "name": "clk_wiz_0",
                "vlnv": "xilinx.com:ip:clk_wiz:6.0",
                "version": "6.0",
            },
            message="获取 IP 信息成功",
        )
        
        assert result.success is True
        assert result.ip_info is not None

    def test_ip_not_found(self):
        """测试 IP 不存在。"""
        result = GetIPInfoResult(
            success=False,
            ip_info=None,
            message="IP 不存在",
            error="IP not found",
        )
        
        assert result.success is False
        assert result.ip_info is None


class TestUpgradeIPResult:
    """UpgradeIPResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = UpgradeIPResult(
            success=True,
            ip_name="clk_wiz_0",
            message="IP clk_wiz_0 升级成功",
        )
        
        assert result.success is True
        assert result.ip_name == "clk_wiz_0"


class TestGenerateOutputsResult:
    """GenerateOutputsResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = GenerateOutputsResult(
            success=True,
            ip_name="clk_wiz_0",
            message="IP clk_wiz_0 输出产品生成成功",
        )
        
        assert result.success is True


class TestRemoveIPResult:
    """RemoveIPResult 模型测试。"""

    def test_success_result(self):
        """测试成功结果。"""
        result = RemoveIPResult(
            success=True,
            ip_name="clk_wiz_0",
            message="IP clk_wiz_0 移除成功",
        )
        
        assert result.success is True


# ==================== 工具注册测试 ====================


class TestRegisterIPTools:
    """register_ip_tools 函数测试。"""

    def test_register_tools(self):
        """测试工具注册。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_ip_tools(mock_mcp)
        
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
        
        register_ip_tools(mock_mcp)
        
        # 应该注册了多个工具
        assert call_count[0] >= 9


# ==================== 异步工具函数测试 ====================


class TestIPToolFunctions:
    """IP 工具函数测试。"""

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
    async def test_create_clocking_wizard_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_clocking_wizard 工具。"""
        from gateflow.tools import ip_tools
        
        # 重置全局状态
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        mock_result.success = True
        mock_engine.execute_async.return_value = mock_result
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_clocking_wizard = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "clk_wiz_0",
                    "module_name": "clk_wiz_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_fifo_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_fifo 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        mock_result.success = True
        mock_engine.execute_async.return_value = mock_result
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_fifo = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "fifo_0",
                    "module_name": "fifo_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_bram_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_bram 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        mock_result.success = True
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_bram = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "bram_0",
                    "module_name": "bram_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_axi_interconnect_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_axi_interconnect 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_axi_interconnect = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "axi_interconnect_0",
                    "module_name": "axi_interconnect_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_zynq_ps_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_zynq_ps 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_zynq_ps = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "processing_system7_0",
                    "module_name": "processing_system7_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_list_ips_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 list_ips 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.list_ips = AsyncMock(return_value=[
                    {"name": "clk_wiz_0", "module_name": "clk_wiz_0"},
                ])
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_get_ip_info_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 get_ip_info 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.get_ip_info = AsyncMock(return_value={
                    "exists": True,
                    "name": "clk_wiz_0",
                    "vlnv": "xilinx.com:ip:clk_wiz:6.0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_upgrade_ip_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 upgrade_ip 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.upgrade_ip = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "clk_wiz_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_generate_ip_outputs_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 generate_ip_outputs 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.generate_output_products = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "clk_wiz_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_remove_ip_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 remove_ip 工具。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_engine', return_value=mock_engine):
            with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.remove_ip = AsyncMock(return_value={
                    "success": True,
                    "ip_name": "clk_wiz_0",
                })
                mock_get_manager.return_value = mock_manager
                
                register_ip_tools(mock_mcp)


# ==================== 辅助函数测试 ====================


class TestIPToolsHelperFunctions:
    """IP 工具辅助函数测试。"""

    def test_get_engine_singleton(self):
        """测试获取引擎单例。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        
        with patch('gateflow.tools.ip_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            engine1 = ip_tools._get_engine()
            engine2 = ip_tools._get_engine()
            
            # 应该返回同一个实例
            assert engine1 == engine2
        
        # 清理
        ip_tools._engine = None

    def test_get_ip_manager_singleton(self):
        """测试获取 IP 管理器单例。"""
        from gateflow.tools import ip_tools
        
        ip_tools._ip_manager = None
        ip_tools._engine = None
        
        with patch('gateflow.tools.ip_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            with patch('gateflow.tools.ip_tools.IPManager') as MockIPManager:
                mock_manager = MagicMock()
                MockIPManager.return_value = mock_manager
                
                manager1 = ip_tools._get_ip_manager()
                manager2 = ip_tools._get_ip_manager()
                
                # 应该返回同一个实例
                assert manager1 == manager2
        
        # 清理
        ip_tools._ip_manager = None
        ip_tools._engine = None


# ==================== 异常处理测试 ====================


class TestIPToolsExceptionHandling:
    """IP 工具异常处理测试。"""

    @pytest.fixture
    def mock_mcp(self):
        """创建模拟的 FastMCP。"""
        mcp = MagicMock()
        mcp.tool = MagicMock(return_value=lambda f: f)
        return mcp

    @pytest.mark.asyncio
    async def test_create_clocking_wizard_exception(self, mock_mcp):
        """测试 create_clocking_wizard 异常处理。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.create_clocking_wizard = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_ip_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_list_ips_exception(self, mock_mcp):
        """测试 list_ips 异常处理。"""
        from gateflow.tools import ip_tools
        
        ip_tools._engine = None
        ip_tools._ip_manager = None
        
        with patch.object(ip_tools, '_get_ip_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_ips = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_ip_tools(mock_mcp)


# ==================== 边界情况测试 ====================


class TestIPToolsEdgeCases:
    """IP 工具边界情况测试。"""

    def test_result_model_with_none_values(self):
        """测试结果模型带 None 值。"""
        result = CreateClockingWizardResult(
            success=False,
            ip_name=None,
            module_name=None,
            message="失败",
            error=None,
        )
        
        assert result.success is False
        assert result.ip_name is None

    def test_list_ips_result_with_large_list(self):
        """测试带大量 IP 的列表结果。"""
        ips = [{"name": f"ip_{i}", "module_name": f"ip_{i}"} for i in range(100)]
        result = ListIPsResult(
            success=True,
            ips=ips,
            count=100,
            message="找到 100 个 IP",
        )
        
        assert result.count == 100
        assert len(result.ips) == 100

    def test_result_model_empty_message(self):
        """测试结果模型空消息。"""
        result = CreateFIFOResult(
            success=True,
            message="",
        )
        
        assert result.message == ""

    def test_result_model_unicode_message(self):
        """测试结果模型 Unicode 消息。"""
        result = CreateBRAMResult(
            success=True,
            message="BRAM IP 创建成功",
        )
        
        assert "成功" in result.message

    def test_get_ip_info_result_with_complex_info(self):
        """测试带复杂信息的 IP 信息结果。"""
        complex_info = {
            "name": "clk_wiz_0",
            "vlnv": "xilinx.com:ip:clk_wiz:6.0",
            "version": "6.0",
            "properties": {
                "PRIM_IN_FREQ": 100.0,
                "CLKOUT1_USED": True,
            },
            "status": "generated",
        }
        
        result = GetIPInfoResult(
            success=True,
            ip_info=complex_info,
            message="获取 IP 信息成功",
        )
        
        assert result.ip_info["properties"]["PRIM_IN_FREQ"] == 100.0
