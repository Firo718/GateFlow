"""
仿真模块测试。

测试 SimulatorType、SimulationMode、SimulationStatus 枚举，
SimulationConfig、TestbenchConfig、SimulationResult、WaveSignal 数据类，
SimulationTclGenerator 和 SimulationManager。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.vivado.simulation import (
    SimulatorType,
    SimulationMode,
    SimulationStatus,
    SimulationConfig,
    TestbenchConfig,
    SimulationResult,
    WaveSignal,
    SimulationTclGenerator,
    SimulationManager,
    TestbenchRunner,
)


# ==================== 枚举测试 ====================


class TestSimulatorType:
    """SimulatorType 枚举测试。"""

    def test_simulator_type_values(self):
        """测试仿真器类型枚举值。"""
        assert SimulatorType.VIVADO.value == "vivado"
        assert SimulatorType.MODELSIM.value == "modelsim"
        assert SimulatorType.QUESTASIM.value == "questasim"
        assert SimulatorType.XCELIUM.value == "xcelium"
        assert SimulatorType.VCS.value == "vcs"

    def test_simulator_type_count(self):
        """测试仿真器类型数量。"""
        types = list(SimulatorType)
        assert len(types) == 5


class TestSimulationMode:
    """SimulationMode 枚举测试。"""

    def test_simulation_mode_values(self):
        """测试仿真模式枚举值。"""
        assert SimulationMode.BEHAVIORAL.value == "behavioral"
        assert SimulationMode.POST_SYNTHESIS.value == "post_synth"
        assert SimulationMode.POST_IMPLEMENTATION.value == "post_impl"

    def test_simulation_mode_count(self):
        """测试仿真模式数量。"""
        modes = list(SimulationMode)
        assert len(modes) == 3


class TestSimulationStatus:
    """SimulationStatus 枚举测试。"""

    def test_simulation_status_values(self):
        """测试仿真状态枚举值。"""
        assert SimulationStatus.NOT_STARTED.value == "not_started"
        assert SimulationStatus.RUNNING.value == "running"
        assert SimulationStatus.COMPLETED.value == "completed"
        assert SimulationStatus.FAILED.value == "failed"
        assert SimulationStatus.STOPPED.value == "stopped"

    def test_simulation_status_count(self):
        """测试仿真状态数量。"""
        statuses = list(SimulationStatus)
        assert len(statuses) == 5


# ==================== 数据类测试 ====================


class TestSimulationConfig:
    """SimulationConfig 数据类测试。"""

    def test_simulation_config_default_values(self):
        """测试仿真配置默认值。"""
        config = SimulationConfig()
        
        assert config.name == "sim_1"
        assert config.top_module is None
        assert config.simulator == SimulatorType.VIVADO
        assert config.mode == SimulationMode.BEHAVIORAL
        assert config.simulation_time == "100us"
        assert config.run_mode == "default"

    def test_simulation_config_custom_values(self):
        """测试仿真配置自定义值。"""
        config = SimulationConfig(
            name="tb_sim",
            top_module="tb_top",
            simulator=SimulatorType.MODELSIM,
            mode=SimulationMode.POST_SYNTHESIS,
            simulation_time="1ms",
            run_mode="gui",
        )
        
        assert config.name == "tb_sim"
        assert config.top_module == "tb_top"
        assert config.simulator == SimulatorType.MODELSIM
        assert config.mode == SimulationMode.POST_SYNTHESIS
        assert config.simulation_time == "1ms"
        assert config.run_mode == "gui"


class TestTestbenchConfig:
    """TestbenchConfig 数据类测试。"""

    def test_testbench_config_required_fields(self):
        """测试 Testbench 配置必需字段。"""
        config = TestbenchConfig(name="tb_uart", dut_module="uart")
        
        assert config.name == "tb_uart"
        assert config.dut_module == "uart"
        assert config.test_cases == []
        assert config.source_files == []

    def test_testbench_config_custom_values(self):
        """测试 Testbench 配置自定义值。"""
        config = TestbenchConfig(
            name="tb_uart",
            dut_module="uart",
            test_cases=["test_tx", "test_rx"],
            source_files=[Path("/sim/tb_uart.v"), Path("/sim/uart_helper.v")],
        )
        
        assert len(config.test_cases) == 2
        assert len(config.source_files) == 2


class TestSimulationResult:
    """SimulationResult 数据类测试。"""

    def test_simulation_result_required_fields(self):
        """测试仿真结果必需字段。"""
        result = SimulationResult(success=True)
        
        assert result.success is True
        assert result.log_file is None
        assert result.waveform_file is None
        assert result.errors == 0
        assert result.warnings == 0
        assert result.simulation_time == 0.0
        assert result.status == SimulationStatus.NOT_STARTED
        assert result.message == ""

    def test_simulation_result_custom_values(self):
        """测试仿真结果自定义值。"""
        result = SimulationResult(
            success=False,
            log_file="/path/to/sim.log",
            waveform_file="/path/to/wave.wdb",
            errors=5,
            warnings=10,
            simulation_time=100.5,
            status=SimulationStatus.FAILED,
            message="Simulation failed",
        )
        
        assert result.success is False
        assert result.errors == 5
        assert result.status == SimulationStatus.FAILED


class TestWaveSignal:
    """WaveSignal 数据类测试。"""

    def test_wave_signal_required_fields(self):
        """测试波形信号必需字段。"""
        signal = WaveSignal(path="tb/clk")
        
        assert signal.path == "tb/clk"
        assert signal.name is None
        assert signal.radix == "binary"
        assert signal.color is None

    def test_wave_signal_custom_values(self):
        """测试波形信号自定义值。"""
        signal = WaveSignal(
            path="tb/data_bus",
            name="Data Bus",
            radix="hex",
            color="blue",
        )
        
        assert signal.name == "Data Bus"
        assert signal.radix == "hex"
        assert signal.color == "blue"


# ==================== SimulationTclGenerator 测试 ====================


class TestSimulationTclGenerator:
    """SimulationTclGenerator 测试。"""

    # --- 仿真器设置命令测试 ---

    def test_set_simulator_tcl_vivado(self):
        """测试设置 Vivado 仿真器 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulator_tcl(SimulatorType.VIVADO)
        
        assert "set_property target_simulator Vivado" in tcl

    def test_set_simulator_tcl_modelsim(self):
        """测试设置 ModelSim 仿真器 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulator_tcl(SimulatorType.MODELSIM)
        
        assert "set_property target_simulator ModelSim" in tcl

    def test_set_simulator_tcl_questasim(self):
        """测试设置 QuestaSim 仿真器 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulator_tcl(SimulatorType.QUESTASIM)
        
        assert "set_property target_simulator Questa" in tcl

    def test_set_simulator_tcl_xcelium(self):
        """测试设置 Xcelium 仿真器 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulator_tcl(SimulatorType.XCELIUM)
        
        assert "set_property target_simulator Xcelium" in tcl

    def test_set_simulator_tcl_vcs(self):
        """测试设置 VCS 仿真器 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulator_tcl(SimulatorType.VCS)
        
        assert "set_property target_simulator VCS" in tcl

    # --- 仿真集命令测试 ---

    def test_create_simulation_set_tcl(self):
        """测试创建仿真集 Tcl 生成。"""
        tcl = SimulationTclGenerator.create_simulation_set_tcl(
            "tb_uart",
            ["/sim/tb_uart.v", "/sim/helper.v"],
        )
        
        assert "create_fileset -simset tb_uart" in tcl
        assert "add_files -fileset tb_uart" in tcl

    def test_add_simulation_files_tcl(self):
        """测试添加仿真文件 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_simulation_files_tcl(
            ["/sim/tb.v", "/sim/helper.v"],
            "sim_1",
        )
        
        assert "add_files -fileset sim_1" in tcl
        assert "/sim/tb.v" in tcl

    def test_set_simulation_top_tcl(self):
        """测试设置仿真顶层模块 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulation_top_tcl("tb_top", "sim_1")
        
        assert "set_property top tb_top" in tcl
        assert "get_filesets sim_1" in tcl

    # --- 仿真控制命令测试 ---

    def test_launch_simulation_tcl_behavioral(self):
        """测试启动行为仿真 Tcl 生成。"""
        config = SimulationConfig(
            name="sim_1",
            mode=SimulationMode.BEHAVIORAL,
        )
        tcl = SimulationTclGenerator.launch_simulation_tcl(config)
        
        assert "launch_simulation" in tcl
        assert "-mode behavioral" in tcl

    def test_launch_simulation_tcl_post_synth(self):
        """测试启动综合后仿真 Tcl 生成。"""
        config = SimulationConfig(
            name="sim_1",
            mode=SimulationMode.POST_SYNTHESIS,
        )
        tcl = SimulationTclGenerator.launch_simulation_tcl(config)
        
        assert "-mode post_synth" in tcl

    def test_launch_simulation_tcl_post_impl(self):
        """测试启动实现后仿真 Tcl 生成。"""
        config = SimulationConfig(
            name="sim_1",
            mode=SimulationMode.POST_IMPLEMENTATION,
        )
        tcl = SimulationTclGenerator.launch_simulation_tcl(config)
        
        assert "-mode post_impl" in tcl

    def test_launch_simulation_tcl_gui_mode(self):
        """测试 GUI 模式启动仿真 Tcl 生成。"""
        config = SimulationConfig(
            name="sim_1",
            run_mode="gui",
        )
        tcl = SimulationTclGenerator.launch_simulation_tcl(config)
        
        assert "-gui" in tcl

    def test_launch_simulation_tcl_run_all(self):
        """测试 run_all 模式启动仿真 Tcl 生成。"""
        config = SimulationConfig(
            name="sim_1",
            run_mode="all",
        )
        tcl = SimulationTclGenerator.launch_simulation_tcl(config)
        
        assert "-run_all" in tcl

    def test_run_simulation_tcl_time(self):
        """测试运行仿真指定时间 Tcl 生成。"""
        tcl = SimulationTclGenerator.run_simulation_tcl("100us")
        
        assert "run 100us" in tcl

    def test_run_simulation_tcl_all(self):
        """测试运行完整仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.run_simulation_tcl("all")
        
        assert "run all" in tcl

    def test_stop_simulation_tcl(self):
        """测试停止仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.stop_simulation_tcl()
        
        assert tcl == "stop"

    def test_restart_simulation_tcl(self):
        """测试重启仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.restart_simulation_tcl()
        
        assert tcl == "restart"

    # --- 波形命令测试 ---

    def test_add_wave_tcl(self):
        """测试添加波形信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_wave_tcl("tb/clk", "binary")
        
        assert "add_wave" in tcl
        assert "/tb/clk" in tcl
        assert "-radix binary" in tcl

    def test_add_wave_tcl_hex(self):
        """测试十六进制波形信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_wave_tcl("tb/data", "hex")
        
        assert "-radix hex" in tcl

    def test_add_wave_group_tcl(self):
        """测试添加波形信号组 Tcl 生成。"""
        signals = [
            WaveSignal(path="tb/clk", name="Clock"),
            WaveSignal(path="tb/rst", name="Reset", radix="binary"),
        ]
        tcl = SimulationTclGenerator.add_wave_group_tcl("Control", signals)
        
        assert "add_wave_group Control" in tcl
        assert "tb/clk" in tcl

    def test_save_wave_config_tcl(self):
        """测试保存波形配置 Tcl 生成。"""
        tcl = SimulationTclGenerator.save_wave_config_tcl("/path/to/wave.wcfg")
        
        assert "save_wave_config" in tcl
        assert "/path/to/wave.wcfg" in tcl

    def test_open_wave_config_tcl(self):
        """测试打开波形配置 Tcl 生成。"""
        tcl = SimulationTclGenerator.open_wave_config_tcl("/path/to/wave.wcfg")
        
        assert "open_wave_config" in tcl

    # --- 导出命令测试 ---

    def test_export_simulation_tcl(self):
        """测试导出仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.export_simulation_tcl(
            "/path/to/export",
            SimulatorType.MODELSIM,
        )
        
        assert "export_simulation" in tcl
        assert "-directory" in tcl
        assert "-simulator ModelSim" in tcl

    # --- 状态查询命令测试 ---

    def test_get_simulation_time_tcl(self):
        """测试获取仿真时间 Tcl 生成。"""
        tcl = SimulationTclGenerator.get_simulation_time_tcl()
        
        assert "get_property SIM_TIME" in tcl

    def test_get_simulation_status_tcl(self):
        """测试获取仿真状态 Tcl 生成。"""
        tcl = SimulationTclGenerator.get_simulation_status_tcl()
        
        assert "get_property STATUS" in tcl

    # --- 属性设置命令测试 ---

    def test_set_simulation_property_tcl(self):
        """测试设置仿真属性 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulation_property_tcl(
            "sim.sim_time",
            "1ms",
            "sim_1",
        )
        
        assert "set_property sim.sim_time 1ms" in tcl

    def test_set_simulation_time_tcl(self):
        """测试设置仿真时间 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_simulation_time_tcl("1ms", "sim_1")
        
        assert "set_property sim.sim_time 1ms" in tcl

    # --- 编译命令测试 ---

    def test_compile_simulation_tcl(self):
        """测试编译仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.compile_simulation_tcl("sim_1")
        
        assert "compile_sim" in tcl
        assert "get_filesets sim_1" in tcl

    def test_elaborate_simulation_tcl(self):
        """测试详细化仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.elaborate_simulation_tcl("sim_1")
        
        assert "elaborate_sim" in tcl

    # --- 关闭命令测试 ---

    def test_close_simulation_tcl(self):
        """测试关闭仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.close_simulation_tcl()
        
        assert tcl == "close_sim"

    def test_close_simulation_force_tcl(self):
        """测试强制关闭仿真 Tcl 生成。"""
        tcl = SimulationTclGenerator.close_simulation_force_tcl()
        
        assert "close_sim -force" in tcl

    # --- 仿真集查询命令测试 ---

    def test_get_simulation_sets_tcl(self):
        """测试获取所有仿真集 Tcl 生成。"""
        tcl = SimulationTclGenerator.get_simulation_sets_tcl()
        
        assert "get_filesets -simset" in tcl

    def test_current_simulation_set_tcl(self):
        """测试设置当前仿真集 Tcl 生成。"""
        tcl = SimulationTclGenerator.current_simulation_set_tcl("sim_1")
        
        assert "current_fileset -simset sim_1" in tcl

    # --- 波形记录命令测试 ---

    def test_log_wave_tcl_default(self):
        """测试默认波形记录 Tcl 生成。"""
        tcl = SimulationTclGenerator.log_wave_tcl()
        
        assert "log_wave -recursive *" in tcl

    def test_log_wave_tcl_with_depth(self):
        """测试带深度的波形记录 Tcl 生成。"""
        tcl = SimulationTclGenerator.log_wave_tcl(depth=10)
        
        assert "log_wave -depth 10" in tcl

    # --- Verilog 定义命令测试 ---

    def test_set_vlog_define_tcl(self):
        """测试设置 Verilog 定义 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_vlog_define_tcl("DEBUG", "1", "sim_1")
        
        assert "vlog.define" in tcl
        assert "DEBUG=1" in tcl

    def test_set_vlog_include_tcl(self):
        """测试设置 Verilog 包含路径 Tcl 生成。"""
        tcl = SimulationTclGenerator.set_vlog_include_tcl("/path/to/include", "sim_1")
        
        assert "vlog.include_dirs" in tcl
        assert "/path/to/include" in tcl

    # --- 激励命令测试 ---

    def test_add_force_tcl(self):
        """测试添加激励信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_force_tcl("tb/clk", "0 1")
        
        assert "add_force" in tcl
        assert "{tb/clk}" in tcl
        assert "{0 1}" in tcl

    def test_add_force_tcl_with_repeat(self):
        """测试带重复的激励信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_force_tcl(
            "tb/clk",
            "0 1",
            repeat="10ns",
        )
        
        assert "-repeat 10ns" in tcl

    def test_add_force_tcl_with_after(self):
        """测试带延迟的激励信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_force_tcl(
            "tb/rst",
            "1",
            after="100ns",
        )
        
        assert "-after 100ns" in tcl

    def test_remove_force_tcl(self):
        """测试移除激励信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.remove_force_tcl("tb/clk")
        
        assert "remove_force" in tcl
        assert "{tb/clk}" in tcl

    def test_get_value_tcl(self):
        """测试获取信号值 Tcl 生成。"""
        tcl = SimulationTclGenerator.get_value_tcl("tb/data")
        
        assert "get_value" in tcl
        assert "{tb/data}" in tcl


# ==================== SimulationManager 测试 ====================


@pytest.mark.integration
class TestSimulationManager:
    """SimulationManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """创建仿真管理器。"""
        return SimulationManager(mock_engine)

    # --- set_simulator 测试 ---

    @pytest.mark.asyncio
    async def test_set_simulator_success(self, manager, mock_engine):
        """测试成功设置仿真器。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_simulator(SimulatorType.MODELSIM)
        
        assert result["success"] is True
        assert result["simulator"] == "modelsim"

    # --- create_simulation_set 测试 ---

    @pytest.mark.asyncio
    async def test_create_simulation_set_success(self, manager, mock_engine):
        """测试成功创建仿真集。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_simulation_set(
            "tb_uart",
            ["/sim/tb_uart.v"],
        )
        
        assert result["success"] is True
        assert result["name"] == "tb_uart"

    # --- add_simulation_files 测试 ---

    @pytest.mark.asyncio
    async def test_add_simulation_files_success(self, manager, mock_engine):
        """测试成功添加仿真文件。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.add_simulation_files(
            ["/sim/tb.v", "/sim/helper.v"],
            "sim_1",
        )
        
        assert result["success"] is True
        assert result["files_added"] == 2

    # --- set_simulation_top 测试 ---

    @pytest.mark.asyncio
    async def test_set_simulation_top_success(self, manager, mock_engine):
        """测试成功设置仿真顶层模块。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_simulation_top("tb_top", "sim_1")
        
        assert result["success"] is True
        assert result["top_module"] == "tb_top"

    # --- launch_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_launch_simulation_success(self, manager, mock_engine):
        """测试成功启动仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        config = SimulationConfig(name="sim_1", simulation_time="100us")
        result = await manager.launch_simulation(config)
        
        assert result["success"] is True
        assert manager._simulation_running is True

    @pytest.mark.asyncio
    async def test_launch_simulation_failure(self, manager, mock_engine):
        """测试启动仿真失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Compilation failed"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        config = SimulationConfig(name="sim_1")
        result = await manager.launch_simulation(config)
        
        assert result["success"] is False
        assert manager._simulation_running is False

    # --- run_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_run_simulation_success(self, manager, mock_engine):
        """测试成功运行仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.run_simulation("100us")
        
        assert result["success"] is True
        assert result["time"] == "100us"

    # --- stop_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_stop_simulation_success(self, manager, mock_engine):
        """测试成功停止仿真。"""
        manager._simulation_running = True
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.stop_simulation()
        
        assert result["success"] is True
        assert manager._simulation_running is False

    # --- restart_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_restart_simulation_success(self, manager, mock_engine):
        """测试成功重启仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.restart_simulation()
        
        assert result["success"] is True

    # --- close_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_close_simulation_success(self, manager, mock_engine):
        """测试成功关闭仿真。"""
        manager._simulation_running = True
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.close_simulation()
        
        assert result["success"] is True
        assert manager._simulation_running is False

    @pytest.mark.asyncio
    async def test_close_simulation_force(self, manager, mock_engine):
        """测试强制关闭仿真。"""
        manager._simulation_running = True
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.close_simulation(force=True)
        
        assert result["success"] is True

    # --- add_wave 测试 ---

    @pytest.mark.asyncio
    async def test_add_wave_success(self, manager, mock_engine):
        """测试成功添加波形信号。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.add_wave("tb/clk", "binary")
        
        assert result["success"] is True
        assert result["signal"] == "tb/clk"

    # --- add_wave_group 测试 ---

    @pytest.mark.asyncio
    async def test_add_wave_group_success(self, manager, mock_engine):
        """测试成功添加波形信号组。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        signals = [
            WaveSignal(path="tb/clk"),
            WaveSignal(path="tb/rst"),
        ]
        result = await manager.add_wave_group("Control", signals)
        
        assert result["success"] is True
        assert result["signals_count"] == 2

    # --- save_wave_config 测试 ---

    @pytest.mark.asyncio
    async def test_save_wave_config_success(self, manager, mock_engine):
        """测试成功保存波形配置。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.save_wave_config("/path/to/wave.wcfg")
        
        assert result["success"] is True
        assert result["path"] == "/path/to/wave.wcfg"

    # --- open_wave_config 测试 ---

    @pytest.mark.asyncio
    async def test_open_wave_config_success(self, manager, mock_engine):
        """测试成功打开波形配置。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.open_wave_config("/path/to/wave.wcfg")
        
        assert result["success"] is True

    # --- export_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_export_simulation_success(self, manager, mock_engine):
        """测试成功导出仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.export_simulation(
            "/path/to/export",
            SimulatorType.MODELSIM,
        )
        
        assert result["success"] is True
        assert result["simulator"] == "modelsim"

    # --- get_simulation_sets 测试 ---

    @pytest.mark.asyncio
    async def test_get_simulation_sets_success(self, manager, mock_engine):
        """测试成功获取仿真集列表。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "sim_1\nsim_2\n"
        mock_engine.execute_async.return_value = mock_result
        
        sim_sets = await manager.get_simulation_sets()
        
        assert len(sim_sets) >= 2

    # --- get_simulation_status 测试 ---

    @pytest.mark.asyncio
    async def test_get_simulation_status_running(self, manager, mock_engine):
        """测试获取正在运行的仿真状态。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "running"
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        status = await manager.get_simulation_status()
        
        assert status["running"] is True

    @pytest.mark.asyncio
    async def test_get_simulation_status_stopped(self, manager, mock_engine):
        """测试获取已停止的仿真状态。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "stopped"
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        status = await manager.get_simulation_status()
        
        assert status["running"] is False

    # --- get_simulation_time 测试 ---

    @pytest.mark.asyncio
    async def test_get_simulation_time_success(self, manager, mock_engine):
        """测试成功获取仿真时间。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "100us\n"
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.get_simulation_time()
        
        assert result["success"] is True
        assert result["time"] == "100us"

    # --- set_simulation_time 测试 ---

    @pytest.mark.asyncio
    async def test_set_simulation_time_success(self, manager, mock_engine):
        """测试成功设置仿真时间。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_simulation_time("1ms", "sim_1")
        
        assert result["success"] is True

    # --- compile_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_compile_simulation_success(self, manager, mock_engine):
        """测试成功编译仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.compile_simulation("sim_1")
        
        assert result["success"] is True

    # --- elaborate_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_elaborate_simulation_success(self, manager, mock_engine):
        """测试成功详细化仿真。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.elaborate_simulation("sim_1")
        
        assert result["success"] is True

    # --- log_wave 测试 ---

    @pytest.mark.asyncio
    async def test_log_wave_success(self, manager, mock_engine):
        """测试成功设置波形记录。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.log_wave(depth=10)
        
        assert result["success"] is True
        assert result["depth"] == 10

    # --- set_vlog_define 测试 ---

    @pytest.mark.asyncio
    async def test_set_vlog_define_success(self, manager, mock_engine):
        """测试成功设置 Verilog 定义。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_vlog_define("DEBUG", "1", "sim_1")
        
        assert result["success"] is True
        assert result["define"] == "DEBUG=1"

    # --- set_vlog_include 测试 ---

    @pytest.mark.asyncio
    async def test_set_vlog_include_success(self, manager, mock_engine):
        """测试成功设置 Verilog 包含路径。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_vlog_include("/path/to/include", "sim_1")
        
        assert result["success"] is True

    # --- add_force 测试 ---

    @pytest.mark.asyncio
    async def test_add_force_success(self, manager, mock_engine):
        """测试成功添加激励信号。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.add_force("tb/clk", "0 1", repeat="10ns")
        
        assert result["success"] is True

    # --- remove_force 测试 ---

    @pytest.mark.asyncio
    async def test_remove_force_success(self, manager, mock_engine):
        """测试成功移除激励信号。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.remove_force("tb/clk")
        
        assert result["success"] is True

    # --- get_signal_value 测试 ---

    @pytest.mark.asyncio
    async def test_get_signal_value_success(self, manager, mock_engine):
        """测试成功获取信号值。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "1010\n"
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.get_signal_value("tb/data")
        
        assert result["success"] is True
        assert result["value"] == "1010"

    # --- run_full_simulation 测试 ---

    @pytest.mark.asyncio
    async def test_run_full_simulation_success(self, manager, mock_engine):
        """测试成功运行完整仿真流程。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = "completed\n"
        mock_engine.execute_async.return_value = mock_result
        
        config = SimulationConfig(name="sim_1", simulation_time="100us")
        result = await manager.run_full_simulation(config)
        
        assert result.success is True
        assert result.status == SimulationStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_run_full_simulation_launch_failure(self, manager, mock_engine):
        """测试完整仿真流程启动失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Launch failed"]
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = SimulationConfig(name="sim_1")
        result = await manager.run_full_simulation(config)
        
        assert result.success is False
        assert result.status == SimulationStatus.FAILED

    # --- 辅助方法测试 ---

    def test_parse_simulation_sets(self, manager):
        """测试解析仿真集列表。"""
        output = "sim_1\nsim_2\n# comment\n"
        sim_sets = manager._parse_simulation_sets(output)
        
        assert len(sim_sets) == 2

    def test_parse_simulation_sets_empty(self, manager):
        """测试解析空仿真集列表。"""
        sim_sets = manager._parse_simulation_sets("")
        
        assert sim_sets == []

    def test_parse_simulation_time_us(self, manager):
        """测试解析微秒时间。"""
        time_ns = manager._parse_simulation_time("100us")
        
        assert time_ns == 100000.0

    def test_parse_simulation_time_ms(self, manager):
        """测试解析毫秒时间。"""
        time_ns = manager._parse_simulation_time("1ms")
        
        assert time_ns == 1000000.0

    def test_parse_simulation_time_ns(self, manager):
        """测试解析纳秒时间。"""
        time_ns = manager._parse_simulation_time("100ns")
        
        assert time_ns == 100.0

    def test_parse_simulation_time_ps(self, manager):
        """测试解析皮秒时间。"""
        time_ns = manager._parse_simulation_time("1000ps")
        
        assert time_ns == 1.0

    def test_parse_simulation_time_none(self, manager):
        """测试解析空时间。"""
        time_ns = manager._parse_simulation_time(None)
        
        assert time_ns == 0.0


# ==================== TestbenchRunner 测试 ====================


class TestTestbenchRunner:
    """TestbenchRunner 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def simulation_manager(self, mock_engine):
        """创建仿真管理器。"""
        return SimulationManager(mock_engine)

    @pytest.fixture
    def runner(self, simulation_manager):
        """创建 Testbench 运行器。"""
        return TestbenchRunner(simulation_manager)

    # --- setup_testbench 测试 ---

    @pytest.mark.asyncio
    async def test_setup_testbench_success(self, runner, mock_engine):
        """测试成功设置 Testbench。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(
            name="tb_uart",
            dut_module="uart",
            source_files=[Path("/sim/tb_uart.v")],
        )
        result = await runner.setup_testbench(config)
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_setup_testbench_failure(self, runner, mock_engine):
        """测试设置 Testbench 失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["File not found"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(
            name="tb_uart",
            dut_module="uart",
            source_files=[Path("/sim/nonexistent.v")],
        )
        result = await runner.setup_testbench(config)
        
        assert result["success"] is False

    # --- run_testbench 测试 ---

    @pytest.mark.asyncio
    async def test_run_testbench_success(self, runner, mock_engine):
        """测试成功运行 Testbench。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = "completed\n"
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(name="tb_uart", dut_module="uart")
        result = await runner.run_testbench(config)
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_testbench_setup_failure(self, runner, mock_engine):
        """测试运行 Testbench 设置失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Setup failed"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(name="tb_uart", dut_module="uart")
        result = await runner.run_testbench(config)
        
        assert result.success is False

    # --- run_test_cases 测试 ---

    @pytest.mark.asyncio
    async def test_run_test_cases_success(self, runner, mock_engine):
        """测试成功运行多个测试用例。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = "completed\n"
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(
            name="tb_uart",
            dut_module="uart",
            test_cases=["test_tx", "test_rx"],
        )
        results = await runner.run_test_cases(config)
        
        assert "test_tx" in results
        assert "test_rx" in results

    @pytest.mark.asyncio
    async def test_run_test_cases_custom_list(self, runner, mock_engine):
        """测试使用自定义列表运行测试用例。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = "completed\n"
        mock_engine.execute_async.return_value = mock_result
        
        config = TestbenchConfig(name="tb_uart", dut_module="uart")
        results = await runner.run_test_cases(
            config,
            test_cases=["custom_test"],
        )
        
        assert "custom_test" in results


# ==================== 边界情况测试 ====================


class TestSimulationEdgeCases:
    """仿真模块边界情况测试。"""

    def test_simulation_config_empty_name(self):
        """测试空名称仿真配置。"""
        config = SimulationConfig(name="")
        assert config.name == ""

    def test_simulation_config_long_time(self):
        """测试长时间仿真配置。"""
        config = SimulationConfig(simulation_time="1000ms")
        assert config.simulation_time == "1000ms"

    def test_wave_signal_empty_path(self):
        """测试空路径波形信号。"""
        signal = WaveSignal(path="")
        assert signal.path == ""

    def test_wave_signal_all_radix_types(self):
        """测试所有进制类型。"""
        for radix in ["binary", "hex", "unsigned", "decimal", "ascii"]:
            signal = WaveSignal(path="test", radix=radix)
            assert signal.radix == radix

    def test_simulation_result_all_statuses(self):
        """测试所有仿真状态。"""
        for status in SimulationStatus:
            result = SimulationResult(success=True, status=status)
            assert result.status == status

    def test_testbench_config_empty_test_cases(self):
        """测试空测试用例列表。"""
        config = TestbenchConfig(
            name="tb",
            dut_module="dut",
            test_cases=[],
        )
        assert config.test_cases == []

    def test_testbench_config_many_test_cases(self):
        """测试多个测试用例。"""
        cases = [f"test_{i}" for i in range(100)]
        config = TestbenchConfig(
            name="tb",
            dut_module="dut",
            test_cases=cases,
        )
        assert len(config.test_cases) == 100

    def test_parse_simulation_time_invalid(self):
        """测试解析无效时间字符串。"""
        engine = MagicMock()
        manager = SimulationManager(engine)
        
        time_ns = manager._parse_simulation_time("invalid")
        assert time_ns == 0.0

    def test_parse_simulation_time_numeric(self):
        """测试解析纯数字时间。"""
        engine = MagicMock()
        manager = SimulationManager(engine)
        
        time_ns = manager._parse_simulation_time("100")
        assert time_ns == 100.0

    def test_simulation_config_all_modes(self):
        """测试所有仿真模式。"""
        for mode in SimulationMode:
            config = SimulationConfig(mode=mode)
            assert config.mode == mode

    def test_simulation_config_all_simulators(self):
        """测试所有仿真器类型。"""
        for simulator in SimulatorType:
            config = SimulationConfig(simulator=simulator)
            assert config.simulator == simulator

    def test_add_force_tcl_all_options(self):
        """测试带所有选项的激励信号 Tcl 生成。"""
        tcl = SimulationTclGenerator.add_force_tcl(
            signal="tb/clk",
            value="0 1",
            repeat="10ns",
            after="5ns",
        )
        
        assert "add_force" in tcl
        assert "-repeat 10ns" in tcl
        assert "-after 5ns" in tcl


class TestSimulationFailureClassification:
    """SimulationManager failure classification tests."""

    @pytest.fixture
    def mock_engine(self):
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        return SimulationManager(mock_engine)

    @pytest.mark.asyncio
    async def test_launch_simulation_without_top_is_classified(self, manager):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["launch_simulation failed"]
        mock_result.warnings = []
        mock_result.output = ""
        manager.engine.execute_async.return_value = mock_result

        result = await manager.launch_simulation(SimulationConfig(name="sim_1"))

        assert result["success"] is False
        assert result["error_code"] == "top_not_set"
        assert result["failure_category"] == "top_not_set"

    @pytest.mark.asyncio
    async def test_compile_missing_simset_is_classified(self, manager, mock_engine):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["get_filesets sim_missing failed"]
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result

        result = await manager.compile_simulation("sim_missing")

        assert result["success"] is False
        assert result["error_code"] == "simset_not_found"
        assert result["failure_category"] == "simulation_set_missing"

    @pytest.mark.asyncio
    async def test_run_without_launch_is_classified(self, manager):
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["simulation session not running"]
        mock_result.warnings = []
        mock_result.output = ""
        manager.engine.execute_async.return_value = mock_result

        result = await manager.run_simulation("100ns")

        assert result["success"] is False
        assert result["error_code"] == "simulation_not_started"
        assert result["failure_category"] == "simulation_not_started"

    @pytest.mark.asyncio
    async def test_launch_tcp_failure_is_classified(self, manager, mock_engine):
        manager._simulation_tops["sim_1"] = "tb_top"
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["TCP timeout while launching simulation"]
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result

        result = await manager.launch_simulation(
            SimulationConfig(name="sim_1", top_module="tb_top")
        )

        assert result["success"] is False
        assert result["error_code"] == "tcp_interaction_failed"
        assert result["failure_category"] == "tcp_interaction_failed"
