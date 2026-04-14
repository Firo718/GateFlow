"""
Vivado 实现相关 Tcl 命令封装

该模块提供实现运行、比特流生成、时序分析等操作的 Tcl 命令生成功能。
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ImplementationStrategy(Enum):
    """实现策略枚举"""
    DEFAULT = "Vivado Implementation Defaults"
    PERFORMANCE = "Performance_Explore"
    AREA = "Area_Explore"
    POWER = "Power_Explore"
    TIMING = "Timing_Explore"


class BitstreamFormat(Enum):
    """比特流格式枚举"""
    BIN = "bin"
    BIT = "bit"
    MST = "mst"  # 用于配置存储器
    RBT = "rbt"  # 原始文本格式


@dataclass
class ImplementationResult:
    """实现结果"""
    success: bool  # 是否成功
    timing_met: bool  # 时序是否满足
    wns: float  # Worst Negative Slack
    tns: float  # Total Negative Slack
    wns_hold: float  # Hold WNS
    utilization: dict  # 资源利用率
    bitstream_path: Optional[Path] = None  # 比特流路径
    report_paths: dict = None  # 报告路径字典
    errors: list[str] = None  # 错误列表
    warnings: list[str] = None  # 警告列表
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.report_paths is None:
            self.report_paths = {}


@dataclass
class TimingSummary:
    """时序摘要"""
    wns: float  # Worst Negative Slack (Setup)
    tns: float  # Total Negative Slack (Setup)
    wns_hold: float  # Worst Negative Slack (Hold)
    tns_hold: float  # Total Negative Slack (Hold)
    wps: float  # Worst Positive Slack
    tps: float  # Total Positive Slack
    timing_met: bool  # 时序是否满足


class ImplementationTclGenerator:
    """
    实现 Tcl 命令生成器
    
    生成用于实现运行、比特流生成、时序分析等操作的 Tcl 命令。
    """
    
    @staticmethod
    def run_implementation_tcl(
        run_name: str = "impl_1",
        jobs: int = 4,
        quiet: bool = False,
    ) -> str:
        """
        生成运行实现的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
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
    def wait_for_implementation_tcl(
        run_name: str = "impl_1",
        timeout: Optional[int] = None,
    ) -> str:
        """
        生成等待实现完成的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            timeout: 超时时间（秒）
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'wait_on_run {run_name}'
        
        if timeout:
            cmd += f' -timeout {timeout}'
        
        return cmd
    
    @staticmethod
    def run_implementation_complete_tcl(
        run_name: str = "impl_1",
        jobs: int = 4,
    ) -> list[str]:
        """
        生成完整的实现运行命令序列
        
        Args:
            run_name: 实现运行名称
            jobs: 并行任务数
            
        Returns:
            Tcl 命令列表
        """
        return [
            ImplementationTclGenerator.run_implementation_tcl(run_name, jobs),
            ImplementationTclGenerator.wait_for_implementation_tcl(run_name),
        ]
    
    @staticmethod
    def run_implementation_steps_tcl(
        run_name: str = "impl_1",
        steps: Optional[list[str]] = None,
        jobs: int = 4,
    ) -> list[str]:
        """
        生成按步骤运行实现的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            steps: 步骤列表（opt_design, place_design, route_design, etc.）
            jobs: 并行任务数
            
        Returns:
            Tcl 命令列表
        """
        if steps is None:
            steps = ['opt_design', 'place_design', 'route_design']
        
        commands = []
        
        # 打开综合设计
        commands.append(f'open_run synth_1')
        
        # 执行各步骤
        for step in steps:
            if step == 'opt_design':
                commands.append('opt_design')
            elif step == 'place_design':
                commands.append('place_design')
            elif step == 'route_design':
                commands.append('route_design')
            elif step == 'phys_opt_design':
                commands.append('phys_opt_design')
            elif step == 'post_route_phys_opt_design':
                commands.append('phys_opt_design -post_route')
        
        return commands
    
    @staticmethod
    def reset_implementation_tcl(run_name: str = "impl_1") -> str:
        """
        生成重置实现的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'reset_run {run_name}'
    
    @staticmethod
    def get_implementation_status_tcl(run_name: str = "impl_1") -> str:
        """
        生成获取实现状态的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property STATUS [get_runs {run_name}]'
    
    @staticmethod
    def open_implemented_design_tcl(run_name: str = "impl_1") -> str:
        """
        生成打开实现设计的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'open_run {run_name}'
    
    @staticmethod
    def close_implemented_design_tcl() -> str:
        """
        生成关闭实现设计的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_design'
    
    @staticmethod
    def generate_bitstream_tcl(
        run_name: str = "impl_1",
        output_path: Optional[Path] = None,
        format: BitstreamFormat = BitstreamFormat.BIT,
        force: bool = True,
    ) -> str:
        """
        生成生成比特流的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            output_path: 输出路径
            format: 比特流格式
            force: 是否强制覆盖
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'launch_runs {run_name} -to_step write_bitstream'
        
        return cmd
    
    @staticmethod
    def write_bitstream_tcl(
        output_path: Path,
        force: bool = True,
    ) -> str:
        """
        生成写入比特流的 Tcl 命令
        
        Args:
            output_path: 输出路径
            force: 是否强制覆盖
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'write_bitstream'
        
        if force:
            cmd += ' -force'
        
        cmd += f' "{output_path}"'
        
        return cmd
    
    @staticmethod
    def get_timing_report_tcl(
        output_path: Optional[Path] = None,
        max_paths: int = 10,
        delay_type: str = "max",
        report_type: str = "summary",
    ) -> str:
        """
        生成获取时序报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
            delay_type: 延迟类型（max, min, min_max）
            report_type: 报告类型（summary, timing）
            
        Returns:
            Tcl 命令字符串
        """
        if report_type == "summary":
            cmd = f'report_timing_summary -max_paths {max_paths}'
        else:
            cmd = f'report_timing -max_paths {max_paths}'
        
        if delay_type != "max":
            cmd += f' -delay_type {delay_type}'
        
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
    def get_drc_report_tcl(
        output_path: Optional[Path] = None,
        checks: Optional[list[str]] = None,
    ) -> str:
        """
        生成获取 DRC 报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            checks: 检查项列表
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'report_drc'
        
        if checks:
            cmd += f' -checks {{{" ".join(checks)}}}'
        
        if output_path:
            cmd += f' -file "{output_path}"'
        
        return cmd
    
    @staticmethod
    def get_methodology_report_tcl(
        output_path: Optional[Path] = None,
    ) -> str:
        """
        生成获取方法论报告的 Tcl 命令
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'report_methodology'
        
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
    def set_implementation_strategy_tcl(
        strategy: str,
        run_name: str = "impl_1",
    ) -> str:
        """
        生成设置实现策略的 Tcl 命令
        
        Args:
            strategy: 策略名称
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property strategy "{strategy}" [get_runs {run_name}]'
    
    @staticmethod
    def set_implementation_property_tcl(
        property_name: str,
        value: str,
        run_name: str = "impl_1",
    ) -> str:
        """
        生成设置实现属性的 Tcl 命令
        
        Args:
            property_name: 属性名称
            value: 属性值
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property {property_name} {value} [get_runs {run_name}]'
    
    @staticmethod
    def write_debug_probes_tcl(
        output_path: Path,
        force: bool = True,
    ) -> str:
        """
        生成写入调试探针文件的 Tcl 命令
        
        Args:
            output_path: 输出路径
            force: 是否强制覆盖
            
        Returns:
            Tcl 命令字符串
        """
        cmd = 'write_debug_probes'
        
        if force:
            cmd += ' -force'
        
        cmd += f' "{output_path}"'
        
        return cmd
    
    @staticmethod
    def get_bitstream_path_tcl(run_name: str = "impl_1") -> str:
        """
        生成获取比特流路径的 Tcl 命令
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property DIRECTORY [get_runs {run_name}]'
    
    @staticmethod
    def opt_design_tcl(
        directive: str = "Explore",
        retiming: bool = False,
    ) -> str:
        """
        生成优化设计的 Tcl 命令
        
        Args:
            directive: 优化指令
            retiming: 是否启用重定时
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'opt_design -directive {directive}'
        
        if retiming:
            cmd += ' -retarget'
        
        return cmd
    
    @staticmethod
    def place_design_tcl(
        directive: str = "Default",
    ) -> str:
        """
        生成布局设计的 Tcl 命令
        
        Args:
            directive: 布局指令
            
        Returns:
            Tcl 命令字符串
        """
        return f'place_design -directive {directive}'
    
    @staticmethod
    def route_design_tcl(
        directive: str = "Default",
        no_timing_driven: bool = False,
    ) -> str:
        """
        生成布线设计的 Tcl 命令
        
        Args:
            directive: 布线指令
            no_timing_driven: 是否禁用时序驱动
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'route_design -directive {directive}'
        
        if no_timing_driven:
            cmd += ' -no_timing_driven'
        
        return cmd
    
    @staticmethod
    def phys_opt_design_tcl(
        directive: str = "Explore",
        post_route: bool = False,
    ) -> str:
        """
        生成物理优化设计的 Tcl 命令
        
        Args:
            directive: 优化指令
            post_route: 是否为布线后优化
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'phys_opt_design -directive {directive}'
        
        if post_route:
            cmd += ' -post_route'
        
        return cmd


class ImplementationManager:
    """
    实现管理器
    
    提供高级的实现管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化实现管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
    
    def run_implementation(
        self,
        run_name: str = "impl_1",
        jobs: int = 4,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        运行实现
        
        Args:
            run_name: 实现运行名称
            jobs: 并行任务数
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        commands = ImplementationTclGenerator.run_implementation_complete_tcl(
            run_name, jobs
        )
        result = self.engine.execute(commands, timeout=timeout)
        
        if result.success:
            logger.info(f"实现运行成功: {run_name}")
        else:
            logger.error(f"实现运行失败: {result.errors}")
        
        return result.success
    
    def run_implementation_steps(
        self,
        steps: Optional[list[str]] = None,
        run_name: str = "impl_1",
    ) -> bool:
        """
        按步骤运行实现
        
        Args:
            steps: 步骤列表
            run_name: 实现运行名称
            
        Returns:
            是否成功
        """
        commands = ImplementationTclGenerator.run_implementation_steps_tcl(
            run_name, steps
        )
        result = self.engine.execute(commands)
        
        if result.success:
            logger.info(f"实现步骤执行成功: {steps}")
        else:
            logger.error(f"实现步骤执行失败: {result.errors}")
        
        return result.success
    
    def reset_implementation(self, run_name: str = "impl_1") -> bool:
        """
        重置实现
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            是否成功
        """
        command = ImplementationTclGenerator.reset_implementation_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"实现重置成功: {run_name}")
        else:
            logger.error(f"实现重置失败: {result.errors}")
        
        return result.success
    
    def get_implementation_status(self, run_name: str = "impl_1") -> str:
        """
        获取实现状态
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            状态字符串
        """
        command = ImplementationTclGenerator.get_implementation_status_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            return result.output.strip()
        return "unknown"
    
    def open_implemented_design(self, run_name: str = "impl_1") -> bool:
        """
        打开实现设计
        
        Args:
            run_name: 实现运行名称
            
        Returns:
            是否成功
        """
        command = ImplementationTclGenerator.open_implemented_design_tcl(run_name)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"打开实现设计成功: {run_name}")
        else:
            logger.error(f"打开实现设计失败: {result.errors}")
        
        return result.success
    
    def generate_bitstream(
        self,
        run_name: str = "impl_1",
        output_path: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        生成比特流
        
        Args:
            run_name: 实现运行名称
            output_path: 输出路径
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        commands = [
            ImplementationTclGenerator.generate_bitstream_tcl(run_name, output_path),
            ImplementationTclGenerator.wait_for_implementation_tcl(run_name),
        ]
        
        result = self.engine.execute(commands, timeout=timeout)
        
        if result.success:
            logger.info(f"比特流生成成功: {run_name}")
        else:
            logger.error(f"比特流生成失败: {result.errors}")
        
        return result.success
    
    def write_bitstream(
        self,
        output_path: Path,
    ) -> bool:
        """
        写入比特流
        
        Args:
            output_path: 输出路径
            
        Returns:
            是否成功
        """
        command = ImplementationTclGenerator.write_bitstream_tcl(output_path)
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"比特流写入成功: {output_path}")
        else:
            logger.error(f"比特流写入失败: {result.errors}")
        
        return result.success
    
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
        command = ImplementationTclGenerator.get_timing_report_tcl(
            output_path, max_paths
        )
        result = self.engine.execute(command)
        
        timing = {}
        if result.success:
            timing = self._parse_timing_report(result.output)
        
        return timing
    
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
        command = ImplementationTclGenerator.get_utilization_report_tcl(output_path)
        result = self.engine.execute(command)
        
        utilization = {}
        if result.success:
            utilization = self._parse_utilization_report(result.output)
        
        return utilization
    
    def get_drc_report(
        self,
        output_path: Optional[Path] = None,
    ) -> dict:
        """
        获取 DRC 报告
        
        Args:
            output_path: 输出文件路径
            
        Returns:
            DRC 结果字典
        """
        command = ImplementationTclGenerator.get_drc_report_tcl(output_path)
        result = self.engine.execute(command)
        
        drc = {}
        if result.success:
            drc = self._parse_drc_report(result.output)
        
        return drc
    
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
        command = ImplementationTclGenerator.get_power_report_tcl(output_path)
        result = self.engine.execute(command)
        
        power = {}
        if result.success:
            power = self._parse_power_report(result.output)
        
        return power
    
    def set_strategy(
        self,
        strategy: str,
        run_name: str = "impl_1",
    ) -> bool:
        """
        设置实现策略
        
        Args:
            strategy: 策略名称
            run_name: 实现运行名称
            
        Returns:
            是否成功
        """
        command = ImplementationTclGenerator.set_implementation_strategy_tcl(
            strategy, run_name
        )
        result = self.engine.execute(command)
        
        if result.success:
            logger.info(f"实现策略设置成功: {strategy}")
        else:
            logger.error(f"实现策略设置失败: {result.errors}")
        
        return result.success
    
    def check_timing(self) -> dict:
        """
        检查时序
        
        Returns:
            时序检查结果
        """
        commands = [
            ImplementationTclGenerator.open_implemented_design_tcl(),
            ImplementationTclGenerator.get_timing_report_tcl(),
        ]
        
        result = self.engine.execute(commands)
        
        timing = {}
        if result.success:
            timing = self._parse_timing_report(result.output)
            timing['timing_met'] = timing.get('wns', 0) >= 0
        
        return timing
    
    def _parse_timing_report(self, report: str) -> dict:
        """
        解析时序报告
        
        Args:
            report: 报告内容
            
        Returns:
            时序信息字典
        """
        timing = {}
        
        # 解析 Setup 时序
        wns_pattern = r'WNS\(ns\)\s*:\s*([\d.-]+)'
        tns_pattern = r'TNS\(ns\)\s*:\s*([\d.-]+)'
        
        wns_match = re.search(wns_pattern, report)
        tns_match = re.search(tns_pattern, report)
        
        if wns_match:
            timing['wns'] = float(wns_match.group(1))
        if tns_match:
            timing['tns'] = float(tns_match.group(1))
        
        # 解析 Hold 时序
        wns_hold_pattern = r'WHS\(ns\)\s*:\s*([\d.-]+)'
        tns_hold_pattern = r'THS\(ns\)\s*:\s*([\d.-]+)'
        
        wns_hold_match = re.search(wns_hold_pattern, report)
        tns_hold_match = re.search(tns_hold_pattern, report)
        
        if wns_hold_match:
            timing['wns_hold'] = float(wns_hold_match.group(1))
        if tns_hold_match:
            timing['tns_hold'] = float(tns_hold_match.group(1))
        
        # 解析 PW (Pulse Width)
        wpw_pattern = r'WPW\(ns\)\s*:\s*([\d.-]+)'
        tpw_pattern = r'TPW\(ns\)\s*:\s*([\d.-]+)'
        
        wpw_match = re.search(wpw_pattern, report)
        tpw_match = re.search(tpw_pattern, report)
        
        if wpw_match:
            timing['wpw'] = float(wpw_match.group(1))
        if tpw_match:
            timing['tpw'] = float(tpw_match.group(1))
        
        return timing
    
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
    
    def _parse_drc_report(self, report: str) -> dict:
        """
        解析 DRC 报告
        
        Args:
            report: 报告内容
            
        Returns:
            DRC 结果字典
        """
        drc = {
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'issues': [],
        }
        
        # 解析 DRC 摘要
        error_pattern = r'Number of Errors:\s*(\d+)'
        warning_pattern = r'Number of Warnings:\s*(\d+)'
        info_pattern = r'Number of Info:\s*(\d+)'
        
        error_match = re.search(error_pattern, report)
        warning_match = re.search(warning_pattern, report)
        info_match = re.search(info_pattern, report)
        
        if error_match:
            drc['errors'] = int(error_match.group(1))
        if warning_match:
            drc['warnings'] = int(warning_match.group(1))
        if info_match:
            drc['info'] = int(info_match.group(1))
        
        return drc
    
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
        
        # 解析功耗裕度
        margin_pattern = r'Power Budget:\s*([\d.]+)\s*W'
        margin_match = re.search(margin_pattern, report)
        if margin_match:
            power['budget'] = float(margin_match.group(1))
        
        return power
