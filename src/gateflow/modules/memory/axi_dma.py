"""
AXI DMA 模块封装

提供 AXI DMA IP 核的封装，参考 ADI hdl-main 项目的设计模式。
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
class AXIDMA(IPModule):
    """
    AXI DMA 模块封装
    
    AXI DMA 是直接内存访问控制器，支持 Scatter-Gather 模式。
    
    Features:
        - 支持 MM2S (Memory to Stream) 和 S2MM (Stream to Memory) 通道
        - 支持 Scatter-Gather 模式
        - 可配置数据位宽
        - 支持中断输出
    
    Example:
        # 创建 AXI DMA 实例
        dma = AXIDMA(tcl_engine)
        result = await dma.create("axi_dma_0", {
            "data_width": 32,
            "include_sg": False,
            "include_mm2s": True,
            "include_s2mm": True,
        })
        
        # 连接 DMA
        await dma.connect("axi_dma_0", {
            "S_AXI_LITE": "axi_interconnect_0/M00_AXI",
            "M_AXI_MM2S": "processing_system7_0/S_AXI_HP0",
            "M_AXI_S2MM": "processing_system7_0/S_AXI_HP0",
        })
    """
    
    # IP 基本信息
    ip_name = "axi_dma"
    ip_display_name = "AXI DMA"
    ip_category = IPCategory.MEMORY
    ip_version = "7.1"
    ip_description = "AXI Direct Memory Access Controller"
    ip_documentation_url = "https://docs.xilinx.com/r/en-US/pg021-axi-dma"
    
    def __init__(self, tcl_engine=None):
        """初始化 AXI DMA 模块"""
        super().__init__(tcl_engine)
    
    async def create(
        self,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        创建 AXI DMA 实例
        
        Args:
            instance_name: 实例名称
            config: 配置字典，支持以下参数：
                - data_width: 数据位宽 (8, 16, 32, 64, 128, 256, 512, 1024)，默认 32
                - include_sg: 是否启用 Scatter-Gather 模式，默认 False
                - include_mm2s: 是否启用 MM2S 通道，默认 True
                - include_s2mm: 是否启用 S2MM 通道，默认 True
                - mm2s_burst_size: MM2S 突发大小 (1-256)，默认 16
                - s2mm_burst_size: S2MM 突发大小 (1-256)，默认 16
                - enable_interrupt: 是否启用中断，默认 True
                - micro_dma: 是否启用 Micro DMA 模式，默认 False
        
        Returns:
            创建结果字典
        
        Example:
            # 创建 32 位 DMA，启用 Scatter-Gather
            result = await dma.create("axi_dma_0", {
                "data_width": 32,
                "include_sg": True,
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
            logger.info(f"AXI DMA 实例创建成功: {instance_name}")
        else:
            logger.error(f"AXI DMA 实例创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "instance_name": instance_name,
            "module_name": instance_name,
            "message": f"AXI DMA 实例 {instance_name} 创建成功" if result.success else "创建失败",
            "errors": result.errors,
            "warnings": result.warnings,
        }
    
    def get_default_config(self) -> dict[str, Any]:
        """获取默认配置"""
        return {
            "data_width": 32,
            "include_sg": False,
            "include_mm2s": True,
            "include_s2mm": True,
            "mm2s_burst_size": 16,
            "s2mm_burst_size": 16,
            "enable_interrupt": True,
            "micro_dma": False,
        }
    
    def get_available_properties(self) -> list[IPProperty]:
        """获取可配置属性列表"""
        return [
            IPProperty(
                name="data_width",
                value=32,
                description="数据位宽",
                value_type="int",
                default=32,
                valid_values=[8, 16, 32, 64, 128, 256, 512, 1024],
            ),
            IPProperty(
                name="include_sg",
                value=False,
                description="启用 Scatter-Gather 模式",
                value_type="bool",
                default=False,
            ),
            IPProperty(
                name="include_mm2s",
                value=True,
                description="启用 MM2S 通道",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="include_s2mm",
                value=True,
                description="启用 S2MM 通道",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="mm2s_burst_size",
                value=16,
                description="MM2S 突发大小",
                value_type="int",
                default=16,
                min_value=1,
                max_value=256,
            ),
            IPProperty(
                name="s2mm_burst_size",
                value=16,
                description="S2MM 突发大小",
                value_type="int",
                default=16,
                min_value=1,
                max_value=256,
            ),
            IPProperty(
                name="enable_interrupt",
                value=True,
                description="启用中断输出",
                value_type="bool",
                default=True,
            ),
            IPProperty(
                name="micro_dma",
                value=False,
                description="启用 Micro DMA 模式",
                value_type="bool",
                default=False,
            ),
        ]
    
    def get_ports(self) -> list[IPPort]:
        """获取端口列表"""
        ports = [
            # AXI Lite 控制接口
            IPPort(
                name="S_AXI_LITE",
                direction="inout",
                description="AXI4-Lite 控制接口",
                is_interface=True,
                interface_type="AXI4LITE",
            ),
            # AXI 主接口 (MM2S)
            IPPort(
                name="M_AXI_MM2S",
                direction="inout",
                description="AXI 主接口 (MM2S)",
                is_interface=True,
                interface_type="AXI4",
            ),
            # AXI 主接口 (S2MM)
            IPPort(
                name="M_AXI_S2MM",
                direction="inout",
                description="AXI 主接口 (S2MM)",
                is_interface=True,
                interface_type="AXI4",
            ),
            # AXI Stream 接口 (MM2S)
            IPPort(
                name="M_AXIS_MM2S",
                direction="inout",
                description="AXI Stream 主接口 (MM2S)",
                is_interface=True,
                interface_type="AXI4STREAM",
            ),
            # AXI Stream 接口 (S2MM)
            IPPort(
                name="S_AXIS_S2MM",
                direction="inout",
                description="AXI Stream 从接口 (S2MM)",
                is_interface=True,
                interface_type="AXI4STREAM",
            ),
            # 时钟和复位
            IPPort(
                name="s_axi_lite_aclk",
                direction="input",
                width=1,
                description="AXI Lite 时钟",
                is_clock=True,
            ),
            IPPort(
                name="m_axi_mm2s_aclk",
                direction="input",
                width=1,
                description="MM2S AXI 时钟",
                is_clock=True,
            ),
            IPPort(
                name="m_axi_s2mm_aclk",
                direction="input",
                width=1,
                description="S2MM AXI 时钟",
                is_clock=True,
            ),
            IPPort(
                name="s_axi_lite_aresetn",
                direction="input",
                width=1,
                description="AXI Lite 复位（低有效）",
                is_reset=True,
            ),
            IPPort(
                name="m_axi_mm2s_aresetn",
                direction="input",
                width=1,
                description="MM2S AXI 复位（低有效）",
                is_reset=True,
            ),
            IPPort(
                name="m_axi_s2mm_aresetn",
                direction="input",
                width=1,
                description="S2MM AXI 复位（低有效）",
                is_reset=True,
            ),
            # 中断
            IPPort(
                name="mm2s_introut",
                direction="output",
                width=1,
                description="MM2S 中断输出",
            ),
            IPPort(
                name="s2mm_introut",
                direction="output",
                width=1,
                description="S2MM 中断输出",
            ),
            # Scatter-Gather 接口
            IPPort(
                name="M_AXI_SG",
                direction="inout",
                description="AXI 主接口 (Scatter-Gather)",
                is_interface=True,
                interface_type="AXI4",
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
        
        # 数据位宽
        if "data_width" in config:
            tcl_config["c_m_axi_mm2s_data_width"] = config["data_width"]
            tcl_config["c_m_axi_s2mm_data_width"] = config["data_width"]
            tcl_config["c_m_axis_mm2s_tdata_width"] = config["data_width"]
            tcl_config["c_s_axis_s2mm_tdata_width"] = config["data_width"]
        
        # Scatter-Gather
        if "include_sg" in config:
            tcl_config["c_include_sg"] = 1 if config["include_sg"] else 0
        
        # MM2S 通道
        if "include_mm2s" in config:
            tcl_config["c_include_mm2s"] = 1 if config["include_mm2s"] else 0
        
        # S2MM 通道
        if "include_s2mm" in config:
            tcl_config["c_include_s2mm"] = 1 if config["include_s2mm"] else 0
        
        # 突发大小
        if "mm2s_burst_size" in config:
            tcl_config["c_mm2s_burst_size"] = config["mm2s_burst_size"]
        
        if "s2mm_burst_size" in config:
            tcl_config["c_s2mm_burst_size"] = config["s2mm_burst_size"]
        
        # 中断
        if "enable_interrupt" in config:
            tcl_config["c_include_mm2s_dre"] = 1 if config["enable_interrupt"] else 0
            tcl_config["c_include_s2mm_dre"] = 1 if config["enable_interrupt"] else 0
        
        # Micro DMA
        if "micro_dma" in config:
            tcl_config["c_micro_dma"] = 1 if config["micro_dma"] else 0
        
        return tcl_config


# 便捷创建函数
async def create_axi_dma(
    tcl_engine,
    instance_name: str,
    data_width: int = 32,
    include_sg: bool = False,
    **kwargs,
) -> dict[str, Any]:
    """
    创建 AXI DMA 实例的便捷函数
    
    Args:
        tcl_engine: Tcl 执行引擎
        instance_name: 实例名称
        data_width: 数据位宽
        include_sg: 是否启用 Scatter-Gather
        **kwargs: 其他配置参数
    
    Returns:
        创建结果字典
    
    Example:
        result = await create_axi_dma(
            engine, "axi_dma_0",
            data_width=64,
            include_sg=True,
        )
    """
    dma = AXIDMA(tcl_engine)
    config = {
        "data_width": data_width,
        "include_sg": include_sg,
        **kwargs,
    }
    return await dma.create(instance_name, config)
