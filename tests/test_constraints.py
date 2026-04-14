"""
约束模块测试。

测试 ConstraintsTclGenerator、ConstraintsManager 和约束数据类。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.vivado.constraints import (
    ConstraintType,
    ClockSense,
    DelayType,
    ClockConstraint,
    GeneratedClockConstraint,
    InputDelayConstraint,
    OutputDelayConstraint,
    FalsePathConstraint,
    MulticycleConstraint,
    MaxDelayConstraint,
    MinDelayConstraint,
    ConstraintInfo,
    ConstraintsTclGenerator,
    ConstraintsManager,
)


# ==================== 枚举测试 ====================


class TestConstraintType:
    """ConstraintType 枚举测试。"""

    def test_constraint_type_values(self):
        """测试约束类型枚举值。"""
        assert ConstraintType.CLOCK.value == "clock"
        assert ConstraintType.INPUT_DELAY.value == "input_delay"
        assert ConstraintType.OUTPUT_DELAY.value == "output_delay"
        assert ConstraintType.FALSE_PATH.value == "false_path"
        assert ConstraintType.MULTICYCLE.value == "multicycle"
        assert ConstraintType.MAX_DELAY.value == "max_delay"
        assert ConstraintType.MIN_DELAY.value == "min_delay"
        assert ConstraintType.CLOCK_GROUP.value == "clock_group"

    def test_constraint_type_count(self):
        """测试约束类型数量。"""
        types = list(ConstraintType)
        assert len(types) == 8


class TestClockSense:
    """ClockSense 枚举测试。"""

    def test_clock_sense_values(self):
        """测试时钟感知类型枚举值。"""
        assert ClockSense.POSITIVE.value == "positive"
        assert ClockSense.NEGATIVE.value == "negative"


class TestDelayType:
    """DelayType 枚举测试。"""

    def test_delay_type_values(self):
        """测试延迟类型枚举值。"""
        assert DelayType.MAX.value == "max"
        assert DelayType.MIN.value == "min"
        assert DelayType.BOTH.value == "both"


# ==================== 数据类测试 ====================


class TestClockConstraint:
    """ClockConstraint 数据类测试。"""

    def test_clock_constraint_required_fields(self):
        """测试时钟约束必需字段。"""
        constraint = ClockConstraint(name="clk", period=10.0)
        
        assert constraint.name == "clk"
        assert constraint.period == 10.0
        assert constraint.waveform is None
        assert constraint.target is None
        assert constraint.add is False

    def test_clock_constraint_full(self):
        """测试时钟约束完整参数。"""
        constraint = ClockConstraint(
            name="clk_100mhz",
            period=10.0,
            waveform=[0.0, 5.0],
            target="clk_port",
            add=True,
        )
        
        assert constraint.name == "clk_100mhz"
        assert constraint.period == 10.0
        assert constraint.waveform == [0.0, 5.0]
        assert constraint.target == "clk_port"
        assert constraint.add is True


class TestGeneratedClockConstraint:
    """GeneratedClockConstraint 数据类测试。"""

    def test_generated_clock_constraint_required_fields(self):
        """测试派生时钟约束必需字段。"""
        constraint = GeneratedClockConstraint(name="clk_div2", source="div_reg/Q")
        
        assert constraint.name == "clk_div2"
        assert constraint.source == "div_reg/Q"
        assert constraint.master_clock is None
        assert constraint.divide_by is None
        assert constraint.multiply_by is None
        assert constraint.invert is False
        assert constraint.target is None

    def test_generated_clock_constraint_full(self):
        """测试派生时钟约束完整参数。"""
        constraint = GeneratedClockConstraint(
            name="clk_div2",
            source="div_reg/Q",
            master_clock="clk",
            divide_by=2,
            multiply_by=None,
            invert=True,
            target="clk_out",
        )
        
        assert constraint.master_clock == "clk"
        assert constraint.divide_by == 2
        assert constraint.invert is True
        assert constraint.target == "clk_out"


class TestInputDelayConstraint:
    """InputDelayConstraint 数据类测试。"""

    def test_input_delay_constraint_required_fields(self):
        """测试输入延迟约束必需字段。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=2.0,
            target="data_in",
        )
        
        assert constraint.clock == "clk"
        assert constraint.delay == 2.0
        assert constraint.target == "data_in"
        assert constraint.delay_type == DelayType.MAX
        assert constraint.clock_fall is False

    def test_input_delay_constraint_full(self):
        """测试输入延迟约束完整参数。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=1.5,
            target="data_in",
            delay_type=DelayType.MIN,
            clock_fall=True,
        )
        
        assert constraint.delay_type == DelayType.MIN
        assert constraint.clock_fall is True


class TestOutputDelayConstraint:
    """OutputDelayConstraint 数据类测试。"""

    def test_output_delay_constraint_required_fields(self):
        """测试输出延迟约束必需字段。"""
        constraint = OutputDelayConstraint(
            clock="clk",
            delay=1.0,
            target="data_out",
        )
        
        assert constraint.clock == "clk"
        assert constraint.delay == 1.0
        assert constraint.target == "data_out"
        assert constraint.delay_type == DelayType.MAX

    def test_output_delay_constraint_full(self):
        """测试输出延迟约束完整参数。"""
        constraint = OutputDelayConstraint(
            clock="clk",
            delay=0.5,
            target="data_out",
            delay_type=DelayType.BOTH,
            clock_fall=True,
        )
        
        assert constraint.delay_type == DelayType.BOTH
        assert constraint.clock_fall is True


class TestFalsePathConstraint:
    """FalsePathConstraint 数据类测试。"""

    def test_false_path_constraint_defaults(self):
        """测试虚假路径约束默认值。"""
        constraint = FalsePathConstraint()
        
        assert constraint.from_pins is None
        assert constraint.to_pins is None
        assert constraint.through is None
        assert constraint.setup is True
        assert constraint.hold is True

    def test_false_path_constraint_full(self):
        """测试虚假路径约束完整参数。"""
        constraint = FalsePathConstraint(
            from_pins="rst_async",
            to_pins="data_reg/D",
            through="sync_reg/Q",
            setup=True,
            hold=False,
        )
        
        assert constraint.from_pins == "rst_async"
        assert constraint.to_pins == "data_reg/D"
        assert constraint.through == "sync_reg/Q"
        assert constraint.hold is False


class TestMulticycleConstraint:
    """MulticycleConstraint 数据类测试。"""

    def test_multicycle_constraint_required_fields(self):
        """测试多周期路径约束必需字段。"""
        constraint = MulticycleConstraint(cycles=2)
        
        assert constraint.cycles == 2
        assert constraint.from_pins is None
        assert constraint.to_pins is None
        assert constraint.setup is True
        assert constraint.hold is False

    def test_multicycle_constraint_full(self):
        """测试多周期路径约束完整参数。"""
        constraint = MulticycleConstraint(
            cycles=3,
            from_pins="data_reg/Q",
            to_pins="result_reg/D",
            setup=True,
            hold=True,
        )
        
        assert constraint.cycles == 3
        assert constraint.from_pins == "data_reg/Q"
        assert constraint.to_pins == "result_reg/D"
        assert constraint.hold is True


class TestMaxDelayConstraint:
    """MaxDelayConstraint 数据类测试。"""

    def test_max_delay_constraint_required_fields(self):
        """测试最大延迟约束必需字段。"""
        constraint = MaxDelayConstraint(delay=5.0)
        
        assert constraint.delay == 5.0
        assert constraint.from_pins is None
        assert constraint.to_pins is None
        assert constraint.datapath_only is False

    def test_max_delay_constraint_full(self):
        """测试最大延迟约束完整参数。"""
        constraint = MaxDelayConstraint(
            delay=3.0,
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
            datapath_only=True,
        )
        
        assert constraint.delay == 3.0
        assert constraint.from_pins == "src_reg/Q"
        assert constraint.to_pins == "dst_reg/D"
        assert constraint.datapath_only is True


class TestMinDelayConstraint:
    """MinDelayConstraint 数据类测试。"""

    def test_min_delay_constraint_required_fields(self):
        """测试最小延迟约束必需字段。"""
        constraint = MinDelayConstraint(delay=1.0)
        
        assert constraint.delay == 1.0
        assert constraint.from_pins is None
        assert constraint.to_pins is None
        assert constraint.datapath_only is False


class TestConstraintInfo:
    """ConstraintInfo 数据类测试。"""

    def test_constraint_info_required_fields(self):
        """测试约束信息必需字段。"""
        info = ConstraintInfo(
            name="clk",
            constraint_type=ConstraintType.CLOCK,
            target="clk_port",
        )
        
        assert info.name == "clk"
        assert info.constraint_type == ConstraintType.CLOCK
        assert info.target == "clk_port"
        assert info.properties == {}

    def test_constraint_info_with_properties(self):
        """测试带属性的约束信息。"""
        info = ConstraintInfo(
            name="clk",
            constraint_type=ConstraintType.CLOCK,
            target="clk_port",
            properties={"period": 10.0, "waveform": [0, 5]},
        )
        
        assert info.properties["period"] == 10.0
        assert info.properties["waveform"] == [0, 5]


# ==================== ConstraintsTclGenerator 测试 ====================


class TestConstraintsTclGenerator:
    """ConstraintsTclGenerator 测试。"""

    # --- create_clock_tcl 测试 ---

    def test_create_clock_tcl_basic(self):
        """测试基本时钟约束 Tcl 生成。"""
        constraint = ClockConstraint(name="clk", period=10.0)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "create_clock" in tcl
        assert "-name clk" in tcl
        assert "-period 10" in tcl

    def test_create_clock_tcl_with_target(self):
        """测试带目标的时钟约束 Tcl 生成。"""
        constraint = ClockConstraint(name="clk", period=10.0, target="clk_port")
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "[get_ports clk_port]" in tcl

    def test_create_clock_tcl_with_waveform(self):
        """测试带波形的时钟约束 Tcl 生成。"""
        constraint = ClockConstraint(
            name="clk",
            period=10.0,
            waveform=[0.0, 5.0],
        )
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "-waveform" in tcl
        assert "0" in tcl
        assert "5" in tcl

    def test_create_clock_tcl_with_add(self):
        """测试带 add 选项的时钟约束 Tcl 生成。"""
        constraint = ClockConstraint(name="clk", period=10.0, add=True)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "-add" in tcl

    # --- create_generated_clock_tcl 测试 ---

    def test_create_generated_clock_tcl_basic(self):
        """测试基本派生时钟约束 Tcl 生成。"""
        constraint = GeneratedClockConstraint(name="clk_div2", source="div_reg/Q")
        tcl = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        
        assert "create_generated_clock" in tcl
        assert "-name clk_div2" in tcl
        assert "-source [get_pins div_reg/Q]" in tcl

    def test_create_generated_clock_tcl_with_divide_by(self):
        """测试带分频的派生时钟约束 Tcl 生成。"""
        constraint = GeneratedClockConstraint(
            name="clk_div2",
            source="div_reg/Q",
            divide_by=2,
        )
        tcl = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        
        assert "-divide_by 2" in tcl

    def test_create_generated_clock_tcl_with_multiply_by(self):
        """测试带倍频的派生时钟约束 Tcl 生成。"""
        constraint = GeneratedClockConstraint(
            name="clk_x2",
            source="pll/clk_out",
            multiply_by=2,
        )
        tcl = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        
        assert "-multiply_by 2" in tcl

    def test_create_generated_clock_tcl_with_master_clock(self):
        """测试带主时钟的派生时钟约束 Tcl 生成。"""
        constraint = GeneratedClockConstraint(
            name="clk_div2",
            source="div_reg/Q",
            master_clock="clk_ref",
        )
        tcl = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        
        assert "-master_clock [get_clocks clk_ref]" in tcl

    def test_create_generated_clock_tcl_with_invert(self):
        """测试带反相的派生时钟约束 Tcl 生成。"""
        constraint = GeneratedClockConstraint(
            name="clk_inv",
            source="inv_reg/Q",
            invert=True,
        )
        tcl = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        
        assert "-invert" in tcl

    # --- set_input_delay_tcl 测试 ---

    def test_set_input_delay_tcl_max(self):
        """测试最大输入延迟约束 Tcl 生成。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=2.0,
            target="data_in",
            delay_type=DelayType.MAX,
        )
        tcl = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        
        assert "set_input_delay" in tcl
        assert "-max" in tcl
        assert "2.0" in tcl
        assert "-clock [get_clocks clk]" in tcl
        assert "[get_ports data_in]" in tcl

    def test_set_input_delay_tcl_min(self):
        """测试最小输入延迟约束 Tcl 生成。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=0.5,
            target="data_in",
            delay_type=DelayType.MIN,
        )
        tcl = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        
        assert "-min" in tcl

    def test_set_input_delay_tcl_both(self):
        """测试双向输入延迟约束 Tcl 生成。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=1.0,
            target="data_in",
            delay_type=DelayType.BOTH,
        )
        tcl = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        
        assert "-max -min" in tcl

    def test_set_input_delay_tcl_clock_fall(self):
        """测试时钟下降沿输入延迟约束 Tcl 生成。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=1.0,
            target="data_in",
            clock_fall=True,
        )
        tcl = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        
        assert "-clock_fall" in tcl

    # --- set_output_delay_tcl 测试 ---

    def test_set_output_delay_tcl_max(self):
        """测试最大输出延迟约束 Tcl 生成。"""
        constraint = OutputDelayConstraint(
            clock="clk",
            delay=1.5,
            target="data_out",
            delay_type=DelayType.MAX,
        )
        tcl = ConstraintsTclGenerator.set_output_delay_tcl(constraint)
        
        assert "set_output_delay" in tcl
        assert "-max" in tcl
        assert "1.5" in tcl
        assert "[get_ports data_out]" in tcl

    def test_set_output_delay_tcl_min(self):
        """测试最小输出延迟约束 Tcl 生成。"""
        constraint = OutputDelayConstraint(
            clock="clk",
            delay=0.3,
            target="data_out",
            delay_type=DelayType.MIN,
        )
        tcl = ConstraintsTclGenerator.set_output_delay_tcl(constraint)
        
        assert "-min" in tcl

    # --- set_false_path_tcl 测试 ---

    def test_set_false_path_tcl_basic(self):
        """测试基本虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint()
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "set_false_path" in tcl

    def test_set_false_path_tcl_with_from(self):
        """测试带起始引脚的虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint(from_pins="rst_async")
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "-from [get_pins rst_async]" in tcl

    def test_set_false_path_tcl_with_to(self):
        """测试带终止引脚的虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint(to_pins="data_reg/D")
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "-to [get_pins data_reg/D]" in tcl

    def test_set_false_path_tcl_with_through(self):
        """测试带经过引脚的虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint(through="sync_reg/Q")
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "-through [get_pins sync_reg/Q]" in tcl

    def test_set_false_path_tcl_setup_only(self):
        """测试仅 Setup 的虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint(setup=True, hold=False)
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "-setup" in tcl

    def test_set_false_path_tcl_hold_only(self):
        """测试仅 Hold 的虚假路径约束 Tcl 生成。"""
        constraint = FalsePathConstraint(setup=False, hold=True)
        tcl = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        
        assert "-hold" in tcl

    # --- set_multicycle_path_tcl 测试 ---

    def test_set_multicycle_path_tcl_basic(self):
        """测试基本多周期路径约束 Tcl 生成。"""
        constraint = MulticycleConstraint(cycles=2)
        tcl = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        
        assert "set_multicycle_path" in tcl
        assert "2" in tcl

    def test_set_multicycle_path_tcl_setup(self):
        """测试 Setup 多周期路径约束 Tcl 生成。"""
        constraint = MulticycleConstraint(cycles=2, setup=True, hold=False)
        tcl = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        
        assert "-setup" in tcl

    def test_set_multicycle_path_tcl_hold(self):
        """测试 Hold 多周期路径约束 Tcl 生成。"""
        constraint = MulticycleConstraint(cycles=1, setup=False, hold=True)
        tcl = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        
        assert "-hold" in tcl

    def test_set_multicycle_path_tcl_with_from_to(self):
        """测试带起始和终止引脚的多周期路径约束 Tcl 生成。"""
        constraint = MulticycleConstraint(
            cycles=2,
            from_pins="data_reg/Q",
            to_pins="result_reg/D",
        )
        tcl = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        
        assert "-from [get_pins data_reg/Q]" in tcl
        assert "-to [get_pins result_reg/D]" in tcl

    # --- set_max_delay_tcl 测试 ---

    def test_set_max_delay_tcl_basic(self):
        """测试基本最大延迟约束 Tcl 生成。"""
        constraint = MaxDelayConstraint(
            delay=5.0,
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
        )
        tcl = ConstraintsTclGenerator.set_max_delay_tcl(constraint)
        
        assert "set_max_delay" in tcl
        assert "5.0" in tcl
        assert "-from [get_pins src_reg/Q]" in tcl
        assert "-to [get_pins dst_reg/D]" in tcl

    def test_set_max_delay_tcl_with_datapath_only(self):
        """测试带 datapath_only 的最大延迟约束 Tcl 生成。"""
        constraint = MaxDelayConstraint(
            delay=3.0,
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
            datapath_only=True,
        )
        tcl = ConstraintsTclGenerator.set_max_delay_tcl(constraint)
        
        assert "-datapath_only" in tcl

    # --- set_min_delay_tcl 测试 ---

    def test_set_min_delay_tcl_basic(self):
        """测试基本最小延迟约束 Tcl 生成。"""
        constraint = MinDelayConstraint(
            delay=1.0,
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
        )
        tcl = ConstraintsTclGenerator.set_min_delay_tcl(constraint)
        
        assert "set_min_delay" in tcl
        assert "1.0" in tcl

    # --- set_clock_groups_tcl 测试 ---

    def test_set_clock_groups_tcl_exclusive(self):
        """测试互斥时钟组约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_clock_groups_tcl(
            name="async_groups",
            groups=[["clk_a", "clk_b"], ["clk_c"]],
            exclusive=True,
        )
        
        assert "set_clock_groups" in tcl
        assert "-exclusive" in tcl
        assert "-group" in tcl

    def test_set_clock_groups_tcl_asynchronous(self):
        """测试异步时钟组约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_clock_groups_tcl(
            name="async_groups",
            groups=[["clk_a"], ["clk_b"]],
            exclusive=False,
            asynchronous=True,
        )
        
        assert "-asynchronous" in tcl

    # --- get_clocks_tcl 测试 ---

    def test_get_clocks_tcl_default(self):
        """测试默认获取时钟 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.get_clocks_tcl()
        
        assert tcl == "get_clocks *"

    def test_get_clocks_tcl_with_pattern(self):
        """测试带模式的获取时钟 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.get_clocks_tcl("clk_*")
        
        assert tcl == "get_clocks clk_*"

    # --- get_ports_tcl 测试 ---

    def test_get_ports_tcl_default(self):
        """测试默认获取端口 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.get_ports_tcl()
        
        assert tcl == "get_ports *"

    def test_get_ports_tcl_with_pattern(self):
        """测试带模式的获取端口 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.get_ports_tcl("data_*")
        
        assert tcl == "get_ports data_*"

    # --- report_timing_summary_tcl 测试 ---

    def test_report_timing_summary_tcl_basic(self):
        """测试基本时序摘要报告 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.report_timing_summary_tcl()
        
        assert "report_timing_summary" in tcl
        assert "-max_paths 10" in tcl

    def test_report_timing_summary_tcl_with_output(self):
        """测试带输出文件的时序摘要报告 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.report_timing_summary_tcl(
            output_path=Path("/tmp/timing.rpt")
        )
        
        assert "-file" in tcl
        assert "timing.rpt" in tcl

    # --- report_timing_tcl 测试 ---

    def test_report_timing_tcl_basic(self):
        """测试基本时序报告 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.report_timing_tcl()
        
        assert "report_timing" in tcl
        assert "-max_paths 10" in tcl

    def test_report_timing_tcl_with_from_to(self):
        """测试带起始和终止引脚的时序报告 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.report_timing_tcl(
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
        )
        
        assert "-from [get_pins src_reg/Q]" in tcl
        assert "-to [get_pins dst_reg/D]" in tcl

    # --- read_xdc_tcl 测试 ---

    def test_read_xdc_tcl(self):
        """测试读取 XDC 文件 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.read_xdc_tcl(Path("/tmp/constraints.xdc"))
        
        assert "read_xdc" in tcl
        assert "constraints.xdc" in tcl

    # --- write_xdc_tcl 测试 ---

    def test_write_xdc_tcl_basic(self):
        """测试基本写入 XDC 文件 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.write_xdc_tcl(Path("/tmp/output.xdc"))
        
        assert "write_xdc -force" in tcl
        assert "output.xdc" in tcl

    def test_write_xdc_tcl_with_constraints(self):
        """测试带约束的写入 XDC 文件 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.write_xdc_tcl(
            Path("/tmp/output.xdc"),
            constraints=["create_clock -name clk -period 10"],
        )
        
        assert "-constraints" in tcl

    # --- IO 约束测试 ---

    def test_set_package_pin_tcl(self):
        """测试设置封装引脚约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_package_pin_tcl("led", "A1")
        
        assert "set_property PACKAGE_PIN A1 [get_ports led]" in tcl

    def test_set_iostandard_tcl(self):
        """测试设置 IO 标准约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_iostandard_tcl("led", "LVCMOS33")
        
        assert "set_property IOSTANDARD LVCMOS33 [get_ports led]" in tcl

    def test_set_pulltype_tcl(self):
        """测试设置上拉/下拉类型 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_pulltype_tcl("btn", "PULLUP")
        
        assert "set_property PULLTYPE PULLUP [get_ports btn]" in tcl

    def test_set_drive_strength_tcl(self):
        """测试设置驱动强度 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_drive_strength_tcl("led", 12)
        
        assert "set_property DRIVE 12 [get_ports led]" in tcl

    def test_set_slew_rate_tcl(self):
        """测试设置压摆率 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.set_slew_rate_tcl("clk_out", "FAST")
        
        assert "set_property SLEW FAST [get_ports clk_out]" in tcl

    # --- 其他命令测试 ---

    def test_get_timing_constraints_tcl(self):
        """测试获取时序约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.get_timing_constraints_tcl()
        
        assert tcl == "get_timing_constraints"

    def test_reset_timing_tcl(self):
        """测试重置时序约束 Tcl 生成。"""
        tcl = ConstraintsTclGenerator.reset_timing_tcl()
        
        assert tcl == "reset_timing"


# ==================== ConstraintsManager 测试 ====================


@pytest.mark.integration
class TestConstraintsManager:
    """ConstraintsManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """创建约束管理器。"""
        return ConstraintsManager(mock_engine)

    # --- create_clock 测试 ---

    @pytest.mark.asyncio
    async def test_create_clock_success(self, manager, mock_engine):
        """测试成功创建时钟约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_clock(
            name="clk",
            period=10.0,
            target="clk_port",
        )
        
        assert result["success"] is True
        assert len(manager.constraints) == 1
        assert manager.constraints[0].name == "clk"

    @pytest.mark.asyncio
    async def test_create_clock_failure(self, manager, mock_engine):
        """测试创建时钟约束失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Error: clock already exists"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_clock(name="clk", period=10.0)
        
        assert result["success"] is False
        assert len(manager.constraints) == 0

    # --- create_generated_clock 测试 ---

    @pytest.mark.asyncio
    async def test_create_generated_clock_success(self, manager, mock_engine):
        """测试成功创建派生时钟约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_generated_clock(
            name="clk_div2",
            source="div_reg/Q",
            divide_by=2,
        )
        
        assert result["success"] is True

    # --- set_input_delay 测试 ---

    @pytest.mark.asyncio
    async def test_set_input_delay_success(self, manager, mock_engine):
        """测试成功设置输入延迟约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_input_delay(
            clock="clk",
            delay=2.0,
            target="data_in",
        )
        
        assert result["success"] is True

    # --- set_output_delay 测试 ---

    @pytest.mark.asyncio
    async def test_set_output_delay_success(self, manager, mock_engine):
        """测试成功设置输出延迟约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_output_delay(
            clock="clk",
            delay=1.5,
            target="data_out",
        )
        
        assert result["success"] is True

    # --- set_false_path 测试 ---

    @pytest.mark.asyncio
    async def test_set_false_path_success(self, manager, mock_engine):
        """测试成功设置虚假路径约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_false_path(
            from_pins="rst_async",
            to_pins="data_reg/D",
        )
        
        assert result["success"] is True

    # --- set_multicycle_path 测试 ---

    @pytest.mark.asyncio
    async def test_set_multicycle_path_success(self, manager, mock_engine):
        """测试成功设置多周期路径约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_multicycle_path(
            cycles=2,
            from_pins="data_reg/Q",
            to_pins="result_reg/D",
        )
        
        assert result["success"] is True

    # --- set_max_delay 测试 ---

    @pytest.mark.asyncio
    async def test_set_max_delay_success(self, manager, mock_engine):
        """测试成功设置最大延迟约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_max_delay(
            delay=5.0,
            from_pins="src_reg/Q",
            to_pins="dst_reg/D",
        )
        
        assert result["success"] is True

    # --- get_clocks 测试 ---

    @pytest.mark.asyncio
    async def test_get_clocks_success(self, manager, mock_engine):
        """测试成功获取时钟列表。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "clk\nclk_div2\nclk_x2"
        mock_engine.execute_async.return_value = mock_result
        
        clocks = await manager.get_clocks()
        
        assert len(clocks) == 3
        assert "clk" in clocks

    @pytest.mark.asyncio
    async def test_get_clocks_empty(self, manager, mock_engine):
        """测试获取空时钟列表。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        clocks = await manager.get_clocks()
        
        assert clocks == []

    # --- get_constraints 测试 ---

    @pytest.mark.asyncio
    async def test_get_constraints_success(self, manager, mock_engine):
        """测试成功获取约束列表。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "create_clock -name clk -period 10\nset_input_delay 2 -clock clk"
        mock_engine.execute_async.return_value = mock_result
        
        constraints = await manager.get_constraints()
        
        assert len(constraints) >= 1

    # --- read_xdc 测试 ---

    @pytest.mark.asyncio
    async def test_read_xdc_file_not_found(self, manager):
        """测试读取不存在的 XDC 文件。"""
        result = await manager.read_xdc("/nonexistent/path.xdc")
        
        assert result["success"] is False
        assert "不存在" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_read_xdc_success(self, manager, mock_engine, tmp_path):
        """测试成功读取 XDC 文件。"""
        xdc_file = tmp_path / "constraints.xdc"
        xdc_file.write_text("create_clock -name clk -period 10\n")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.read_xdc(xdc_file)
        
        assert result["success"] is True

    # --- write_xdc 测试 ---

    @pytest.mark.asyncio
    async def test_write_xdc_success(self, manager, mock_engine):
        """测试成功写入 XDC 文件。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.write_xdc("/tmp/output.xdc")
        
        assert result["success"] is True

    # --- report_timing_summary 测试 ---

    @pytest.mark.asyncio
    async def test_report_timing_summary_success(self, manager, mock_engine):
        """测试成功生成时序摘要报告。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "WNS(ns): 2.5\nTNS(ns): 0.0\nWHS(ns): 0.8\nTHS(ns): 0.0"
        mock_engine.execute_async.return_value = mock_result
        
        summary = await manager.report_timing_summary()
        
        assert "wns" in summary
        assert summary["wns"] == 2.5

    # --- set_io_constraint 测试 ---

    @pytest.mark.asyncio
    async def test_set_io_constraint_success(self, manager, mock_engine):
        """测试成功设置 IO 约束。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_io_constraint(
            port="led",
            pin="A1",
            iostandard="LVCMOS33",
        )
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_set_io_constraint_no_constraints(self, manager):
        """测试设置 IO 约束时未指定任何约束。"""
        result = await manager.set_io_constraint(port="led")
        
        assert result["success"] is False
        assert "未指定任何约束" in result["errors"][0]

    # --- 解析方法测试 ---

    def test_parse_list_output(self, manager):
        """测试解析列表输出。"""
        output = "clk\nclk_div2\n# comment\nclk_x2\n"
        items = manager._parse_list_output(output)
        
        assert len(items) == 3
        assert "clk" in items
        assert "clk_div2" in items

    def test_parse_list_output_empty(self, manager):
        """测试解析空列表输出。"""
        items = manager._parse_list_output("")
        
        assert items == []

    def test_parse_constraints_output(self, manager):
        """测试解析约束输出。"""
        output = "create_clock -name clk -period 10\n# comment\nset_input_delay 2"
        constraints = manager._parse_constraints_output(output)
        
        assert len(constraints) == 2

    def test_parse_timing_summary(self, manager):
        """测试解析时序摘要报告。"""
        report = """
Timing Summary
WNS(ns): 2.5
TNS(ns): 0.0
WHS(ns): 0.8
THS(ns): 0.0
"""
        summary = manager._parse_timing_summary(report)
        
        assert summary["wns"] == 2.5
        assert summary["tns"] == 0.0
        assert summary["whs"] == 0.8
        assert summary["ths"] == 0.0
        assert summary["timing_met"] is True

    def test_parse_timing_summary_negative_slack(self, manager):
        """测试解析负裕量时序摘要报告。"""
        report = """
WNS(ns): -1.5
TNS(ns): -5.0
WHS(ns): 0.3
THS(ns): 0.0
"""
        summary = manager._parse_timing_summary(report)
        
        assert summary["wns"] == -1.5
        assert summary["timing_met"] is False


# ==================== 边界情况测试 ====================


class TestConstraintsEdgeCases:
    """约束模块边界情况测试。"""

    def test_clock_constraint_zero_period(self):
        """测试零周期时钟约束。"""
        constraint = ClockConstraint(name="clk", period=0.0)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "-period 0" in tcl

    def test_clock_constraint_negative_period(self):
        """测试负周期时钟约束。"""
        constraint = ClockConstraint(name="clk", period=-10.0)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        # 应该生成 Tcl，但 Vivado 会报错
        assert "-period -10" in tcl

    def test_multicycle_constraint_zero_cycles(self):
        """测试零周期多周期约束。"""
        constraint = MulticycleConstraint(cycles=0)
        tcl = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        
        assert "0" in tcl

    def test_delay_constraint_negative_delay(self):
        """测试负延迟约束。"""
        constraint = InputDelayConstraint(
            clock="clk",
            delay=-1.0,
            target="data_in",
        )
        tcl = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        
        assert "-1.0" in tcl

    def test_empty_waveform(self):
        """测试空波形。"""
        constraint = ClockConstraint(name="clk", period=10.0, waveform=[])
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        # 空波形不应该生成 -waveform 选项
        assert "-waveform" not in tcl

    def test_special_characters_in_name(self):
        """测试名称中的特殊字符。"""
        constraint = ClockConstraint(name="clk_100MHz_main", period=10.0)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "clk_100MHz_main" in tcl

    def test_very_long_name(self):
        """测试超长名称。"""
        long_name = "a" * 1000
        constraint = ClockConstraint(name=long_name, period=10.0)
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert long_name in tcl

    def test_unicode_in_target(self):
        """测试目标中的 Unicode 字符。"""
        constraint = ClockConstraint(name="clk", period=10.0, target="端口_1")
        tcl = ConstraintsTclGenerator.create_clock_tcl(constraint)
        
        assert "端口_1" in tcl
