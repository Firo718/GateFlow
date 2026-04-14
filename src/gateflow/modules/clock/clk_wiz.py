"""
Clock Wizard 模块封装

提供 Clocking Wizard IP 核的封装，参考 ADI hdl-main 项目的设计模式。
"""

import logging
from typing import Any

from gateflow.modules.base import (
    IPCategory,
    IPModule,
    IPPort,
    IPProperty,
    register_module,
)

logger = logging.getLogger(__name__)


@register_module
class ClockWizard(IPModule):
    """
    Clock Wizard 模块封装
    
    Clocking Wizard 是时钟管理单元 IP，支持 PLL 和 MMCM 配置。
    
    Features:
        - 支持 PLL 和 MMCM 两种原语
        - 可配置多个输出时钟 (最多 7 个)
        - 支持动态重配置
        - 支持扩频功能
    
    Example:
        # 创建 Clock Wizard 实例
        clk_wiz = ClockWizard(tcl_engine)
        result = await clk_wiz.create("clk_wiz_0", {
            "input_frequency": 100.0,
            "output_clocks": [
                {"name": "clk_out1", "frequency": 50.0},
                {"name": "clk_out2", "frequency": 200.0},
            ],
        })
    """
    
    # IP 基本信息
    ip_name = "clk_wiz"
    ip_display_name = "Clocking Wizard"
    ip_category = IPCategory.CLOCK
    ip_version = "6.0"
    ip_description = "Clocking Wizard - Clock Management Unit"
    ip_documentation_url = "https://docs.xilinx.com/r/en-US/pg065-clk-wiz"
    
    def __init__(self, tcl_engine=None):
        """初始化 Clock Wizard 模块"""
        super().__init__(tcl_engine)
    
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 Clock Wizard 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典，支持以下参数：
                - input_frequency: 输入时钟频率 (MHz)，默认 100.0
                - input_jitter: 输入抖动 (UI)，可选
                - use_pll: 是否使用 PLL (False 使用 MMCM)，默认 False
                - output_clocks: 输出时钟列表，每个时钟包含：
                    - name: 时钟名称 (clk_out1 - clk_out7)
                    - frequency: 输出频率 (MHz)
                    - phase: 相位偏移 (度)，可选，默认 0
                    - duty_cycle: 占空比 (0.0-1.0)，可选，默认 0.5
                - reset_type: 复位类型 ("ACTIVE_HIGH", "ACTIVE_LOW")，默认 "ACTIVE_LOW"
                - locked_output: 是否输出 locked 信号，默认 True
                - spread_spectrum: 是否启用扩频，默认 False
        
        Returns:
            创建结果字典
        
        Example:
            # 创建 100MHz 输入，生成 50MHz 和 200MHz 输出
            result = await clk_wiz.create("clk_wiz_0", {
                "input_frequency": 100.0,
                "output_clocks": [
                    {"name": "clk_out1", "frequency": 50.0},
                    {"name": "clk_out2", "frequency": 200.0},
                ],
            })
        """
        if not self._tcl_engine:
            return {
                "success": False,
                "error": "Tcl 引擎未初始化",
            }
        
        # 合并默认配置
        final_config = self.get_default_config()
        if config:
            final_config.update(config)
        
        # 验证配置
        valid, errors = self.validate_config(final_config)
        if not valid:
            return {
                "success": False,
                "error": "配置验证失败",
                "errors": errors,
            }
        
        # 生成创建命令
        commands = [self._generate_create_command(instance_name)]
        
        # 生成配置命令
        if final_config:
            tcl_config = self._convert_config_to_tcl(final_config)
            commands.append(self._generate_config_commands(instance_name, tcl_config))
        
        # 执行命令
        result = await self._tcl_engine.execute_async(commands)
        
        if result.success:
            # 注册实例
            self._register_instance(instance_name, instance_name, final_config)
            logger.info(f"Clock Wizard 实例创建成功: {instance_name}")
        else:
            logger.error(f"Clock Wizard 实例创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "module_name": instance_name,
            "message": f"Clock Wizard 实例 {instance_name} 创建成功" if result.success else "创建失败",
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "input_frequency": 100.0,
            "use_pll": False,
            "output_clocks": [],
            "reset_type": "ACTIVE_LOW",
            "locked_output": True,
            "spread_spectrum": False,
        }
    
    def get_available_properties(self) -> list[IPProperty]:
        """获取可配置属性列表"""
        return [
            IPProperty(
                name="input_frequency",
                value=100.0,
                description="输入时钟频率 (MHz)",
                value_type="float",
                default=100.0,
                min_value=1.0,
                max_value=1000.0,
            ),
            IPProperty(
                name="input_jitter",
                value=None,
                description="输入抖动 (UI)",
                value_type="float",
            ),
            IPProperty(
                name="use_pll",
                value=False,
                description="使用 PLL (False 使用 MMCM)",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="reset_type",
                value="ACTIVE_LOW",
                description="复位类型",
                value_type="string",
                default="ACTIVE_LOW",
                valid_values=["ACTIVE_HIGH", "ACTIVE_LOW"],
            ),
            IPProperty(
                name="locked_output",
                value=True,
                description="是否输出 locked 信号",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="spread_spectrum",
                value=False,
                description="是否启用扩频",
                value_type="bool",
                default=False,
            ),
        ]
    
    def get_ports(self) -> list[IPPort]:
        """获取端口列表"""
        ports = [
            # 输入时钟
            IPPort(
                name="clk_in1",
                direction="input",
                width=1,
                description="输入时钟",
                is_clock=True,
            ),
            IPPort(
                name="clk_in2",
                direction="input",
                width=1,
                description="备用输入时钟",
                is_clock=True,
            ),
            IPPort(
                name="clk_in_sel",
                direction="input",
                width=1,
                description="时钟选择",
            ),
            # 复位
            IPPort(
                name="reset",
                direction="input",
                width=1,
                description="复位信号",
                is_reset=True,
            ),
            IPPort(
                name="resetn",
                direction="input",
                width=1,
                description="复位信号（低有效）",
                is_reset=True,
            ),
            # 输出时钟
            IPPort(
                name="clk_out1",
                direction="output",
                width=1,
                description="输出时钟 1",
                is_clock=True,
            ),
            IPPort(
                name="clk_out2",
                direction="output",
                width=1,
                description="输出时钟 2",
                is_clock=True,
            ),
            IPPort(
                name="clk_out3",
                direction="output",
                width=1,
                description="输出时钟 3",
                is_clock=True,
            ),
            IPPort(
                name="clk_out4",
                direction="output",
                width=1,
                description="输出时钟 4",
                is_clock=True,
            ),
            IPPort(
                name="clk_out5",
                direction="output",
                width=1,
                description="输出时钟 5",
                is_clock=True,
            ),
            IPPort(
                name="clk_out6",
                direction="output",
                width=1,
                description="输出时钟 6",
                is_clock=True,
            ),
            IPPort(
                name="clk_out7",
                direction="output",
                width=1,
                description="输出时钟 7",
                is_clock=True,
            ),
            # 状态信号
            IPPort(
                name="locked",
                direction="output",
                width=1,
                description="时钟锁定指示",
            ),
            IPPort(
                name="clkfb_out",
                direction="output",
                width=1,
                description="反馈时钟输出",
                is_clock=True,
            ),
            # 动态重配置接口
            IPPort(
                name="s_axi_aclk",
                direction="input",
                width=1,
                description="AXI 时钟",
                is_clock=True,
            ),
            IPPort(
                name="s_axi_aresetn",
                direction="input",
                width=1,
                description="AXI 复位（低有效）",
                is_reset=True,
            ),
            IPPort(
                name="s_axi",
                direction="inout",
                description="AXI4-Lite 从接口",
                is_interface=True,
                interface_type="AXI4LITE",
            ),
        ]
        return ports
    
    def _convert_config_to_tcl(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        将配置转换为 Tcl 属性格式
        
        Args:
            config: 用户配置字典
        
        Returns:
            Tcl 属性字典
        """
        tcl_config = {}
        
        # 原语类型
        if "use_pll" in config:
            tcl_config["PRIMITIVE"] = "PLL" if config["use_pll"] else "MMCM"
        
        # 输入时钟频率
        if "input_frequency" in config:
            tcl_config["PRIM_IN_FREQ"] = config["input_frequency"]
        
        # 输入抖动
        if "input_jitter" in config:
            tcl_config["JITTER_SEL"] = config["input_jitter"]
        
        # 复位类型
        if "reset_type" in config:
            tcl_config["RESET_TYPE"] = config["reset_type"]
        
        # locked 输出
        if "locked_output" in config:
            tcl_config["LOCKED_PORT"] = "true" if config["locked_output"] else "false"
        
        # 扩频
        if "spread_spectrum" in config:
            tcl_config["SS_MODE"] = "CENTER_HIGH" if config["spread_spectrum"] else "NONE"
        
        # 输出时钟配置
        output_clocks = config.get("output_clocks", [])
        for i, clk in enumerate(output_clocks, start=1):
            if i <= 7:
                tcl_config[f"CLKOUT{i}_USED"] = "true"
                tcl_config[f"CLKOUT{i}_REQUESTED_OUT_FREQ"] = clk.get("frequency", 100.0)
                tcl_config[f"CLKOUT{i}_REQUESTED_PHASE"] = clk.get("phase", 0.0)
                tcl_config[f"CLKOUT{i}_REQUESTED_DUTY_CYCLE"] = clk.get("duty_cycle", 0.5) * 100
        
        return tcl_config


# 便捷创建函数
async def create_clock_wizard(
    tcl_engine,
    instance_name: str,
    input_frequency: float = 100.0,
    output_clocks: list[dict] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """
    创建 Clock Wizard 实例的便捷函数
    
    Args:
        tcl_engine: Tcl 执行引擎
        instance_name: 实例名称
        input_frequency: 输入频率 (MHz)
        output_clocks: 输出时钟列表
        **kwargs: 其他配置参数
    
    Returns:
        创建结果字典
    
    Example:
        result = await create_clock_wizard(
            engine, "clk_gen",
            input_frequency=100.0,
            output_clocks=[
                {"name": "clk_out1", "frequency": 50.0},
                {"name": "clk_out2", "frequency": 200.0},
            ]
        )
    """
    clk_wiz = ClockWizard(tcl_engine)
    config = {
        "input_frequency": input_frequency,
        **kwargs,
    }
    if output_clocks:
        config["output_clocks"] = output_clocks
    return await clk_wiz.create(instance_name, config)
