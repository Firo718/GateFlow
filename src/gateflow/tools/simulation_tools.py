"""
仿真 MCP 工具。

提供 Vivado 仿真相关的 MCP 工具接口。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.vivado.simulation import (
    SimulationConfig,
    SimulationManager,
    SimulationMode,
    SimulatorType,
)
from gateflow.vivado.tcl_engine import TclEngine

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None
_simulation_manager: SimulationManager | None = None


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if _engine is None:
        _engine = TclEngine()
    return _engine


def _get_simulation_manager() -> SimulationManager:
    """获取或创建仿真管理器实例。"""
    global _simulation_manager
    if _simulation_manager is None:
        _simulation_manager = SimulationManager(_get_engine())
    return _simulation_manager


def _parse_simulator(simulator: str) -> SimulatorType:
    """
    解析仿真器类型字符串。

    Args:
        simulator: 仿真器类型字符串

    Returns:
        SimulatorType 枚举值

    Raises:
        ValueError: 无效的仿真器类型
    """
    simulator_map = {
        "vivado": SimulatorType.VIVADO,
        "modelsim": SimulatorType.MODELSIM,
        "questasim": SimulatorType.QUESTASIM,
        "xcelium": SimulatorType.XCELIUM,
        "vcs": SimulatorType.VCS,
    }
    simulator_lower = simulator.lower()
    if simulator_lower not in simulator_map:
        raise ValueError(
            f"无效的仿真器类型: {simulator}。支持的类型: {', '.join(simulator_map.keys())}"
        )
    return simulator_map[simulator_lower]


def _parse_simulation_mode(mode: str) -> SimulationMode:
    """
    解析仿真模式字符串。

    Args:
        mode: 仿真模式字符串

    Returns:
        SimulationMode 枚举值

    Raises:
        ValueError: 无效的仿真模式
    """
    mode_map = {
        "behavioral": SimulationMode.BEHAVIORAL,
        "post_synth": SimulationMode.POST_SYNTHESIS,
        "post_impl": SimulationMode.POST_IMPLEMENTATION,
    }
    mode_lower = mode.lower()
    if mode_lower not in mode_map:
        raise ValueError(
            f"无效的仿真模式: {mode}。支持的模式: {', '.join(mode_map.keys())}"
        )
    return mode_map[mode_lower]


# ============================================================================
# 结果模型定义
# ============================================================================


class SetSimulatorResult(BaseModel):
    """设置仿真器结果模型。"""

    success: bool = Field(description="操作是否成功")
    simulator: str | None = Field(default=None, description="仿真器类型")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class CreateSimSetResult(BaseModel):
    """创建仿真集结果模型。"""

    success: bool = Field(description="操作是否成功")
    name: str | None = Field(default=None, description="仿真集名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class AddSimFilesResult(BaseModel):
    """添加仿真文件结果模型。"""

    success: bool = Field(description="操作是否成功")
    files_added: int = Field(default=0, description="成功添加的文件数量")
    sim_set: str | None = Field(default=None, description="仿真集名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class SetSimTopResult(BaseModel):
    """设置仿真顶层模块结果模型。"""

    success: bool = Field(description="操作是否成功")
    top_module: str | None = Field(default=None, description="顶层模块名称")
    sim_set: str | None = Field(default=None, description="仿真集名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class LaunchSimulationResult(BaseModel):
    """启动仿真结果模型。"""

    success: bool = Field(description="操作是否成功")
    mode: str | None = Field(default=None, description="仿真模式")
    run_time: str | None = Field(default=None, description="仿真运行时间")
    gui: bool = Field(default=False, description="是否以 GUI 模式运行")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class RunSimulationResult(BaseModel):
    """运行仿真结果模型。"""

    success: bool = Field(description="操作是否成功")
    time: str | None = Field(default=None, description="仿真运行时间")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class StopSimulationResult(BaseModel):
    """停止仿真结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class RestartSimulationResult(BaseModel):
    """重启仿真结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class AddWaveResult(BaseModel):
    """添加波形信号结果模型。"""

    success: bool = Field(description="操作是否成功")
    signal: str | None = Field(default=None, description="信号路径")
    radix: str | None = Field(default=None, description="显示进制")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class GetSimStatusResult(BaseModel):
    """获取仿真状态结果模型。"""

    success: bool = Field(description="操作是否成功")
    running: bool = Field(default=False, description="仿真是否正在运行")
    status: str | None = Field(default=None, description="仿真状态")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ExportSimulationResult(BaseModel):
    """导出仿真脚本结果模型。"""

    success: bool = Field(description="操作是否成功")
    output_dir: str | None = Field(default=None, description="输出目录")
    simulator: str | None = Field(default=None, description="目标仿真器")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class SimulationSetsResult(BaseModel):
    """仿真集列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    simulation_sets: list[dict[str, Any]] = Field(default_factory=list, description="仿真集列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class SimulationConfigResult(BaseModel):
    """仿真配置类操作结果。"""

    success: bool = Field(description="操作是否成功")
    sim_set: str | None = Field(default=None, description="仿真集名称")
    value: str | None = Field(default=None, description="配置值")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class SignalValueResult(BaseModel):
    """仿真信号值结果。"""

    success: bool = Field(description="操作是否成功")
    signal: str | None = Field(default=None, description="信号路径")
    value: str | None = Field(default=None, description="信号值")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ForceSignalResult(BaseModel):
    """仿真激励结果。"""

    success: bool = Field(description="操作是否成功")
    signal: str | None = Field(default=None, description="信号路径")
    value: str | None = Field(default=None, description="激励值")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


# ============================================================================
# 工具注册函数
# ============================================================================


def register_simulation_tools(mcp: FastMCP) -> None:
    """
    注册仿真相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def set_simulator(simulator: str) -> SetSimulatorResult:
        """
        设置仿真器。

        此工具用于设置 Vivado 项目使用的仿真器类型。支持多种主流仿真器，
        包括 Vivado 内置仿真器、ModelSim、QuestaSim、Xcelium 和 VCS。

        Args:
            simulator: 仿真器类型，可选值:
                - "vivado": Vivado 内置仿真器 (默认)
                - "modelsim": ModelSim 仿真器
                - "questasim": QuestaSim 仿真器
                - "xcelium": Xcelium 仿真器
                - "vcs": VCS 仿真器

        Returns:
            SetSimulatorResult 包含设置结果。

        Example:
            设置 ModelSim 为仿真器:
            ```
            result = set_simulator(simulator="modelsim")
            if result.success:
                print(f"仿真器已设置为: {result.simulator}")
            ```
        """
        logger.info(f"设置仿真器: simulator={simulator}")

        try:
            simulator_type = _parse_simulator(simulator)
            manager = _get_simulation_manager()
            result = await manager.set_simulator(simulator_type)

            return SetSimulatorResult(
                success=result.get("success", False),
                simulator=result.get("simulator"),
                message="仿真器设置成功" if result.get("success") else "仿真器设置失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except ValueError as e:
            logger.error(f"设置仿真器失败: {e}")
            return SetSimulatorResult(
                success=False,
                simulator=None,
                message="仿真器设置失败",
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"设置仿真器异常: {e}")
            return SetSimulatorResult(
                success=False,
                simulator=None,
                message="仿真器设置失败",
                error=str(e),
            )

    @mcp.tool()
    async def create_simulation_set(
        name: str,
        sources: list[str],
    ) -> CreateSimSetResult:
        """
        创建仿真集。

        此工具用于创建一个新的仿真集，并添加指定的仿真源文件。
        仿真集是 Vivado 中管理仿真文件和配置的容器。

        Args:
            name: 仿真集名称，如 "sim_1"、"tb_set" 等。
            sources: 仿真源文件列表，支持 Testbench 文件、
                仿真辅助文件等。支持绝对路径和相对路径。

        Returns:
            CreateSimSetResult 包含创建结果。

        Example:
            创建仿真集:
            ```
            result = create_simulation_set(
                name="tb_uart",
                sources=[
                    "/project/sim/tb_uart.v",
                    "/project/sim/uart_test_helper.v"
                ]
            )
            if result.success:
                print(f"仿真集已创建: {result.name}")
            ```
        """
        logger.info(f"创建仿真集: name={name}, sources={sources}")

        try:
            manager = _get_simulation_manager()
            result = await manager.create_simulation_set(name, sources)

            return CreateSimSetResult(
                success=result.get("success", False),
                name=result.get("name"),
                message="仿真集创建成功" if result.get("success") else "仿真集创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"创建仿真集异常: {e}")
            return CreateSimSetResult(
                success=False,
                name=None,
                message="仿真集创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def add_simulation_files(
        files: list[str],
        sim_set: str = "sim_1",
    ) -> AddSimFilesResult:
        """
        添加仿真文件。

        此工具将指定的仿真文件添加到现有的仿真集中。
        通常用于添加 Testbench 文件、仿真模型等。

        Args:
            files: 文件路径列表，支持 Verilog (.v)、VHDL (.vhd)、
                SystemVerilog (.sv) 等仿真源文件。
            sim_set: 仿真集名称，默认为 "sim_1"。

        Returns:
            AddSimFilesResult 包含添加结果和文件数量。

        Example:
            添加仿真文件:
            ```
            result = add_simulation_files(
                files=[
                    "/project/sim/tb_top.v",
                    "/project/sim/test_tasks.v"
                ],
                sim_set="sim_1"
            )
            if result.success:
                print(f"已添加 {result.files_added} 个文件")
            ```
        """
        logger.info(f"添加仿真文件: files={files}, sim_set={sim_set}")

        try:
            manager = _get_simulation_manager()
            result = await manager.add_simulation_files(files, sim_set)

            return AddSimFilesResult(
                success=result.get("success", False),
                files_added=result.get("files_added", 0),
                sim_set=result.get("sim_set"),
                message=f"成功添加 {result.get('files_added', 0)} 个仿真文件"
                if result.get("success")
                else "添加仿真文件失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"添加仿真文件异常: {e}")
            return AddSimFilesResult(
                success=False,
                files_added=0,
                sim_set=sim_set,
                message="添加仿真文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_simulation_top(
        module: str,
        sim_set: str = "sim_1",
    ) -> SetSimTopResult:
        """
        设置仿真顶层模块。

        此工具将指定的模块设置为仿真的顶层模块。
        顶层模块通常是 Testbench 模块，是仿真运行的入口点。

        Args:
            module: 顶层模块名称，必须与 Testbench 文件中定义的模块名一致。
            sim_set: 仿真集名称，默认为 "sim_1"。

        Returns:
            SetSimTopResult 包含设置结果。

        Example:
            设置仿真顶层模块:
            ```
            result = set_simulation_top(
                module="tb_uart",
                sim_set="sim_1"
            )
            if result.success:
                print(f"仿真顶层已设置为: {result.top_module}")
            ```
        """
        logger.info(f"设置仿真顶层模块: module={module}, sim_set={sim_set}")

        try:
            manager = _get_simulation_manager()
            result = await manager.set_simulation_top(module, sim_set)

            return SetSimTopResult(
                success=result.get("success", False),
                top_module=result.get("top_module"),
                sim_set=result.get("sim_set"),
                message=f"仿真顶层模块已设置为: {module}"
                if result.get("success")
                else "设置仿真顶层模块失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"设置仿真顶层模块异常: {e}")
            return SetSimTopResult(
                success=False,
                top_module=None,
                sim_set=sim_set,
                message="设置仿真顶层模块失败",
                error=str(e),
            )

    @mcp.tool()
    async def launch_simulation(
        mode: str = "behavioral",
        run_time: str = "100us",
        gui: bool = False,
    ) -> LaunchSimulationResult:
        """
        启动仿真。

        此工具启动 Vivado 仿真器运行仿真。支持三种仿真模式：
        行为仿真、综合后仿真和实现后仿真。

        Args:
            mode: 仿真模式，可选值:
                - "behavioral": 行为仿真 (默认)，对 RTL 代码进行仿真
                - "post_synth": 综合后仿真，对综合后的网表进行仿真
                - "post_impl": 实现后仿真，对布局布线后的网表进行仿真，
                    包含最准确的时序信息
            run_time: 仿真运行时间，如 "100us"、"1ms"、"10ms" 等。
                默认为 "100us"。
            gui: 是否以 GUI 模式运行。True 表示打开仿真波形窗口，
                False 表示在后台运行。默认为 False。

        Returns:
            LaunchSimulationResult 包含启动结果。

        Example:
            启动行为仿真:
            ```
            result = launch_simulation(
                mode="behavioral",
                run_time="1ms",
                gui=False
            )
            if result.success:
                print("仿真已启动")
            ```

            启动 GUI 模式仿真:
            ```
            result = launch_simulation(
                mode="behavioral",
                run_time="all",
                gui=True
            )
            ```
        """
        logger.info(
            f"启动仿真: mode={mode}, run_time={run_time}, gui={gui}"
        )

        try:
            mode_type = _parse_simulation_mode(mode)
            manager = _get_simulation_manager()

            # 创建仿真配置
            config = SimulationConfig(
                name="sim_1",
                mode=mode_type,
                simulation_time=run_time,
                run_mode="gui" if gui else "default",
            )

            result = await manager.launch_simulation(config)

            return LaunchSimulationResult(
                success=result.get("success", False),
                mode=mode,
                run_time=run_time,
                gui=gui,
                message="仿真启动成功" if result.get("success") else "仿真启动失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except ValueError as e:
            logger.error(f"启动仿真失败: {e}")
            return LaunchSimulationResult(
                success=False,
                mode=mode,
                run_time=run_time,
                gui=gui,
                message="仿真启动失败",
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"启动仿真异常: {e}")
            return LaunchSimulationResult(
                success=False,
                mode=mode,
                run_time=run_time,
                gui=gui,
                message="仿真启动失败",
                error=str(e),
            )

    @mcp.tool()
    async def run_simulation(time: str = "all") -> RunSimulationResult:
        """
        运行仿真。

        此工具在已启动的仿真中继续运行指定的时间。
        通常用于在 GUI 模式下控制仿真运行。

        Args:
            time: 运行时间，可选值:
                - "all": 运行直到仿真结束 (默认)
                - 具体时间: 如 "100us"、"1ms"、"10ns" 等

        Returns:
            RunSimulationResult 包含运行结果。

        Example:
            运行仿真指定时间:
            ```
            result = run_simulation(time="100us")
            if result.success:
                print(f"仿真已运行: {result.time}")
            ```

            运行完整仿真:
            ```
            result = run_simulation(time="all")
            ```
        """
        logger.info(f"运行仿真: time={time}")

        try:
            manager = _get_simulation_manager()
            result = await manager.run_simulation(time)

            return RunSimulationResult(
                success=result.get("success", False),
                time=result.get("time"),
                message=f"仿真运行完成: {time}" if result.get("success") else "仿真运行失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"运行仿真异常: {e}")
            return RunSimulationResult(
                success=False,
                time=time,
                message="仿真运行失败",
                error=str(e),
            )

    @mcp.tool()
    async def stop_simulation() -> StopSimulationResult:
        """
        停止仿真。

        此工具停止当前正在运行的仿真。仿真将被暂停，
        但不会关闭仿真器，可以稍后继续运行或重启。

        Returns:
            StopSimulationResult 包含停止结果。

        Example:
            停止仿真:
            ```
            result = stop_simulation()
            if result.success:
                print("仿真已停止")
            ```
        """
        logger.info("停止仿真")

        try:
            manager = _get_simulation_manager()
            result = await manager.stop_simulation()

            return StopSimulationResult(
                success=result.get("success", False),
                message="仿真已停止" if result.get("success") else "停止仿真失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"停止仿真异常: {e}")
            return StopSimulationResult(
                success=False,
                message="停止仿真失败",
                error=str(e),
            )

    @mcp.tool()
    async def restart_simulation() -> RestartSimulationResult:
        """
        重启仿真。

        此工具重启当前仿真，将仿真时间重置为 0。
        所有信号将恢复到初始状态，可以重新开始仿真。

        Returns:
            RestartSimulationResult 包含重启结果。

        Example:
            重启仿真:
            ```
            result = restart_simulation()
            if result.success:
                print("仿真已重启")
            ```
        """
        logger.info("重启仿真")

        try:
            manager = _get_simulation_manager()
            result = await manager.restart_simulation()

            return RestartSimulationResult(
                success=result.get("success", False),
                message="仿真已重启" if result.get("success") else "重启仿真失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"重启仿真异常: {e}")
            return RestartSimulationResult(
                success=False,
                message="重启仿真失败",
                error=str(e),
            )

    @mcp.tool()
    async def add_wave_signal(
        signal: str,
        radix: str = "binary",
    ) -> AddWaveResult:
        """
        添加波形信号。

        此工具将指定的信号添加到波形窗口中，用于观察信号变化。
        可以设置信号的显示进制格式。

        Args:
            signal: 信号路径，格式为 "模块名/信号名" 或层次化路径，
                如 "tb_uart/clk"、"tb_uart/dut/tx_data"。
            radix: 显示进制，可选值:
                - "binary": 二进制显示 (默认)
                - "hex": 十六进制显示
                - "decimal": 有符号十进制显示
                - "unsigned": 无符号十进制显示
                - "ascii": ASCII 字符显示

        Returns:
            AddWaveResult 包含添加结果。

        Example:
            添加信号到波形窗口:
            ```
            result = add_wave_signal(
                signal="tb_uart/clk",
                radix="binary"
            )
            if result.success:
                print(f"信号已添加: {result.signal}")
            ```

            添加十六进制显示的数据信号:
            ```
            result = add_wave_signal(
                signal="tb_uart/dut/data_bus",
                radix="hex"
            )
            ```
        """
        logger.info(f"添加波形信号: signal={signal}, radix={radix}")

        try:
            manager = _get_simulation_manager()
            result = await manager.add_wave(signal, radix)

            return AddWaveResult(
                success=result.get("success", False),
                signal=result.get("signal"),
                radix=result.get("radix"),
                message=f"信号已添加到波形窗口: {signal}"
                if result.get("success")
                else "添加波形信号失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"添加波形信号异常: {e}")
            return AddWaveResult(
                success=False,
                signal=signal,
                radix=radix,
                message="添加波形信号失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_simulation_status() -> GetSimStatusResult:
        """
        获取仿真状态。

        此工具返回当前仿真的运行状态，包括是否正在运行、
        当前状态等信息。用于监控仿真进度。

        Returns:
            GetSimStatusResult 包含仿真状态信息。

        Example:
            获取仿真状态:
            ```
            result = get_simulation_status()
            if result.success:
                if result.running:
                    print(f"仿真正在运行，状态: {result.status}")
                else:
                    print("仿真未运行")
            ```
        """
        logger.info("获取仿真状态")

        try:
            manager = _get_simulation_manager()
            result = await manager.get_simulation_status()

            return GetSimStatusResult(
                success=True,
                running=result.get("running", False),
                status=result.get("status"),
                message="获取仿真状态成功",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"获取仿真状态异常: {e}")
            return GetSimStatusResult(
                success=False,
                running=False,
                status=None,
                message="获取仿真状态失败",
                error=str(e),
            )

    @mcp.tool()
    async def export_simulation(
        output_dir: str,
        simulator: str = "modelsim",
    ) -> ExportSimulationResult:
        """
        导出仿真脚本。

        此工具将当前仿真配置导出为第三方仿真器可用的脚本文件。
        便于在 Vivado 之外使用 ModelSim、QuestaSim 等仿真器运行仿真。

        Args:
            output_dir: 输出目录路径，导出的脚本和文件将保存在此目录。
            simulator: 目标仿真器，可选值:
                - "modelsim": ModelSim 仿真器 (默认)
                - "questasim": QuestaSim 仿真器
                - "xcelium": Xcelium 仿真器
                - "vcs": VCS 仿真器

        Returns:
            ExportSimulationResult 包含导出结果。

        Example:
            导出 ModelSim 仿真脚本:
            ```
            result = export_simulation(
                output_dir="/project/sim/export",
                simulator="modelsim"
            )
            if result.success:
                print(f"仿真脚本已导出到: {result.output_dir}")
            ```

            导出 Xcelium 仿真脚本:
            ```
            result = export_simulation(
                output_dir="/project/sim/xcelium",
                simulator="xcelium"
            )
            ```
        """
        logger.info(f"导出仿真脚本: output_dir={output_dir}, simulator={simulator}")

        try:
            simulator_type = _parse_simulator(simulator)
            manager = _get_simulation_manager()
            result = await manager.export_simulation(output_dir, simulator_type)

            return ExportSimulationResult(
                success=result.get("success", False),
                output_dir=result.get("output_dir"),
                simulator=result.get("simulator"),
                message=f"仿真脚本已导出到: {output_dir}"
                if result.get("success")
                else "导出仿真脚本失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except ValueError as e:
            logger.error(f"导出仿真脚本失败: {e}")
            return ExportSimulationResult(
                success=False,
                output_dir=output_dir,
                simulator=simulator,
                message="导出仿真脚本失败",
                error=str(e),
            )

    @mcp.tool()
    async def list_simulation_sets() -> SimulationSetsResult:
        """列出工程中所有仿真集。"""
        logger.info("列出仿真集")
        try:
            manager = _get_simulation_manager()
            sim_sets = await manager.get_simulation_sets()
            return SimulationSetsResult(
                success=True,
                simulation_sets=sim_sets,
                message=f"找到 {len(sim_sets)} 个仿真集",
                error=None,
            )
        except Exception as e:
            logger.exception(f"列出仿真集异常: {e}")
            return SimulationSetsResult(
                success=False,
                simulation_sets=[],
                message="列出仿真集失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_simulation_time(
        time: str,
        sim_set: str = "sim_1",
    ) -> SimulationConfigResult:
        """设置仿真集的默认运行时间。"""
        logger.info(f"设置仿真时间: time={time}, sim_set={sim_set}")
        try:
            manager = _get_simulation_manager()
            result = await manager.set_simulation_time(time, sim_set)
            return SimulationConfigResult(
                success=result.get("success", False),
                sim_set=result.get("sim_set"),
                value=time,
                message="仿真时间设置成功" if result.get("success") else "仿真时间设置失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"设置仿真时间异常: {e}")
            return SimulationConfigResult(
                success=False,
                sim_set=sim_set,
                value=time,
                message="仿真时间设置失败",
                error=str(e),
            )

    @mcp.tool()
    async def compile_simulation(
        sim_set: str = "sim_1",
    ) -> SimulationConfigResult:
        """编译指定仿真集。"""
        logger.info(f"编译仿真集: {sim_set}")
        try:
            manager = _get_simulation_manager()
            result = await manager.compile_simulation(sim_set)
            return SimulationConfigResult(
                success=result.get("success", False),
                sim_set=result.get("sim_set"),
                value="compiled" if result.get("success") else None,
                message="仿真编译成功" if result.get("success") else "仿真编译失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"编译仿真异常: {e}")
            return SimulationConfigResult(
                success=False,
                sim_set=sim_set,
                value=None,
                message="仿真编译失败",
                error=str(e),
            )

    @mcp.tool()
    async def elaborate_simulation(
        sim_set: str = "sim_1",
    ) -> SimulationConfigResult:
        """对指定仿真集执行 elaboration。"""
        logger.info(f"详细化仿真集: {sim_set}")
        try:
            manager = _get_simulation_manager()
            result = await manager.elaborate_simulation(sim_set)
            return SimulationConfigResult(
                success=result.get("success", False),
                sim_set=result.get("sim_set"),
                value="elaborated" if result.get("success") else None,
                message="仿真详细化成功" if result.get("success") else "仿真详细化失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"详细化仿真异常: {e}")
            return SimulationConfigResult(
                success=False,
                sim_set=sim_set,
                value=None,
                message="仿真详细化失败",
                error=str(e),
            )

    @mcp.tool()
    async def log_wave(depth: int = 0) -> SimulationConfigResult:
        """启用波形记录。"""
        logger.info(f"设置波形记录: depth={depth}")
        try:
            manager = _get_simulation_manager()
            result = await manager.log_wave(depth)
            return SimulationConfigResult(
                success=result.get("success", False),
                sim_set="sim_1",
                value=str(depth),
                message="波形记录已启用" if result.get("success") else "波形记录启用失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"设置波形记录异常: {e}")
            return SimulationConfigResult(
                success=False,
                sim_set="sim_1",
                value=str(depth),
                message="波形记录启用失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_signal_value(signal: str) -> SignalValueResult:
        """读取仿真中指定信号的当前值。"""
        logger.info(f"获取信号值: signal={signal}")
        try:
            manager = _get_simulation_manager()
            result = await manager.get_signal_value(signal)
            return SignalValueResult(
                success=result.get("success", False),
                signal=result.get("signal"),
                value=result.get("value"),
                message="获取信号值成功" if result.get("success") else "获取信号值失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"获取信号值异常: {e}")
            return SignalValueResult(
                success=False,
                signal=signal,
                value=None,
                message="获取信号值失败",
                error=str(e),
            )

    @mcp.tool()
    async def add_force_signal(
        signal: str,
        value: str,
        repeat: str | None = None,
        after: str | None = None,
    ) -> ForceSignalResult:
        """给仿真信号施加激励。"""
        logger.info(
            f"添加仿真激励: signal={signal}, value={value}, repeat={repeat}, after={after}"
        )
        try:
            manager = _get_simulation_manager()
            result = await manager.add_force(signal, value, repeat=repeat, after=after)
            return ForceSignalResult(
                success=result.get("success", False),
                signal=result.get("signal"),
                value=result.get("value"),
                message="仿真激励添加成功" if result.get("success") else "仿真激励添加失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"添加仿真激励异常: {e}")
            return ForceSignalResult(
                success=False,
                signal=signal,
                value=value,
                message="仿真激励添加失败",
                error=str(e),
            )

    @mcp.tool()
    async def remove_force_signal(signal: str) -> ForceSignalResult:
        """移除仿真信号上的激励。"""
        logger.info(f"移除仿真激励: signal={signal}")
        try:
            manager = _get_simulation_manager()
            result = await manager.remove_force(signal)
            return ForceSignalResult(
                success=result.get("success", False),
                signal=result.get("signal"),
                value=None,
                message="仿真激励已移除" if result.get("success") else "移除仿真激励失败",
                error=result.get("errors")[0] if result.get("errors") else None,
            )
        except Exception as e:
            logger.exception(f"移除仿真激励异常: {e}")
            return ForceSignalResult(
                success=False,
                signal=signal,
                value=None,
                message="移除仿真激励失败",
                error=str(e),
            )

    @mcp.tool()
    async def probe_signal(signal: str, radix: str = "binary") -> AddWaveResult:
        """将信号加入波形窗口，作为仿真 probe 入口。"""
        return await add_wave_signal(signal=signal, radix=radix)
