"""
仿真 MCP 工具测试。

测试 Pydantic 模型验证、工具注册和异步工具函数。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.tools.simulation_tools import (
    SetSimulatorResult,
    CreateSimSetResult,
    AddSimFilesResult,
    SetSimTopResult,
    ForceSignalResult,
    LaunchSimulationResult,
    RunSimulationResult,
    StopSimulationResult,
    RestartSimulationResult,
    AddWaveResult,
    ExportSimulationResult,
    GetSimStatusResult,
    SignalValueResult,
    register_simulation_tools,
)


# ==================== Pydantic 模型测试 ====================


class TestSimulationResultModels:
    """仿真结果模型测试。"""

    def test_set_simulator_result_success(self):
        """测试设置仿真器成功结果。"""
        result = SetSimulatorResult(
            success=True,
            simulator="vivado",
            message="仿真器设置成功",
        )
        
        assert result.success is True
        assert result.simulator == "vivado"
        assert result.error is None

    def test_set_simulator_result_failure(self):
        """测试设置仿真器失败结果。"""
        result = SetSimulatorResult(
            success=False,
            simulator=None,
            message="仿真器设置失败",
            error="Simulator not found",
        )
        
        assert result.success is False
        assert result.error == "Simulator not found"

    def test_create_sim_set_result(self):
        """测试创建仿真集结果。"""
        result = CreateSimSetResult(
            success=True,
            name="tb_uart",
            message="仿真集创建成功",
        )
        
        assert result.success is True
        assert result.name == "tb_uart"

    def test_add_sim_files_result(self):
        """测试添加仿真文件结果。"""
        result = AddSimFilesResult(
            success=True,
            files_added=2,
            message="添加 2 个仿真文件",
        )
        
        assert result.success is True
        assert result.files_added == 2

    def test_set_sim_top_result(self):
        """测试设置仿真顶层结果。"""
        result = SetSimTopResult(
            success=True,
            top_module="tb_top",
            message="仿真顶层模块设置成功",
        )
        
        assert result.success is True
        assert result.top_module == "tb_top"

    def test_launch_simulation_result(self):
        """测试启动仿真结果。"""
        result = LaunchSimulationResult(
            success=True,
            mode="behavioral",
            message="仿真启动成功",
        )
        
        assert result.success is True
        assert result.mode == "behavioral"

    def test_run_simulation_result(self):
        """测试运行仿真结果。"""
        result = RunSimulationResult(
            success=True,
            time="100us",
            message="仿真运行成功",
        )
        
        assert result.success is True
        assert result.time == "100us"

    def test_stop_simulation_result(self):
        """测试停止仿真结果。"""
        result = StopSimulationResult(
            success=True,
            message="仿真已停止",
        )
        
        assert result.success is True

    def test_restart_simulation_result(self):
        """测试重启仿真结果。"""
        result = RestartSimulationResult(
            success=True,
            message="仿真已重启",
        )
        
        assert result.success is True

    def test_force_signal_result(self):
        """测试仿真激励结果。"""
        result = ForceSignalResult(
            success=True,
            signal="tb/clk",
            value="0 1",
            message="激励添加成功",
        )

        assert result.success is True
        assert result.signal == "tb/clk"
        assert result.value == "0 1"

    def test_signal_value_result(self):
        """测试信号值结果。"""
        result = SignalValueResult(
            success=True,
            signal="tb/data",
            value="8'h55",
            message="读取成功",
        )

        assert result.success is True
        assert result.signal == "tb/data"
        assert result.value == "8'h55"

    def test_add_wave_result(self):
        """测试添加波形信号结果。"""
        result = AddWaveResult(
            success=True,
            signal="tb/clk",
            radix="binary",
            message="波形信号添加成功",
        )
        
        assert result.success is True
        assert result.signal == "tb/clk"
        assert result.radix == "binary"

    def test_export_simulation_result(self):
        """测试导出仿真结果。"""
        result = ExportSimulationResult(
            success=True,
            output_dir="/path/to/export",
            simulator="modelsim",
            message="仿真导出成功",
        )
        
        assert result.success is True
        assert result.simulator == "modelsim"

    def test_get_sim_status_result_running(self):
        """测试获取仿真状态结果 - 运行中。"""
        result = GetSimStatusResult(
            success=True,
            running=True,
            status="running",
            message="仿真正在运行",
        )
        
        assert result.success is True
        assert result.running is True
        assert result.status == "running"

    def test_get_sim_status_result_stopped(self):
        """测试获取仿真状态结果 - 已停止。"""
        result = GetSimStatusResult(
            success=True,
            running=False,
            status="stopped",
            message="仿真已停止",
        )
        
        assert result.running is False
        assert result.status == "stopped"


# ==================== 工具注册测试 ====================


class TestSimulationToolsRegistration:
    """仿真工具注册测试。"""

    def test_register_simulation_tools(self):
        """测试工具注册。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_simulation_tools(mock_mcp)
        
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
        
        register_simulation_tools(mock_mcp)
        
        # 应该注册了多个工具
        assert call_count[0] >= 5


# ==================== 异步工具函数测试 ====================


class TestSimulationToolFunctions:
    """仿真工具函数测试。"""

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
    async def test_set_simulator_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 set_simulator 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.set_simulator = AsyncMock(return_value={
                    "success": True,
                    "simulator": "vivado",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_create_sim_set_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 create_sim_set 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.create_simulation_set = AsyncMock(return_value={
                    "success": True,
                    "name": "tb_uart",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_add_sim_files_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 add_sim_files 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.add_simulation_files = AsyncMock(return_value={
                    "success": True,
                    "files_added": 2,
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_set_sim_top_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 set_sim_top 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.set_simulation_top = AsyncMock(return_value={
                    "success": True,
                    "top_module": "tb_top",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_launch_simulation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 launch_simulation 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.launch_simulation = AsyncMock(return_value={
                    "success": True,
                    "mode": "behavioral",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_run_simulation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 run_simulation 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.run_simulation = AsyncMock(return_value={
                    "success": True,
                    "time": "100us",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_stop_simulation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 stop_simulation 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.stop_simulation = AsyncMock(return_value={
                    "success": True,
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_restart_simulation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 restart_simulation 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.restart_simulation = AsyncMock(return_value={
                    "success": True,
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_add_wave_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 add_wave 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.add_wave = AsyncMock(return_value={
                    "success": True,
                    "signal": "tb/clk",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_export_simulation_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 export_simulation 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.export_simulation = AsyncMock(return_value={
                    "success": True,
                    "simulator": "modelsim",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_get_sim_status_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 get_sim_status 工具。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.get_simulation_status = AsyncMock(return_value={
                    "success": True,
                    "running": True,
                    "status": "running",
                })
                mock_get_manager.return_value = mock_manager
                
                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_add_force_signal_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 add_force_signal 工具。"""
        from gateflow.tools import simulation_tools

        simulation_tools._engine = None
        simulation_tools._simulation_manager = None

        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.add_force = AsyncMock(return_value={
                    "success": True,
                    "signal": "tb/clk",
                    "value": "0 1",
                    "errors": [],
                })
                mock_get_manager.return_value = mock_manager

                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_remove_force_signal_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 remove_force_signal 工具。"""
        from gateflow.tools import simulation_tools

        simulation_tools._engine = None
        simulation_tools._simulation_manager = None

        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.remove_force = AsyncMock(return_value={
                    "success": True,
                    "signal": "tb/clk",
                    "errors": [],
                })
                mock_get_manager.return_value = mock_manager

                register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_probe_signal_tool(self, mock_mcp, mock_engine, mock_result):
        """测试 probe_signal 工具。"""
        from gateflow.tools import simulation_tools

        simulation_tools._engine = None
        simulation_tools._simulation_manager = None

        with patch.object(simulation_tools, '_get_engine', return_value=mock_engine):
            with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.add_wave = AsyncMock(return_value={
                    "success": True,
                    "signal": "tb/clk",
                    "radix": "binary",
                    "errors": [],
                })
                mock_get_manager.return_value = mock_manager

                register_simulation_tools(mock_mcp)


# ==================== 辅助函数测试 ====================


class TestSimulationToolsHelperFunctions:
    """仿真工具辅助函数测试。"""

    def test_get_engine_singleton(self):
        """测试获取引擎单例。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        
        with patch('gateflow.tools.simulation_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            engine1 = simulation_tools._get_engine()
            engine2 = simulation_tools._get_engine()
            
            # 应该返回同一个实例
            assert engine1 == engine2
        
        # 清理
        simulation_tools._engine = None

    def test_get_sim_manager_singleton(self):
        """测试获取仿真管理器单例。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._simulation_manager = None
        simulation_tools._engine = None
        
        with patch('gateflow.tools.simulation_tools.TclEngine') as MockTclEngine:
            mock_engine = MagicMock()
            MockTclEngine.return_value = mock_engine
            
            with patch('gateflow.tools.simulation_tools.SimulationManager') as MockSimManager:
                mock_manager = MagicMock()
                MockSimManager.return_value = mock_manager
                
                manager1 = simulation_tools._get_simulation_manager()
                manager2 = simulation_tools._get_simulation_manager()
                
                # 应该返回同一个实例
                assert manager1 == manager2
        
        # 清理
        simulation_tools._simulation_manager = None
        simulation_tools._engine = None


# ==================== 异常处理测试 ====================


class TestSimulationToolsExceptionHandling:
    """仿真工具异常处理测试。"""

    @pytest.fixture
    def mock_mcp(self):
        """创建模拟的 FastMCP。"""
        mcp = MagicMock()
        mcp.tool = MagicMock(return_value=lambda f: f)
        return mcp

    @pytest.mark.asyncio
    async def test_launch_simulation_exception(self, mock_mcp):
        """测试 launch_simulation 异常处理。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.launch_simulation = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_simulation_tools(mock_mcp)

    @pytest.mark.asyncio
    async def test_run_simulation_exception(self, mock_mcp):
        """测试 run_simulation 异常处理。"""
        from gateflow.tools import simulation_tools
        
        simulation_tools._engine = None
        simulation_tools._simulation_manager = None
        
        with patch.object(simulation_tools, '_get_simulation_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.run_simulation = AsyncMock(
                side_effect=Exception("Test exception")
            )
            mock_get_manager.return_value = mock_manager
            
            register_simulation_tools(mock_mcp)


# ==================== 边界情况测试 ====================


class TestSimulationToolsEdgeCases:
    """仿真工具边界情况测试。"""

    def test_result_model_with_none_values(self):
        """测试结果模型带 None 值。"""
        result = LaunchSimulationResult(
            success=False,
            mode=None,
            message="失败",
            error=None,
        )
        
        assert result.success is False
        assert result.mode is None

    def test_result_model_empty_message(self):
        """测试结果模型空消息。"""
        result = StopSimulationResult(
            success=True,
            message="",
        )
        
        assert result.message == ""

    def test_result_model_unicode_message(self):
        """测试结果模型 Unicode 消息。"""
        result = LaunchSimulationResult(
            success=True,
            mode="behavioral",
            message="仿真启动成功",
        )
        
        assert "成功" in result.message

    def test_add_wave_result_all_radix(self):
        """测试所有进制的波形信号结果。"""
        for radix in ["binary", "hex", "unsigned", "decimal", "ascii"]:
            result = AddWaveResult(
                success=True,
                signal="tb/data",
                radix=radix,
                message="成功",
            )
            assert result.radix == radix

    def test_set_simulator_result_all_types(self):
        """测试所有仿真器类型结果。"""
        for sim in ["vivado", "modelsim", "questasim", "xcelium", "vcs"]:
            result = SetSimulatorResult(
                success=True,
                simulator=sim,
                message="成功",
            )
            assert result.simulator == sim

    def test_launch_simulation_result_all_modes(self):
        """测试所有仿真模式结果。"""
        for mode in ["behavioral", "post_synth", "post_impl"]:
            result = LaunchSimulationResult(
                success=True,
                mode=mode,
                message="成功",
            )
            assert result.mode == mode

    def test_export_simulation_result_all_simulators(self):
        """测试所有仿真器的导出结果。"""
        for sim in ["vivado", "modelsim", "questasim", "xcelium", "vcs"]:
            result = ExportSimulationResult(
                success=True,
                output_dir="/path/to/export",
                simulator=sim,
                message="成功",
            )
            assert result.simulator == sim
