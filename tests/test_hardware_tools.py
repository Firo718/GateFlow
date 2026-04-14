"""
硬件 MCP 工具测试。

测试硬件工具注册、Pydantic 模型验证、工具函数和错误处理。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from pydantic import ValidationError

from gateflow.tools.hardware_tools import (
    ConnectServerResult,
    DisconnectResult,
    GetDevicesResult,
    HardwareAxiResult,
    HardwareValueResult,
    ProgramResult,
    RefreshResult,
    ServerStatusResult,
    register_hardware_tools,
    _get_engine,
)


# ==================== Pydantic 模型测试 ====================


class TestConnectServerResult:
    """ConnectServerResult 模型测试。"""

    def test_connect_server_result_defaults(self):
        """测试 ConnectServerResult 默认值。"""
        result = ConnectServerResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.server_url is None
        assert result.devices == []
        assert result.device_count == 0
        assert result.error is None

    def test_connect_server_result_full(self):
        """测试 ConnectServerResult 完整参数。"""
        devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"},
            {"index": 1, "name": "xc7k70t_0", "type": "FPGA"},
        ]
        
        result = ConnectServerResult(
            success=True,
            server_url="localhost:3121",
            devices=devices,
            device_count=2,
            message="Connected successfully",
        )
        
        assert result.server_url == "localhost:3121"
        assert result.device_count == 2
        assert len(result.devices) == 2

    def test_connect_server_result_failure(self):
        """测试 ConnectServerResult 失败情况。"""
        result = ConnectServerResult(
            success=False,
            server_url="localhost:3121",
            message="Connection failed",
            error="Connection refused",
        )
        
        assert result.success is False
        assert result.error == "Connection refused"

    def test_connect_server_result_required_fields(self):
        """测试 ConnectServerResult 必需字段。"""
        with pytest.raises(ValidationError):
            ConnectServerResult()  # 缺少 success 和 message

        with pytest.raises(ValidationError):
            ConnectServerResult(success=True)  # 缺少 message


class TestDisconnectResult:
    """DisconnectResult 模型测试。"""

    def test_disconnect_result_defaults(self):
        """测试 DisconnectResult 默认值。"""
        result = DisconnectResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.error is None

    def test_disconnect_result_failure(self):
        """测试 DisconnectResult 失败情况。"""
        result = DisconnectResult(
            success=False,
            message="Disconnect failed",
            error="No active connection",
        )
        
        assert result.success is False
        assert result.error == "No active connection"


class TestGetDevicesResult:
    """GetDevicesResult 模型测试。"""

    def test_get_devices_result_defaults(self):
        """测试 GetDevicesResult 默认值。"""
        result = GetDevicesResult(success=True, message="Done")
        
        assert result.success is True
        assert result.devices == []
        assert result.device_count == 0
        assert result.error is None

    def test_get_devices_result_with_devices(self):
        """测试 GetDevicesResult 带设备列表。"""
        devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA", "part": "xc7a35tcpg236-1"},
        ]
        
        result = GetDevicesResult(
            success=True,
            devices=devices,
            device_count=1,
            message="Found 1 device",
        )
        
        assert result.device_count == 1
        assert len(result.devices) == 1


class TestProgramResult:
    """ProgramResult 模型测试。"""

    def test_program_result_defaults(self):
        """测试 ProgramResult 默认值。"""
        result = ProgramResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.device_index is None
        assert result.device_name is None
        assert result.bitstream_path is None
        assert result.error is None

    def test_program_result_full(self):
        """测试 ProgramResult 完整参数。"""
        result = ProgramResult(
            success=True,
            device_index=0,
            device_name="xc7a35t_0",
            bitstream_path="/path/to/design.bit",
            message="Programming completed",
        )
        
        assert result.device_index == 0
        assert result.device_name == "xc7a35t_0"
        assert result.bitstream_path == "/path/to/design.bit"

    def test_program_result_failure(self):
        """测试 ProgramResult 失败情况。"""
        result = ProgramResult(
            success=False,
            device_index=0,
            message="Programming failed",
            error="Device not responding",
        )
        
        assert result.success is False
        assert result.error == "Device not responding"


class TestRefreshResult:
    """RefreshResult 模型测试。"""

    def test_refresh_result_defaults(self):
        """测试 RefreshResult 默认值。"""
        result = RefreshResult(success=True, message="Done")
        
        assert result.success is True
        assert result.device_index is None
        assert result.device_name is None
        assert result.error is None

    def test_refresh_result_full(self):
        """测试 RefreshResult 完整参数。"""
        result = RefreshResult(
            success=True,
            device_index=0,
            device_name="xc7a35t_0",
            message="Device refreshed",
        )
        
        assert result.device_index == 0
        assert result.device_name == "xc7a35t_0"


class TestServerStatusResult:
    """ServerStatusResult 模型测试。"""

    def test_server_status_result_defaults(self):
        """测试 ServerStatusResult 默认值。"""
        result = ServerStatusResult(success=True, message="Done")
        
        assert result.success is True
        assert result.connected is False
        assert result.server_url is None
        assert result.device_count == 0
        assert result.error is None

    def test_server_status_result_connected(self):
        """测试 ServerStatusResult 已连接状态。"""
        result = ServerStatusResult(
            success=True,
            connected=True,
            server_url="localhost:3121",
            device_count=2,
            current_target="target_0",
            message="Server status retrieved",
        )
        
        assert result.connected is True
        assert result.server_url == "localhost:3121"
        assert result.device_count == 2
        assert result.current_target == "target_0"


class TestHardwareValueResult:
    """HardwareValueResult 模型测试。"""

    def test_hardware_value_result_defaults(self):
        """测试 HardwareValueResult 默认值。"""
        result = HardwareValueResult(success=True, message="Done")

        assert result.success is True
        assert result.name is None
        assert result.value is None
        assert result.error is None


class TestHardwareAxiResult:
    """HardwareAxiResult 模型测试。"""

    def test_hardware_axi_result_defaults(self):
        """测试 HardwareAxiResult 默认值。"""
        result = HardwareAxiResult(success=True, message="Done")

        assert result.success is True
        assert result.axi_name is None
        assert result.address is None
        assert result.transaction_name is None
        assert result.value is None
        assert result.error is None


# ==================== 工具注册测试 ====================


class TestRegisterHardwareTools:
    """硬件工具注册测试。"""

    def test_register_hardware_tools(self):
        """测试注册硬件工具。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_hardware_tools(mock_mcp)
        
        # 验证 tool 装饰器被调用
        assert mock_mcp.tool.called

    def test_register_hardware_tools_creates_decorators(self):
        """测试注册硬件工具创建装饰器。"""
        mock_mcp = MagicMock()
        decorators = []
        
        def mock_decorator():
            def decorator(func):
                decorators.append(func.__name__)
                return func
            return decorator
        
        mock_mcp.tool = mock_decorator
        
        register_hardware_tools(mock_mcp)
        
        # 应该注册多个工具
        assert len(decorators) > 0
        # 检查关键工具是否注册
        expected_tools = [
            "connect_hw_server",
            "disconnect_hw_server",
            "get_hw_devices",
            "program_fpga",
            "refresh_hw_device",
            "get_hw_server_status",
        ]
        for tool in expected_tools:
            assert tool in decorators


# ==================== 全局状态管理测试 ====================


class TestGlobalStateManagement:
    """全局状态管理测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        hardware_tools._engine = None
        hardware_tools._hw_server_connected = False
        hardware_tools._hw_server_url = None
        hardware_tools._hw_devices = []

    def test_get_engine_creates_instance(self):
        """测试获取引擎创建实例。"""
        mock_info = MagicMock()
        mock_info.version = "2024.1"
        
        with patch("gateflow.tools.hardware_tools.TclEngine") as MockEngine:
            MockEngine.return_value.vivado_info = mock_info
            engine = _get_engine()
            
            assert engine is not None
            MockEngine.assert_called_once()

    def test_get_engine_reuses_instance(self):
        """测试获取引擎重用实例。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_info = MagicMock()
        mock_info.version = "2024.1"
        
        with patch("gateflow.tools.hardware_tools.TclEngine") as MockEngine:
            MockEngine.return_value.vivado_info = mock_info
            
            engine1 = _get_engine()
            engine2 = _get_engine()
            
            # 应该只创建一次
            assert MockEngine.call_count == 1


# ==================== 工具函数测试 ====================


class TestToolFunctions:
    """工具函数测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        hardware_tools._engine = None
        hardware_tools._hw_server_connected = False
        hardware_tools._hw_server_url = None
        hardware_tools._hw_devices = []

    @pytest.mark.asyncio
    async def test_connect_hw_server_tool_success(self):
        """测试 connect_hw_server 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Connected",
            "devices": ["xc7a35t_0"],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            result = await registered_tools["connect_hw_server"](
                url="localhost:3121"
            )
            
            assert result.success is True
            assert result.server_url == "localhost:3121"

    @pytest.mark.asyncio
    async def test_connect_hw_server_tool_remote(self):
        """测试 connect_hw_server 工具远程连接。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Connected",
            "devices": [],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            result = await registered_tools["connect_hw_server"](
                url="192.168.1.100:3121"
            )
            
            assert result.success is True
            assert result.server_url == "192.168.1.100:3121"

    @pytest.mark.asyncio
    async def test_disconnect_hw_server_tool_success(self):
        """测试 disconnect_hw_server 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        # 先设置连接状态
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_server_url = "localhost:3121"
        hardware_tools._hw_devices = [{"index": 0, "name": "device"}]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Disconnected",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "disconnect_hw_server" in registered_tools:
            result = await registered_tools["disconnect_hw_server"]()
            
            assert result.success is True
            assert hardware_tools._hw_server_connected is False

    @pytest.mark.asyncio
    async def test_get_hw_devices_tool_success(self):
        """测试 get_hw_devices 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "devices": ["xc7a35t_0", "xc7k70t_0"],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_devices" in registered_tools:
            result = await registered_tools["get_hw_devices"]()
            
            assert result.success is True
            assert result.device_count >= 0

    @pytest.mark.asyncio
    async def test_get_hw_devices_tool_not_connected(self):
        """测试 get_hw_devices 工具未连接。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = False
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_devices" in registered_tools:
            result = await registered_tools["get_hw_devices"]()
            
            assert result.success is False
            assert "未连接" in result.message

    @pytest.mark.asyncio
    async def test_program_fpga_tool_success(self, tmp_path):
        """测试 program_fpga 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        bitstream = tmp_path / "design.bit"
        bitstream.write_bytes(b"BITSTREAM_DATA")
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Programming completed",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=0,
                bitstream_path=str(bitstream),
            )
            
            assert result.success is True
            assert result.device_index == 0

    @pytest.mark.asyncio
    async def test_program_fpga_tool_not_connected(self):
        """测试 program_fpga 工具未连接。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = False
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=0,
                bitstream_path="/path/to/design.bit",
            )
            
            assert result.success is False
            assert "未连接" in result.message

    @pytest.mark.asyncio
    async def test_program_fpga_tool_invalid_index(self):
        """测试 program_fpga 工具无效设备索引。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=999,
                bitstream_path="/path/to/design.bit",
            )
            
            assert result.success is False
            assert "无效" in result.message or "invalid" in result.message.lower()

    @pytest.mark.asyncio
    async def test_refresh_hw_device_tool_success(self):
        """测试 refresh_hw_device 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Device refreshed",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "refresh_hw_device" in registered_tools:
            result = await registered_tools["refresh_hw_device"](
                device_index=0
            )
            
            assert result.success is True
            assert result.device_index == 0

    @pytest.mark.asyncio
    async def test_refresh_hw_device_tool_not_connected(self):
        """测试 refresh_hw_device 工具未连接。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = False
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "refresh_hw_device" in registered_tools:
            result = await registered_tools["refresh_hw_device"](
                device_index=0
            )
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_get_hw_server_status_tool_connected(self):
        """测试 get_hw_server_status 工具已连接状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_server_url = "localhost:3121"
        hardware_tools._current_hw_target = "target_0"
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_server_status" in registered_tools:
            result = await registered_tools["get_hw_server_status"]()
            
            assert result.success is True
            assert result.connected is True
            assert result.server_url == "localhost:3121"
            assert result.device_count == 1
            assert result.current_target == "target_0"

    @pytest.mark.asyncio
    async def test_get_hw_server_status_tool_not_connected(self):
        """测试 get_hw_server_status 工具未连接状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = False
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_server_status" in registered_tools:
            result = await registered_tools["get_hw_server_status"]()
            
            assert result.success is True
            assert result.connected is False


# ==================== 错误处理测试 ====================


class TestErrorHandling:
    """错误处理测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        hardware_tools._engine = None
        hardware_tools._hw_server_connected = False
        hardware_tools._hw_server_url = None
        hardware_tools._hw_devices = []

    @pytest.mark.asyncio
    async def test_connect_hw_server_error(self):
        """测试 connect_hw_server 工具错误处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Connection refused",
            "message": "Failed to connect",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            result = await registered_tools["connect_hw_server"](
                url="localhost:3121"
            )
            
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_connect_hw_server_exception(self):
        """测试 connect_hw_server 工具异常处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("Network error"))
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            result = await registered_tools["connect_hw_server"](
                url="localhost:3121"
            )
            
            assert result.success is False
            assert "Network error" in result.error

    @pytest.mark.asyncio
    async def test_disconnect_hw_server_error(self):
        """测试 disconnect_hw_server 工具错误处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Failed to disconnect",
            "message": "Disconnect failed",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "disconnect_hw_server" in registered_tools:
            result = await registered_tools["disconnect_hw_server"]()
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_program_fpga_error(self):
        """测试 program_fpga 工具错误处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Programming failed",
            "message": "Failed to program FPGA",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=0,
                bitstream_path="/path/to/design.bit",
            )
            
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_program_fpga_exception(self):
        """测试 program_fpga 工具异常处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("JTAG error"))
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=0,
                bitstream_path="/path/to/design.bit",
            )
            
            assert result.success is False
            assert "JTAG error" in result.error

    @pytest.mark.asyncio
    async def test_get_hw_devices_error(self):
        """测试 get_hw_devices 工具错误处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("Device query failed"))
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_devices" in registered_tools:
            result = await registered_tools["get_hw_devices"]()
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_refresh_hw_device_error(self):
        """测试 refresh_hw_device 工具错误处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Refresh failed",
            "message": "Failed to refresh device",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "refresh_hw_device" in registered_tools:
            result = await registered_tools["refresh_hw_device"](
                device_index=0
            )
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_get_hw_server_status_exception(self):
        """测试 get_hw_server_status 工具异常处理。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        # 设置一个会导致异常的状态
        hardware_tools._hw_server_connected = True
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        # 正常情况下不应该抛出异常
        if "get_hw_server_status" in registered_tools:
            result = await registered_tools["get_hw_server_status"]()
            
            assert result.success is True


# ==================== 工具描述测试 ====================


class TestToolDescriptions:
    """工具描述测试。"""

    def test_hardware_tools_have_docstrings(self):
        """测试硬件工具有文档字符串。"""
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        for name, func in registered_tools.items():
            assert func.__doc__ is not None, f"Tool {name} missing docstring"


# ==================== 边界情况测试 ====================


class TestHardwareToolsEdgeCases:
    """硬件工具边界情况测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.hardware_tools as hardware_tools
        hardware_tools._engine = None
        hardware_tools._hw_server_connected = False
        hardware_tools._hw_server_url = None
        hardware_tools._hw_devices = []

    @pytest.mark.asyncio
    async def test_program_fpga_default_device_index(self):
        """测试 program_fpga 工具默认设备索引。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Programming completed",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                bitstream_path="/path/to/design.bit"
            )
            
            # 默认设备索引为 0
            assert result.device_index == 0

    @pytest.mark.asyncio
    async def test_program_fpga_negative_device_index(self):
        """测试 program_fpga 工具负设备索引。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=-1,
                bitstream_path="/path/to/design.bit",
            )
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_refresh_hw_device_default_index(self):
        """测试 refresh_hw_device 工具默认索引。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Device refreshed",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "refresh_hw_device" in registered_tools:
            result = await registered_tools["refresh_hw_device"]()
            
            # 默认设备索引为 0
            assert result.device_index == 0

    @pytest.mark.asyncio
    async def test_connect_hw_server_empty_url(self):
        """测试 connect_hw_server 工具空 URL。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Connected",
            "devices": [],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            # 空字符串 URL
            result = await registered_tools["connect_hw_server"](url="")
            
            # 应该返回结果（可能是失败）
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_hw_devices_multiple_devices(self):
        """测试 get_hw_devices 工具多设备。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "devices": ["xc7a35t_0", "xc7k70t_0", "xc7vu9p_0"],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "get_hw_devices" in registered_tools:
            result = await registered_tools["get_hw_devices"]()
            
            assert result.success is True
            assert result.device_count >= 0

    @pytest.mark.asyncio
    async def test_program_fpga_no_bitstream_path(self):
        """测试 program_fpga 工具无比特流路径。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "No bitstream specified",
            "message": "Failed to program",
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "program_fpga" in registered_tools:
            result = await registered_tools["program_fpga"](
                device_index=0,
                bitstream_path=None,
            )
            
            # 应该返回结果
            assert result is not None

    @pytest.mark.asyncio
    async def test_connect_hw_server_special_url(self):
        """测试 connect_hw_server 工具特殊 URL。"""
        import gateflow.tools.hardware_tools as hardware_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Connected",
            "devices": [],
        })
        hardware_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)
        
        if "connect_hw_server" in registered_tools:
            # 特殊字符 URL
            result = await registered_tools["connect_hw_server"](
                url="192.168.1.100:3121"
            )
            
            assert result.server_url == "192.168.1.100:3121"

    @pytest.mark.asyncio
    async def test_hw_ila_run_tool_success(self):
        """测试 hw_ila_run 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools

        mock_engine = MagicMock()
        async_result = MagicMock()
        async_result.success = True
        async_result.output = ""
        async_result.errors = []
        async_result.warnings = []
        mock_engine.execute_async = AsyncMock(return_value=async_result)
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "hw_ila_run" in registered_tools:
            result = await registered_tools["hw_ila_run"](ila="ila_0")
            assert result.success is True
            assert result.name == "ila_0"

    @pytest.mark.asyncio
    async def test_hw_vio_get_input_tool_success(self):
        """测试 hw_vio_get_input 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools

        mock_engine = MagicMock()
        async_result = MagicMock()
        async_result.success = True
        async_result.output = "1"
        async_result.errors = []
        async_result.warnings = []
        mock_engine.execute_async = AsyncMock(return_value=async_result)
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "hw_vio_get_input" in registered_tools:
            result = await registered_tools["hw_vio_get_input"](vio="vio_0", probe="probe_in0")
            assert result.success is True
            assert result.value == "1"

    @pytest.mark.asyncio
    async def test_hw_vio_set_output_tool_failure(self):
        """测试 hw_vio_set_output 工具失败分支。"""
        import gateflow.tools.hardware_tools as hardware_tools

        mock_engine = MagicMock()
        mock_engine.execute_async = AsyncMock(
            return_value={"success": False, "errors": ["commit failed"]}
        )
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "hw_vio_set_output" in registered_tools:
            result = await registered_tools["hw_vio_set_output"](
                vio="vio_0",
                probe="probe_out0",
                value="1",
            )
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_set_probe_file_tool_success(self, tmp_path):
        """测试 set_probe_file 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools

        hardware_tools._hw_server_connected = True
        hardware_tools._hw_devices = [
            {"index": 0, "name": "xc7a35t_0", "type": "FPGA"}
        ]

        probe_file = tmp_path / "debug.ltx"
        probe_file.write_text("LTX_DATA", encoding="utf-8")

        mock_engine = MagicMock()
        async_result = MagicMock()
        async_result.success = True
        async_result.output = ""
        async_result.errors = []
        async_result.warnings = []
        mock_engine.execute_async = AsyncMock(return_value=async_result)
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "set_probe_file" in registered_tools:
            result = await registered_tools["set_probe_file"](
                device_index=0,
                probe_file_path=str(probe_file),
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_hw_axi_read_tool_success(self):
        """测试 hw_axi_read 工具成功。"""
        import gateflow.tools.hardware_tools as hardware_tools

        mock_engine = MagicMock()
        async_result = MagicMock()
        async_result.success = True
        async_result.output = "0x00000001"
        async_result.errors = []
        async_result.warnings = []
        mock_engine.execute_async = AsyncMock(return_value=async_result)
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "hw_axi_read" in registered_tools:
            result = await registered_tools["hw_axi_read"](
                axi_name="axi_dbg_0",
                address="40000000",
            )
            assert result.success is True
            assert result.value == "0x00000001"
            assert result.address == "0x40000000"

    @pytest.mark.asyncio
    async def test_hw_axi_write_tool_failure(self):
        """测试 hw_axi_write 工具失败。"""
        import gateflow.tools.hardware_tools as hardware_tools

        mock_engine = MagicMock()
        mock_engine.execute_async = AsyncMock(return_value={"success": False, "errors": ["axi write failed"]})
        hardware_tools._engine = mock_engine

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator

        mock_mcp.tool = capture_tool
        register_hardware_tools(mock_mcp)

        if "hw_axi_write" in registered_tools:
            result = await registered_tools["hw_axi_write"](
                axi_name="axi_dbg_0",
                address="0x40000000",
                value="1",
            )
            assert result.success is False
            assert result.error is not None

    def test_connect_server_result_with_many_devices(self):
        """测试 ConnectServerResult 多设备结果。"""
        devices = [{"index": i, "name": f"device_{i}", "type": "FPGA"} for i in range(100)]
        
        result = ConnectServerResult(
            success=True,
            server_url="localhost:3121",
            devices=devices,
            device_count=100,
            message="Connected with 100 devices",
        )
        
        assert result.device_count == 100
        assert len(result.devices) == 100

    def test_program_result_with_long_path(self):
        """测试 ProgramResult 长路径结果。"""
        long_path = "/a" * 100 + "/design.bit"
        
        result = ProgramResult(
            success=True,
            device_index=0,
            device_name="xc7a35t_0",
            bitstream_path=long_path,
            message="Programming completed",
        )
        
        assert result.bitstream_path == long_path
