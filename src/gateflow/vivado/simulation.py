"""
Vivado 仿真支持模块

提供行为仿真、Testbench 管理等功能。
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

from gateflow.vivado.result_utils import format_result, path_artifact


class SimulatorType(Enum):
    """仿真器类型"""
    VIVADO = "vivado"
    MODELSIM = "modelsim"
    QUESTASIM = "questasim"
    XCELIUM = "xcelium"
    VCS = "vcs"


class SimulationMode(Enum):
    """仿真模式"""
    BEHAVIORAL = "behavioral"
    POST_SYNTHESIS = "post_synth"
    POST_IMPLEMENTATION = "post_impl"


class SimulationStatus(Enum):
    """仿真状态"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SimulationConfig:
    """仿真配置"""
    name: str = "sim_1"
    top_module: str | None = None
    simulator: SimulatorType = SimulatorType.VIVADO
    mode: SimulationMode = SimulationMode.BEHAVIORAL
    simulation_time: str = "100us"  # 仿真时间
    run_mode: str = "default"  # default, all, gui


@dataclass
class TestbenchConfig:
    """Testbench 配置"""
    name: str
    dut_module: str  # 被测模块
    test_cases: list[str] = field(default_factory=list)
    source_files: list[Path] = field(default_factory=list)


@dataclass
class SimulationResult:
    """仿真结果"""
    success: bool
    log_file: str | None = None
    waveform_file: str | None = None
    errors: int = 0
    warnings: int = 0
    simulation_time: float = 0.0
    status: SimulationStatus = SimulationStatus.NOT_STARTED
    message: str = ""


@dataclass
class WaveSignal:
    """波形信号配置"""
    path: str  # 信号路径
    name: str | None = None  # 显示名称
    radix: str = "binary"  # 进制: binary, hex, unsigned, decimal, ascii
    color: str | None = None  # 波形颜色


class SimulationTclGenerator:
    """
    仿真 Tcl 命令生成器
    
    生成用于仿真设置、运行、波形管理等操作的 Tcl 命令。
    """
    
    # 仿真器映射到 Vivado 属性值
    SIMULATOR_MAP = {
        SimulatorType.VIVADO: "Vivado",
        SimulatorType.MODELSIM: "ModelSim",
        SimulatorType.QUESTASIM: "Questa",
        SimulatorType.XCELIUM: "Xcelium",
        SimulatorType.VCS: "VCS",
    }
    
    @staticmethod
    def set_simulator_tcl(simulator: SimulatorType) -> str:
        """
        生成设置仿真器的 Tcl 命令
        
        Args:
            simulator: 仿真器类型
            
        Returns:
            Tcl 命令字符串
        """
        simulator_name = SimulationTclGenerator.SIMULATOR_MAP.get(simulator, "Vivado")
        return f'set_property target_simulator {simulator_name} [current_project]'
    
    @staticmethod
    def create_simulation_set_tcl(name: str, sources: list[str]) -> str:
        """
        生成创建仿真集的 Tcl 命令
        
        Args:
            name: 仿真集名称
            sources: 源文件列表
            
        Returns:
            Tcl 命令字符串
        """
        # 创建仿真文件集
        commands = [
            f'create_fileset -simset {name}',
        ]
        
        # 添加源文件
        for source in sources:
            source_path = source.replace('\\', '/')
            commands.append(
                f'add_files -fileset {name} [glob "{source_path}"]'
            )
        
        return '\n'.join(commands)
    
    @staticmethod
    def add_simulation_files_tcl(files: list[str], sim_set: str = "sim_1") -> str:
        """
        生成添加仿真文件的 Tcl 命令
        
        Args:
            files: 文件路径列表
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        commands = []
        for file_path in files:
            # 统一路径分隔符
            normalized_path = file_path.replace('\\', '/')
            commands.append(
                f'add_files -fileset {sim_set} "{normalized_path}"'
            )
        
        return '\n'.join(commands)
    
    @staticmethod
    def set_simulation_top_tcl(module: str, sim_set: str = "sim_1") -> str:
        """
        生成设置仿真顶层模块的 Tcl 命令
        
        Args:
            module: 顶层模块名称
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property top {module} [get_filesets {sim_set}]'
    
    @staticmethod
    def launch_simulation_tcl(config: SimulationConfig) -> str:
        """
        生成启动仿真的 Tcl 命令
        
        Args:
            config: 仿真配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'launch_simulation'
        
        # 添加模式参数
        if config.mode == SimulationMode.POST_SYNTHESIS:
            cmd += ' -mode post_synth'
        elif config.mode == SimulationMode.POST_IMPLEMENTATION:
            cmd += ' -mode post_impl'
        else:
            cmd += ' -mode behavioral'
        
        # 添加运行模式
        if config.run_mode == "gui":
            cmd += ' -gui'
        elif config.run_mode == "all":
            cmd += ' -run_all'
        
        return cmd
    
    @staticmethod
    def run_simulation_tcl(time: str = "all") -> str:
        """
        生成运行仿真的 Tcl 命令
        
        Args:
            time: 仿真时间，如 "100us", "1ms", "all"
            
        Returns:
            Tcl 命令字符串
        """
        if time.lower() == "all":
            return 'run all'
        else:
            return f'run {time}'
    
    @staticmethod
    def stop_simulation_tcl() -> str:
        """
        生成停止仿真的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'stop'
    
    @staticmethod
    def restart_simulation_tcl() -> str:
        """
        生成重启仿真的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'restart'
    
    @staticmethod
    def add_wave_tcl(signal: str, radix: str = "binary") -> str:
        """
        生成添加波形信号的 Tcl 命令
        
        Args:
            signal: 信号路径
            radix: 进制显示
            
        Returns:
            Tcl 命令字符串
        """
        return f'add_wave {{/{signal}}} -radix {radix}'
    
    @staticmethod
    def add_wave_group_tcl(group_name: str, signals: list[WaveSignal]) -> str:
        """
        生成添加波形信号组的 Tcl 命令
        
        Args:
            group_name: 信号组名称
            signals: 信号列表
            
        Returns:
            Tcl 命令字符串
        """
        commands = [f'set wave_group [add_wave_group {group_name}]']
        
        for signal in signals:
            radix_opt = f' -radix {signal.radix}' if signal.radix else ''
            name_opt = f' -name {{{signal.name}}}' if signal.name else ''
            commands.append(
                f'add_wave -into $wave_group {{{signal.path}}}{radix_opt}{name_opt}'
            )
        
        return '\n'.join(commands)
    
    @staticmethod
    def save_wave_config_tcl(path: str) -> str:
        """
        生成保存波形配置的 Tcl 命令
        
        Args:
            path: 波形配置文件路径 (.wcfg)
            
        Returns:
            Tcl 命令字符串
        """
        normalized_path = path.replace('\\', '/')
        return f'save_wave_config {{{normalized_path}}}'
    
    @staticmethod
    def open_wave_config_tcl(path: str) -> str:
        """
        生成打开波形配置的 Tcl 命令
        
        Args:
            path: 波形配置文件路径 (.wcfg)
            
        Returns:
            Tcl 命令字符串
        """
        normalized_path = path.replace('\\', '/')
        return f'open_wave_config {{{normalized_path}}}'
    
    @staticmethod
    def export_simulation_tcl(output_dir: str, simulator: SimulatorType) -> str:
        """
        生成导出仿真的 Tcl 命令
        
        Args:
            output_dir: 输出目录
            simulator: 目标仿真器
            
        Returns:
            Tcl 命令字符串
        """
        normalized_dir = output_dir.replace('\\', '/')
        simulator_name = SimulationTclGenerator.SIMULATOR_MAP.get(simulator, "Vivado")
        
        return f'export_simulation -directory "{normalized_dir}" -simulator {simulator_name}'
    
    @staticmethod
    def get_simulation_time_tcl() -> str:
        """
        生成获取仿真时间的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_property SIM_TIME [current_sim]'
    
    @staticmethod
    def get_simulation_status_tcl() -> str:
        """
        生成获取仿真状态的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_property STATUS [current_sim]'
    
    @staticmethod
    def set_simulation_property_tcl(
        property_name: str,
        value: str,
        sim_set: str = "sim_1"
    ) -> str:
        """
        生成设置仿真属性的 Tcl 命令
        
        Args:
            property_name: 属性名称
            value: 属性值
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property {property_name} {value} [get_filesets {sim_set}]'
    
    @staticmethod
    def set_simulation_time_tcl(time: str, sim_set: str = "sim_1") -> str:
        """
        生成设置仿真时间的 Tcl 命令
        
        Args:
            time: 仿真时间
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property sim.sim_time {time} [get_filesets {sim_set}]'
    
    @staticmethod
    def compile_simulation_tcl(sim_set: str = "sim_1") -> str:
        """
        生成编译仿真的 Tcl 命令
        
        Args:
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'compile_sim [get_filesets {sim_set}]'
    
    @staticmethod
    def elaborate_simulation_tcl(sim_set: str = "sim_1") -> str:
        """
        生成详细化仿真的 Tcl 命令
        
        Args:
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'elaborate_sim [get_filesets {sim_set}]'
    
    @staticmethod
    def close_simulation_tcl() -> str:
        """
        生成关闭仿真的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_sim'
    
    @staticmethod
    def close_simulation_force_tcl() -> str:
        """
        生成强制关闭仿真的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_sim -force'
    
    @staticmethod
    def get_simulation_sets_tcl() -> str:
        """
        生成获取所有仿真集的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_filesets -simset'
    
    @staticmethod
    def current_simulation_set_tcl(sim_set: str = "sim_1") -> str:
        """
        生成设置当前仿真集的 Tcl 命令
        
        Args:
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'current_fileset -simset {sim_set}'
    
    @staticmethod
    def log_wave_tcl(depth: int = 0) -> str:
        """
        生成记录波形的 Tcl 命令
        
        Args:
            depth: 记录深度，0 表示全部
            
        Returns:
            Tcl 命令字符串
        """
        if depth > 0:
            return f'log_wave -depth {depth}'
        else:
            return 'log_wave -recursive *'
    
    @staticmethod
    def set_vlog_define_tcl(name: str, value: str, sim_set: str = "sim_1") -> str:
        """
        生成设置 Verilog 定义的 Tcl 命令
        
        Args:
            name: 定义名称
            value: 定义值
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property -name {{vlog.define}} -value {{{name}={value}}} -objects [get_filesets {sim_set}]'
    
    @staticmethod
    def set_vlog_include_tcl(path: str, sim_set: str = "sim_1") -> str:
        """
        生成设置 Verilog 包含路径的 Tcl 命令
        
        Args:
            path: 包含路径
            sim_set: 仿真集名称
            
        Returns:
            Tcl 命令字符串
        """
        normalized_path = path.replace('\\', '/')
        return f'set_property -name {{vlog.include_dirs}} -value {{{normalized_path}}} -objects [get_filesets {sim_set}]'
    
    @staticmethod
    def add_force_tcl(
        signal: str,
        value: str,
        repeat: str | None = None,
        after: str | None = None
    ) -> str:
        """
        生成添加激励信号的 Tcl 命令
        
        Args:
            signal: 信号路径
            value: 激励值
            repeat: 重复周期
            after: 延迟时间
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'add_force {{{signal}}} {{{value}}}'
        
        if after:
            cmd += f' -after {after}'
        
        if repeat:
            cmd += f' -repeat {repeat}'
        
        return cmd
    
    @staticmethod
    def remove_force_tcl(signal: str) -> str:
        """
        生成移除激励信号的 Tcl 命令
        
        Args:
            signal: 信号路径
            
        Returns:
            Tcl 命令字符串
        """
        return f'remove_force {{{signal}}}'
    
    @staticmethod
    def get_value_tcl(signal: str) -> str:
        """
        生成获取信号值的 Tcl 命令
        
        Args:
            signal: 信号路径
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_value {{{signal}}}'


class SimulationManager:
    """
    仿真管理器
    
    提供高级的仿真管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化仿真管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self.current_config: SimulationConfig | None = None
        self._simulation_running: bool = False
        self._known_sim_sets: set[str] = {"sim_1"}
        self._simulation_tops: dict[str, str] = {}

    def _result_output(self, result: Any) -> str:
        """Normalize result output access across backends."""
        for attr in ("output", "data", "result", "message"):
            value = getattr(result, attr, None)
            if isinstance(value, str):
                return value.strip()
        return ""

    def _classify_simulation_failure(
        self,
        *,
        phase: str,
        result: Any,
        sim_set: str | None = None,
        top_module: str | None = None,
    ) -> tuple[str, str]:
        """Return a stable failure category and error code for AI-facing recovery."""
        error_blob = "\n".join(
            [
                str(item)
                for item in [*(getattr(result, "errors", None) or []), self._result_output(result)]
                if item
            ]
        ).lower()

        tcp_markers = ["timeout", "timed out", "socket", "tcp", "protocol", "broken pipe", "connection"]
        if any(marker in error_blob for marker in tcp_markers):
            return "tcp_interaction_failed", "tcp_interaction_failed"

        if sim_set and sim_set not in self._known_sim_sets:
            return "simulation_set_missing", "simset_not_found"

        if phase in {"set_top", "launch"}:
            expected_top = top_module or (sim_set and self._simulation_tops.get(sim_set))
            if not expected_top:
                return "top_not_set", "top_not_set"

        if phase in {"run", "probe", "force", "read_value", "remove_force"} and not self._simulation_running:
            return "simulation_not_started", "simulation_not_started"

        tool_markers = {
            "compile": ["compile_sim", "xvlog", "xsim.compile", "compile failed"],
            "elaborate": ["elaborate_sim", "xelab", "elaborate failed"],
            "launch": ["launch_simulation", "xsim", "launch failed"],
        }
        if phase in tool_markers and any(marker in error_blob for marker in tool_markers[phase]):
            return "backend_tool_failed", f"{phase}_tool_failed"

        if "no fileset" in error_blob or "get_filesets" in error_blob:
            return "simulation_set_missing", "simset_not_found"

        return "simulation_not_started", f"{phase}_failed"

    def _failure_result(
        self,
        *,
        phase: str,
        result: Any,
        message: str,
        sim_set: str | None = None,
        top_module: str | None = None,
        **extra: Any,
    ) -> dict:
        """Build a failure payload with stable classification fields."""
        failure_category, error_code = self._classify_simulation_failure(
            phase=phase,
            result=result,
            sim_set=sim_set,
            top_module=top_module,
        )
        return format_result(
            success=False,
            message=message,
            errors=result.errors,
            warnings=result.warnings,
            failure_category=failure_category,
            error_code=error_code,
            **extra,
        )
    
    async def set_simulator(self, simulator: SimulatorType) -> dict:
        """
        设置仿真器
        
        Args:
            simulator: 仿真器类型
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.set_simulator_tcl(simulator)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="仿真器设置成功" if result.success else "仿真器设置失败",
            errors=result.errors,
            warnings=result.warnings,
            simulator=simulator.value,
        )
    
    async def create_simulation_set(self, name: str, sources: list[str]) -> dict:
        """
        创建仿真集
        
        Args:
            name: 仿真集名称
            sources: 源文件列表
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.create_simulation_set_tcl(name, sources)
        result = await self.engine.execute_async(command)
        if result.success:
            self._known_sim_sets.add(name)
            return format_result(
                success=True,
                message=f"仿真集创建成功: {name}",
                errors=result.errors,
                warnings=result.warnings,
                name=name,
            )
        return self._failure_result(
            phase="create_simset",
            result=result,
            message="仿真集创建失败",
            sim_set=name,
            name=name,
        )
    
    async def add_simulation_files(self, files: list[str], sim_set: str = "sim_1") -> dict:
        """
        添加仿真文件
        
        Args:
            files: 文件路径列表
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.add_simulation_files_tcl(files, sim_set)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message=f"添加仿真文件成功: {len(files)}" if result.success else "添加仿真文件失败",
            errors=result.errors,
            warnings=result.warnings,
            files_added=len(files),
            sim_set=sim_set,
            artifacts={"files": files},
        )
    
    async def set_simulation_top(self, module: str, sim_set: str = "sim_1") -> dict:
        """
        设置仿真顶层模块
        
        Args:
            module: 顶层模块名称
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.set_simulation_top_tcl(module, sim_set)
        result = await self.engine.execute_async(command)
        if result.success:
            self._known_sim_sets.add(sim_set)
            self._simulation_tops[sim_set] = module
            return format_result(
                success=True,
                message=f"仿真顶层设置成功: {module}",
                errors=result.errors,
                warnings=result.warnings,
                top_module=module,
                sim_set=sim_set,
            )
        return self._failure_result(
            phase="set_top",
            result=result,
            message="仿真顶层设置失败",
            sim_set=sim_set,
            top_module=module,
            top_module_value=module,
            sim_set_value=sim_set,
        )
    
    async def launch_simulation(self, config: SimulationConfig) -> dict:
        """
        启动仿真
        
        Args:
            config: 仿真配置
            
        Returns:
            执行结果字典
        """
        self.current_config = config
        expected_top = config.top_module or self._simulation_tops.get(config.name)
        command = SimulationTclGenerator.launch_simulation_tcl(config)
        result = await self.engine.execute_async(command)
        if result.success:
            self._simulation_running = True
            self._known_sim_sets.add(config.name)
            logger.info(f"仿真启动成功: {config.name}")
            return format_result(
                success=True,
                message=f"仿真启动成功: {config.name}",
                errors=result.errors,
                warnings=result.warnings,
                config=config,
            )

        logger.error(f"仿真启动失败: {result.errors}")
        return self._failure_result(
            phase="launch",
            result=result,
            message="仿真启动失败",
            sim_set=config.name,
            top_module=expected_top,
            config=config,
        )
    
    async def run_simulation(self, time: str = "all") -> dict:
        """
        运行仿真
        
        Args:
            time: 仿真时间
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.run_simulation_tcl(time)
        result = await self.engine.execute_async(command)
        if result.success:
            return format_result(
                success=True,
                message=f"仿真运行成功: {time}",
                errors=result.errors,
                warnings=result.warnings,
                time=time,
            )
        return self._failure_result(
            phase="run",
            result=result,
            message="仿真运行失败",
            time=time,
        )
    
    async def stop_simulation(self) -> dict:
        """
        停止仿真
        
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.stop_simulation_tcl()
        result = await self.engine.execute_async(command)
        
        if result.success:
            self._simulation_running = False
            logger.info("仿真已停止")
        
        return format_result(
            success=result.success,
            message="仿真停止成功" if result.success else "仿真停止失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def restart_simulation(self) -> dict:
        """
        重启仿真
        
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.restart_simulation_tcl()
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info("仿真已重启")
        
        return format_result(
            success=result.success,
            message="仿真重启成功" if result.success else "仿真重启失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def close_simulation(self, force: bool = False) -> dict:
        """
        关闭仿真
        
        Args:
            force: 是否强制关闭
            
        Returns:
            执行结果字典
        """
        if force:
            command = SimulationTclGenerator.close_simulation_force_tcl()
        else:
            command = SimulationTclGenerator.close_simulation_tcl()
        
        result = await self.engine.execute_async(command)
        
        if result.success:
            self._simulation_running = False
            logger.info("仿真已关闭")
        
        return format_result(
            success=result.success,
            message="仿真关闭成功" if result.success else "仿真关闭失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def add_wave(self, signal: str, radix: str = "binary") -> dict:
        """
        添加波形信号
        
        Args:
            signal: 信号路径
            radix: 进制显示
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.add_wave_tcl(signal, radix)
        result = await self.engine.execute_async(command)
        if result.success:
            return format_result(
                success=True,
                message=f"波形信号添加成功: {signal}",
                errors=result.errors,
                warnings=result.warnings,
                signal=signal,
                radix=radix,
            )
        return self._failure_result(
            phase="probe",
            result=result,
            message="波形信号添加失败",
            signal=signal,
            radix=radix,
        )
    
    async def add_wave_group(self, group_name: str, signals: list[WaveSignal]) -> dict:
        """
        添加波形信号组
        
        Args:
            group_name: 信号组名称
            signals: 信号列表
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.add_wave_group_tcl(group_name, signals)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message=f"波形组添加成功: {group_name}" if result.success else "波形组添加失败",
            errors=result.errors,
            warnings=result.warnings,
            group_name=group_name,
            signals_count=len(signals),
        )
    
    async def save_wave_config(self, path: str) -> dict:
        """
        保存波形配置
        
        Args:
            path: 波形配置文件路径
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.save_wave_config_tcl(path)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="波形配置保存成功" if result.success else "波形配置保存失败",
            errors=result.errors,
            warnings=result.warnings,
            path=path,
            artifacts=path_artifact(path),
        )
    
    async def open_wave_config(self, path: str) -> dict:
        """
        打开波形配置
        
        Args:
            path: 波形配置文件路径
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.open_wave_config_tcl(path)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="波形配置打开成功" if result.success else "波形配置打开失败",
            errors=result.errors,
            warnings=result.warnings,
            path=path,
            artifacts=path_artifact(path),
        )
    
    async def export_simulation(self, output_dir: str, simulator: SimulatorType) -> dict:
        """
        导出仿真
        
        Args:
            output_dir: 输出目录
            simulator: 目标仿真器
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.export_simulation_tcl(output_dir, simulator)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"仿真导出成功: {output_dir}")
        
        return format_result(
            success=result.success,
            message="仿真导出成功" if result.success else "仿真导出失败",
            errors=result.errors,
            warnings=result.warnings,
            output_dir=output_dir,
            simulator=simulator.value,
            artifacts={"output_dir": output_dir},
        )
    
    async def get_simulation_sets(self) -> list[dict]:
        """
        获取所有仿真集
        
        Returns:
            仿真集列表
        """
        command = SimulationTclGenerator.get_simulation_sets_tcl()
        result = await self.engine.execute_async(command)
        
        if result.success:
            # 解析仿真集列表
            sim_sets = self._parse_simulation_sets(result.output)
            return sim_sets
        
        return []
    
    async def get_simulation_status(self) -> dict:
        """
        获取仿真状态
        
        Returns:
            状态字典
        """
        command = SimulationTclGenerator.get_simulation_status_tcl()
        result = await self.engine.execute_async(command)
        
        status = format_result(
            success=result.success,
            message="获取仿真状态成功" if result.success else "获取仿真状态失败",
            errors=result.errors,
            warnings=result.warnings,
            running=self._simulation_running,
            status='unknown',
        )
        
        if result.success:
            status['status'] = result.output.strip()
            status['running'] = 'running' in result.output.lower()
        
        return status
    
    async def get_simulation_time(self) -> dict:
        """
        获取当前仿真时间
        
        Returns:
            包含仿真时间的字典
        """
        command = SimulationTclGenerator.get_simulation_time_tcl()
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="获取仿真时间成功" if result.success else "获取仿真时间失败",
            errors=result.errors,
            warnings=result.warnings,
            time=result.output.strip() if result.success else None,
        )
    
    async def set_simulation_time(self, time: str, sim_set: str = "sim_1") -> dict:
        """
        设置仿真时间
        
        Args:
            time: 仿真时间
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.set_simulation_time_tcl(time, sim_set)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="仿真时间设置成功" if result.success else "仿真时间设置失败",
            errors=result.errors,
            warnings=result.warnings,
            time=time,
            sim_set=sim_set,
        )
    
    async def compile_simulation(self, sim_set: str = "sim_1") -> dict:
        """
        编译仿真
        
        Args:
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.compile_simulation_tcl(sim_set)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"仿真编译成功: {sim_set}")
            self._known_sim_sets.add(sim_set)
            return format_result(
                success=True,
                message="仿真编译成功",
                errors=result.errors,
                warnings=result.warnings,
                sim_set=sim_set,
            )

        logger.error(f"仿真编译失败: {result.errors}")
        return self._failure_result(
            phase="compile",
            result=result,
            message="仿真编译失败",
            sim_set=sim_set,
        )
    
    async def elaborate_simulation(self, sim_set: str = "sim_1") -> dict:
        """
        详细化仿真
        
        Args:
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.elaborate_simulation_tcl(sim_set)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"仿真详细化成功: {sim_set}")
            self._known_sim_sets.add(sim_set)
            return format_result(
                success=True,
                message="仿真详细化成功",
                errors=result.errors,
                warnings=result.warnings,
                sim_set=sim_set,
            )

        logger.error(f"仿真详细化失败: {result.errors}")
        return self._failure_result(
            phase="elaborate",
            result=result,
            message="仿真详细化失败",
            sim_set=sim_set,
        )
    
    async def log_wave(self, depth: int = 0) -> dict:
        """
        设置波形记录
        
        Args:
            depth: 记录深度，0 表示全部
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.log_wave_tcl(depth)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="波形记录设置成功" if result.success else "波形记录设置失败",
            errors=result.errors,
            warnings=result.warnings,
            depth=depth,
        )
    
    async def set_vlog_define(self, name: str, value: str, sim_set: str = "sim_1") -> dict:
        """
        设置 Verilog 定义
        
        Args:
            name: 定义名称
            value: 定义值
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.set_vlog_define_tcl(name, value, sim_set)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="Verilog define 设置成功" if result.success else "Verilog define 设置失败",
            errors=result.errors,
            warnings=result.warnings,
            define=f'{name}={value}',
            sim_set=sim_set,
        )
    
    async def set_vlog_include(self, path: str, sim_set: str = "sim_1") -> dict:
        """
        设置 Verilog 包含路径
        
        Args:
            path: 包含路径
            sim_set: 仿真集名称
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.set_vlog_include_tcl(path, sim_set)
        result = await self.engine.execute_async(command)
        
        return format_result(
            success=result.success,
            message="包含路径设置成功" if result.success else "包含路径设置失败",
            errors=result.errors,
            warnings=result.warnings,
            include_path=path,
            sim_set=sim_set,
            artifacts=path_artifact(path),
        )
    
    async def add_force(
        self,
        signal: str,
        value: str,
        repeat: str | None = None,
        after: str | None = None
    ) -> dict:
        """
        添加激励信号
        
        Args:
            signal: 信号路径
            value: 激励值
            repeat: 重复周期
            after: 延迟时间
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.add_force_tcl(signal, value, repeat, after)
        result = await self.engine.execute_async(command)
        if result.success:
            return format_result(
                success=True,
                message="激励添加成功",
                errors=result.errors,
                warnings=result.warnings,
                signal=signal,
                value=value,
            )
        return self._failure_result(
            phase="force",
            result=result,
            message="激励添加失败",
            signal=signal,
            value=value,
        )
    
    async def remove_force(self, signal: str) -> dict:
        """
        移除激励信号
        
        Args:
            signal: 信号路径
            
        Returns:
            执行结果字典
        """
        command = SimulationTclGenerator.remove_force_tcl(signal)
        result = await self.engine.execute_async(command)
        if result.success:
            return format_result(
                success=True,
                message="激励移除成功",
                errors=result.errors,
                warnings=result.warnings,
                signal=signal,
            )
        return self._failure_result(
            phase="remove_force",
            result=result,
            message="激励移除失败",
            signal=signal,
        )
    
    async def get_signal_value(self, signal: str) -> dict:
        """
        获取信号值
        
        Args:
            signal: 信号路径
            
        Returns:
            包含信号值的字典
        """
        command = SimulationTclGenerator.get_value_tcl(signal)
        result = await self.engine.execute_async(command)
        if result.success:
            raw_value = result.output.strip()
            return format_result(
                success=True,
                message="信号值读取成功",
                errors=result.errors,
                warnings=result.warnings,
                signal=signal,
                value=raw_value,
                raw_report=result.output,
            )
        return self._failure_result(
            phase="read_value",
            result=result,
            message="信号值读取失败",
            signal=signal,
            value=None,
            raw_report=None,
        )
    
    async def run_full_simulation(
        self,
        config: SimulationConfig,
        log_wave: bool = True,
        wave_depth: int = 0
    ) -> SimulationResult:
        """
        运行完整仿真流程
        
        Args:
            config: 仿真配置
            log_wave: 是否记录波形
            wave_depth: 波形记录深度
            
        Returns:
            SimulationResult 仿真结果
        """
        result = SimulationResult(
            success=False,
            status=SimulationStatus.NOT_STARTED
        )
        
        try:
            # 启动仿真
            launch_result = await self.launch_simulation(config)
            if not launch_result['success']:
                result.status = SimulationStatus.FAILED
                result.message = "启动仿真失败"
                return result
            
            # 记录波形
            if log_wave:
                await self.log_wave(wave_depth)
            
            # 运行仿真
            run_result = await self.run_simulation(config.simulation_time)
            if not run_result['success']:
                result.status = SimulationStatus.FAILED
                result.message = "运行仿真失败"
                return result
            
            # 获取仿真状态
            status = await self.get_simulation_status()
            
            result.success = True
            result.status = SimulationStatus.COMPLETED
            result.message = "仿真完成"
            
            # 获取仿真时间
            time_result = await self.get_simulation_time()
            if time_result['success']:
                result.simulation_time = self._parse_simulation_time(time_result['time'])
            
            logger.info(f"仿真完成: {config.name}")
            
        except Exception as e:
            result.status = SimulationStatus.FAILED
            result.message = str(e)
            logger.exception(f"仿真执行异常: {e}")
        
        return result
    
    def _parse_simulation_sets(self, output: str) -> list[dict]:
        """
        解析仿真集列表
        
        Args:
            output: Tcl 输出
            
        Returns:
            仿真集列表
        """
        sim_sets = []
        
        # 解析仿真集名称
        lines = output.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                sim_sets.append({
                    'name': line,
                    'type': 'simset'
                })
        
        return sim_sets
    
    def _parse_simulation_time(self, time_str: str | None) -> float:
        """
        解析仿真时间字符串
        
        Args:
            time_str: 时间字符串，如 "100us", "1ms"
            
        Returns:
            时间值（纳秒）
        """
        if not time_str:
            return 0.0
        
        # 时间单位映射到纳秒
        time_units = {
            'fs': 1e-6,
            'ps': 1e-3,
            'ns': 1.0,
            'us': 1e3,
            'ms': 1e6,
            's': 1e9,
        }
        
        # 解析时间值和单位
        match = re.match(r'([\d.]+)\s*([a-z]+)', time_str.lower())
        if match:
            value = float(match.group(1))
            unit = match.group(2)
            multiplier = time_units.get(unit, 1.0)
            return value * multiplier
        
        # 尝试解析纯数字
        try:
            return float(time_str)
        except ValueError:
            return 0.0


class TestbenchRunner:
    """
    Testbench 运行器
    
    提供便捷的 Testbench 运行和管理功能。
    """
    
    def __init__(self, simulation_manager: SimulationManager):
        """
        初始化 Testbench 运行器
        
        Args:
            simulation_manager: SimulationManager 实例
        """
        self.sim_manager = simulation_manager
    
    async def setup_testbench(self, config: TestbenchConfig) -> dict:
        """
        设置 Testbench
        
        Args:
            config: Testbench 配置
            
        Returns:
            设置结果字典
        """
        results = {
            'success': True,
            'config': config,
            'errors': [],
            'warnings': [],
        }
        
        # 添加源文件
        if config.source_files:
            files = [str(f) for f in config.source_files]
            add_result = await self.sim_manager.add_simulation_files(files)
            if not add_result['success']:
                results['success'] = False
                results['errors'].extend(add_result['errors'])
            results['warnings'].extend(add_result.get('warnings', []))
        
        # 设置顶层模块
        set_top_result = await self.sim_manager.set_simulation_top(config.name)
        if not set_top_result['success']:
            results['success'] = False
            results['errors'].extend(set_top_result['errors'])
        results['warnings'].extend(set_top_result.get('warnings', []))
        
        return results
    
    async def run_testbench(
        self,
        config: TestbenchConfig,
        simulation_time: str = "1ms",
        log_wave: bool = True
    ) -> SimulationResult:
        """
        运行 Testbench
        
        Args:
            config: Testbench 配置
            simulation_time: 仿真时间
            log_wave: 是否记录波形
            
        Returns:
            SimulationResult 仿真结果
        """
        # 设置 Testbench
        setup_result = await self.setup_testbench(config)
        if not setup_result['success']:
            return SimulationResult(
                success=False,
                status=SimulationStatus.FAILED,
                message=f"Testbench 设置失败: {setup_result['errors']}"
            )
        
        # 创建仿真配置
        sim_config = SimulationConfig(
            name=config.name,
            top_module=config.name,
            simulation_time=simulation_time,
        )
        
        # 运行仿真
        return await self.sim_manager.run_full_simulation(
            sim_config,
            log_wave=log_wave
        )
    
    async def run_test_cases(
        self,
        config: TestbenchConfig,
        test_cases: list[str] | None = None
    ) -> dict[str, SimulationResult]:
        """
        运行多个测试用例
        
        Args:
            config: Testbench 配置
            test_cases: 测试用例列表，None 使用配置中的用例
            
        Returns:
            测试用例名称到结果的映射
        """
        cases = test_cases or config.test_cases
        results = {}
        
        for test_case in cases:
            # 设置测试用例定义
            await self.sim_manager.set_vlog_define('TEST_CASE', test_case)
            
            # 运行测试
            result = await self.run_testbench(config)
            results[test_case] = result
            
            logger.info(f"测试用例 {test_case}: {'通过' if result.success else '失败'}")
        
        return results
