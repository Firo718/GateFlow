"""
约束管理 MCP 工具。

提供 Vivado 时序约束相关的 MCP 工具接口。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.tools.context_utils import AsyncContextBlockedProxy, project_context_error_message
from gateflow.tools.result_utils import clean_artifacts
from gateflow.vivado.tcl_engine import TclEngine

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None
_constraints: list[dict[str, Any]] = []  # 存储已创建的约束


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if project_context_error_message("constraint"):
        return AsyncContextBlockedProxy("constraint")  # type: ignore[return-value]
    if _engine is None:
        _engine = TclEngine()
    return _engine


# ==================== 结果模型 ====================


class CreateClockResult(BaseModel):
    """创建时钟约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    clock_name: str | None = Field(default=None, description="时钟名称")
    period: float | None = Field(default=None, description="时钟周期 (ns)")
    target: str | None = Field(default=None, description="目标端口或引脚")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GeneratedClockResult(BaseModel):
    """派生时钟约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    clock_name: str | None = Field(default=None, description="派生时钟名称")
    source: str | None = Field(default=None, description="源时钟引脚")
    master_clock: str | None = Field(default=None, description="主时钟名称")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class InputDelayResult(BaseModel):
    """输入延迟约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    clock: str | None = Field(default=None, description="参考时钟")
    delay: float | None = Field(default=None, description="延迟值 (ns)")
    ports: list[str] = Field(default_factory=list, description="目标端口列表")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class OutputDelayResult(BaseModel):
    """输出延迟约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    clock: str | None = Field(default=None, description="参考时钟")
    delay: float | None = Field(default=None, description="延迟值 (ns)")
    ports: list[str] = Field(default_factory=list, description="目标端口列表")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class FalsePathResult(BaseModel):
    """虚假路径约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    from_pins: list[str] = Field(default_factory=list, description="起始引脚列表")
    to_pins: list[str] = Field(default_factory=list, description="目标引脚列表")
    through: list[str] = Field(default_factory=list, description="经过引脚列表")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class MulticyclePathResult(BaseModel):
    """多周期路径约束结果模型。"""

    success: bool = Field(description="操作是否成功")
    cycles: int | None = Field(default=None, description="周期数")
    from_pins: list[str] = Field(default_factory=list, description="起始引脚列表")
    to_pins: list[str] = Field(default_factory=list, description="目标引脚列表")
    setup: bool = Field(default=True, description="是否为 Setup 约束")
    tcl_command: str | None = Field(default=None, description="生成的 Tcl 命令")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GetClocksResult(BaseModel):
    """获取时钟列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    clocks: list[dict[str, Any]] = Field(default_factory=list, description="时钟约束列表")
    count: int = Field(default=0, description="时钟数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ReadXdcResult(BaseModel):
    """读取 XDC 文件结果模型。"""

    success: bool = Field(description="操作是否成功")
    path: str | None = Field(default=None, description="文件路径")
    constraints: list[str] = Field(default_factory=list, description="读取的约束列表")
    constraint_count: int = Field(default=0, description="约束数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class WriteXdcResult(BaseModel):
    """写入 XDC 文件结果模型。"""

    success: bool = Field(description="操作是否成功")
    path: str | None = Field(default=None, description="文件路径")
    constraint_count: int = Field(default=0, description="写入的约束数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


# ==================== 工具注册 ====================


def register_constraint_tools(mcp: FastMCP) -> None:
    """
    注册约束管理相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def create_clock(
        name: str,
        period: float,
        target: str | None = None,
        waveform: list[float] | None = None,
    ) -> CreateClockResult:
        """
        创建时钟约束。

        此工具用于创建主时钟约束，定义设计中的时钟信号特性。
        时钟约束是时序分析的基础，必须在综合前设置。

        Args:
            name: 时钟名称，用于标识时钟信号。
            period: 时钟周期，单位为纳秒 (ns)。例如 100MHz 时钟周期为 10ns。
            target: 目标端口或引脚，指定时钟信号输入位置。
                   可以是端口名、引脚名或通配符模式。
            waveform: 波形定义 [上升沿, 下降沿]，单位为 ns。
                     默认为 [0, period/2]，即 50% 占空比。
                     例如 [0, 5] 表示 0ns 上升，5ns 下降。

        Returns:
            CreateClockResult 包含创建结果和生成的 Tcl 命令。

        Example:
            创建 100MHz 时钟:
            ```
            create_clock(
                name="clk",
                period=10.0,
                target="clk"
            )
            ```

            创建自定义占空比时钟:
            ```
            create_clock(
                name="clk_100mhz",
                period=10.0,
                target="[get_ports clk]",
                waveform=[0, 3]
            )
            ```
        """
        logger.info(f"创建时钟约束: name={name}, period={period}, target={target}")

        try:
            # 构建 Tcl 命令
            tcl_cmd = f"create_clock -name {name} -period {period}"

            if target:
                # 如果 target 不包含 get_ports/get_pins，自动添加
                if not target.startswith("[get_"):
                    tcl_cmd += f" [get_ports {target}]"
                else:
                    tcl_cmd += f" {target}"

            if waveform and len(waveform) >= 2:
                tcl_cmd += f" -waveform {{{waveform[0]} {waveform[1]}}}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "create_clock",
                "name": name,
                "period": period,
                "target": target,
                "waveform": waveform,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return CreateClockResult(
                success=result.get("success", False),
                clock_name=name,
                period=period,
                target=target,
                tcl_command=tcl_cmd,
                message=result.get("message", f"时钟约束 '{name}' 创建成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"clock_name": name, "target": target}),
            )

        except Exception as e:
            logger.error(f"创建时钟约束失败: {e}")
            return CreateClockResult(
                success=False,
                clock_name=name,
                period=period,
                target=target,
                message="创建时钟约束失败",
                error=str(e),
            )

    @mcp.tool()
    async def create_generated_clock(
        name: str,
        source: str,
        master_clock: str,
        divide_by: int | None = None,
        multiply_by: int | None = None,
    ) -> GeneratedClockResult:
        """
        创建派生时钟约束。

        此工具用于创建派生时钟（Generated Clock），派生时钟是从主时钟
        通过分频、倍频或相位变换得到的时钟信号。

        Args:
            name: 派生时钟名称，用于标识该时钟。
            source: 源时钟引脚，指定派生时钟的来源。
                   通常是时钟分频器或 PLL 的输出引脚。
            master_clock: 主时钟名称，派生时钟的参考时钟。
            divide_by: 分频系数，可选。例如 divide_by=2 表示 2 分频。
            multiply_by: 倍频系数，可选。例如 multiply_by=2 表示 2 倍频。

        Returns:
            GeneratedClockResult 包含创建结果和生成的 Tcl 命令。

        Example:
            创建 2 分频时钟:
            ```
            create_generated_clock(
                name="clk_div2",
                source="[get_pins div_reg/Q]",
                master_clock="clk",
                divide_by=2
            )
            ```

            创建 2 倍频时钟:
            ```
            create_generated_clock(
                name="clk_x2",
                source="[get_pins pll/clk_out]",
                master_clock="clk_ref",
                multiply_by=2
            )
            ```
        """
        logger.info(
            f"创建派生时钟: name={name}, source={source}, "
            f"master_clock={master_clock}, divide_by={divide_by}, multiply_by={multiply_by}"
        )

        try:
            # 构建 Tcl 命令
            tcl_cmd = f"create_generated_clock -name {name}"

            # 处理 source 参数
            if not source.startswith("[get_"):
                tcl_cmd += f" -source [get_pins {source}]"
            else:
                tcl_cmd += f" -source {source}"

            tcl_cmd += f" -master_clock {master_clock}"

            if divide_by:
                tcl_cmd += f" -divide_by {divide_by}"
            if multiply_by:
                tcl_cmd += f" -multiply_by {multiply_by}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "create_generated_clock",
                "name": name,
                "source": source,
                "master_clock": master_clock,
                "divide_by": divide_by,
                "multiply_by": multiply_by,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return GeneratedClockResult(
                success=result.get("success", False),
                clock_name=name,
                source=source,
                master_clock=master_clock,
                tcl_command=tcl_cmd,
                message=result.get("message", f"派生时钟 '{name}' 创建成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"clock_name": name, "master_clock": master_clock}),
            )

        except Exception as e:
            logger.error(f"创建派生时钟失败: {e}")
            return GeneratedClockResult(
                success=False,
                clock_name=name,
                source=source,
                master_clock=master_clock,
                message="创建派生时钟失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_input_delay(
        clock: str,
        delay: float,
        ports: list[str],
        max_delay: bool = True,
    ) -> InputDelayResult:
        """
        设置输入延迟约束。

        此工具用于设置输入端口的时序约束，定义外部信号相对于时钟的
        到达时间。输入延迟用于建模外部器件到 FPGA 的传输延迟。

        Args:
            clock: 参考时钟名称，输入信号相对于该时钟进行约束。
            delay: 延迟值，单位为纳秒 (ns)。表示外部信号的最大/最小延迟。
            ports: 目标端口列表，要约束的输入端口名称。
            max_delay: 是否为最大延迟约束。True 表示 -max (setup 分析)，
                      False 表示 -min (hold 分析)。默认为 True。

        Returns:
            InputDelayResult 包含设置结果和生成的 Tcl 命令。

        Example:
            设置输入最大延迟:
            ```
            set_input_delay(
                clock="clk",
                delay=2.0,
                ports=["data_in", "valid_in"],
                max_delay=True
            )
            ```

            设置输入最小延迟:
            ```
            set_input_delay(
                clock="clk",
                delay=0.5,
                ports=["data_in"],
                max_delay=False
            )
            ```
        """
        logger.info(
            f"设置输入延迟: clock={clock}, delay={delay}, "
            f"ports={ports}, max_delay={max_delay}"
        )

        try:
            # 构建 Tcl 命令
            delay_type = "-max" if max_delay else "-min"
            ports_str = " ".join([f"[get_ports {p}]" for p in ports])

            tcl_cmd = f"set_input_delay {delay_type} {delay} -clock {clock} {ports_str}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "set_input_delay",
                "clock": clock,
                "delay": delay,
                "ports": ports,
                "max_delay": max_delay,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return InputDelayResult(
                success=result.get("success", False),
                clock=clock,
                delay=delay,
                ports=ports,
                tcl_command=tcl_cmd,
                message=result.get("message", f"输入延迟约束设置成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"clock": clock, "ports": ports}),
            )

        except Exception as e:
            logger.error(f"设置输入延迟失败: {e}")
            return InputDelayResult(
                success=False,
                clock=clock,
                delay=delay,
                ports=ports,
                message="设置输入延迟失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_output_delay(
        clock: str,
        delay: float,
        ports: list[str],
        max_delay: bool = True,
    ) -> OutputDelayResult:
        """
        设置输出延迟约束。

        此工具用于设置输出端口的时序约束，定义 FPGA 输出信号相对于时钟
        需要满足的建立/保持时间。输出延迟用于建模 FPGA 到外部器件的传输延迟。

        Args:
            clock: 参考时钟名称，输出信号相对于该时钟进行约束。
            delay: 延迟值，单位为纳秒 (ns)。表示外部器件要求的建立/保持时间。
            ports: 目标端口列表，要约束的输出端口名称。
            max_delay: 是否为最大延迟约束。True 表示 -max (setup 分析)，
                      False 表示 -min (hold 分析)。默认为 True。

        Returns:
            OutputDelayResult 包含设置结果和生成的 Tcl 命令。

        Example:
            设置输出最大延迟:
            ```
            set_output_delay(
                clock="clk",
                delay=1.5,
                ports=["data_out", "valid_out"],
                max_delay=True
            )
            ```

            设置输出最小延迟:
            ```
            set_output_delay(
                clock="clk",
                delay=0.3,
                ports=["data_out"],
                max_delay=False
            )
            ```
        """
        logger.info(
            f"设置输出延迟: clock={clock}, delay={delay}, "
            f"ports={ports}, max_delay={max_delay}"
        )

        try:
            # 构建 Tcl 命令
            delay_type = "-max" if max_delay else "-min"
            ports_str = " ".join([f"[get_ports {p}]" for p in ports])

            tcl_cmd = f"set_output_delay {delay_type} {delay} -clock {clock} {ports_str}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "set_output_delay",
                "clock": clock,
                "delay": delay,
                "ports": ports,
                "max_delay": max_delay,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return OutputDelayResult(
                success=result.get("success", False),
                clock=clock,
                delay=delay,
                ports=ports,
                tcl_command=tcl_cmd,
                message=result.get("message", f"输出延迟约束设置成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"clock": clock, "ports": ports}),
            )

        except Exception as e:
            logger.error(f"设置输出延迟失败: {e}")
            return OutputDelayResult(
                success=False,
                clock=clock,
                delay=delay,
                ports=ports,
                message="设置输出延迟失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_false_path(
        from_pins: list[str] | None = None,
        to_pins: list[str] | None = None,
        through: list[str] | None = None,
    ) -> FalsePathResult:
        """
        设置虚假路径约束。

        此工具用于标记不需要进行时序分析的路径。虚假路径通常用于:
        - 异步信号跨时钟域
        - 复位信号
        - 测试信号
        - 静态配置信号

        Args:
            from_pins: 起始引脚列表，路径的起点。可选。
            to_pins: 目标引脚列表，路径的终点。可选。
            through: 经过引脚列表，路径必须经过的点。可选。

        Returns:
            FalsePathResult 包含设置结果和生成的 Tcl 命令。

        Example:
            设置从异步复位到所有寄存器的虚假路径:
            ```
            set_false_path(
                from_pins=["rst_async"],
                to_pins=["[get_cells -hierarchical *reg*]"]
            )
            ```

            设置跨时钟域路径为虚假路径:
            ```
            set_false_path(
                from_pins=["[get_clocks clk_a]"],
                to_pins=["[get_clocks clk_b]"]
            )
            ```
        """
        logger.info(
            f"设置虚假路径: from={from_pins}, to={to_pins}, through={through}"
        )

        try:
            # 构建 Tcl 命令
            tcl_cmd = "set_false_path"

            if from_pins:
                from_str = " ".join([f"[get_pins {p}]" if not p.startswith("[") else p for p in from_pins])
                tcl_cmd += f" -from {from_str}"

            if to_pins:
                to_str = " ".join([f"[get_pins {p}]" if not p.startswith("[") else p for p in to_pins])
                tcl_cmd += f" -to {to_str}"

            if through:
                through_str = " ".join([f"[get_pins {p}]" if not p.startswith("[") else p for p in through])
                tcl_cmd += f" -through {through_str}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "set_false_path",
                "from_pins": from_pins,
                "to_pins": to_pins,
                "through": through,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return FalsePathResult(
                success=result.get("success", False),
                from_pins=from_pins or [],
                to_pins=to_pins or [],
                through=through or [],
                tcl_command=tcl_cmd,
                message=result.get("message", "虚假路径约束设置成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"from_pins": from_pins or [], "to_pins": to_pins or []}),
            )

        except Exception as e:
            logger.error(f"设置虚假路径失败: {e}")
            return FalsePathResult(
                success=False,
                from_pins=from_pins or [],
                to_pins=to_pins or [],
                through=through or [],
                message="设置虚假路径失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_multicycle_path(
        cycles: int,
        from_pins: list[str] | None = None,
        to_pins: list[str] | None = None,
        setup: bool = True,
    ) -> MulticyclePathResult:
        """
        设置多周期路径约束。

        此工具用于放宽特定路径的时序约束，允许数据在多个时钟周期内传输。
        多周期路径通常用于:
        - 数据路径需要多个周期处理
        - 使能信号控制的数据传输
        - 低速外设接口

        Args:
            cycles: 周期数，表示允许的时钟周期数。
                   例如 cycles=2 表示允许 2 个时钟周期。
            from_pins: 起始引脚列表，路径的起点。可选。
            to_pins: 目标引脚列表，路径的终点。可选。
            setup: 是否为 Setup 约束。True 表示 setup 多周期，
                  False 表示 hold 多周期。默认为 True。

        Returns:
            MulticyclePathResult 包含设置结果和生成的 Tcl 命令。

        Example:
            设置 2 周期 setup 多周期路径:
            ```
            set_multicycle_path(
                cycles=2,
                from_pins=["[get_cells data_reg]"],
                to_pins=["[get_cells result_reg]"],
                setup=True
            )
            ```

            设置对应的 hold 多周期路径:
            ```
            set_multicycle_path(
                cycles=1,
                from_pins=["[get_cells data_reg]"],
                to_pins=["[get_cells result_reg]"],
                setup=False
            )
            ```
        """
        logger.info(
            f"设置多周期路径: cycles={cycles}, from={from_pins}, "
            f"to={to_pins}, setup={setup}"
        )

        try:
            # 构建 Tcl 命令
            setup_type = "-setup" if setup else "-hold"
            tcl_cmd = f"set_multicycle_path {setup_type} {cycles}"

            if from_pins:
                from_str = " ".join([f"[get_pins {p}]" if not p.startswith("[") else p for p in from_pins])
                tcl_cmd += f" -from {from_str}"

            if to_pins:
                to_str = " ".join([f"[get_pins {p}]" if not p.startswith("[") else p for p in to_pins])
                tcl_cmd += f" -to {to_str}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 存储约束信息
            constraint_info = {
                "type": "set_multicycle_path",
                "cycles": cycles,
                "from_pins": from_pins,
                "to_pins": to_pins,
                "setup": setup,
                "tcl_command": tcl_cmd,
            }
            _constraints.append(constraint_info)

            return MulticyclePathResult(
                success=result.get("success", False),
                cycles=cycles,
                from_pins=from_pins or [],
                to_pins=to_pins or [],
                setup=setup,
                tcl_command=tcl_cmd,
                message=result.get("message", f"多周期路径约束设置成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"cycles": cycles, "from_pins": from_pins or [], "to_pins": to_pins or []}),
            )

        except Exception as e:
            logger.error(f"设置多周期路径失败: {e}")
            return MulticyclePathResult(
                success=False,
                cycles=cycles,
                from_pins=from_pins or [],
                to_pins=to_pins or [],
                setup=setup,
                message="设置多周期路径失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_clocks() -> GetClocksResult:
        """
        获取所有时钟约束。

        此工具返回当前设计中定义的所有时钟约束信息，包括:
        - 主时钟 (create_clock)
        - 派生时钟 (create_generated_clock)
        - 虚拟时钟

        时钟信息包括名称、周期、波形等属性。

        Returns:
            GetClocksResult 包含时钟约束列表。

        Example:
            获取所有时钟:
            ```
            result = get_clocks()
            if result.success:
                for clock in result.clocks:
                    print(f"时钟: {clock['name']}, 周期: {clock['period']}ns")
            ```
        """
        logger.info("获取所有时钟约束")

        try:
            # 执行 Tcl 命令获取时钟列表
            engine = _get_engine()
            result = await engine.execute("get_clocks -quiet")

            # 从本地约束存储中获取时钟信息
            clocks = [
                c for c in _constraints
                if c.get("type") in ["create_clock", "create_generated_clock"]
            ]

            return GetClocksResult(
                success=True,
                clocks=clocks,
                count=len(clocks),
                message=f"找到 {len(clocks)} 个时钟约束",
                error=None,
                artifacts={"count": len(clocks)},
            )

        except Exception as e:
            logger.error(f"获取时钟约束失败: {e}")
            return GetClocksResult(
                success=False,
                clocks=[],
                count=0,
                message="获取时钟约束失败",
                error=str(e),
            )

    @mcp.tool()
    async def read_xdc(path: str) -> ReadXdcResult:
        """
        读取 XDC 约束文件。

        此工具读取指定的 XDC 约束文件并应用其中的约束。
        XDC 文件是 Vivado 的标准约束文件格式，包含时序约束、
        引脚约束和物理约束等。

        Args:
            path: XDC 文件路径，可以是绝对路径或相对路径。

        Returns:
            ReadXdcResult 包含读取结果和约束信息。

        Example:
            读取约束文件:
            ```
            result = read_xdc(path="/home/user/project/constraints/timing.xdc")
            if result.success:
                print(f"读取了 {result.constraint_count} 条约束")
            ```
        """
        logger.info(f"读取 XDC 文件: path={path}")

        try:
            # 构建 Tcl 命令
            tcl_cmd = f'read_xdc "{path}"'

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 尝试读取文件内容以获取约束数量
            constraints = []
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # 简单统计非空行和非注释行
                    constraints = [
                        line.strip()
                        for line in content.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ]
            except Exception:
                pass

            return ReadXdcResult(
                success=result.get("success", False),
                path=path,
                constraints=constraints,
                constraint_count=len(constraints),
                message=result.get("message", f"XDC 文件读取成功"),
                error=result.get("error"),
                artifacts=clean_artifacts({"path": path, "constraint_count": len(constraints)}),
            )

        except Exception as e:
            logger.error(f"读取 XDC 文件失败: {e}")
            return ReadXdcResult(
                success=False,
                path=path,
                constraints=[],
                constraint_count=0,
                message="读取 XDC 文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def write_xdc(
        path: str,
        constraints: list[str] | None = None,
    ) -> WriteXdcResult:
        """
        写入 XDC 约束文件。

        此工具将当前约束或指定的约束写入 XDC 文件。
        可用于保存约束设置或导出约束供其他项目使用。

        Args:
            path: XDC 文件路径，可以是绝对路径或相对路径。
            constraints: 要写入的约束列表，可选。
                        如果未提供，将写入所有已创建的约束。

        Returns:
            WriteXdcResult 包含写入结果。

        Example:
            写入所有约束到文件:
            ```
            result = write_xdc(path="/home/user/project/constraints/output.xdc")
            if result.success:
                print(f"写入了 {result.constraint_count} 条约束")
            ```

            写入指定约束:
            ```
            result = write_xdc(
                path="/home/user/project/constraints/custom.xdc",
                constraints=[
                    "create_clock -name clk -period 10",
                    "set_input_delay -max 2 -clock clk [get_ports data_in]"
                ]
            )
            ```
        """
        logger.info(f"写入 XDC 文件: path={path}, constraints={constraints}")

        try:
            # 确定要写入的约束
            if constraints is None:
                # 从本地存储获取所有约束的 Tcl 命令
                constraints = [
                    c.get("tcl_command", "")
                    for c in _constraints
                    if c.get("tcl_command")
                ]

            # 写入文件
            content = "\n".join(constraints)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return WriteXdcResult(
                success=True,
                path=path,
                constraint_count=len(constraints),
                message=f"成功写入 {len(constraints)} 条约束到 {path}",
                error=None,
                artifacts=clean_artifacts({"path": path, "constraint_count": len(constraints)}),
            )

        except Exception as e:
            logger.error(f"写入 XDC 文件失败: {e}")
            return WriteXdcResult(
                success=False,
                path=path,
                constraint_count=0,
                message="写入 XDC 文件失败",
                error=str(e),
            )
