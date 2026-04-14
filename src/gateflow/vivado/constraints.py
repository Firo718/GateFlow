"""
Vivado 时序约束管理模块

该模块提供时钟约束、IO约束、时序例外等操作的 Tcl 命令生成功能。
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ConstraintType(Enum):
    """约束类型枚举"""
    CLOCK = "clock"
    INPUT_DELAY = "input_delay"
    OUTPUT_DELAY = "output_delay"
    FALSE_PATH = "false_path"
    MULTICYCLE = "multicycle"
    MAX_DELAY = "max_delay"
    MIN_DELAY = "min_delay"
    CLOCK_GROUP = "clock_group"


class ClockSense(Enum):
    """时钟感知类型"""
    POSITIVE = "positive"
    NEGATIVE = "negative"


class DelayType(Enum):
    """延迟类型"""
    MAX = "max"
    MIN = "min"
    BOTH = "both"


@dataclass
class ClockConstraint:
    """时钟约束配置"""
    name: str  # 时钟名称
    period: float  # 周期（ns）
    waveform: list[float] | None = None  # 波形 [rise, fall]
    target: str | None = None  # 目标端口/引脚
    add: bool = False  # 是否添加到现有约束


@dataclass
class GeneratedClockConstraint:
    """派生时钟约束配置"""
    name: str  # 时钟名称
    source: str  # 源时钟引脚
    master_clock: str | None = None  # 主时钟名称
    divide_by: int | None = None  # 分频系数
    multiply_by: int | None = None  # 倍频系数
    invert: bool = False  # 是否反相
    target: str | None = None  # 目标端口/引脚


@dataclass
class InputDelayConstraint:
    """输入延迟约束配置"""
    clock: str  # 时钟名称
    delay: float  # 延迟值（ns）
    target: str  # 目标端口
    delay_type: DelayType = DelayType.MAX  # 延迟类型
    clock_fall: bool = False  # 是否为时钟下降沿


@dataclass
class OutputDelayConstraint:
    """输出延迟约束配置"""
    clock: str  # 时钟名称
    delay: float  # 延迟值（ns）
    target: str  # 目标端口
    delay_type: DelayType = DelayType.MAX  # 延迟类型
    clock_fall: bool = False  # 是否为时钟下降沿


@dataclass
class FalsePathConstraint:
    """虚假路径约束配置"""
    from_pins: str | None = None  # 起始引脚
    to_pins: str | None = None  # 终止引脚
    through: str | None = None  # 经过引脚
    setup: bool = True  # 是否为 Setup 检查
    hold: bool = True  # 是否为 Hold 检查


@dataclass
class MulticycleConstraint:
    """多周期路径约束配置"""
    cycles: int  # 周期数
    from_pins: str | None = None  # 起始引脚
    to_pins: str | None = None  # 终止引脚
    setup: bool = True  # 是否为 Setup 检查
    hold: bool = False  # 是否为 Hold 检查


@dataclass
class MaxDelayConstraint:
    """最大延迟约束配置"""
    delay: float  # 延迟值（ns）
    from_pins: str | None = None  # 起始引脚
    to_pins: str | None = None  # 终止引脚
    datapath_only: bool = False  # 是否仅数据路径


@dataclass
class MinDelayConstraint:
    """最小延迟约束配置"""
    delay: float  # 延迟值（ns）
    from_pins: str | None = None  # 起始引脚
    to_pins: str | None = None  # 终止引脚
    datapath_only: bool = False  # 是否仅数据路径


@dataclass
class ConstraintInfo:
    """约束信息"""
    name: str  # 约束名称
    constraint_type: ConstraintType  # 约束类型
    target: str  # 目标对象
    properties: dict = field(default_factory=dict)  # 属性字典


class ConstraintsTclGenerator:
    """
    约束 Tcl 命令生成器
    
    生成用于时钟约束、IO约束、时序例外等操作的 Tcl 命令。
    """
    
    @staticmethod
    def create_clock_tcl(constraint: ClockConstraint) -> str:
        """
        生成创建时钟约束的 Tcl 命令
        
        Args:
            constraint: 时钟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['create_clock']
        
        if constraint.add:
            cmd_parts.append('-add')
        
        cmd_parts.append(f'-name {constraint.name}')
        cmd_parts.append(f'-period {constraint.period}')
        
        if constraint.waveform:
            waveform_str = ' '.join(str(w) for w in constraint.waveform)
            cmd_parts.append(f'-waveform {{{waveform_str}}}')
        
        if constraint.target:
            cmd_parts.append(f'[get_ports {constraint.target}]')
        else:
            cmd_parts.append('-name')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def create_generated_clock_tcl(constraint: GeneratedClockConstraint) -> str:
        """
        生成派生时钟约束的 Tcl 命令
        
        Args:
            constraint: 派生时钟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['create_generated_clock']
        
        cmd_parts.append(f'-name {constraint.name}')
        cmd_parts.append(f'-source [get_pins {constraint.source}]')
        
        if constraint.master_clock:
            cmd_parts.append(f'-master_clock [get_clocks {constraint.master_clock}]')
        
        if constraint.divide_by:
            cmd_parts.append(f'-divide_by {constraint.divide_by}')
        
        if constraint.multiply_by:
            cmd_parts.append(f'-multiply_by {constraint.multiply_by}')
        
        if constraint.invert:
            cmd_parts.append('-invert')
        
        if constraint.target:
            cmd_parts.append(f'[get_pins {constraint.target}]')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_input_delay_tcl(constraint: InputDelayConstraint) -> str:
        """
        设置输入延迟约束的 Tcl 命令
        
        Args:
            constraint: 输入延迟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_input_delay']
        
        if constraint.delay_type == DelayType.MAX:
            cmd_parts.append('-max')
        elif constraint.delay_type == DelayType.MIN:
            cmd_parts.append('-min')
        else:
            cmd_parts.append('-max -min')
        
        cmd_parts.append(f'{constraint.delay}')
        cmd_parts.append(f'-clock [get_clocks {constraint.clock}]')
        
        if constraint.clock_fall:
            cmd_parts.append('-clock_fall')
        
        cmd_parts.append(f'[get_ports {constraint.target}]')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_output_delay_tcl(constraint: OutputDelayConstraint) -> str:
        """
        设置输出延迟约束的 Tcl 命令
        
        Args:
            constraint: 输出延迟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_output_delay']
        
        if constraint.delay_type == DelayType.MAX:
            cmd_parts.append('-max')
        elif constraint.delay_type == DelayType.MIN:
            cmd_parts.append('-min')
        else:
            cmd_parts.append('-max -min')
        
        cmd_parts.append(f'{constraint.delay}')
        cmd_parts.append(f'-clock [get_clocks {constraint.clock}]')
        
        if constraint.clock_fall:
            cmd_parts.append('-clock_fall')
        
        cmd_parts.append(f'[get_ports {constraint.target}]')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_false_path_tcl(constraint: FalsePathConstraint) -> str:
        """
        设置虚假路径约束的 Tcl 命令
        
        Args:
            constraint: 虚假路径约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_false_path']
        
        if constraint.from_pins:
            cmd_parts.append(f'-from [get_pins {constraint.from_pins}]')
        
        if constraint.to_pins:
            cmd_parts.append(f'-to [get_pins {constraint.to_pins}]')
        
        if constraint.through:
            cmd_parts.append(f'-through [get_pins {constraint.through}]')
        
        if not constraint.setup:
            cmd_parts.append('-hold')
        elif not constraint.hold:
            cmd_parts.append('-setup')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_multicycle_path_tcl(constraint: MulticycleConstraint) -> str:
        """
        设置多周期路径约束的 Tcl 命令
        
        Args:
            constraint: 多周期路径约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_multicycle_path']
        cmd_parts.append(str(constraint.cycles))
        
        if constraint.setup and not constraint.hold:
            cmd_parts.append('-setup')
        elif constraint.hold and not constraint.setup:
            cmd_parts.append('-hold')
        
        if constraint.from_pins:
            cmd_parts.append(f'-from [get_pins {constraint.from_pins}]')
        
        if constraint.to_pins:
            cmd_parts.append(f'-to [get_pins {constraint.to_pins}]')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_max_delay_tcl(constraint: MaxDelayConstraint) -> str:
        """
        设置最大延迟约束的 Tcl 命令
        
        Args:
            constraint: 最大延迟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_max_delay']
        cmd_parts.append(f'-from [get_pins {constraint.from_pins}]')
        cmd_parts.append(f'-to [get_pins {constraint.to_pins}]')
        cmd_parts.append(str(constraint.delay))
        
        if constraint.datapath_only:
            cmd_parts.append('-datapath_only')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_min_delay_tcl(constraint: MinDelayConstraint) -> str:
        """
        设置最小延迟约束的 Tcl 命令
        
        Args:
            constraint: 最小延迟约束配置
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_min_delay']
        cmd_parts.append(f'-from [get_pins {constraint.from_pins}]')
        cmd_parts.append(f'-to [get_pins {constraint.to_pins}]')
        cmd_parts.append(str(constraint.delay))
        
        if constraint.datapath_only:
            cmd_parts.append('-datapath_only')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def set_clock_groups_tcl(
        name: str,
        groups: list[list[str]],
        exclusive: bool = True,
        asynchronous: bool = False,
    ) -> str:
        """
        设置时钟组约束的 Tcl 命令
        
        Args:
            name: 约束名称
            groups: 时钟组列表
            exclusive: 是否互斥
            asynchronous: 是否异步
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['set_clock_groups']
        
        if exclusive:
            cmd_parts.append('-exclusive')
        elif asynchronous:
            cmd_parts.append('-asynchronous')
        
        for group in groups:
            clocks_str = ' '.join(group)
            cmd_parts.append(f'-group [get_clocks {{{clocks_str}}}]')
        
        return ' '.join(cmd_parts)
    
    @staticmethod
    def get_clocks_tcl(pattern: str = "*") -> str:
        """
        获取所有时钟的 Tcl 命令
        
        Args:
            pattern: 时钟名称模式
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_clocks {pattern}'
    
    @staticmethod
    def get_ports_tcl(pattern: str = "*") -> str:
        """
        获取端口的 Tcl 命令
        
        Args:
            pattern: 端口名称模式
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_ports {pattern}'
    
    @staticmethod
    def report_timing_summary_tcl(
        output_path: Path | None = None,
        max_paths: int = 10,
        delay_type: str = "min_max",
    ) -> str:
        """
        生成时序摘要报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            delay_type: 延迟类型
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'report_timing_summary -max_paths {max_paths} -delay_type {delay_type}'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        return cmd
    
    @staticmethod
    def report_timing_tcl(
        output_path: Path | None = None,
        max_paths: int = 10,
        delay_type: str = "max",
        from_pins: str | None = None,
        to_pins: str | None = None,
    ) -> str:
        """
        生成时序报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            delay_type: 延迟类型
            from_pins: 起始引脚
            to_pins: 终止引脚
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'report_timing -max_paths {max_paths} -delay_type {delay_type}'
        
        if from_pins:
            cmd += f' -from [get_pins {from_pins}]'
        
        if to_pins:
            cmd += f' -to [get_pins {to_pins}]'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        return cmd
    
    @staticmethod
    def read_xdc_tcl(path: Path) -> str:
        """
        读取 XDC 约束文件的 Tcl 命令
        
        Args:
            path: XDC 文件路径
            
        Returns:
            Tcl 命令字符串
        """
        return f'read_xdc "{path}"'
    
    @staticmethod
    def write_xdc_tcl(
        path: Path,
        constraints: list[str] | None = None,
    ) -> str:
        """
        写入 XDC 约束文件的 Tcl 命令
        
        Args:
            path: XDC 文件路径
            constraints: 约束列表（可选）
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'write_xdc -force "{path}"'
        
        if constraints:
            constraints_str = ' '.join(constraints)
            cmd += f' -constraints {{{constraints_str}}}'
        
        return cmd
    
    @staticmethod
    def get_timing_constraints_tcl() -> str:
        """
        获取所有时序约束的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_timing_constraints'
    
    @staticmethod
    def reset_timing_tcl() -> str:
        """
        重置时序约束的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'reset_timing'
    
    @staticmethod
    def set_package_pin_tcl(port: str, pin: str) -> str:
        """
        设置封装引脚约束的 Tcl 命令
        
        Args:
            port: 端口名称
            pin: 引脚编号
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property PACKAGE_PIN {pin} [get_ports {port}]'
    
    @staticmethod
    def set_iostandard_tcl(port: str, iostandard: str) -> str:
        """
        设置 IO 标准约束的 Tcl 命令
        
        Args:
            port: 端口名称
            iostandard: IO 标准（如 LVCMOS33, LVDS 等）
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property IOSTANDARD {iostandard} [get_ports {port}]'
    
    @staticmethod
    def set_pulltype_tcl(port: str, pulltype: str) -> str:
        """
        设置上拉/下拉类型的 Tcl 命令
        
        Args:
            port: 端口名称
            pulltype: 上拉/下拉类型（PULLUP, PULLDOWN, NONE）
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property PULLTYPE {pulltype} [get_ports {port}]'
    
    @staticmethod
    def set_drive_strength_tcl(port: str, strength: int) -> str:
        """
        设置驱动强度的 Tcl 命令
        
        Args:
            port: 端口名称
            strength: 驱动强度（mA）
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property DRIVE {strength} [get_ports {port}]'
    
    @staticmethod
    def set_slew_rate_tcl(port: str, slew: str) -> str:
        """
        设置压摆率的 Tcl 命令
        
        Args:
            port: 端口名称
            slew: 压摆率（SLOW, FAST）
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property SLEW {slew} [get_ports {port}]'


class ConstraintsManager:
    """
    约束管理器
    
    提供高级的约束管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化约束管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self.constraints: list[ConstraintInfo] = []
    
    async def create_clock(
        self,
        name: str,
        period: float,
        target: str | None = None,
        waveform: list[float] | None = None,
        add: bool = False,
    ) -> dict:
        """
        创建时钟约束
        
        Args:
            name: 时钟名称
            period: 周期（ns）
            target: 目标端口/引脚
            waveform: 波形 [rise, fall]
            add: 是否添加到现有约束
            
        Returns:
            执行结果字典
        """
        constraint = ClockConstraint(
            name=name,
            period=period,
            target=target,
            waveform=waveform,
            add=add,
        )
        
        command = ConstraintsTclGenerator.create_clock_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            self.constraints.append(ConstraintInfo(
                name=name,
                constraint_type=ConstraintType.CLOCK,
                target=target or name,
                properties={'period': period, 'waveform': waveform},
            ))
            logger.info(f"时钟约束创建成功: {name}")
        else:
            logger.error(f"时钟约束创建失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def create_generated_clock(
        self,
        name: str,
        source: str,
        target: str | None = None,
        master_clock: str | None = None,
        divide_by: int | None = None,
        multiply_by: int | None = None,
        invert: bool = False,
    ) -> dict:
        """
        创建派生时钟约束
        
        Args:
            name: 时钟名称
            source: 源时钟引脚
            target: 目标端口/引脚
            master_clock: 主时钟名称
            divide_by: 分频系数
            multiply_by: 倍频系数
            invert: 是否反相
            
        Returns:
            执行结果字典
        """
        constraint = GeneratedClockConstraint(
            name=name,
            source=source,
            target=target,
            master_clock=master_clock,
            divide_by=divide_by,
            multiply_by=multiply_by,
            invert=invert,
        )
        
        command = ConstraintsTclGenerator.create_generated_clock_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"派生时钟约束创建成功: {name}")
        else:
            logger.error(f"派生时钟约束创建失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def set_input_delay(
        self,
        clock: str,
        delay: float,
        target: str,
        delay_type: DelayType = DelayType.MAX,
        clock_fall: bool = False,
    ) -> dict:
        """
        设置输入延迟约束
        
        Args:
            clock: 时钟名称
            delay: 延迟值（ns）
            target: 目标端口
            delay_type: 延迟类型
            clock_fall: 是否为时钟下降沿
            
        Returns:
            执行结果字典
        """
        constraint = InputDelayConstraint(
            clock=clock,
            delay=delay,
            target=target,
            delay_type=delay_type,
            clock_fall=clock_fall,
        )
        
        command = ConstraintsTclGenerator.set_input_delay_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"输入延迟约束设置成功: {target}")
        else:
            logger.error(f"输入延迟约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def set_output_delay(
        self,
        clock: str,
        delay: float,
        target: str,
        delay_type: DelayType = DelayType.MAX,
        clock_fall: bool = False,
    ) -> dict:
        """
        设置输出延迟约束
        
        Args:
            clock: 时钟名称
            delay: 延迟值（ns）
            target: 目标端口
            delay_type: 延迟类型
            clock_fall: 是否为时钟下降沿
            
        Returns:
            执行结果字典
        """
        constraint = OutputDelayConstraint(
            clock=clock,
            delay=delay,
            target=target,
            delay_type=delay_type,
            clock_fall=clock_fall,
        )
        
        command = ConstraintsTclGenerator.set_output_delay_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"输出延迟约束设置成功: {target}")
        else:
            logger.error(f"输出延迟约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def set_false_path(
        self,
        from_pins: str | None = None,
        to_pins: str | None = None,
        through: str | None = None,
        setup: bool = True,
        hold: bool = True,
    ) -> dict:
        """
        设置虚假路径约束
        
        Args:
            from_pins: 起始引脚
            to_pins: 终止引脚
            through: 经过引脚
            setup: 是否为 Setup 检查
            hold: 是否为 Hold 检查
            
        Returns:
            执行结果字典
        """
        constraint = FalsePathConstraint(
            from_pins=from_pins,
            to_pins=to_pins,
            through=through,
            setup=setup,
            hold=hold,
        )
        
        command = ConstraintsTclGenerator.set_false_path_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info("虚假路径约束设置成功")
        else:
            logger.error(f"虚假路径约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def set_multicycle_path(
        self,
        cycles: int,
        from_pins: str | None = None,
        to_pins: str | None = None,
        setup: bool = True,
        hold: bool = False,
    ) -> dict:
        """
        设置多周期路径约束
        
        Args:
            cycles: 周期数
            from_pins: 起始引脚
            to_pins: 终止引脚
            setup: 是否为 Setup 检查
            hold: 是否为 Hold 检查
            
        Returns:
            执行结果字典
        """
        constraint = MulticycleConstraint(
            cycles=cycles,
            from_pins=from_pins,
            to_pins=to_pins,
            setup=setup,
            hold=hold,
        )
        
        command = ConstraintsTclGenerator.set_multicycle_path_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"多周期路径约束设置成功: {cycles} 周期")
        else:
            logger.error(f"多周期路径约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def set_max_delay(
        self,
        delay: float,
        from_pins: str | None = None,
        to_pins: str | None = None,
        datapath_only: bool = False,
    ) -> dict:
        """
        设置最大延迟约束
        
        Args:
            delay: 延迟值（ns）
            from_pins: 起始引脚
            to_pins: 终止引脚
            datapath_only: 是否仅数据路径
            
        Returns:
            执行结果字典
        """
        constraint = MaxDelayConstraint(
            delay=delay,
            from_pins=from_pins,
            to_pins=to_pins,
            datapath_only=datapath_only,
        )
        
        command = ConstraintsTclGenerator.set_max_delay_tcl(constraint)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"最大延迟约束设置成功: {delay} ns")
        else:
            logger.error(f"最大延迟约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def get_clocks(self, pattern: str = "*") -> list[str]:
        """
        获取所有时钟
        
        Args:
            pattern: 时钟名称模式
            
        Returns:
            时钟名称列表
        """
        command = ConstraintsTclGenerator.get_clocks_tcl(pattern)
        result = await self.engine.execute_async(command)
        
        if result.success:
            # 解析输出获取时钟列表
            clocks = self._parse_list_output(result.output)
            return clocks
        
        return []
    
    async def get_constraints(self) -> list[dict]:
        """
        获取所有约束
        
        Returns:
            约束信息列表
        """
        command = ConstraintsTclGenerator.get_timing_constraints_tcl()
        result = await self.engine.execute_async(command)
        
        constraints = []
        if result.success:
            # 解析约束信息
            constraints = self._parse_constraints_output(result.output)
        
        return constraints
    
    async def read_xdc(self, path: str | Path) -> dict:
        """
        读取 XDC 约束文件
        
        Args:
            path: XDC 文件路径
            
        Returns:
            执行结果字典
        """
        path = Path(path)
        if not path.exists():
            return {
                'success': False,
                'errors': [f'文件不存在: {path}'],
                'warnings': [],
            }
        
        command = ConstraintsTclGenerator.read_xdc_tcl(path)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"XDC 文件读取成功: {path}")
        else:
            logger.error(f"XDC 文件读取失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def write_xdc(self, path: str | Path) -> dict:
        """
        写入 XDC 约束文件
        
        Args:
            path: XDC 文件路径
            
        Returns:
            执行结果字典
        """
        path = Path(path)
        command = ConstraintsTclGenerator.write_xdc_tcl(path)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"XDC 文件写入成功: {path}")
        else:
            logger.error(f"XDC 文件写入失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    async def report_timing_summary(
        self,
        output_path: str | Path | None = None,
        max_paths: int = 10,
    ) -> dict:
        """
        生成时序摘要报告
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            
        Returns:
            时序摘要字典
        """
        command = ConstraintsTclGenerator.report_timing_summary_tcl(
            output_path=Path(output_path) if output_path else None,
            max_paths=max_paths,
        )
        result = await self.engine.execute_async(command)
        
        timing_summary = {}
        if result.success:
            timing_summary = self._parse_timing_summary(result.output)
            logger.info("时序摘要报告生成成功")
        else:
            logger.error(f"时序摘要报告生成失败: {result.errors}")
        
        return timing_summary
    
    async def set_io_constraint(
        self,
        port: str,
        pin: str | None = None,
        iostandard: str | None = None,
        pulltype: str | None = None,
        drive: int | None = None,
        slew: str | None = None,
    ) -> dict:
        """
        设置 IO 约束
        
        Args:
            port: 端口名称
            pin: 引脚编号
            iostandard: IO 标准
            pulltype: 上拉/下拉类型
            drive: 驱动强度
            slew: 压摆率
            
        Returns:
            执行结果字典
        """
        commands = []
        
        if pin:
            commands.append(ConstraintsTclGenerator.set_package_pin_tcl(port, pin))
        
        if iostandard:
            commands.append(ConstraintsTclGenerator.set_iostandard_tcl(port, iostandard))
        
        if pulltype:
            commands.append(ConstraintsTclGenerator.set_pulltype_tcl(port, pulltype))
        
        if drive:
            commands.append(ConstraintsTclGenerator.set_drive_strength_tcl(port, drive))
        
        if slew:
            commands.append(ConstraintsTclGenerator.set_slew_rate_tcl(port, slew))
        
        if not commands:
            return {
                'success': False,
                'errors': ['未指定任何约束'],
                'warnings': [],
            }
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            logger.info(f"IO 约束设置成功: {port}")
        else:
            logger.error(f"IO 约束设置失败: {result.errors}")
        
        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }
    
    def _parse_list_output(self, output: str) -> list[str]:
        """
        解析列表输出
        
        Args:
            output: 输出字符串
            
        Returns:
            列表
        """
        items = []
        for line in output.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                items.append(line)
        return items
    
    def _parse_constraints_output(self, output: str) -> list[dict]:
        """
        解析约束输出
        
        Args:
            output: 输出字符串
            
        Returns:
            约束列表
        """
        constraints = []
        # 简单解析，实际可能需要更复杂的逻辑
        for line in output.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                constraints.append({'raw': line})
        return constraints
    
    def _parse_timing_summary(self, report: str) -> dict:
        """
        解析时序摘要报告
        
        Args:
            report: 报告内容
            
        Returns:
            时序摘要字典
        """
        summary = {}
        
        # 解析 Setup 时序
        wns_pattern = r'WNS\(ns\)\s*:\s*([\d.-]+)'
        tns_pattern = r'TNS\(ns\)\s*:\s*([\d.-]+)'
        
        wns_match = re.search(wns_pattern, report)
        tns_match = re.search(tns_pattern, report)
        
        if wns_match:
            summary['wns'] = float(wns_match.group(1))
        if tns_match:
            summary['tns'] = float(tns_match.group(1))
        
        # 解析 Hold 时序
        whs_pattern = r'WHS\(ns\)\s*:\s*([\d.-]+)'
        ths_pattern = r'THS\(ns\)\s*:\s*([\d.-]+)'
        
        whs_match = re.search(whs_pattern, report)
        ths_match = re.search(ths_pattern, report)
        
        if whs_match:
            summary['whs'] = float(whs_match.group(1))
        if ths_match:
            summary['ths'] = float(ths_match.group(1))
        
        # 判断时序是否满足
        summary['timing_met'] = summary.get('wns', 0) >= 0 and summary.get('whs', 0) >= 0
        
        return summary
