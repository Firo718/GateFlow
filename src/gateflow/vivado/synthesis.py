"""
Vivado 综合相关 Tcl 命令封装

该模块提供综合运行、报告获取等操作的 Tcl 命令生成功能。
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SynthesisStrategy(Enum):
    """综合策略枚举"""
    DEFAULT = "Vivado Synthesis Defaults"
    AREA = "Vivado Synthesis Defaults"  # 面积优化
    SPEED = "Vivado Synthesis Defaults"  # 速度优化
    POWER = "Vivado Synthesis Defaults"  # 功耗优化


class RunStatus(Enum):
    """运行状态枚举"""
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SynthesisResult:
    """综合结果"""
    success: bool  # 是否成功
    status: RunStatus  # 运行状态
    utilization: dict  # 资源利用率
    timing: dict  # 时序信息
    report_path: Optional[Path] = None  # 报告路径
    log_path: Optional[Path] = None  # 日志路径
    errors: list[str] = None  # 错误列表
    warnings: list[str] = None  # 警告列表
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ResourceUtilization:
    """资源利用率"""
    slice_lut: tuple[int, int, float]  # (已用, 总量, 利用率%)
    slice_registers: tuple[int, int, float]
    slice: tuple[int, int, float]
    lut: tuple[int, int, float]
    lut_as_logic: tuple[int, int, float]
    lut_as_memory: tuple[int, int, float]
    bram: tuple[int, int, float]
    dsp: tuple[int, int, float]
    iob: tuple[int, int, float]
    pll: tuple[int, int, float]
    mmcm: tuple[int, int, float]


class SynthesisTclGenerator:
    """
    综合 Tcl 命令生成器
    
    生成用于综合运行、报告获取等操作的 Tcl 命令。
    """
    
    @staticmethod
    def run_synthesis_tcl(
        run_name: str = "synth_1",
        jobs: int = 4,
        quiet: bool = False,
    ) -> str:
        """
        生成运行综合的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            jobs: 并行任务数
            quiet: 是否静默模式
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'launch_runs {run_name}'
        
        if jobs > 1:
            cmd += f' -jobs {jobs}'
        
        if quiet:
            cmd += ' -quiet'
        
        return cmd
    
    @staticmethod
    def wait_for_synthesis_tcl(
        run_name: str = "synth_1",
        timeout: Optional[int] = None,
    ) -> str:
        """
        生成等待综合完成的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            timeout: 超时时间（秒）
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'wait_on_run {run_name}'
        
        if timeout:
            cmd += f' -timeout {timeout}'
        
        return cmd
    
    @staticmethod
    def run_synthesis_complete_tcl(
        run_name: str = "synth_1",
        jobs: int = 4,
    ) -> list[str]:
        """
        生成完整的综合运行命令序列
        
        Args:
            run_name: 综合运行名称
            jobs: 并行任务数
            
        Returns:
            Tcl 命令列表
        """
        return [
            SynthesisTclGenerator.run_synthesis_tcl(run_name, jobs),
            SynthesisTclGenerator.wait_for_synthesis_tcl(run_name),
        ]
    
    @staticmethod
    def reset_synthesis_tcl(run_name: str = "synth_1") -> str:
        """
        生成重置综合的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'reset_run {run_name}'
    
    @staticmethod
    def get_synthesis_status_tcl(run_name: str = "synth_1") -> str:
        """
        生成获取综合状态的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property STATUS [get_runs {run_name}]'
    
    @staticmethod
    def get_synthesis_progress_tcl(run_name: str = "synth_1") -> str:
        """
        生成获取综合进度的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property PROGRESS [get_runs {run_name}]'
    
    @staticmethod
    def open_synthesized_design_tcl(run_name: str = "synth_1") -> str:
        """
        生成打开综合设计的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'open_run {run_name}'
    
    @staticmethod
    def close_synthesized_design_tcl() -> str:
        """
        生成关闭综合设计的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_design'
    
    @staticmethod
    def get_synthesis_report_tcl(
        report_type: str = "utilization",
        output_path: Optional[Path] = None,
    ) -> str:
        """
        生成获取综合报告的 Tcl 命令
        
        Args:
            report_type: 报告类型（utilization, timing, power, etc.）
            output_path: 输出文件路径
            
        Returns:
            Tcl 命令字符串
        """
        if report_type == "utilization":
            cmd = 'report_utilization'
        elif report_type == "timing":
            cmd = 'report_timing_summary'
        elif report_type == "power":
            cmd = 'report_power'
        elif report_type == "drc":
            cmd = 'report_drc'
        elif report_type == "methodology":
            cmd = 'report_methodology'
        else:
            cmd = f'report_{report_type}'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        return cmd
    
    @staticmethod
    def get_utilization_report_tcl(
        output_path: Optional[Path] = None,
        hierarchical: bool = False,
    ) -> str:
        """
        生成获取资源利用率报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            hierarchical: 是否分层显示
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'report_utilization'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        if hierarchical:
            cmd += ' -hierarchical'
        
        return cmd
    
    @staticmethod
    def get_timing_report_tcl(
        output_path: Optional[Path] = None,
        max_paths: int = 10,
        delay_type: str = "max",
    ) -> str:
        """
        生成获取时序报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            delay_type: 延迟类型（max, min）
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'report_timing_summary -max_paths {max_paths}'
        
        if delay_type == "min":
            cmd += ' -delay_type min'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        return cmd
    
    @staticmethod
    def get_power_report_tcl(
        output_path: Optional[Path] = None,
        include_xpe: bool = False,
    ) -> str:
        """
        生成获取功耗报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            include_xpe: 是否包含 XPE 数据
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'report_power'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        if include_xpe:
            cmd += ' -xpe'
        
        return cmd
    
    @staticmethod
    def set_synthesis_strategy_tcl(
        strategy: str,
        run_name: str = "synth_1",
    ) -> str:
        """
        生成设置综合策略的 Tcl 命令
        
        Args:
            strategy: 策略名称
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property strategy "{strategy}" [get_runs {run_name}]'
    
    @staticmethod
    def set_synthesis_property_tcl(
        property_name: str,
        value: str,
        run_name: str = "synth_1",
    ) -> str:
        """
        生成设置综合属性的 Tcl 命令
        
        Args:
            property_name: 属性名称
            value: 属性值
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property {property_name} {value} [get_runs {run_name}]'
    
    @staticmethod
    def get_synthesis_log_tcl(run_name: str = "synth_1") -> str:
        """
        生成获取综合日志路径的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property LOG_FILE [get_runs {run_name}]'
    
    @staticmethod
    def get_synthesis_dcp_tcl(run_name: str = "synth_1") -> str:
        """
        生成获取综合检查点路径的 Tcl 命令
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property DIRECTORY [get_runs {run_name}]'
    
    @staticmethod
    def write_checkpoint_tcl(
        output_path: Path,
        force: bool = True,
    ) -> str:
        """
        生成写入检查点的 Tcl 命令
        
        Args:
            output_path: 输出路径
            force: 是否强制覆盖
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'write_checkpoint -force "{output_path}"'
        return cmd


class SynthesisManager:
    """
    综合管理器
    
    提供高级的综合管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化综合管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
    
    def run_synthesis(
        self,
        run_name: str = "synth_1",
        jobs: int = 4,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        运行综合
        
        Args:
            run_name: 综合运行名称
            jobs: 并行任务数
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        commands = SynthesisTclGenerator.run_synthesis_complete_tcl(run_name, jobs)
        result = self.engine.execute(commands, timeout=timeout)
        
        if result.success:
            logger.info(f"综合运行成功: {run_name}")
        else:
            logger.error(f"综合运行失败: {result.errors}")
        
        return result.success
    
    def reset_synthesis(self, run_name: str = "synth_1") -> bool:
        """
        重置综合
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            是否成功
        """
        command = SynthesisTclGenerator.reset_synthesis_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"综合重置成功: {run_name}")
        else:
            logger.error(f"综合重置失败: {result.errors}")
        
        return result.success
    
    def get_synthesis_status(self, run_name: str = "synth_1") -> str:
        """
        获取综合状态
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            状态字符串
        """
        command = SynthesisTclGenerator.get_synthesis_status_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            return result.output.strip()
        return "unknown"
    
    def open_synthesized_design(self, run_name: str = "synth_1") -> bool:
        """
        打开综合设计
        
        Args:
            run_name: 综合运行名称
            
        Returns:
            是否成功
        """
        command = SynthesisTclGenerator.open_synthesized_design_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"打开综合设计成功: {run_name}")
        else:
            logger.error(f"打开综合设计失败: {result.errors}")
        
        return result.success
    
    def get_utilization_report(
        self,
        output_path: Optional[Path] = None,
    ) -> dict:
        """
        获取资源利用率报告
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            资源利用率字典
        """
        command = SynthesisTclGenerator.get_utilization_report_tcl(output_path)
        result = self.engine.execute(command)
        
        utilization = {}
        if result.success:
            utilization = self._parse_utilization_report(result.output)
        
        return utilization
    
    def get_timing_report(
        self,
        output_path: Optional[Path] = None,
        max_paths: int = 10,
    ) -> dict:
        """
        获取时序报告
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            
        Returns:
            时序信息字典
        """
        command = SynthesisTclGenerator.get_timing_report_tcl(
            output_path, max_paths
        )
        result = self.engine.execute(command)
        
        timing = {}
        if result.success:
            timing = self._parse_timing_report(result.output)
        
        return timing
    
    def get_power_report(
        self,
        output_path: Optional[Path] = None,
    ) -> dict:
        """
        获取功耗报告
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            功耗信息字典
        """
        command = SynthesisTclGenerator.get_power_report_tcl(output_path)
        result = self.engine.execute(command)
        
        power = {}
        if result.success:
            power = self._parse_power_report(result.output)
        
        return power
    
    def write_checkpoint(
        self,
        output_path: Path,
    ) -> bool:
        """
        写入检查点
        
        Args:
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        command = SynthesisTclGenerator.write_checkpoint_tcl(output_path)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"检查点写入成功: {output_path}")
        else:
            logger.error(f"检查点写入失败: {result.errors}")
        
        return result.success
    
    def set_strategy(
        self,
        strategy: str,
        run_name: str = "synth_1",
    ) -> bool:
        """
        设置综合策略
        
        Args:
            strategy: 策略名称
            run_name: 综合运行名称
            
        Returns:
            是否成功
        """
        command = SynthesisTclGenerator.set_synthesis_strategy_tcl(
            strategy, run_name
        )
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"综合策略设置成功: {strategy}")
        else:
            logger.error(f"综合策略设置失败: {result.errors}")
        
        return result.success
    
    def _parse_utilization_report(self, report: str) -> dict:
        """
        解析资源利用率报告
        
        Args:
            report: 报告内容
            
        Returns:
            资源利用率字典
        """
        utilization = {}
        
        # 解析表格格式的资源利用率
        patterns = {
            'slice_lut': r'Slice LUTs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'slice_registers': r'Slice Registers\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'lut': r'LUT as Logic\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'bram': r'Block RAM Tile\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'dsp': r'DSPs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'iob': r'IO\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, report)
            if match:
                utilization[key] = {
                    'used': int(match.group(1)),
                    'available': int(match.group(2)),
                    'utilization': float(match.group(3)),
                }
        
        return utilization
    
    def _parse_timing_report(self, report: str) -> dict:
        """
        解析时序报告
        
        Args:
            report: 报告内容
            
        Returns:
            时序信息字典
        """
        timing = {}
        
        # 解析时序摘要
        wns_pattern = r'Design Timing Summary.*?WNS\(ns\)\s*:\s*([\d.-]+)'
        tns_pattern = r'TNS\(ns\)\s*:\s*([\d.-]+)'
        wns_match = re.search(wns_pattern, report, re.DOTALL)
        tns_match = re.search(tns_pattern, report)
        
        if wns_match:
            timing['wns'] = float(wns_match.group(1))
        if tns_match:
            timing['tns'] = float(tns_match.group(1))
        
        # 解析时序约束
        constraints_pattern = r'Timing Constraints.*?(-?\d+\.?\d*)\s+(-?\d+\.?\d*)'
        constraints_match = re.search(constraints_pattern, report, re.DOTALL)
        if constraints_match:
            timing['slack'] = float(constraints_match.group(1))
        
        return timing
    
    def _parse_power_report(self, report: str) -> dict:
        """
        解析功耗报告
        
        Args:
            report: 报告内容
            
        Returns:
            功耗信息字典
        """
        power = {}
        
        # 解析总功耗
        total_pattern = r'Total On-Chip Power:\s*([\d.]+)\s*W'
        total_match = re.search(total_pattern, report)
        if total_match:
            power['total'] = float(total_match.group(1))
        
        # 解析动态功耗
        dynamic_pattern = r'Dynamic:\s*([\d.]+)\s*W'
        dynamic_match = re.search(dynamic_pattern, report)
        if dynamic_match:
            power['dynamic'] = float(dynamic_match.group(1))
        
        # 解析静态功耗
        static_pattern = r'Device Static:\s*([\d.]+)\s*W'
        static_match = re.search(static_pattern, report)
        if static_match:
            power['static'] = float(static_match.group(1))
        
        return power
