"""
平台模板基类和数据结构

提供平台信息的数据类和模板基类，用于支持各种 FPGA 开发板。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PSType(Enum):
    """PS（Processing System）类型枚举"""
    ZYNQ = "zynq"           # Zynq-7000 系列
    ZYNQMP = "zynqmp"       # Zynq UltraScale+ MPSoC
    VERSAL = "versal"       # Versal ACAP
    ARTIX = "artix"         # Artix-7 (无 PS)
    KINTEX = "kintex"       # Kintex-7/UP (无 PS)
    VIRTEX = "virtex"       # Virtex-7/UP (无 PS)


@dataclass
class PlatformInfo:
    """
    平台信息数据类
    
    存储特定开发板的硬件配置信息。
    
    Attributes:
        name: 平台名称，如 "zcu102", "zed"
        display_name: 显示名称，如 "ZCU102", "Zedboard"
        device: 器件型号，如 "xczu9eg-ffvb1156-2-e"
        board_part: 板级支持包，如 "xilinx.com:zcu102:part0"
        ps_type: PS 类型
        default_clock: 默认时钟频率 (MHz)
        description: 平台描述
        vendor: 厂商
        family: 器件系列
        speed_grade: 速度等级
        package: 封装
        presets_file: PS 预设文件路径（可选）
    """
    name: str
    display_name: str
    device: str
    board_part: str
    ps_type: PSType
    default_clock: float = 100.0
    description: str = ""
    vendor: str = "xilinx"
    family: str = ""
    speed_grade: str = ""
    package: str = ""
    presets_file: str | None = None
    
    def __post_init__(self):
        """初始化后自动解析器件信息"""
        if not self.family:
            self.family = self._parse_family()
        if not self.speed_grade:
            self.speed_grade = self._parse_speed_grade()
        if not self.package:
            self.package = self._parse_package()
    
    def _parse_family(self) -> str:
        """从器件型号解析系列"""
        device_lower = self.device.lower()
        if "xczu" in device_lower:
            return "zynq-ultrascale+"
        elif "xc7z" in device_lower:
            return "zynq-7000"
        elif "xcvc" in device_lower:
            return "versal"
        elif "xc7a" in device_lower:
            return "artix-7"
        elif "xc7k" in device_lower:
            return "kintex-7"
        elif "xcku" in device_lower:
            return "kintex-ultrascale"
        elif "xc7v" in device_lower:
            return "virtex-7"
        elif "xcvu" in device_lower:
            return "virtex-ultrascale"
        return "unknown"
    
    def _parse_speed_grade(self) -> str:
        """从器件型号解析速度等级"""
        # 器件型号格式: xc7z020clg400-1
        # 速度等级是最后一个数字
        parts = self.device.split("-")
        if len(parts) >= 2:
            return parts[-1]
        return ""
    
    def _parse_package(self) -> str:
        """从器件型号解析封装"""
        # 器件型号格式: xc7z020clg400-1
        # 封装是 clg400 部分
        import re
        match = re.search(r'[a-z]+(\d+)', self.device.lower())
        if match:
            return match.group(0)
        return ""
    
    def has_ps(self) -> bool:
        """检查是否有 PS（Processing System）"""
        return self.ps_type in [PSType.ZYNQ, PSType.ZYNQMP, PSType.VERSAL]
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "device": self.device,
            "board_part": self.board_part,
            "ps_type": self.ps_type.value,
            "default_clock": self.default_clock,
            "description": self.description,
            "vendor": self.vendor,
            "family": self.family,
            "speed_grade": self.speed_grade,
            "package": self.package,
            "presets_file": self.presets_file,
            "has_ps": self.has_ps(),
        }


@dataclass
class PSConfig:
    """
    PS（Processing System）配置
    
    用于配置 Zynq/ZynqMP 的 PS 设置。
    """
    # 时钟配置
    fpga_clk0: float = 100.0  # FPGA PL Clock 0 (MHz)
    fpga_clk1: float = 100.0  # FPGA PL Clock 1 (MHz)
    fpga_clk2: float | None = None  # FPGA PL Clock 2 (MHz)
    fpga_clk3: float | None = None  # FPGA PL Clock 3 (MHz)
    
    # DDR 配置
    ddr_enabled: bool = True
    ddr_type: str = "DDR3"  # DDR3, DDR4, LPDDR2
    ddr_clock: float = 533.0  # MHz
    
    # 外设配置
    uart_enabled: bool = True
    uart_baud_rate: int = 115200
    
    ethernet_enabled: bool = False
    ethernet_type: str = "GMII"  # GMII, RGMII, SGMII
    
    usb_enabled: bool = False
    usb_type: str = "USB2.0"
    
    sd_enabled: bool = True
    sd_type: str = "SD2.0"
    
    # GPIO 配置
    gpio_enabled: bool = True
    gpio_inputs: int = 0
    gpio_outputs: int = 0
    
    # 中断配置
    irq_enabled: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "fpga_clk0": self.fpga_clk0,
            "fpga_clk1": self.fpga_clk1,
            "fpga_clk2": self.fpga_clk2,
            "fpga_clk3": self.fpga_clk3,
            "ddr_enabled": self.ddr_enabled,
            "ddr_type": self.ddr_type,
            "ddr_clock": self.ddr_clock,
            "uart_enabled": self.uart_enabled,
            "uart_baud_rate": self.uart_baud_rate,
            "ethernet_enabled": self.ethernet_enabled,
            "ethernet_type": self.ethernet_type,
            "usb_enabled": self.usb_enabled,
            "usb_type": self.usb_type,
            "sd_enabled": self.sd_enabled,
            "sd_type": self.sd_type,
            "gpio_enabled": self.gpio_enabled,
            "gpio_inputs": self.gpio_inputs,
            "gpio_outputs": self.gpio_outputs,
            "irq_enabled": self.irq_enabled,
        }


@dataclass
class PeripheralConfig:
    """
    外设配置
    
    用于配置 PL 端的外设 IP。
    """
    name: str
    ip_type: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "ip_type": self.ip_type,
            "config": self.config,
            "enabled": self.enabled,
        }


class PlatformTemplate(ABC):
    """
    平台模板基类
    
    提供创建特定平台项目的抽象接口。子类需要实现具体的平台配置。
    
    Example:
        ```python
        class ZedboardTemplate(PlatformTemplate):
            @classmethod
            def get_info(cls) -> PlatformInfo:
                return PlatformInfo(
                    name="zed",
                    display_name="Zedboard",
                    device="xc7z020clg484-1",
                    board_part="xilinx.com:zed:part0",
                    ps_type=PSType.ZYNQ,
                )
        ```
    """
    
    @classmethod
    @abstractmethod
    def get_info(cls) -> PlatformInfo:
        """
        获取平台信息
        
        Returns:
            PlatformInfo 实例
        """
        pass
    
    @classmethod
    def get_default_ps_config(cls) -> PSConfig:
        """
        获取默认 PS 配置
        
        Returns:
            PSConfig 实例
        """
        info = cls.get_info()
        return PSConfig(
            fpga_clk0=info.default_clock,
            fpga_clk1=info.default_clock,
        )
    
    @classmethod
    def get_default_peripherals(cls) -> list[PeripheralConfig]:
        """
        获取默认外设配置列表
        
        Returns:
            PeripheralConfig 列表
        """
        return []
    
    @classmethod
    def get_tcl_create_project_commands(
        cls,
        name: str,
        path: str,
    ) -> list[str]:
        """
        生成创建项目的 Tcl 命令
        
        Args:
            name: 项目名称
            path: 项目路径
            
        Returns:
            Tcl 命令列表
        """
        info = cls.get_info()
        
        commands = [
            f'create_project "{name}" "{path}" -part "{info.device}" -force',
            f'set_property board_part {info.board_part} [current_project]',
            'set_property target_language Verilog [current_project]',
            'set_property simulator_language Verilog [current_project]',
            'set_property default_lib work [current_project]',
        ]
        
        return commands
    
    @classmethod
    def get_tcl_setup_ps_commands(
        cls,
        config: PSConfig | None = None,
    ) -> list[str]:
        """
        生成配置 PS 的 Tcl 命令
        
        Args:
            config: PS 配置，如果为 None 则使用默认配置
            
        Returns:
            Tcl 命令列表
        """
        if config is None:
            config = cls.get_default_ps_config()
        
        info = cls.get_info()
        
        if not info.has_ps():
            return []
        
        commands = []
        
        # 创建 Block Design
        commands.append('create_bd_design "system"')
        
        # 添加 PS IP
        if info.ps_type == PSType.ZYNQ:
            commands.append('create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.7 processing_system7_0')
        elif info.ps_type == PSType.ZYNQMP:
            commands.append('create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0')
        
        # 应用预设
        if info.presets_file:
            commands.append(f'source {info.presets_file}')
        else:
            # 使用默认配置
            if info.ps_type == PSType.ZYNQ:
                commands.extend(cls._get_zynq_ps_config_commands(config))
            elif info.ps_type == PSType.ZYNQMP:
                commands.extend(cls._get_zynqmp_ps_config_commands(config))
        
        return commands
    
    @classmethod
    def _get_zynq_ps_config_commands(cls, config: PSConfig) -> list[str]:
        """生成 Zynq-7000 PS 配置命令"""
        commands = []
        
        # 基本配置
        ps_config = {
            'PCW_FPGA0_PERIPHERAL_FREQMHZ': config.fpga_clk0,
            'PCW_FPGA1_PERIPHERAL_FREQMHZ': config.fpga_clk1,
            'PCW_UART1_PERIPHERAL_ENABLE': 1 if config.uart_enabled else 0,
            'PCW_ENET0_PERIPHERAL_ENABLE': 1 if config.ethernet_enabled else 0,
            'PCW_USB0_PERIPHERAL_ENABLE': 1 if config.usb_enabled else 0,
            'PCW_SD0_PERIPHERAL_ENABLE': 1 if config.sd_enabled else 0,
        }
        
        # 构建配置字典
        config_str = ' '.join(f'{k} {{{v}}}' for k, v in ps_config.items())
        commands.append(f'set_property -dict [list {config_str}] [get_bd_cells processing_system7_0]')
        
        return commands
    
    @classmethod
    def _get_zynqmp_ps_config_commands(cls, config: PSConfig) -> list[str]:
        """生成 Zynq UltraScale+ PS 配置命令"""
        commands = []
        
        # 基本配置
        ps_config = {
            'CRL.APLL_TO_FPD_CTRL_REFCLKSEL': 0,
            'CRL.PL0_REF_CTRL_FREQMHZ': config.fpga_clk0,
            'CRL.PL1_REF_CTRL_FREQMHZ': config.fpga_clk1,
        }
        
        if config.fpga_clk2 is not None:
            ps_config['CRL.PL2_REF_CTRL_FREQMHZ'] = config.fpga_clk2
        if config.fpga_clk3 is not None:
            ps_config['CRL.PL3_REF_CTRL_FREQMHZ'] = config.fpga_clk3
        
        # 构建配置字典
        config_str = ' '.join(f'{k} {{{v}}}' for k, v in ps_config.items())
        commands.append(f'set_property -dict [list {config_str}] [get_bd_cells zynq_ultra_ps_e_0]')
        
        return commands
    
    @classmethod
    def get_tcl_add_peripheral_commands(
        cls,
        peripherals: list[PeripheralConfig] | None = None,
    ) -> list[str]:
        """
        生成添加外设的 Tcl 命令
        
        Args:
            peripherals: 外设配置列表，如果为 None 则使用默认配置
            
        Returns:
            Tcl 命令列表
        """
        if peripherals is None:
            peripherals = cls.get_default_peripherals()
        
        commands = []
        
        for periph in peripherals:
            if not periph.enabled:
                continue
            
            # 创建 IP
            commands.append(f'create_bd_cell -type ip -vlnv {periph.ip_type} {periph.name}')
            
            # 配置 IP
            if periph.config:
                config_str = ' '.join(f'{k} {{{v}}}' for k, v in periph.config.items())
                commands.append(f'set_property -dict [list {config_str}] [get_bd_cells {periph.name}]')
        
        return commands
    
    @classmethod
    def get_tcl_complete_bd_commands(cls) -> list[str]:
        """
        生成完成 Block Design 的 Tcl 命令
        
        包括自动连接、验证、生成 wrapper 等。
        
        Returns:
            Tcl 命令列表
        """
        commands = [
            # 应用 AXI 自动连接
            'apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {Auto} Slave {Auto} ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} [get_bd_intf_pins -filter {MODE==Master && VLNV=="xilinx.com:interface:aximm_rtl:1.0"}]',
            # 验证设计
            'validate_bd_design',
            # 保存设计
            'save_bd_design',
            # 生成 wrapper
            'generate_target all [get_files [get_property FILE_NAME [get_bd_designs system]]]',
            # 设置顶层模块
            'set_property top system_wrapper [current_fileset]',
            'update_compile_order -fileset sources_1',
        ]
        
        return commands
    
    @classmethod
    def get_full_project_tcl(
        cls,
        name: str,
        path: str,
        ps_config: PSConfig | None = None,
        peripherals: list[PeripheralConfig] | None = None,
    ) -> list[str]:
        """
        生成完整项目创建的 Tcl 命令序列
        
        Args:
            name: 项目名称
            path: 项目路径
            ps_config: PS 配置
            peripherals: 外设配置列表
            
        Returns:
            完整的 Tcl 命令列表
        """
        commands = []
        
        # 创建项目
        commands.extend(cls.get_tcl_create_project_commands(name, path))
        
        # 配置 PS
        commands.extend(cls.get_tcl_setup_ps_commands(ps_config))
        
        # 添加外设
        commands.extend(cls.get_tcl_add_peripheral_commands(peripherals))
        
        # 完成 Block Design
        commands.extend(cls.get_tcl_complete_bd_commands())
        
        return commands
