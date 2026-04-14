"""
约束 MCP 工具测试。

测试约束工具注册、Pydantic 模型验证、工具函数和错误处理。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from pydantic import ValidationError

from gateflow.tools.constraint_tools import (
    CreateClockResult,
    GeneratedClockResult,
    InputDelayResult,
    OutputDelayResult,
    FalsePathResult,
    MulticyclePathResult,
    GetClocksResult,
    ReadXdcResult,
    WriteXdcResult,
    register_constraint_tools,
    _get_engine,
    _constraints,
)


# ==================== Pydantic 模型测试 ====================


class TestCreateClockResult:
    """CreateClockResult 模型测试。"""

    def test_create_clock_result_defaults(self):
        """测试 CreateClockResult 默认值。"""
        result = CreateClockResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.clock_name is None
        assert result.period is None
        assert result.target is None
        assert result.tcl_command is None
        assert result.error is None

    def test_create_clock_result_full(self):
        """测试 CreateClockResult 完整参数。"""
        result = CreateClockResult(
            success=True,
            clock_name="clk",
            period=10.0,
            target="clk_port",
            tcl_command="create_clock -name clk -period 10",
            message="Clock created successfully",
        )
        
        assert result.clock_name == "clk"
        assert result.period == 10.0
        assert result.target == "clk_port"
        assert result.tcl_command == "create_clock -name clk -period 10"

    def test_create_clock_result_failure(self):
        """测试 CreateClockResult 失败情况。"""
        result = CreateClockResult(
            success=False,
            message="Failed to create clock",
            error="Clock already exists",
        )
        
        assert result.success is False
        assert result.error == "Clock already exists"

    def test_create_clock_result_required_fields(self):
        """测试 CreateClockResult 必需字段。"""
        with pytest.raises(ValidationError):
            CreateClockResult()  # 缺少 success 和 message

        with pytest.raises(ValidationError):
            CreateClockResult(success=True)  # 缺少 message


class TestGeneratedClockResult:
    """GeneratedClockResult 模型测试。"""

    def test_generated_clock_result_defaults(self):
        """测试 GeneratedClockResult 默认值。"""
        result = GeneratedClockResult(success=True, message="Done")
        
        assert result.success is True
        assert result.clock_name is None
        assert result.source is None
        assert result.master_clock is None
        assert result.tcl_command is None

    def test_generated_clock_result_full(self):
        """测试 GeneratedClockResult 完整参数。"""
        result = GeneratedClockResult(
            success=True,
            clock_name="clk_div2",
            source="div_reg/Q",
            master_clock="clk",
            tcl_command="create_generated_clock -name clk_div2 -source [get_pins div_reg/Q]",
            message="Generated clock created",
        )
        
        assert result.clock_name == "clk_div2"
        assert result.source == "div_reg/Q"
        assert result.master_clock == "clk"


class TestInputDelayResult:
    """InputDelayResult 模型测试。"""

    def test_input_delay_result_defaults(self):
        """测试 InputDelayResult 默认值。"""
        result = InputDelayResult(success=True, message="Done")
        
        assert result.success is True
        assert result.clock is None
        assert result.delay is None
        assert result.ports == []
        assert result.tcl_command is None

    def test_input_delay_result_full(self):
        """测试 InputDelayResult 完整参数。"""
        result = InputDelayResult(
            success=True,
            clock="clk",
            delay=2.0,
            ports=["data_in", "valid_in"],
            tcl_command="set_input_delay -max 2.0 -clock clk",
            message="Input delay set",
        )
        
        assert result.clock == "clk"
        assert result.delay == 2.0
        assert result.ports == ["data_in", "valid_in"]


class TestOutputDelayResult:
    """OutputDelayResult 模型测试。"""

    def test_output_delay_result_defaults(self):
        """测试 OutputDelayResult 默认值。"""
        result = OutputDelayResult(success=True, message="Done")
        
        assert result.success is True
        assert result.clock is None
        assert result.delay is None
        assert result.ports == []

    def test_output_delay_result_full(self):
        """测试 OutputDelayResult 完整参数。"""
        result = OutputDelayResult(
            success=True,
            clock="clk",
            delay=1.5,
            ports=["data_out"],
            tcl_command="set_output_delay -max 1.5 -clock clk",
            message="Output delay set",
        )
        
        assert result.delay == 1.5
        assert result.ports == ["data_out"]


class TestFalsePathResult:
    """FalsePathResult 模型测试。"""

    def test_false_path_result_defaults(self):
        """测试 FalsePathResult 默认值。"""
        result = FalsePathResult(success=True, message="Done")
        
        assert result.success is True
        assert result.from_pins == []
        assert result.to_pins == []
        assert result.through == []
        assert result.tcl_command is None

    def test_false_path_result_full(self):
        """测试 FalsePathResult 完整参数。"""
        result = FalsePathResult(
            success=True,
            from_pins=["rst_async"],
            to_pins=["data_reg/D"],
            through=["sync_reg/Q"],
            tcl_command="set_false_path -from [get_pins rst_async]",
            message="False path set",
        )
        
        assert result.from_pins == ["rst_async"]
        assert result.to_pins == ["data_reg/D"]
        assert result.through == ["sync_reg/Q"]


class TestMulticyclePathResult:
    """MulticyclePathResult 模型测试。"""

    def test_multicycle_path_result_defaults(self):
        """测试 MulticyclePathResult 默认值。"""
        result = MulticyclePathResult(success=True, message="Done")
        
        assert result.success is True
        assert result.cycles is None
        assert result.from_pins == []
        assert result.to_pins == []
        assert result.setup is True

    def test_multicycle_path_result_full(self):
        """测试 MulticyclePathResult 完整参数。"""
        result = MulticyclePathResult(
            success=True,
            cycles=2,
            from_pins=["data_reg/Q"],
            to_pins=["result_reg/D"],
            setup=True,
            tcl_command="set_multicycle_path -setup 2",
            message="Multicycle path set",
        )
        
        assert result.cycles == 2
        assert result.setup is True


class TestGetClocksResult:
    """GetClocksResult 模型测试。"""

    def test_get_clocks_result_defaults(self):
        """测试 GetClocksResult 默认值。"""
        result = GetClocksResult(success=True, message="Done")
        
        assert result.success is True
        assert result.clocks == []
        assert result.count == 0

    def test_get_clocks_result_with_clocks(self):
        """测试 GetClocksResult 带时钟列表。"""
        clocks = [
            {"type": "create_clock", "name": "clk", "period": 10.0},
            {"type": "create_generated_clock", "name": "clk_div2"},
        ]
        
        result = GetClocksResult(
            success=True,
            clocks=clocks,
            count=2,
            message="Found 2 clocks",
        )
        
        assert result.count == 2
        assert len(result.clocks) == 2


class TestReadXdcResult:
    """ReadXdcResult 模型测试。"""

    def test_read_xdc_result_defaults(self):
        """测试 ReadXdcResult 默认值。"""
        result = ReadXdcResult(success=True, message="Done")
        
        assert result.success is True
        assert result.path is None
        assert result.constraints == []
        assert result.constraint_count == 0

    def test_read_xdc_result_full(self):
        """测试 ReadXdcResult 完整参数。"""
        result = ReadXdcResult(
            success=True,
            path="/path/to/constraints.xdc",
            constraints=["create_clock -name clk -period 10"],
            constraint_count=1,
            message="XDC file read",
        )
        
        assert result.path == "/path/to/constraints.xdc"
        assert result.constraint_count == 1


class TestWriteXdcResult:
    """WriteXdcResult 模型测试。"""

    def test_write_xdc_result_defaults(self):
        """测试 WriteXdcResult 默认值。"""
        result = WriteXdcResult(success=True, message="Done")
        
        assert result.success is True
        assert result.path is None
        assert result.constraint_count == 0

    def test_write_xdc_result_full(self):
        """测试 WriteXdcResult 完整参数。"""
        result = WriteXdcResult(
            success=True,
            path="/path/to/output.xdc",
            constraint_count=5,
            message="XDC file written",
        )
        
        assert result.path == "/path/to/output.xdc"
        assert result.constraint_count == 5


# ==================== 工具注册测试 ====================


class TestRegisterConstraintTools:
    """约束工具注册测试。"""

    def test_register_constraint_tools(self):
        """测试注册约束工具。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_constraint_tools(mock_mcp)
        
        # 验证 tool 装饰器被调用
        assert mock_mcp.tool.called

    def test_register_constraint_tools_creates_decorators(self):
        """测试注册约束工具创建装饰器。"""
        mock_mcp = MagicMock()
        decorators = []
        
        def mock_decorator():
            def decorator(func):
                decorators.append(func.__name__)
                return func
            return decorator
        
        mock_mcp.tool = mock_decorator
        
        register_constraint_tools(mock_mcp)
        
        # 应该注册多个工具
        assert len(decorators) > 0
        # 检查关键工具是否注册
        expected_tools = [
            "create_clock",
            "create_generated_clock",
            "set_input_delay",
            "set_output_delay",
            "set_false_path",
            "set_multicycle_path",
            "get_clocks",
            "read_xdc",
            "write_xdc",
        ]
        for tool in expected_tools:
            assert tool in decorators


# ==================== 全局状态管理测试 ====================


class TestGlobalStateManagement:
    """全局状态管理测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.constraint_tools as constraint_tools
        constraint_tools._engine = None
        constraint_tools._constraints.clear()

    def test_get_engine_creates_instance(self):
        """测试获取引擎创建实例。"""
        mock_info = MagicMock()
        mock_info.version = "2024.1"
        
        with patch("gateflow.tools.constraint_tools.TclEngine") as MockEngine:
            MockEngine.return_value.vivado_info = mock_info
            engine = _get_engine()
            
            assert engine is not None
            MockEngine.assert_called_once()

    def test_get_engine_reuses_instance(self):
        """测试获取引擎重用实例。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_info = MagicMock()
        mock_info.version = "2024.1"
        
        with patch("gateflow.tools.constraint_tools.TclEngine") as MockEngine:
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
        import gateflow.tools.constraint_tools as constraint_tools
        constraint_tools._engine = None
        constraint_tools._constraints.clear()

    @pytest.mark.asyncio
    async def test_create_clock_tool_success(self):
        """测试 create_clock 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=10.0,
                target="clk_port",
            )
            
            assert result.success is True
            assert result.clock_name == "clk"
            assert result.period == 10.0

    @pytest.mark.asyncio
    async def test_create_clock_tool_with_waveform(self):
        """测试 create_clock 工具带波形。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=10.0,
                waveform=[0.0, 5.0],
            )
            
            assert result.success is True
            assert "-waveform" in result.tcl_command

    @pytest.mark.asyncio
    async def test_create_generated_clock_tool_success(self):
        """测试 create_generated_clock 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Generated clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_generated_clock" in registered_tools:
            result = await registered_tools["create_generated_clock"](
                name="clk_div2",
                source="div_reg/Q",
                master_clock="clk",
                divide_by=2,
            )
            
            assert result.success is True
            assert result.clock_name == "clk_div2"

    @pytest.mark.asyncio
    async def test_set_input_delay_tool_success(self):
        """测试 set_input_delay 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Input delay set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_input_delay" in registered_tools:
            result = await registered_tools["set_input_delay"](
                clock="clk",
                delay=2.0,
                ports=["data_in"],
                max_delay=True,
            )
            
            assert result.success is True
            assert result.clock == "clk"
            assert result.delay == 2.0

    @pytest.mark.asyncio
    async def test_set_output_delay_tool_success(self):
        """测试 set_output_delay 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Output delay set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_output_delay" in registered_tools:
            result = await registered_tools["set_output_delay"](
                clock="clk",
                delay=1.5,
                ports=["data_out"],
                max_delay=True,
            )
            
            assert result.success is True

    @pytest.mark.asyncio
    async def test_set_false_path_tool_success(self):
        """测试 set_false_path 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "False path set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_false_path" in registered_tools:
            result = await registered_tools["set_false_path"](
                from_pins=["rst_async"],
                to_pins=["data_reg/D"],
            )
            
            assert result.success is True

    @pytest.mark.asyncio
    async def test_set_multicycle_path_tool_success(self):
        """测试 set_multicycle_path 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Multicycle path set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_multicycle_path" in registered_tools:
            result = await registered_tools["set_multicycle_path"](
                cycles=2,
                from_pins=["data_reg/Q"],
                to_pins=["result_reg/D"],
                setup=True,
            )
            
            assert result.success is True
            assert result.cycles == 2

    @pytest.mark.asyncio
    async def test_get_clocks_tool_success(self):
        """测试 get_clocks 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clocks retrieved",
        })
        constraint_tools._engine = mock_engine
        
        # 添加一些时钟约束
        constraint_tools._constraints.append({
            "type": "create_clock",
            "name": "clk",
            "period": 10.0,
        })
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "get_clocks" in registered_tools:
            result = await registered_tools["get_clocks"]()
            
            assert result.success is True
            assert result.count >= 1

    @pytest.mark.asyncio
    async def test_read_xdc_tool_success(self, tmp_path):
        """测试 read_xdc 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        xdc_file = tmp_path / "constraints.xdc"
        xdc_file.write_text("create_clock -name clk -period 10\n")
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "XDC file read",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "read_xdc" in registered_tools:
            result = await registered_tools["read_xdc"](path=str(xdc_file))
            
            assert result.success is True
            assert result.path == str(xdc_file)

    @pytest.mark.asyncio
    async def test_write_xdc_tool_success(self, tmp_path):
        """测试 write_xdc 工具成功。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "XDC file written",
        })
        constraint_tools._engine = mock_engine
        
        # 添加一些约束
        constraint_tools._constraints.append({
            "type": "create_clock",
            "tcl_command": "create_clock -name clk -period 10",
        })
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        output_file = tmp_path / "output.xdc"
        
        if "write_xdc" in registered_tools:
            result = await registered_tools["write_xdc"](path=str(output_file))
            
            assert result.success is True
            assert result.constraint_count >= 1


# ==================== 错误处理测试 ====================


class TestErrorHandling:
    """错误处理测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.constraint_tools as constraint_tools
        constraint_tools._engine = None
        constraint_tools._constraints.clear()

    @pytest.mark.asyncio
    async def test_create_clock_error(self):
        """测试 create_clock 工具错误处理。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Clock already exists",
            "message": "Failed to create clock",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=10.0,
            )
            
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_create_clock_exception(self):
        """测试 create_clock 工具异常处理。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("Unexpected error"))
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=10.0,
            )
            
            assert result.success is False
            assert "Unexpected error" in result.error

    @pytest.mark.asyncio
    async def test_set_input_delay_error(self):
        """测试 set_input_delay 工具错误处理。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "Clock not found",
            "message": "Failed to set input delay",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_input_delay" in registered_tools:
            result = await registered_tools["set_input_delay"](
                clock="nonexistent_clk",
                delay=2.0,
                ports=["data_in"],
            )
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_read_xdc_file_not_found(self):
        """测试 read_xdc 工具文件不存在。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": False,
            "error": "File not found",
            "message": "Failed to read XDC",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "read_xdc" in registered_tools:
            result = await registered_tools["read_xdc"](
                path="/nonexistent/path.xdc"
            )
            
            assert result.success is False

    @pytest.mark.asyncio
    async def test_write_xdc_error(self):
        """测试 write_xdc 工具错误处理。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "write_xdc" in registered_tools:
            # 尝试写入无效路径
            result = await registered_tools["write_xdc"](
                path="/invalid/path/output.xdc"
            )
            
            # 应该返回失败结果
            assert result.success is False

    @pytest.mark.asyncio
    async def test_get_clocks_exception(self):
        """测试 get_clocks 工具异常处理。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(side_effect=Exception("Database error"))
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "get_clocks" in registered_tools:
            result = await registered_tools["get_clocks"]()
            
            assert result.success is False
            assert result.error is not None


# ==================== 工具描述测试 ====================


class TestToolDescriptions:
    """工具描述测试。"""

    def test_constraint_tools_have_docstrings(self):
        """测试约束工具有文档字符串。"""
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        for name, func in registered_tools.items():
            assert func.__doc__ is not None, f"Tool {name} missing docstring"


# ==================== 边界情况测试 ====================


class TestConstraintToolsEdgeCases:
    """约束工具边界情况测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.constraint_tools as constraint_tools
        constraint_tools._engine = None
        constraint_tools._constraints.clear()

    @pytest.mark.asyncio
    async def test_create_clock_zero_period(self):
        """测试创建零周期时钟。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=0.0,
            )
            
            assert result.period == 0.0

    @pytest.mark.asyncio
    async def test_create_clock_negative_period(self):
        """测试创建负周期时钟。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=-10.0,
            )
            
            # 应该接受负值（Vivado 会报错）
            assert result.period == -10.0

    @pytest.mark.asyncio
    async def test_set_input_delay_empty_ports(self):
        """测试设置空端口列表的输入延迟。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Input delay set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_input_delay" in registered_tools:
            result = await registered_tools["set_input_delay"](
                clock="clk",
                delay=2.0,
                ports=[],
            )
            
            assert result.ports == []

    @pytest.mark.asyncio
    async def test_set_multicycle_path_zero_cycles(self):
        """测试设置零周期多周期路径。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Multicycle path set",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "set_multicycle_path" in registered_tools:
            result = await registered_tools["set_multicycle_path"](
                cycles=0,
            )
            
            assert result.cycles == 0

    @pytest.mark.asyncio
    async def test_write_xdc_with_custom_constraints(self, tmp_path):
        """测试写入自定义约束到 XDC 文件。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        output_file = tmp_path / "custom.xdc"
        custom_constraints = [
            "create_clock -name clk -period 10",
            "set_input_delay -max 2 -clock clk [get_ports data_in]",
        ]
        
        if "write_xdc" in registered_tools:
            result = await registered_tools["write_xdc"](
                path=str(output_file),
                constraints=custom_constraints,
            )
            
            assert result.success is True
            assert result.constraint_count == 2

    @pytest.mark.asyncio
    async def test_create_clock_with_get_ports_syntax(self):
        """测试使用 get_ports 语法的目标。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_clock" in registered_tools:
            result = await registered_tools["create_clock"](
                name="clk",
                period=10.0,
                target="[get_ports clk]",
            )
            
            # 不应该重复添加 get_ports
            assert result.tcl_command.count("get_ports") == 1

    @pytest.mark.asyncio
    async def test_create_generated_clock_with_multiply_by(self):
        """测试创建倍频派生时钟。"""
        import gateflow.tools.constraint_tools as constraint_tools
        
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock(return_value={
            "success": True,
            "message": "Generated clock created",
        })
        constraint_tools._engine = mock_engine
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_constraint_tools(mock_mcp)
        
        if "create_generated_clock" in registered_tools:
            result = await registered_tools["create_generated_clock"](
                name="clk_x2",
                source="pll/clk_out",
                master_clock="clk_ref",
                multiply_by=2,
            )
            
            assert result.success is True
            assert "-multiply_by 2" in result.tcl_command
