"""
Vivado IP 配置模块

提供常用 IP 核的配置和管理功能，包括 Clocking Wizard、FIFO、BRAM 等。
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class IPType(Enum):
    """IP 类型枚举"""
    CLOCKING_WIZARD = "clk_wiz"
    FIFO_GENERATOR = "fifo_generator"
    BLOCK_MEMORY = "blk_mem_gen"
    DISTRIBUTED_MEMORY = "dist_mem_gen"
    DDS_COMPILER = "dds_compiler"
    PLL = "clk_wiz"  # 使用 clk_wiz 配置 PLL
    MMCM = "clk_wiz"  # 使用 clk_wiz 配置 MMCM
    XADC = "xadc_wiz"
    DMA = "axi_dma"
    AXI_INTERCONNECT = "axi_interconnect"
    AXI_BRAM_CTRL = "axi_bram_ctrl"
    PROCESSOR_SYSTEM = "processing_system7"  # Zynq PS
    AXI_GPIO = "axi_gpio"
    AXI_UART = "axi_uartlite"
    AXI_TIMER = "axi_timer"
    AXI_IIC = "axi_iic"
    AXI_SPI = "axi_quad_spi"
    MIG = "mig_7series"  # Memory Interface Generator
    AXI_VDMA = "axi_vdma"  # AXI Video DMA
    AXI_INTERRUPT_CTRL = "axi_intc"  # AXI Interrupt Controller
    ILA = "ila"  # Integrated Logic Analyzer
    VIO = "vio"  # Virtual Input/Output
    JTAG_TO_AXI = "jtag_axi"


class IPInterfaceType(Enum):
    """IP 接口类型枚举"""
    NATIVE = "Native"
    AXI4_STREAM = "AXI4Stream"
    AXI4_LITE = "AXI4Lite"
    AXI4 = "AXI4"


class MemoryType(Enum):
    """存储器类型枚举"""
    RAM = "RAM"
    ROM = "ROM"
    DUAL_PORT = "DualPort"
    SIMPLE_DUAL_PORT = "SimpleDualPort"


@dataclass
class IPConfig:
    """IP 配置基类"""
    name: str
    ip_type: IPType = IPType.CLOCKING_WIZARD  # 默认值，子类会覆盖
    version: str | None = None
    vendor: str = "xilinx.com"
    library: str = "ip"
    module_name: str | None = None  # 自动生成，格式为 {name}_0

    def __post_init__(self):
        """初始化后处理"""
        if self.module_name is None:
            self.module_name = self.name

    def get_ip_vlnv(self) -> str:
        """获取 IP 的 VLNV (Vendor:Library:Name:Version) 标识符"""
        vlnv = f"{self.vendor}:{self.library}:{self.ip_type.value}"
        if self.version:
            vlnv += f":{self.version}"
        return vlnv


@dataclass
class ClockingWizardConfig(IPConfig):
    """Clocking Wizard 配置
    
    用于配置时钟管理单元，包括 PLL 和 MMCM。
    """
    input_frequency: float = 100.0  # MHz，输入时钟频率
    output_clocks: list[dict] = field(default_factory=list)
    # 输出时钟示例: [{"name": "clk_out1", "frequency": 100.0, "phase": 0.0, "duty_cycle": 0.5}]
    reset_type: str = "ACTIVE_HIGH"  # ACTIVE_HIGH, ACTIVE_LOW
    locked_output: bool = True  # 是否输出 locked 信号
    use_pll: bool = False  # True 使用 PLL，False 使用 MMCM
    input_jitter: float | None = None  # 输入抖动（UI 单位）
    spread_spectrum: bool = False  # 是否启用扩频

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.CLOCKING_WIZARD


@dataclass
class FIFOConfig(IPConfig):
    """FIFO Generator 配置
    
    用于配置 FIFO 缓冲器，支持同步和异步模式。
    """
    interface_type: IPInterfaceType = IPInterfaceType.NATIVE
    data_width: int = 32  # 数据位宽
    depth: int = 1024  # FIFO 深度
    almost_full_threshold: int | None = None  # 几乎满阈值
    almost_empty_threshold: int | None = None  # 几乎空阈值
    read_clock: str | None = None  # 异步 FIFO 读时钟
    write_clock: str | None = None  # 异步 FIFO 写时钟
    enable_reset: bool = True  # 是否启用复位
    enable_data_count: bool = False  # 是否启用数据计数
    enable_almost_flags: bool = False  # 是否启用几乎满/空标志
    output_register: bool = False  # 是否使用输出寄存器

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.FIFO_GENERATOR

    def is_synchronous(self) -> bool:
        """判断是否为同步 FIFO"""
        return self.read_clock is None and self.write_clock is None


@dataclass
class BRAMConfig(IPConfig):
    """Block Memory 配置
    
    用于配置块存储器，支持单端口、双端口和 ROM 模式。
    """
    memory_type: MemoryType = MemoryType.RAM
    data_width: int = 32  # 数据位宽
    depth: int = 1024  # 存储深度
    write_enable: bool = True  # 是否有写使能
    init_file: str | None = None  # 初始化文件路径（.coe 或 .mif）
    enable_ecc: bool = False  # 是否启用 ECC
    port_a_width: int | None = None  # 端口 A 数据位宽（双端口模式）
    port_b_width: int | None = None  # 端口 B 数据位宽（双端口模式）
    register_output: bool = True  # 是否寄存输出

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.BLOCK_MEMORY


@dataclass
class AXIInterconnectConfig(IPConfig):
    """AXI Interconnect 配置
    
    用于配置 AXI 互连，支持多主多从拓扑。
    """
    num_master_interfaces: int = 1  # 主接口数量
    num_slave_interfaces: int = 1  # 从接口数量
    data_width: int = 32  # 数据位宽
    address_width: int = 32  # 地址位宽
    enable_protocol_checker: bool = False  # 是否启用协议检查器
    enable_register_slice: bool = False  # 是否启用寄存器切片
    enable_data_fifo: bool = False  # 是否启用数据 FIFO

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_INTERCONNECT


@dataclass
class DMAConfig(IPConfig):
    """AXI DMA 配置
    
    用于配置直接内存访问控制器。
    """
    data_width: int = 32  # 数据位宽
    enable_sg: bool = False  # 是否启用分散/聚集模式
    enable_mm2s: bool = True  # 是否启用内存到流通道
    enable_s2mm: bool = True  # 是否启用流到内存通道
    mm2s_burst_size: int = 16  # MM2S 突发大小
    s2mm_burst_size: int = 16  # S2MM 突发大小

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.DMA


@dataclass
class ZynqPSConfig(IPConfig):
    """Zynq Processing System 配置
    
    用于配置 Zynq 器件的 ARM 处理系统。
    """
    enable_fabric_clock: bool = True  # 是否启用 PL 时钟
    enable_fabric_reset: bool = True  # 是否启用 PL 复位
    enable_ddr: bool = True  # 是否启用 DDR 控制器
    enable_ethernet: bool = False  # 是否启用以太网
    enable_usb: bool = False  # 是否启用 USB
    enable_sd: bool = False  # 是否启用 SD 卡
    enable_uart: bool = True  # 是否启用 UART
    enable_i2c: bool = False  # 是否启用 I2C
    enable_spi: bool = False  # 是否启用 SPI
    enable_gpio: bool = False  # 是否启用 GPIO
    enable_ttc: bool = False  # 是否启用定时器
    enable_can: bool = False  # 是否启用 CAN
    enable_pci: bool = False  # 是否启用 PCIe
    enable_dma: bool = False  # 是否启用 DMA
    enable_fpga_reset: bool = True  # 是否启用 FPGA 复位
    preset: str | None = None  # 预设配置（开发板名称）

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.PROCESSOR_SYSTEM


@dataclass
class XADCConfig(IPConfig):
    """XADC Wizard 配置
    
    用于配置 Xilinx ADC 模块。
    """
    enable_auxiliary_channels: bool = False  # 是否启用辅助通道
    enable_temperature: bool = True  # 是否启用温度传感器
    enable_vccint: bool = True  # 是否启用 VCCINT 监测
    enable_vccaux: bool = True  # 是否启用 VCCAUX 监测
    enable_vccbram: bool = True  # 是否启用 VCCBRAM 监测
    enable_user_supply: bool = False  # 是否启用用户供电
    channel_averaging: int = 0  # 通道平均次数
    sample_rate: int = 96  # 采样率（KSPS）
    enable_drp: bool = True  # 是否启用 DRP 接口
    enable_axi: bool = False  # 是否启用 AXI 接口

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.XADC


@dataclass
class DistributedMemoryConfig(IPConfig):
    """分布式存储器配置
    
    用于配置分布式 RAM/ROM，使用 LUT 资源实现。
    """
    memory_type: str = "ram"  # ram, rom
    data_width: int = 32
    depth: int = 64
    write_enable: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.DISTRIBUTED_MEMORY


@dataclass
class DDSCompilerConfig(IPConfig):
    """DDS 编译器配置
    
    用于配置直接数字频率合成器，生成正弦/余弦波形。
    """
    system_clock: float = 100.0  # MHz
    output_frequency: float = 10.0  # MHz
    phase_width: int = 16
    output_width: int = 16
    phase_increment: str = "Programmable"  # Programmable, Fixed

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.DDS_COMPILER


@dataclass
class AXIDMAConfig(IPConfig):
    """AXI DMA 配置
    
    用于配置直接内存访问控制器，支持 Scatter-Gather 模式。
    """
    include_sg: bool = False  # Scatter-Gather
    data_width: int = 32
    include_mm2s: bool = True
    include_s2mm: bool = True
    mm2s_length_width: int = 23
    s2mm_length_width: int = 23

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.DMA


@dataclass
class AXIVDMAConfig(IPConfig):
    """AXI VDMA 配置
    
    用于配置视频直接内存访问控制器，支持帧缓冲。
    """
    include_mm2s: bool = True
    include_s2mm: bool = True
    data_width: int = 32
    frame_buffer_count: int = 3
    enable_circular_buffer: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_VDMA


@dataclass
class AXIGPIOConfig(IPConfig):
    """AXI GPIO 配置
    
    用于配置通用输入输出接口。
    """
    is_dual: bool = False
    gpio_width: int = 32
    gpio2_width: int = 32
    all_inputs: bool = False
    all_outputs: bool = False
    default_output: int = 0

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_GPIO


@dataclass
class AXIUARTConfig(IPConfig):
    """AXI UART 配置
    
    用于配置串口通信接口。
    """
    baud_rate: int = 115200
    data_bits: int = 8
    parity: str = "None"  # None, Even, Odd
    stop_bits: int = 1
    enable_interrupt: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_UART


@dataclass
class AXITimerConfig(IPConfig):
    """AXI Timer 配置
    
    用于配置定时器/计数器。
    """
    is_dual: bool = False
    count_width: int = 32
    enable_interrupt: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_TIMER


@dataclass
class AXIIICConfig(IPConfig):
    """AXI IIC 配置
    
    用于配置 I2C 通信接口。
    """
    iic_frequency: float = 100.0  # kHz
    enable_interrupt: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_IIC


@dataclass
class AXISPIConfig(IPConfig):
    """AXI SPI 配置
    
    用于配置串行外设接口。
    """
    spi_mode: int = 0  # 0-3
    data_width: int = 8
    clock_frequency: float = 1000.0  # kHz
    enable_interrupt: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_SPI


@dataclass
class AXIBRAMCtrlConfig(IPConfig):
    """AXI BRAM Controller 配置
    
    用于配置 AXI 到 BRAM 的接口控制器。
    """
    data_width: int = 32
    num_bram_ports: int = 1
    ecc_type: str = "None"  # None, Hamming

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_BRAM_CTRL


@dataclass
class AXIInterruptCtrlConfig(IPConfig):
    """AXI Interrupt Controller 配置
    
    用于配置中断控制器。
    """
    num_interrupts: int = 32
    enable_interrupt: bool = True

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.AXI_INTERRUPT_CTRL


@dataclass
class MIGConfig(IPConfig):
    """MIG DDR 控制器配置
    
    用于配置内存接口生成器，支持 DDR3/DDR4/LPDDR4。
    """
    memory_type: str = "DDR4"  # DDR4, DDR3, LPDDR4
    memory_part: str | None = None
    clock_frequency: float = 300.0  # MHz
    data_width: int = 64

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.MIG


@dataclass
class ILAConfig(IPConfig):
    """ILA (Integrated Logic Analyzer) 配置
    
    用于配置片上逻辑分析仪。
    """
    num_probes: int = 1  # 探针数量
    data_depth: int = 1024  # 数据深度
    probe_widths: list[int] = field(default_factory=lambda: [1])  # 各探针位宽
    enable_trigger: bool = True  # 是否启用触发
    enable_storage: bool = True  # 是否启用存储
    trigger_output: bool = False  # 是否输出触发信号

    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        self.ip_type = IPType.ILA


class IPTclGenerator:
    """IP Tcl 命令生成器
    
    生成用于创建、配置和管理 IP 核的 Tcl 命令。
    """

    @staticmethod
    def create_ip_tcl(config: IPConfig) -> str:
        """生成创建 IP 的 Tcl 命令
        
        Args:
            config: IP 配置对象
            
        Returns:
            Tcl 命令字符串
        """
        vlnv = config.get_ip_vlnv()
        cmd = f'create_ip -vlnv {vlnv} -module_name {config.module_name}'
        return cmd

    @staticmethod
    def create_ip_with_config_tcl(config: IPConfig, properties: dict[str, Any]) -> list[str]:
        """生成创建并配置 IP 的完整 Tcl 命令序列
        
        Args:
            config: IP 配置对象
            properties: IP 属性字典
            
        Returns:
            Tcl 命令列表
        """
        commands = []
        
        # 创建 IP
        commands.append(IPTclGenerator.create_ip_tcl(config))
        
        # 设置属性
        if properties:
            commands.extend(IPTclGenerator.set_property_tcl(config.module_name, properties))
        
        return commands

    @staticmethod
    def set_property_tcl(ip_name: str, properties: dict[str, Any]) -> list[str]:
        """生成设置 IP 属性的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            properties: 属性字典
            
        Returns:
            Tcl 命令列表
        """
        commands = []
        
        for prop_name, prop_value in properties.items():
            # 根据属性值类型进行格式化
            if isinstance(prop_value, bool):
                value = "true" if prop_value else "false"
            elif isinstance(prop_value, str):
                value = prop_value
            elif isinstance(prop_value, (list, tuple)):
                # 列表类型，转换为 Tcl 列表格式
                value = " ".join(str(v) for v in prop_value)
            else:
                value = str(prop_value)
            
            commands.append(
                f'set_property -name "{prop_name}" -value "{value}" -objects [get_ips {ip_name}]'
            )
        
        return commands

    @staticmethod
    def get_ip_report_tcl(ip_name: str) -> str:
        """生成获取 IP 报告的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'report_property [get_ips {ip_name}]'

    @staticmethod
    def get_ip_info_tcl(ip_name: str) -> list[str]:
        """生成获取 IP 详细信息的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            
        Returns:
            Tcl 命令列表
        """
        return [
            f'set ip_obj [get_ips {ip_name}]',
            'set ip_name [get_property NAME $ip_obj]',
            'set ip_vlnv [get_property VLNV $ip_obj]',
            'set ip_version [get_property IPDEF $ip_obj]',
            'puts "IP Name: $ip_name"',
            'puts "IP VLNV: $ip_vlnv"',
            'puts "IP Version: $ip_version"',
        ]

    @staticmethod
    def upgrade_ip_tcl(ip_name: str) -> str:
        """生成升级 IP 的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'upgrade_ip [get_ips {ip_name}]'

    @staticmethod
    def generate_output_products_tcl(ip_name: str, force: bool = False) -> str:
        """生成生成输出产品的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            force: 是否强制重新生成
            
        Returns:
            Tcl 命令字符串
        """
        cmd = f'generate_target all [get_ips {ip_name}]'
        if force:
            cmd += ' -force'
        return cmd

    @staticmethod
    def reset_target_tcl(ip_name: str) -> str:
        """生成重置目标的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'reset_target all [get_ips {ip_name}]'

    @staticmethod
    def remove_ip_tcl(ip_name: str) -> str:
        """生成移除 IP 的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'remove_ip [get_ips {ip_name}]'

    @staticmethod
    def list_ips_tcl() -> str:
        """生成列出所有 IP 的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_ips'

    @staticmethod
    def get_ip_properties_tcl(ip_name: str, property_names: list[str] | None = None) -> list[str]:
        """生成获取 IP 指定属性的 Tcl 命令
        
        Args:
            ip_name: IP 名称
            property_names: 属性名称列表，如果为 None 则获取所有属性
            
        Returns:
            Tcl 命令列表
        """
        commands = []
        
        if property_names:
            for prop in property_names:
                commands.append(f'get_property {prop} [get_ips {ip_name}]')
        else:
            commands.append(f'report_property [get_ips {ip_name}]')
        
        return commands

    @staticmethod
    def generate_clocking_wizard_properties(config: ClockingWizardConfig) -> dict[str, Any]:
        """生成 Clocking Wizard IP 的属性字典
        
        Args:
            config: Clocking Wizard 配置
            
        Returns:
            属性字典
        """
        properties = {
            "PRIMITIVE": "MMCM" if not config.use_pll else "PLL",
            "INPUT_MODE": "Single_ended_clock_capable_pin",
            "PRIM_IN_FREQ": config.input_frequency,
            "CLKOUT1_USED": False,
            "CLKOUT2_USED": False,
            "CLKOUT3_USED": False,
            "CLKOUT4_USED": False,
            "CLKOUT5_USED": False,
            "CLKOUT6_USED": False,
            "CLKOUT7_USED": False,
            "RESET_TYPE": config.reset_type,
            "LOCKED_PORT": config.locked_output,
        }
        
        # 设置输出时钟
        for i, clk_out in enumerate(config.output_clocks, start=1):
            if i <= 7:
                properties[f"CLKOUT{i}_USED"] = True
                properties[f"CLKOUT{i}_REQUESTED_OUT_FREQ"] = clk_out.get("frequency", 100.0)
                properties[f"CLKOUT{i}_REQUESTED_PHASE"] = clk_out.get("phase", 0.0)
                properties[f"CLKOUT{i}_REQUESTED_DUTY_CYCLE"] = clk_out.get("duty_cycle", 0.5) * 100
        
        return properties

    @staticmethod
    def generate_fifo_properties(config: FIFOConfig) -> dict[str, Any]:
        """生成 FIFO Generator IP 的属性字典
        
        Args:
            config: FIFO 配置
            
        Returns:
            属性字典
        """
        # 确定 FIFO 类型
        if config.is_synchronous():
            fifo_type = "Independent_Clock_Block_RAM"
        else:
            fifo_type = "Common_Clock_Block_RAM"
        
        properties = {
            "Fifo_Implementation": fifo_type,
            "Interface_Type": config.interface_type.value,
            "Data_Width": config.data_width,
            "Write_Data_Count": config.enable_data_count,
            "Read_Data_Count": config.enable_data_count,
            "Full_Threshold_Assert_Value": config.almost_full_threshold or (config.depth - 1),
            "Empty_Threshold_Assert_Value": config.almost_empty_threshold or 1,
            "Output_Data_Width": config.data_width,
            "Input_Data_Width": config.data_width,
            "Enable_Safety_Circuit": config.enable_reset,
        }
        
        # 设置深度
        if config.is_synchronous():
            properties["Write_Depth"] = config.depth
            properties["Read_Depth"] = config.depth
        else:
            properties["Write_Depth"] = config.depth
            properties["Read_Depth"] = config.depth
        
        return properties

    @staticmethod
    def generate_bram_properties(config: BRAMConfig) -> dict[str, Any]:
        """生成 Block Memory IP 的属性字典
        
        Args:
            config: BRAM 配置
            
        Returns:
            属性字典
        """
        # 确定存储器类型
        memory_type_map = {
            MemoryType.RAM: "True_Dual_Port_RAM",
            MemoryType.ROM: "Single_Port_ROM",
            MemoryType.DUAL_PORT: "True_Dual_Port_RAM",
            MemoryType.SIMPLE_DUAL_PORT: "Simple_Dual_Port_RAM",
        }
        
        properties = {
            "Memory_Type": memory_type_map.get(config.memory_type, "True_Dual_Port_RAM"),
            "Write_Width_A": config.port_a_width or config.data_width,
            "Read_Width_A": config.port_a_width or config.data_width,
            "Write_Width_B": config.port_b_width or config.data_width,
            "Read_Width_B": config.port_b_width or config.data_width,
            "Write_Depth_A": config.depth,
            "Read_Depth_A": config.depth,
            "Write_Depth_B": config.depth,
            "Read_Depth_B": config.depth,
            "Enable_Port_Type_A": "WRITE_FIRST" if config.write_enable else "NO_CHANGE",
            "Enable_Port_Type_B": "WRITE_FIRST" if config.write_enable else "NO_CHANGE",
            "Register_PortA_Output_of_Memory_Primitives": config.register_output,
            "Register_PortB_Output_of_Memory_Primitives": config.register_output,
            "Use_Byte_Write_Enable": config.write_enable,
        }
        
        # 设置初始化文件
        if config.init_file:
            properties["Coe_File"] = config.init_file
            properties["Load_Init_File"] = True
        
        # ECC 配置
        if config.enable_ecc:
            properties["ECC_Type"] = "Hamming"
            properties["ECC_Mode"] = "Both"
        
        return properties

    @staticmethod
    def generate_axi_interconnect_properties(config: AXIInterconnectConfig) -> dict[str, Any]:
        """生成 AXI Interconnect IP 的属性字典
        
        Args:
            config: AXI Interconnect 配置
            
        Returns:
            属性字典
        """
        properties = {
            "NUM_MI": config.num_master_interfaces,
            "NUM_SI": config.num_slave_interfaces,
            "DATA_WIDTH": config.data_width,
            "ADDR_WIDTH": config.address_width,
            "PROTOCOL": "AXI4",
            "ENABLE_PROTOCOL_CHECKERS": config.enable_protocol_checker,
            "ENABLE_ADVANCED_OPTIONS": True,
        }
        
        # 为每个接口配置寄存器切片和 FIFO
        for i in range(config.num_master_interfaces):
            properties[f"MI{i}_ENABLE_REGISTER_SLICE"] = config.enable_register_slice
            properties[f"MI{i}_ENABLE_DATA_FIFO"] = config.enable_data_fifo
        
        for i in range(config.num_slave_interfaces):
            properties[f"SI{i}_ENABLE_REGISTER_SLICE"] = config.enable_register_slice
            properties[f"SI{i}_ENABLE_DATA_FIFO"] = config.enable_data_fifo
        
        return properties

    @staticmethod
    def generate_dma_properties(config: DMAConfig) -> dict[str, Any]:
        """生成 AXI DMA IP 的属性字典
        
        Args:
            config: DMA 配置
            
        Returns:
            属性字典
        """
        properties = {
            "c_include_sg": config.enable_sg,
            "c_include_mm2s": config.enable_mm2s,
            "c_include_s2mm": config.enable_s2mm,
            "c_m_axi_mm2s_data_width": config.data_width,
            "c_m_axi_s2mm_data_width": config.data_width,
            "c_mm2s_burst_size": config.mm2s_burst_size,
            "c_s2mm_burst_size": config.s2mm_burst_size,
        }
        
        return properties

    @staticmethod
    def generate_zynq_ps_properties(config: ZynqPSConfig) -> dict[str, Any]:
        """生成 Zynq Processing System IP 的属性字典
        
        Args:
            config: Zynq PS 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ": 100,
            "CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ": 100 if config.enable_fabric_clock else 0,
            "CONFIG.PCW_FPGA2_PERIPHERAL_FREQMHZ": 100 if config.enable_fabric_clock else 0,
            "CONFIG.PCW_FPGA3_PERIPHERAL_FREQMHZ": 100 if config.enable_fabric_clock else 0,
            "CONFIG.PCW_USE_FABRIC_INTERRUPT": config.enable_fabric_reset,
            "CONFIG.PCW_USE_M_AXI_GP0": True,
            "CONFIG.PCW_USE_M_AXI_GP1": False,
            "CONFIG.PCW_USE_S_AXI_HP0": False,
            "CONFIG.PCW_USE_S_AXI_HP1": False,
            "CONFIG.PCW_USE_S_AXI_HP2": False,
            "CONFIG.PCW_USE_S_AXI_HP3": False,
        }
        
        # DDR 配置
        if config.enable_ddr:
            properties["CONFIG.PCW_DDR_RAM_HIGHADDR"] = "0x1FFFFFFF"
            properties["CONFIG.PCW_UIPARAM_DDR_FREQ_MHZ"] = 525
        
        # 外设配置
        properties["CONFIG.PCW_EN_ETH0"] = config.enable_ethernet
        properties["CONFIG.PCW_EN_USB0"] = config.enable_usb
        properties["CONFIG.PCW_EN_SD0"] = config.enable_sd
        properties["CONFIG.PCW_EN_UART0"] = config.enable_uart
        properties["CONFIG.PCW_EN_I2C0"] = config.enable_i2c
        properties["CONFIG.PCW_EN_SPI0"] = config.enable_spi
        properties["CONFIG.PCW_EN_GPIO"] = config.enable_gpio
        properties["CONFIG.PCW_EN_TTC0"] = config.enable_ttc
        properties["CONFIG.PCW_EN_CAN0"] = config.enable_can
        
        # 预设配置
        if config.preset:
            properties["CONFIG.preset"] = config.preset
        
        return properties

    @staticmethod
    def generate_xadc_properties(config: XADCConfig) -> dict[str, Any]:
        """生成 XADC Wizard IP 的属性字典
        
        Args:
            config: XADC 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.ENABLE_TEMP": config.enable_temperature,
            "CONFIG.ENABLE_VCCINT": config.enable_vccint,
            "CONFIG.ENABLE_VCCAUX": config.enable_vccaux,
            "CONFIG.ENABLE_VCCBRAM": config.enable_vccbram,
            "CONFIG.ENABLE_VUSER": config.enable_user_supply,
            "CONFIG.ENABLE_AUXILIARY": config.enable_auxiliary_channels,
            "CONFIG.AVERAGE_ENABLE": config.channel_averaging > 0,
            "CONFIG.AVERAGE_COUNT": config.channel_averaging,
            "CONFIG.SAMPLE_RATE": config.sample_rate,
            "CONFIG.ENABLE_DPR": config.enable_drp,
            "CONFIG.ENABLE_AXI4": config.enable_axi,
        }
        
        return properties

    @staticmethod
    def generate_ila_properties(config: ILAConfig) -> dict[str, Any]:
        """生成 ILA IP 的属性字典
        
        Args:
            config: ILA 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_NUM_OF_PROBES": config.num_probes,
            "CONFIG.C_DATA_DEPTH": config.data_depth,
            "CONFIG.C_TRIGIN_EN": config.enable_trigger,
            "CONFIG.C_TRIGOUT_EN": config.trigger_output,
            "CONFIG.C_EN_STRG_QUAL": config.enable_storage,
        }
        
        # 设置各探针位宽
        for i, width in enumerate(config.probe_widths[:config.num_probes]):
            properties[f"CONFIG.C_PROBE{i}_WIDTH"] = width
        
        return properties

    @staticmethod
    def generate_distributed_memory_properties(config: DistributedMemoryConfig) -> dict[str, Any]:
        """生成 Distributed Memory IP 的属性字典
        
        Args:
            config: 分布式存储器配置
            
        Returns:
            属性字典
        """
        memory_type_map = {
            "ram": "ram",
            "rom": "rom",
        }
        
        properties = {
            "CONFIG.memory_type": memory_type_map.get(config.memory_type.lower(), "ram"),
            "CONFIG.data_width": config.data_width,
            "CONFIG.depth": config.depth,
            "CONFIG.write_enable": config.write_enable,
        }
        
        return properties

    @staticmethod
    def generate_dds_compiler_properties(config: DDSCompilerConfig) -> dict[str, Any]:
        """生成 DDS Compiler IP 的属性字典
        
        Args:
            config: DDS 编译器配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG DDS_Clock_Rate": config.system_clock,
            "CONFIG.Frequency": config.output_frequency,
            "CONFIG.Phase_Width": config.phase_width,
            "CONFIG.Output_Width": config.output_width,
            "CONFIG.Phase_Increment": config.phase_increment,
            "CONFIG.Noise_Shaping": "None",
            "CONFIG.Output_Frequency1": config.output_frequency,
        }
        
        return properties

    @staticmethod
    def generate_xadc_properties_new(config: XADCConfig) -> dict[str, Any]:
        """生成 XADC Wizard IP 的属性字典（新版）
        
        Args:
            config: XADC 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.ENABLE_AXI4": config.enable_axi,
            "CONFIG.ENABLE_DPR": config.enable_drp,
            "CONFIG.ENABLE_TEMP": config.enable_temperature,
            "CONFIG.ENABLE_VCCINT": config.enable_vccint,
            "CONFIG.ENABLE_VCCAUX": config.enable_vccaux,
            "CONFIG.ENABLE_VCCBRAM": config.enable_vccbram,
            "CONFIG.ENABLE_VUSER": config.enable_user_supply,
            "CONFIG.ENABLE_AUXILIARY": config.enable_auxiliary_channels,
            "CONFIG.AVERAGE_ENABLE": config.channel_averaging > 0,
            "CONFIG.AVERAGE_COUNT": config.channel_averaging,
            "CONFIG.SAMPLE_RATE": config.sample_rate,
        }
        
        return properties

    @staticmethod
    def generate_axi_dma_properties(config: AXIDMAConfig) -> dict[str, Any]:
        """生成 AXI DMA IP 的属性字典
        
        Args:
            config: AXI DMA 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.c_include_sg": config.include_sg,
            "CONFIG.c_include_mm2s": config.include_mm2s,
            "CONFIG.c_include_s2mm": config.include_s2mm,
            "CONFIG.c_m_axi_mm2s_data_width": config.data_width,
            "CONFIG.c_m_axi_s2mm_data_width": config.data_width,
            "CONFIG.c_mm2s_length_width": config.mm2s_length_width,
            "CONFIG.c_s2mm_length_width": config.s2mm_length_width,
            "CONFIG.c_addr_width": 32,
        }
        
        return properties

    @staticmethod
    def generate_axi_vdma_properties(config: AXIVDMAConfig) -> dict[str, Any]:
        """生成 AXI VDMA IP 的属性字典
        
        Args:
            config: AXI VDMA 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.c_include_mm2s": config.include_mm2s,
            "CONFIG.c_include_s2mm": config.include_s2mm,
            "CONFIG.c_m_axi_mm2s_data_width": config.data_width,
            "CONFIG.c_m_axi_s2mm_data_width": config.data_width,
            "CONFIG.c_num_fstores": config.frame_buffer_count,
            "CONFIG.c_use_fsync": 1,
            "CONFIG.c_m_axis_mm2s_tdata_width": config.data_width,
            "CONFIG.c_s_axis_s2mm_tdata_width": config.data_width,
        }
        
        return properties

    @staticmethod
    def generate_axi_gpio_properties(config: AXIGPIOConfig) -> dict[str, Any]:
        """生成 AXI GPIO IP 的属性字典
        
        Args:
            config: AXI GPIO 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_IS_DUAL": config.is_dual,
            "CONFIG.C_GPIO_WIDTH": config.gpio_width,
            "CONFIG.C_GPIO2_WIDTH": config.gpio2_width,
            "CONFIG.C_ALL_INPUTS": config.all_inputs,
            "CONFIG.C_ALL_OUTPUTS": config.all_outputs,
            "CONFIG.C_DOUT_DEFAULT": hex(config.default_output),
            "CONFIG.C_INTERRUPT_PRESENT": True,
        }
        
        return properties

    @staticmethod
    def generate_axi_uart_properties(config: AXIUARTConfig) -> dict[str, Any]:
        """生成 AXI UART IP 的属性字典
        
        Args:
            config: AXI UART 配置
            
        Returns:
            属性字典
        """
        parity_map = {
            "None": 0,
            "Even": 1,
            "Odd": 2,
        }
        
        properties = {
            "CONFIG.C_BAUDRATE": config.baud_rate,
            "CONFIG.C_DATA_BITS": config.data_bits,
            "CONFIG.C_USE_PARITY": parity_map.get(config.parity, 0),
            "CONFIG.C_PARITY": config.parity,
            "CONFIG.C_STOP_BITS": config.stop_bits,
            "CONFIG.C_S_AXI_ACLK_FREQ_HZ": 100000000,  # 100MHz
        }
        
        if config.enable_interrupt:
            properties["CONFIG.C_HAS_INTERRUPT"] = True
        
        return properties

    @staticmethod
    def generate_axi_timer_properties(config: AXITimerConfig) -> dict[str, Any]:
        """生成 AXI Timer IP 的属性字典
        
        Args:
            config: AXI Timer 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_COUNT_WIDTH": config.count_width,
            "CONFIG.C_ONE_TIMER_ONLY": not config.is_dual,
            "CONFIG.C_ENABLE_TIMER2": config.is_dual,
        }
        
        if config.enable_interrupt:
            properties["CONFIG.C_HAS_INTERRUPT"] = True
        
        return properties

    @staticmethod
    def generate_axi_iic_properties(config: AXIIICConfig) -> dict[str, Any]:
        """生成 AXI IIC IP 的属性字典
        
        Args:
            config: AXI IIC 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_IIC_FREQ": int(config.iic_frequency * 1000),  # 转换为 Hz
            "CONFIG.C_S_AXI_ACLK_FREQ_HZ": 100000000,  # 100MHz
        }
        
        if config.enable_interrupt:
            properties["CONFIG.C_HAS_INTR"] = True
        
        return properties

    @staticmethod
    def generate_axi_spi_properties(config: AXISPIConfig) -> dict[str, Any]:
        """生成 AXI SPI IP 的属性字典
        
        Args:
            config: AXI SPI 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_SPI_MODE": config.spi_mode,
            "CONFIG.C_NUM_TRANSFER_BITS": config.data_width,
            "CONFIG.C_SCK_RATIO": int(100000 / config.clock_frequency),  # 时钟分频比
            "CONFIG.C_NUM_SS_BITS": 1,
        }
        
        if config.enable_interrupt:
            properties["CONFIG.C_HAS_INTERRUPT"] = True
        
        return properties

    @staticmethod
    def generate_axi_bram_ctrl_properties(config: AXIBRAMCtrlConfig) -> dict[str, Any]:
        """生成 AXI BRAM Controller IP 的属性字典
        
        Args:
            config: AXI BRAM Controller 配置
            
        Returns:
            属性字典
        """
        ecc_map = {
            "None": 0,
            "Hamming": 1,
        }
        
        properties = {
            "CONFIG.DATA_WIDTH": config.data_width,
            "CONFIG.NUM_BRAM_PORTS": config.num_bram_ports,
            "CONFIG.ECC_TYPE": ecc_map.get(config.ecc_type, 0),
            "CONFIG.ECC_MODE": config.ecc_type,
        }
        
        return properties

    @staticmethod
    def generate_axi_interrupt_ctrl_properties(config: AXIInterruptCtrlConfig) -> dict[str, Any]:
        """生成 AXI Interrupt Controller IP 的属性字典
        
        Args:
            config: AXI Interrupt Controller 配置
            
        Returns:
            属性字典
        """
        properties = {
            "CONFIG.C_NUM_INTR_INPUTS": config.num_interrupts,
            "CONFIG.C_HAS_IPR": True,
            "CONFIG.C_HAS_IER": True,
            "CONFIG.C_HAS_ILR": True,
            "CONFIG.C_HAS_SIE": True,
            "CONFIG.C_HAS_CIE": True,
            "CONFIG.C_HAS_IVR": True,
        }
        
        if config.enable_interrupt:
            properties["CONFIG.C_HAS_IRQ"] = True
        
        return properties

    @staticmethod
    def generate_mig_properties(config: MIGConfig) -> dict[str, Any]:
        """生成 MIG DDR 控制器 IP 的属性字典
        
        Args:
            config: MIG 配置
            
        Returns:
            属性字典
        """
        memory_type_map = {
            "DDR4": "DDR4",
            "DDR3": "DDR3",
            "LPDDR4": "LPDDR4",
        }
        
        properties = {
            "CONFIG.MEMORY_TYPE": memory_type_map.get(config.memory_type, "DDR4"),
            "CONFIG.C_MEMORY_DEVICE_TYPE": memory_type_map.get(config.memory_type, "DDR4"),
            "CONFIG.C_SYSTEM_CLOCK": f"{int(config.clock_frequency)}MHz",
            "CONFIG.C_DDR_DATA_WIDTH": config.data_width,
            "CONFIG.C_DDR_DATA_WIDTH_RESERVED": config.data_width,
        }
        
        # 如果指定了具体型号
        if config.memory_part:
            properties["CONFIG.C_PART"] = config.memory_part
        
        return properties


class IPManager:
    """IP 管理器
    
    提供高级的 IP 创建、配置和管理接口。
    """
    
    def __init__(self, tcl_engine):
        """初始化 IP 管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self._created_ips: dict[str, IPConfig] = {}

    async def create_clocking_wizard(self, config: ClockingWizardConfig) -> dict:
        """创建 Clocking Wizard IP
        
        Args:
            config: Clocking Wizard 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_clocking_wizard_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_fifo(self, config: FIFOConfig) -> dict:
        """创建 FIFO IP
        
        Args:
            config: FIFO 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_fifo_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_bram(self, config: BRAMConfig) -> dict:
        """创建 Block Memory IP
        
        Args:
            config: BRAM 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_bram_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_interconnect(self, config: AXIInterconnectConfig) -> dict:
        """创建 AXI Interconnect IP
        
        Args:
            config: AXI Interconnect 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_interconnect_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_dma(self, config: DMAConfig) -> dict:
        """创建 AXI DMA IP
        
        Args:
            config: DMA 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_dma_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_zynq_ps(self, config: ZynqPSConfig) -> dict:
        """创建 Zynq Processing System IP
        
        Args:
            config: Zynq PS 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_zynq_ps_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_xadc(self, config: XADCConfig) -> dict:
        """创建 XADC IP
        
        Args:
            config: XADC 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_xadc_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_ila(self, config: ILAConfig) -> dict:
        """创建 ILA IP
        
        Args:
            config: ILA 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_ila_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_distributed_memory(self, config: DistributedMemoryConfig) -> dict:
        """创建分布式存储器 IP
        
        Args:
            config: 分布式存储器配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_distributed_memory_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_dds_compiler(self, config: DDSCompilerConfig) -> dict:
        """创建 DDS 编译器 IP
        
        Args:
            config: DDS 编译器配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_dds_compiler_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_xadc_new(self, config: XADCConfig) -> dict:
        """创建 XADC IP（使用新配置）
        
        Args:
            config: XADC 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_xadc_properties_new(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_dma(self, config: AXIDMAConfig) -> dict:
        """创建 AXI DMA IP
        
        Args:
            config: AXI DMA 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_dma_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_vdma(self, config: AXIVDMAConfig) -> dict:
        """创建 AXI VDMA IP
        
        Args:
            config: AXI VDMA 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_vdma_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_gpio(self, config: AXIGPIOConfig) -> dict:
        """创建 AXI GPIO IP
        
        Args:
            config: AXI GPIO 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_gpio_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_uart(self, config: AXIUARTConfig) -> dict:
        """创建 AXI UART IP
        
        Args:
            config: AXI UART 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_uart_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_timer(self, config: AXITimerConfig) -> dict:
        """创建 AXI Timer IP
        
        Args:
            config: AXI Timer 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_timer_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_iic(self, config: AXIIICConfig) -> dict:
        """创建 AXI IIC IP
        
        Args:
            config: AXI IIC 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_iic_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_spi(self, config: AXISPIConfig) -> dict:
        """创建 AXI SPI IP
        
        Args:
            config: AXI SPI 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_spi_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_bram_ctrl(self, config: AXIBRAMCtrlConfig) -> dict:
        """创建 AXI BRAM Controller IP
        
        Args:
            config: AXI BRAM Controller 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_bram_ctrl_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_axi_interrupt_ctrl(self, config: AXIInterruptCtrlConfig) -> dict:
        """创建 AXI Interrupt Controller IP
        
        Args:
            config: AXI Interrupt Controller 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_axi_interrupt_ctrl_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_mig(self, config: MIGConfig) -> dict:
        """创建 MIG DDR 控制器 IP
        
        Args:
            config: MIG 配置
            
        Returns:
            执行结果字典
        """
        properties = IPTclGenerator.generate_mig_properties(config)
        return await self.create_ip_with_properties(config, properties)

    async def create_ip_with_properties(
        self,
        config: IPConfig,
        properties: dict[str, Any]
    ) -> dict:
        """创建 IP 并设置属性
        
        Args:
            config: IP 配置
            properties: 属性字典
            
        Returns:
            执行结果字典
        """
        commands = IPTclGenerator.create_ip_with_config_tcl(config, properties)
        result = await self.engine.execute_async(commands)
        
        if result.success:
            self._created_ips[config.name] = config
            logger.info(f"IP 创建成功: {config.name} ({config.ip_type.value})")
        else:
            logger.error(f"IP 创建失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": config.name,
            "module_name": config.module_name,
            "errors": result.errors,
            "warnings": result.warnings,
            "output": result.output,
        }

    async def create_ip(self, config: IPConfig) -> dict:
        """通用创建 IP 方法
        
        根据配置类型自动选择合适的创建方法。
        
        Args:
            config: IP 配置对象
            
        Returns:
            执行结果字典
        """
        # 根据配置类型生成属性
        properties = {}
        
        if isinstance(config, ClockingWizardConfig):
            properties = IPTclGenerator.generate_clocking_wizard_properties(config)
        elif isinstance(config, FIFOConfig):
            properties = IPTclGenerator.generate_fifo_properties(config)
        elif isinstance(config, BRAMConfig):
            properties = IPTclGenerator.generate_bram_properties(config)
        elif isinstance(config, AXIInterconnectConfig):
            properties = IPTclGenerator.generate_axi_interconnect_properties(config)
        elif isinstance(config, DMAConfig):
            properties = IPTclGenerator.generate_dma_properties(config)
        elif isinstance(config, ZynqPSConfig):
            properties = IPTclGenerator.generate_zynq_ps_properties(config)
        elif isinstance(config, XADCConfig):
            properties = IPTclGenerator.generate_xadc_properties(config)
        elif isinstance(config, ILAConfig):
            properties = IPTclGenerator.generate_ila_properties(config)
        elif isinstance(config, DistributedMemoryConfig):
            properties = IPTclGenerator.generate_distributed_memory_properties(config)
        elif isinstance(config, DDSCompilerConfig):
            properties = IPTclGenerator.generate_dds_compiler_properties(config)
        elif isinstance(config, AXIDMAConfig):
            properties = IPTclGenerator.generate_axi_dma_properties(config)
        elif isinstance(config, AXIVDMAConfig):
            properties = IPTclGenerator.generate_axi_vdma_properties(config)
        elif isinstance(config, AXIGPIOConfig):
            properties = IPTclGenerator.generate_axi_gpio_properties(config)
        elif isinstance(config, AXIUARTConfig):
            properties = IPTclGenerator.generate_axi_uart_properties(config)
        elif isinstance(config, AXITimerConfig):
            properties = IPTclGenerator.generate_axi_timer_properties(config)
        elif isinstance(config, AXIIICConfig):
            properties = IPTclGenerator.generate_axi_iic_properties(config)
        elif isinstance(config, AXISPIConfig):
            properties = IPTclGenerator.generate_axi_spi_properties(config)
        elif isinstance(config, AXIBRAMCtrlConfig):
            properties = IPTclGenerator.generate_axi_bram_ctrl_properties(config)
        elif isinstance(config, AXIInterruptCtrlConfig):
            properties = IPTclGenerator.generate_axi_interrupt_ctrl_properties(config)
        elif isinstance(config, MIGConfig):
            properties = IPTclGenerator.generate_mig_properties(config)
        else:
            logger.warning(f"未知的 IP 配置类型: {type(config)}，使用默认配置")
        
        return await self.create_ip_with_properties(config, properties)

    async def get_ip_info(self, ip_name: str) -> dict:
        """获取 IP 信息
        
        Args:
            ip_name: IP 名称
            
        Returns:
            IP 信息字典
        """
        commands = IPTclGenerator.get_ip_info_tcl(ip_name)
        result = await self.engine.execute_async(commands)
        
        info = {
            "name": ip_name,
            "exists": result.success,
        }
        
        if result.success:
            # 解析输出获取 IP 信息
            for line in result.output.split('\n'):
                if line.startswith('IP Name:'):
                    info['name'] = line.split(':', 1)[1].strip()
                elif line.startswith('IP VLNV:'):
                    info['vlnv'] = line.split(':', 1)[1].strip()
                elif line.startswith('IP Version:'):
                    info['version'] = line.split(':', 1)[1].strip()
        else:
            info['errors'] = result.errors
        
        return info

    async def get_ip_properties(
        self,
        ip_name: str,
        property_names: list[str] | None = None
    ) -> dict:
        """获取 IP 属性
        
        Args:
            ip_name: IP 名称
            property_names: 要获取的属性名称列表，如果为 None 则获取所有属性
            
        Returns:
            属性字典
        """
        commands = IPTclGenerator.get_ip_properties_tcl(ip_name, property_names)
        result = await self.engine.execute_async(commands)
        
        properties = {}
        
        if result.success:
            # 解析属性输出
            # Vivado 输出格式: Property Name: Value
            for line in result.output.split('\n'):
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        prop_name = parts[0].strip()
                        prop_value = parts[1].strip()
                        properties[prop_name] = prop_value
        else:
            properties['errors'] = result.errors
        
        return properties

    async def list_ips(self) -> list[dict]:
        """列出所有 IP
        
        Returns:
            IP 信息列表
        """
        command = IPTclGenerator.list_ips_tcl()
        result = await self.engine.execute_async(command)
        
        ips = []
        
        if result.success:
            # 解析 IP 列表
            ip_names = result.output.strip().split()
            for ip_name in ip_names:
                ip_name = ip_name.strip()
                if ip_name:
                    ips.append({
                        "name": ip_name,
                        "module_name": ip_name,
                    })
        else:
            logger.error(f"获取 IP 列表失败: {result.errors}")
        
        return ips

    async def upgrade_ip(self, ip_name: str) -> dict:
        """升级 IP
        
        将 IP 升级到当前 Vivado 版本。
        
        Args:
            ip_name: IP 名称
            
        Returns:
            执行结果字典
        """
        command = IPTclGenerator.upgrade_ip_tcl(ip_name)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"IP 升级成功: {ip_name}")
        else:
            logger.error(f"IP 升级失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    async def generate_output_products(
        self,
        ip_name: str,
        force: bool = False
    ) -> dict:
        """生成输出产品
        
        生成 IP 的输出文件，包括实例化模板、综合文件等。
        
        Args:
            ip_name: IP 名称
            force: 是否强制重新生成
            
        Returns:
            执行结果字典
        """
        command = IPTclGenerator.generate_output_products_tcl(ip_name, force)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"IP 输出产品生成成功: {ip_name}")
        else:
            logger.error(f"IP 输出产品生成失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    async def reset_target(self, ip_name: str) -> dict:
        """重置 IP 目标
        
        清除已生成的输出产品。
        
        Args:
            ip_name: IP 名称
            
        Returns:
            执行结果字典
        """
        command = IPTclGenerator.reset_target_tcl(ip_name)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"IP 目标重置成功: {ip_name}")
        else:
            logger.error(f"IP 目标重置失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "errors": result.errors,
        }

    async def remove_ip(self, ip_name: str) -> dict:
        """移除 IP
        
        从项目中删除指定的 IP。
        
        Args:
            ip_name: IP 名称
            
        Returns:
            执行结果字典
        """
        command = IPTclGenerator.remove_ip_tcl(ip_name)
        result = await self.engine.execute_async(command)
        
        if result.success:
            # 从缓存中移除
            if ip_name in self._created_ips:
                del self._created_ips[ip_name]
            logger.info(f"IP 移除成功: {ip_name}")
        else:
            logger.error(f"IP 移除失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "errors": result.errors,
        }

    async def set_ip_properties(
        self,
        ip_name: str,
        properties: dict[str, Any]
    ) -> dict:
        """设置 IP 属性
        
        Args:
            ip_name: IP 名称
            properties: 属性字典
            
        Returns:
            执行结果字典
        """
        commands = IPTclGenerator.set_property_tcl(ip_name, properties)
        result = await self.engine.execute_async(commands)
        
        if result.success:
            logger.info(f"IP 属性设置成功: {ip_name}")
        else:
            logger.error(f"IP 属性设置失败: {result.errors}")
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "errors": result.errors,
            "warnings": result.warnings,
        }

    async def get_ip_report(self, ip_name: str) -> dict:
        """获取 IP 报告
        
        Args:
            ip_name: IP 名称
            
        Returns:
            报告字典
        """
        command = IPTclGenerator.get_ip_report_tcl(ip_name)
        result = await self.engine.execute_async(command)
        
        return {
            "success": result.success,
            "ip_name": ip_name,
            "report": result.output,
            "errors": result.errors,
        }

    def get_created_ip(self, ip_name: str) -> IPConfig | None:
        """获取已创建的 IP 配置
        
        Args:
            ip_name: IP 名称
            
        Returns:
            IP 配置对象，如果不存在则返回 None
        """
        return self._created_ips.get(ip_name)

    def list_created_ips(self) -> list[str]:
        """列出已创建的 IP 名称
        
        Returns:
            IP 名称列表
        """
        return list(self._created_ips.keys())

    async def create_ip_instance(
        self,
        config: IPConfig,
        instance_name: str,
        properties: dict[str, Any] | None = None
    ) -> dict:
        """创建 IP 实例
        
        创建 IP 并生成输出产品。
        
        Args:
            config: IP 配置
            instance_name: 实例名称
            properties: 额外属性（可选）
            
        Returns:
            执行结果字典
        """
        # 创建 IP
        if properties is None:
            result = await self.create_ip(config)
        else:
            result = await self.create_ip_with_properties(config, properties)
        
        if not result["success"]:
            return result
        
        # 生成输出产品
        gen_result = await self.generate_output_products(config.module_name)
        
        return {
            "success": gen_result["success"],
            "ip_name": config.name,
            "module_name": config.module_name,
            "instance_name": instance_name,
            "errors": gen_result.get("errors", []),
            "warnings": gen_result.get("warnings", []),
        }

    async def batch_create_ips(self, configs: list[IPConfig]) -> dict:
        """批量创建 IP
        
        Args:
            configs: IP 配置列表
            
        Returns:
            批量执行结果字典
        """
        results = {
            "success": True,
            "created": [],
            "failed": [],
        }
        
        for config in configs:
            result = await self.create_ip(config)
            
            if result["success"]:
                results["created"].append(config.name)
            else:
                results["failed"].append({
                    "name": config.name,
                    "errors": result.get("errors", []),
                })
                results["success"] = False
        
        logger.info(
            f"批量创建 IP 完成: 成功 {len(results['created'])} 个, "
            f"失败 {len(results['failed'])} 个"
        )
        
        return results

    async def batch_generate_output_products(
        self,
        ip_names: list[str],
        force: bool = False
    ) -> dict:
        """批量生成输出产品
        
        Args:
            ip_names: IP 名称列表
            force: 是否强制重新生成
            
        Returns:
            批量执行结果字典
        """
        results = {
            "success": True,
            "generated": [],
            "failed": [],
        }
        
        for ip_name in ip_names:
            result = await self.generate_output_products(ip_name, force)
            
            if result["success"]:
                results["generated"].append(ip_name)
            else:
                results["failed"].append({
                    "name": ip_name,
                    "errors": result.get("errors", []),
                })
                results["success"] = False
        
        return results


# 便捷函数
def create_clocking_wizard_config(
    name: str,
    input_freq: float,
    output_clocks: list[dict],
    use_pll: bool = False,
    **kwargs
) -> ClockingWizardConfig:
    """创建 Clocking Wizard 配置的便捷函数
    
    Args:
        name: IP 名称
        input_freq: 输入频率（MHz）
        output_clocks: 输出时钟列表
        use_pll: 是否使用 PLL
        **kwargs: 其他参数
        
    Returns:
        ClockingWizardConfig 对象
    """
    return ClockingWizardConfig(
        name=name,
        input_frequency=input_freq,
        output_clocks=output_clocks,
        use_pll=use_pll,
        **kwargs
    )


def create_fifo_config(
    name: str,
    data_width: int,
    depth: int,
    synchronous: bool = True,
    **kwargs
) -> FIFOConfig:
    """创建 FIFO 配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        depth: FIFO 深度
        synchronous: 是否为同步 FIFO
        **kwargs: 其他参数
        
    Returns:
        FIFOConfig 对象
    """
    return FIFOConfig(
        name=name,
        data_width=data_width,
        depth=depth,
        **kwargs
    )


def create_bram_config(
    name: str,
    data_width: int,
    depth: int,
    memory_type: MemoryType = MemoryType.RAM,
    **kwargs
) -> BRAMConfig:
    """创建 BRAM 配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        depth: 存储深度
        memory_type: 存储器类型
        **kwargs: 其他参数
        
    Returns:
        BRAMConfig 对象
    """
    return BRAMConfig(
        name=name,
        data_width=data_width,
        depth=depth,
        memory_type=memory_type,
        **kwargs
    )


def create_distributed_memory_config(
    name: str,
    data_width: int = 32,
    depth: int = 64,
    memory_type: str = "ram",
    **kwargs
) -> DistributedMemoryConfig:
    """创建分布式存储器配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        depth: 存储深度
        memory_type: 存储器类型 (ram/rom)
        **kwargs: 其他参数
        
    Returns:
        DistributedMemoryConfig 对象
    """
    return DistributedMemoryConfig(
        name=name,
        data_width=data_width,
        depth=depth,
        memory_type=memory_type,
        **kwargs
    )


def create_dds_compiler_config(
    name: str,
    system_clock: float = 100.0,
    output_frequency: float = 10.0,
    **kwargs
) -> DDSCompilerConfig:
    """创建 DDS 编译器配置的便捷函数
    
    Args:
        name: IP 名称
        system_clock: 系统时钟频率（MHz）
        output_frequency: 输出频率（MHz）
        **kwargs: 其他参数
        
    Returns:
        DDSCompilerConfig 对象
    """
    return DDSCompilerConfig(
        name=name,
        system_clock=system_clock,
        output_frequency=output_frequency,
        **kwargs
    )


def create_axi_dma_config(
    name: str,
    data_width: int = 32,
    include_sg: bool = False,
    **kwargs
) -> AXIDMAConfig:
    """创建 AXI DMA 配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        include_sg: 是否启用 Scatter-Gather
        **kwargs: 其他参数
        
    Returns:
        AXIDMAConfig 对象
    """
    return AXIDMAConfig(
        name=name,
        data_width=data_width,
        include_sg=include_sg,
        **kwargs
    )


def create_axi_vdma_config(
    name: str,
    data_width: int = 32,
    frame_buffer_count: int = 3,
    **kwargs
) -> AXIVDMAConfig:
    """创建 AXI VDMA 配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        frame_buffer_count: 帧缓冲数量
        **kwargs: 其他参数
        
    Returns:
        AXIVDMAConfig 对象
    """
    return AXIVDMAConfig(
        name=name,
        data_width=data_width,
        frame_buffer_count=frame_buffer_count,
        **kwargs
    )


def create_axi_gpio_config(
    name: str,
    gpio_width: int = 32,
    is_dual: bool = False,
    **kwargs
) -> AXIGPIOConfig:
    """创建 AXI GPIO 配置的便捷函数
    
    Args:
        name: IP 名称
        gpio_width: GPIO 位宽
        is_dual: 是否双通道
        **kwargs: 其他参数
        
    Returns:
        AXIGPIOConfig 对象
    """
    return AXIGPIOConfig(
        name=name,
        gpio_width=gpio_width,
        is_dual=is_dual,
        **kwargs
    )


def create_axi_uart_config(
    name: str,
    baud_rate: int = 115200,
    **kwargs
) -> AXIUARTConfig:
    """创建 AXI UART 配置的便捷函数
    
    Args:
        name: IP 名称
        baud_rate: 波特率
        **kwargs: 其他参数
        
    Returns:
        AXIUARTConfig 对象
    """
    return AXIUARTConfig(
        name=name,
        baud_rate=baud_rate,
        **kwargs
    )


def create_axi_timer_config(
    name: str,
    count_width: int = 32,
    is_dual: bool = False,
    **kwargs
) -> AXITimerConfig:
    """创建 AXI Timer 配置的便捷函数
    
    Args:
        name: IP 名称
        count_width: 计数器位宽
        is_dual: 是否双定时器
        **kwargs: 其他参数
        
    Returns:
        AXITimerConfig 对象
    """
    return AXITimerConfig(
        name=name,
        count_width=count_width,
        is_dual=is_dual,
        **kwargs
    )


def create_axi_iic_config(
    name: str,
    iic_frequency: float = 100.0,
    **kwargs
) -> AXIIICConfig:
    """创建 AXI IIC 配置的便捷函数
    
    Args:
        name: IP 名称
        iic_frequency: I2C 频率（kHz）
        **kwargs: 其他参数
        
    Returns:
        AXIIICConfig 对象
    """
    return AXIIICConfig(
        name=name,
        iic_frequency=iic_frequency,
        **kwargs
    )


def create_axi_spi_config(
    name: str,
    spi_mode: int = 0,
    data_width: int = 8,
    **kwargs
) -> AXISPIConfig:
    """创建 AXI SPI 配置的便捷函数
    
    Args:
        name: IP 名称
        spi_mode: SPI 模式 (0-3)
        data_width: 数据位宽
        **kwargs: 其他参数
        
    Returns:
        AXISPIConfig 对象
    """
    return AXISPIConfig(
        name=name,
        spi_mode=spi_mode,
        data_width=data_width,
        **kwargs
    )


def create_axi_bram_ctrl_config(
    name: str,
    data_width: int = 32,
    num_bram_ports: int = 1,
    **kwargs
) -> AXIBRAMCtrlConfig:
    """创建 AXI BRAM Controller 配置的便捷函数
    
    Args:
        name: IP 名称
        data_width: 数据位宽
        num_bram_ports: BRAM 端口数量
        **kwargs: 其他参数
        
    Returns:
        AXIBRAMCtrlConfig 对象
    """
    return AXIBRAMCtrlConfig(
        name=name,
        data_width=data_width,
        num_bram_ports=num_bram_ports,
        **kwargs
    )


def create_axi_interrupt_ctrl_config(
    name: str,
    num_interrupts: int = 32,
    **kwargs
) -> AXIInterruptCtrlConfig:
    """创建 AXI Interrupt Controller 配置的便捷函数
    
    Args:
        name: IP 名称
        num_interrupts: 中断输入数量
        **kwargs: 其他参数
        
    Returns:
        AXIInterruptCtrlConfig 对象
    """
    return AXIInterruptCtrlConfig(
        name=name,
        num_interrupts=num_interrupts,
        **kwargs
    )


def create_mig_config(
    name: str,
    memory_type: str = "DDR4",
    clock_frequency: float = 300.0,
    data_width: int = 64,
    **kwargs
) -> MIGConfig:
    """创建 MIG DDR 控制器配置的便捷函数
    
    Args:
        name: IP 名称
        memory_type: 内存类型 (DDR4/DDR3/LPDDR4)
        clock_frequency: 时钟频率（MHz）
        data_width: 数据位宽
        **kwargs: 其他参数
        
    Returns:
        MIGConfig 对象
    """
    return MIGConfig(
        name=name,
        memory_type=memory_type,
        clock_frequency=clock_frequency,
        data_width=data_width,
        **kwargs
    )
