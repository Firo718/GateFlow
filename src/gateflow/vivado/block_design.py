"""
Vivado Block Design 模块

提供 Block Design 的创建、IP 实例化、连接管理等功能。
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

from gateflow.vivado.result_utils import format_result, path_artifact


class BDInterfaceType(Enum):
    """Block Design 接口类型"""
    AXI4LITE = "axi4lite"
    AXI4MM = "axi4mm"
    AXI4STREAM = "axi4stream"
    CLOCK = "clock"
    RESET = "reset"
    INTERRUPT = "interrupt"
    GPIO = "gpio"


class BDAutoConnectRule(Enum):
    """Block Design 自动连接规则"""
    ALL = "all"
    AXI4 = "axi4"
    CLOCK = "clock"
    RESET = "reset"
    INTERRUPT = "interrupt"


@dataclass
class BDPort:
    """Block Design 端口"""
    name: str
    direction: str  # "input", "output", "inout"
    interface_type: BDInterfaceType | None = None
    width: int = 1

    def __post_init__(self):
        """验证端口配置"""
        if self.direction not in ["input", "output", "inout"]:
            raise ValueError(f"无效的端口方向: {self.direction}")
        if self.width < 1:
            raise ValueError(f"端口宽度必须大于 0: {self.width}")


@dataclass
class BDIPInstance:
    """Block Design IP 实例"""
    name: str
    ip_type: str  # IP 类型，如 "xilinx.com:ip:axi_gpio:2.0"
    config: dict[str, Any] = field(default_factory=dict)
    ports: list[BDPort] = field(default_factory=list)

    def __post_init__(self):
        """验证实例名称"""
        if not self.name or not self.name.replace('_', '').isalnum():
            raise ValueError(f"无效的实例名称: {self.name}")


@dataclass
class BDConnection:
    """Block Design 连接"""
    name: str | None  # 连接名称，可选
    source: str  # 格式: "instance_name/port_name"
    destination: str  # 格式: "instance_name/port_name"

    def __post_init__(self):
        """验证连接格式"""
        if '/' not in self.source:
            raise ValueError(f"源端口格式错误，应为 'instance/port': {self.source}")
        if '/' not in self.destination:
            raise ValueError(f"目标端口格式错误，应为 'instance/port': {self.destination}")


@dataclass
class BlockDesignConfig:
    """Block Design 配置"""
    name: str
    ip_instances: list[BDIPInstance] = field(default_factory=list)
    connections: list[BDConnection] = field(default_factory=list)
    external_ports: list[BDPort] = field(default_factory=list)


@dataclass
class ZynqPSConfig:
    """Zynq PS 配置"""
    enable_fabric_reset: bool = True
    enable_fabric_clock: bool = True
    enable_ddr: bool = True
    enable_enet0: bool = False
    enable_enet1: bool = False
    enable_usb0: bool = False
    enable_usb1: bool = False
    enable_sd0: bool = False
    enable_sd1: bool = False
    enable_uart0: bool = True
    enable_uart1: bool = False
    enable_i2c0: bool = False
    enable_i2c1: bool = False
    enable_spi0: bool = False
    enable_spi1: bool = False
    enable_can0: bool = False
    enable_can1: bool = False
    enable_ttc0: bool = False
    enable_ttc1: bool = False
    enable_gpio: bool = False
    custom_config: dict[str, Any] = field(default_factory=dict)


class BlockDesignTclGenerator:
    """
    Block Design Tcl 命令生成器

    生成用于 Block Design 创建、配置、连接等操作的 Tcl 命令。
    """

    @staticmethod
    def create_bd_design_tcl(name: str) -> str:
        """
        生成创建 Block Design 的 Tcl 命令

        Args:
            name: Block Design 名称

        Returns:
            Tcl 命令字符串
        """
        return f'create_bd_design "{name}"'

    @staticmethod
    def open_bd_design_tcl(name: str) -> str:
        """
        生成打开 Block Design 的 Tcl 命令

        Args:
            name: Block Design 名称

        Returns:
            Tcl 命令字符串
        """
        return f'open_bd_design [get_bd_designs "{name}"]'

    @staticmethod
    def close_bd_design_tcl() -> str:
        """
        生成关闭 Block Design 的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'close_bd_design [current_bd_design]'

    @staticmethod
    def create_bd_cell_tcl(instance: BDIPInstance) -> str:
        """
        生成创建 IP 实例的 Tcl 命令

        Args:
            instance: IP 实例配置

        Returns:
            Tcl 命令字符串
        """
        # 创建 IP 实例
        cmd = f'create_bd_cell -type ip -vlnv {instance.ip_type} {instance.name}'
        return cmd

    @staticmethod
    def create_bd_cell_with_config_tcl(instance: BDIPInstance) -> list[str]:
        """
        生成创建并配置 IP 实例的 Tcl 命令序列

        Args:
            instance: IP 实例配置

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建实例
        commands.append(BlockDesignTclGenerator.create_bd_cell_tcl(instance))

        # 配置属性
        if instance.config:
            commands.append(
                BlockDesignTclGenerator.set_bd_property_tcl(instance.name, instance.config)
            )

        return commands

    @staticmethod
    def set_bd_property_tcl(cell_name: str, properties: dict[str, Any]) -> str:
        """
        生成设置 IP 属性的 Tcl 命令

        Args:
            cell_name: 单元名称
            properties: 属性字典

        Returns:
            Tcl 命令字符串
        """
        # 构建属性列表
        prop_list = []
        for key, value in properties.items():
            if isinstance(value, bool):
                prop_list.append(f"{key} {'true' if value else 'false'}")
            elif isinstance(value, str):
                prop_list.append(f'{key} "{value}"')
            else:
                prop_list.append(f"{key} {value}")

        props_str = ' '.join(prop_list)
        return f'set_property -dict [list {props_str}] [get_bd_cells {cell_name}]'

    @staticmethod
    def create_bd_port_tcl(port: BDPort) -> str:
        """
        生成创建外部端口的 Tcl 命令

        Args:
            port: 端口配置

        Returns:
            Tcl 命令字符串
        """
        direction_map = {
            "input": "I",
            "output": "O",
            "inout": "IO",
        }

        direction = direction_map.get(port.direction, "I")

        # 如果是接口端口
        if port.interface_type:
            interface_map = {
                BDInterfaceType.AXI4LITE: "AXI4LITE",
                BDInterfaceType.AXI4MM: "AXI4",
                BDInterfaceType.AXI4STREAM: "AXIS",
                BDInterfaceType.CLOCK: "clock",
                BDInterfaceType.RESET: "reset",
                BDInterfaceType.INTERRUPT: "intr",
                BDInterfaceType.GPIO: "GPIO",
            }
            interface_type = interface_map.get(port.interface_type, "")
            return f'create_bd_intf_port -mode Master -vlnv xilinx.com:interface:{interface_type}_rtl:1.0 {port.name}'
        else:
            # 普通端口
            if port.width > 1:
                return f'create_bd_port -dir {direction} -from {port.width - 1} -to 0 {port.name}'
            else:
                return f'create_bd_port -dir {direction} {port.name}'

    @staticmethod
    def create_bd_intf_port_tcl(
        name: str,
        mode: str,
        vlnv: str,
    ) -> str:
        """
        生成创建接口端口的 Tcl 命令

        Args:
            name: 端口名称
            mode: 端口模式 (Master/Slave)
            vlnv: VLNV 标识符

        Returns:
            Tcl 命令字符串
        """
        return f'create_bd_intf_port -mode {mode} -vlnv {vlnv} {name}'

    @staticmethod
    def connect_bd_intf_net_tcl(connection: BDConnection) -> str:
        """
        生成连接接口网络的 Tcl 命令

        Args:
            connection: 连接配置

        Returns:
            Tcl 命令字符串
        """
        source_parts = connection.source.split('/')
        dest_parts = connection.destination.split('/')

        # 构建接口引脚路径
        if source_parts[0] == 'external':
            source_path = f'[get_bd_intf_ports {source_parts[1]}]'
        else:
            source_path = f'[get_bd_intf_pins {connection.source}]'

        if dest_parts[0] == 'external':
            dest_path = f'[get_bd_intf_ports {dest_parts[1]}]'
        else:
            dest_path = f'[get_bd_intf_pins {connection.destination}]'

        if connection.name:
            return f'connect_bd_intf_net {connection.name} {source_path} {dest_path}'
        else:
            return f'connect_bd_intf_net {source_path} {dest_path}'

    @staticmethod
    def connect_bd_net_tcl(source: str, destinations: list[str]) -> str:
        """
        生成连接普通网络的 Tcl 命令

        Args:
            source: 源端口
            destinations: 目标端口列表

        Returns:
            Tcl 命令字符串
        """
        # 构建源路径
        source_parts = source.split('/')
        if source_parts[0] == 'external':
            source_path = f'[get_bd_ports {source_parts[1]}]'
        else:
            source_path = f'[get_bd_pins {source}]'

        # 构建目标路径列表
        dest_paths = []
        for dest in destinations:
            dest_parts = dest.split('/')
            if dest_parts[0] == 'external':
                dest_paths.append(f'[get_bd_ports {dest_parts[1]}]')
            else:
                dest_paths.append(f'[get_bd_pins {dest}]')

        dests_str = ' '.join(dest_paths)
        return f'connect_bd_net {source_path} {dests_str}'

    @staticmethod
    def apply_bd_automation_tcl(rule: str = "all") -> str:
        """
        生成应用自动连接的 Tcl 命令

        Args:
            rule: 自动连接规则

        Returns:
            Tcl 命令字符串
        """
        return f'apply_bd_automation -rule {rule}'

    @staticmethod
    def apply_bd_automation_full_tcl(
        rule: str = "all",
        exclude_cells: list[str] | None = None,
    ) -> str:
        """
        生成应用自动连接的完整 Tcl 命令

        Args:
            rule: 自动连接规则
            exclude_cells: 排除的单元列表

        Returns:
            Tcl 命令字符串
        """
        cmd = f'apply_bd_automation -rule {rule}'

        if exclude_cells:
            exclude_list = ' '.join(exclude_cells)
            cmd += f' -exclude {{{exclude_list}}}'

        return cmd

    @staticmethod
    def validate_bd_design_tcl() -> str:
        """
        生成验证 Block Design 的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'validate_bd_design'

    @staticmethod
    def generate_bd_wrapper_tcl(
        bd_name: str,
        wrapper_path: Path | None = None,
    ) -> str:
        """
        生成创建 HDL Wrapper 的 Tcl 命令

        Args:
            bd_name: Block Design 名称
            wrapper_path: Wrapper 文件路径（可选）

        Returns:
            Tcl 命令字符串
        """
        if wrapper_path:
            return f'make_wrapper -files [get_files {bd_name}.bd] -top -import -force -fileset sources_1'
        else:
            return f'make_wrapper -files [get_files {bd_name}.bd] -top -import -force'

    @staticmethod
    def save_bd_design_tcl() -> str:
        """
        生成保存 Block Design 的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'save_bd_design'

    @staticmethod
    def save_bd_design_as_tcl(name: str) -> str:
        """
        生成另存为 Block Design 的 Tcl 命令

        Args:
            name: 新的 Block Design 名称

        Returns:
            Tcl 命令字符串
        """
        return f'save_bd_design_as "{name}"'

    @staticmethod
    def get_bd_cells_tcl() -> str:
        """
        生成获取所有 IP 实例的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'get_bd_cells'

    @staticmethod
    def get_bd_cell_tcl(name: str) -> str:
        """
        生成获取指定 IP 实例的 Tcl 命令

        Args:
            name: 实例名称

        Returns:
            Tcl 命令字符串
        """
        return f'get_bd_cells {name}'

    @staticmethod
    def get_bd_intf_pins_tcl(cell_name: str) -> str:
        """
        生成获取接口引脚的 Tcl 命令

        Args:
            cell_name: 单元名称

        Returns:
            Tcl 命令字符串
        """
        return f'get_bd_intf_pins -of_objects [get_bd_cells {cell_name}]'

    @staticmethod
    def get_bd_pins_tcl(cell_name: str) -> str:
        """
        生成获取普通引脚的 Tcl 命令

        Args:
            cell_name: 单元名称

        Returns:
            Tcl 命令字符串
        """
        return f'get_bd_pins -of_objects [get_bd_cells {cell_name}]'

    @staticmethod
    def get_bd_intf_ports_tcl() -> str:
        """
        生成获取所有接口端口的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'get_bd_intf_ports'

    @staticmethod
    def get_bd_ports_tcl() -> str:
        """
        生成获取所有普通端口的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'get_bd_ports'

    @staticmethod
    def delete_bd_cell_tcl(name: str) -> str:
        """
        生成删除 IP 实例的 Tcl 命令

        Args:
            name: 实例名称

        Returns:
            Tcl 命令字符串
        """
        return f'delete_bd_objs [get_bd_cells {name}]'

    @staticmethod
    def delete_bd_port_tcl(name: str) -> str:
        """
        生成删除端口的 Tcl 命令

        Args:
            name: 端口名称

        Returns:
            Tcl 命令字符串
        """
        return f'delete_bd_objs [get_bd_ports {name}]'

    @staticmethod
    def delete_bd_intf_port_tcl(name: str) -> str:
        """
        生成删除接口端口的 Tcl 命令

        Args:
            name: 接口端口名称

        Returns:
            Tcl 命令字符串
        """
        return f'delete_bd_objs [get_bd_intf_ports {name}]'

    @staticmethod
    def create_zynq_ps_tcl(
        name: str = "processing_system7_0",
        config: ZynqPSConfig | None = None,
    ) -> list[str]:
        """
        生成创建 Zynq PS 的 Tcl 命令

        Args:
            name: 实例名称
            config: PS 配置

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 PS7 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 {name}'
        )

        # 应用配置
        if config:
            props = {}

            # 配置预设（使用 ZC702 或其他开发板预设）
            # props['CONFIG.preset'] = 'ZC702'

            # 配置 Fabric Reset
            if config.enable_fabric_reset:
                props['CONFIG.PCW_USE_FABRIC_RESET'] = '1'

            # 配置 Fabric Clock
            if config.enable_fabric_clock:
                props['CONFIG.PCW_USE_M_AXI_GP0'] = '1'
                props['CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ'] = '100'

            # 配置 DDR
            if config.enable_ddr:
                props['CONFIG.PCW_DDR_RAM_HIGHADDR'] = '0x3FFFFFFF'

            # 配置外设
            if config.enable_enet0:
                props['CONFIG.PCW_ENET0_PERIPHERAL_ENABLE'] = '1'
                props['CONFIG.PCW_ENET0_ENET0_IO'] = 'MIO 16 .. 27'

            if config.enable_enet1:
                props['CONFIG.PCW_ENET1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_usb0:
                props['CONFIG.PCW_USB0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_usb1:
                props['CONFIG.PCW_USB1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_sd0:
                props['CONFIG.PCW_SD0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_sd1:
                props['CONFIG.PCW_SD1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_uart0:
                props['CONFIG.PCW_UART0_PERIPHERAL_ENABLE'] = '1'
                props['CONFIG.PCW_UART0_UART0_IO'] = 'MIO 14 .. 15'

            if config.enable_uart1:
                props['CONFIG.PCW_UART1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_i2c0:
                props['CONFIG.PCW_I2C0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_i2c1:
                props['CONFIG.PCW_I2C1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_spi0:
                props['CONFIG.PCW_SPI0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_spi1:
                props['CONFIG.PCW_SPI1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_can0:
                props['CONFIG.PCW_CAN0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_can1:
                props['CONFIG.PCW_CAN1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_ttc0:
                props['CONFIG.PCW_TTC0_PERIPHERAL_ENABLE'] = '1'

            if config.enable_ttc1:
                props['CONFIG.PCW_TTC1_PERIPHERAL_ENABLE'] = '1'

            if config.enable_gpio:
                props['CONFIG.PCW_GPIO_MIO_GPIO_ENABLE'] = '1'

            # 合并自定义配置
            props.update(config.custom_config)

            if props:
                commands.append(
                    BlockDesignTclGenerator.set_bd_property_tcl(name, props)
                )

        return commands

    @staticmethod
    def create_zynq_ultra_ps_tcl(
        name: str = "zynq_ultra_ps_e_0",
        preset: str = "zu7ev",
    ) -> list[str]:
        """
        生成创建 Zynq UltraScale+ PS 的 Tcl 命令

        Args:
            name: 实例名称
            preset: 预设名称

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 Zynq UltraScale+ PS 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 {name}'
        )

        # 设置预设
        if preset:
            commands.append(
                f'set_property -dict [list CONFIG.PSU_PRESET {{preset_{preset}}}] [get_bd_cells {name}]'
            )

        return commands

    @staticmethod
    def create_axi_interconnect_tcl(
        name: str = "axi_interconnect_0",
        num_mi: int = 1,
        num_si: int = 1,
    ) -> list[str]:
        """
        生成创建 AXI Interconnect 的 Tcl 命令

        Args:
            name: 实例名称
            num_mi: 主接口数量
            num_si: 从接口数量

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 AXI Interconnect 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_interconnect:2.1 {name}'
        )

        # 配置接口数量
        props = {
            'CONFIG.NUM_MI': str(num_mi),
            'CONFIG.NUM_SI': str(num_si),
        }

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def create_clock_wizard_tcl(
        name: str = "clk_wiz_0",
        input_freq: float = 100.0,
        output_freqs: list[float] | None = None,
    ) -> list[str]:
        """
        生成创建 Clock Wizard 的 Tcl 命令

        Args:
            name: 实例名称
            input_freq: 输入频率 (MHz)
            output_freqs: 输出频率列表 (MHz)

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 Clock Wizard 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:clk_wiz:6.0 {name}'
        )

        # 配置属性
        props = {
            'CONFIG.PRIM_IN_FREQ': str(input_freq),
            'CONFIG.RESET_TYPE': 'ACTIVE_LOW',
        }

        if output_freqs:
            for i, freq in enumerate(output_freqs):
                if i == 0:
                    props['CONFIG.CLKOUT1_REQUESTED_OUT_FREQ'] = str(freq)
                elif i < 7:  # Clock Wizard 支持最多 7 个输出
                    props[f'CONFIG.CLKOUT{i+1}_REQUESTED_OUT_FREQ'] = str(freq)
                    props[f'CONFIG.CLKOUT{i+1}_USED'] = 'true'

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def create_processor_reset_tcl(
        name: str = "proc_sys_reset_0",
    ) -> str:
        """
        生成创建 Processor System Reset 的 Tcl 命令

        Args:
            name: 实例名称

        Returns:
            Tcl 命令字符串
        """
        return f'create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 {name}'

    @staticmethod
    def create_axi_gpio_tcl(
        name: str = "axi_gpio_0",
        width: int = 32,
        is_dual: bool = False,
    ) -> list[str]:
        """
        生成创建 AXI GPIO 的 Tcl 命令

        Args:
            name: 实例名称
            width: GPIO 宽度
            is_dual: 是否双通道

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 AXI GPIO 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 {name}'
        )

        # 配置属性
        props = {
            'CONFIG.C_GPIO_WIDTH': str(width),
            'CONFIG.C_IS_DUAL': '1' if is_dual else '0',
        }

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def create_axi_bram_tcl(
        name: str = "axi_bram_ctrl_0",
        data_width: int = 32,
        memory_depth: int = 8192,
    ) -> list[str]:
        """
        生成创建 AXI BRAM Controller 的 Tcl 命令

        Args:
            name: 实例名称
            data_width: 数据宽度
            memory_depth: 存储深度

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 AXI BRAM Controller 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 {name}'
        )

        # 配置属性
        props = {
            'CONFIG.DATA_WIDTH': str(data_width),
            'CONFIG.ECC_TYPE': '0',
        }

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def create_axi_dma_tcl(
        name: str = "axi_dma_0",
        include_sg: bool = False,
    ) -> list[str]:
        """
        生成创建 AXI DMA 的 Tcl 命令

        Args:
            name: 实例名称
            include_sg: 是否包含 Scatter-Gather

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 AXI DMA 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_dma:7.1 {name}'
        )

        # 配置属性
        props = {
            'CONFIG.c_include_sg': '1' if include_sg else '0',
            'CONFIG.c_sg_length_width': '16',
        }

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def create_axis_data_fifo_tcl(
        name: str = "axis_data_fifo_0",
        depth: int = 1024,
        width: int = 32,
    ) -> list[str]:
        """
        生成创建 AXI-Stream Data FIFO 的 Tcl 命令

        Args:
            name: 实例名称
            depth: FIFO 深度
            width: 数据宽度

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 创建 AXI-Stream Data FIFO 实例
        commands.append(
            f'create_bd_cell -type ip -vlnv xilinx.com:ip:axis_data_fifo:2.0 {name}'
        )

        # 配置属性
        props = {
            'CONFIG.FIFO_DEPTH': str(depth),
            'CONFIG.TDATA_NUM_BYTES': str(width // 8),
        }

        commands.append(
            BlockDesignTclGenerator.set_bd_property_tcl(name, props)
        )

        return commands

    @staticmethod
    def auto_connect_axi_clock_reset_tcl(
        axi_cell: str,
        clock_source: str = "processing_system7_0/FCLK_CLK0",
        reset_source: str = "proc_sys_reset_0/peripheral_aresetn",
    ) -> list[str]:
        """
        生成自动连接 AXI 时钟和复位的 Tcl 命令

        Args:
            axi_cell: AXI 单元名称
            clock_source: 时钟源
            reset_source: 复位源

        Returns:
            Tcl 命令列表
        """
        commands = []

        # 连接时钟
        commands.append(
            f'connect_bd_net [get_bd_pins {clock_source}] [get_bd_pins {axi_cell}/s_axi_aclk]'
        )

        # 连接复位
        commands.append(
            f'connect_bd_net [get_bd_pins {reset_source}] [get_bd_pins {axi_cell}/s_axi_aresetn]'
        )

        return commands

    @staticmethod
    def export_bd_tcl(bd_name: str, output_path: Path) -> str:
        """
        生成导出 Block Design 为 Tcl 脚本的命令

        Args:
            bd_name: Block Design 名称
            output_path: 输出文件路径

        Returns:
            Tcl 命令字符串
        """
        return f'write_bd_tcl -force "{output_path}"'

    @staticmethod
    def import_bd_tcl(tcl_path: Path) -> str:
        """
        生成从 Tcl 脚本导入 Block Design 的命令

        Args:
            tcl_path: Tcl 脚本路径

        Returns:
            Tcl 命令字符串
        """
        return f'source "{tcl_path}"'


class BlockDesignManager:
    """
    Block Design 管理器

    提供高级的 Block Design 管理接口，结合 TclEngine 执行 Tcl 命令。
    """

    def __init__(self, tcl_engine):
        """
        初始化 Block Design 管理器

        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self.current_design: BlockDesignConfig | None = None

    async def create_design(self, name: str) -> dict:
        """
        创建新的 Block Design

        Args:
            name: Block Design 名称

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.create_bd_design_tcl(name)
        result = await self.engine.execute_async(command)

        if result.success:
            self.current_design = BlockDesignConfig(name=name)
            logger.info(f"Block Design 创建成功: {name}")
        else:
            logger.error(f"Block Design 创建失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"Block Design 创建成功: {name}" if result.success else "Block Design 创建失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def open_design(self, name: str) -> dict:
        """
        打开 Block Design

        Args:
            name: Block Design 名称

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.open_bd_design_tcl(name)
        result = await self.engine.execute_async(command)

        if result.success:
            self.current_design = BlockDesignConfig(name=name)
            logger.info(f"Block Design 打开成功: {name}")
        else:
            logger.error(f"Block Design 打开失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"Block Design 打开成功: {name}" if result.success else "Block Design 打开失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def close_design(self) -> dict:
        """
        关闭当前 Block Design

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.close_bd_design_tcl()
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info(f"Block Design 已关闭: {self.current_design.name if self.current_design else ''}")
            self.current_design = None
        else:
            logger.error(f"Block Design 关闭失败: {result.errors}")

        return format_result(
            success=result.success,
            message="Block Design 关闭成功" if result.success else "Block Design 关闭失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def add_ip_instance(self, instance: BDIPInstance) -> dict:
        """
        添加 IP 实例

        Args:
            instance: IP 实例配置

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_bd_cell_with_config_tcl(instance)
        result = await self.engine.execute_async(commands)

        if result.success:
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"IP 实例添加成功: {instance.name}")
        else:
            logger.error(f"IP 实例添加失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"IP 实例添加成功: {instance.name}" if result.success else "IP 实例添加失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def remove_ip_instance(self, instance_name: str) -> dict:
        """
        移除 IP 实例

        Args:
            instance_name: 实例名称

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.delete_bd_cell_tcl(instance_name)
        result = await self.engine.execute_async(command)

        if result.success:
            if self.current_design:
                # 从列表中移除
                self.current_design.ip_instances = [
                    inst for inst in self.current_design.ip_instances
                    if inst.name != instance_name
                ]
            logger.info(f"IP 实例移除成功: {instance_name}")
        else:
            logger.error(f"IP 实例移除失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"IP 实例移除成功: {instance_name}" if result.success else "IP 实例移除失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def create_external_port(self, port: BDPort) -> dict:
        """
        创建外部端口

        Args:
            port: 端口配置

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.create_bd_port_tcl(port)
        result = await self.engine.execute_async(command)

        if result.success:
            if self.current_design:
                self.current_design.external_ports.append(port)
            logger.info(f"外部端口创建成功: {port.name}")
        else:
            logger.error(f"外部端口创建失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"外部端口创建成功: {port.name}" if result.success else "外部端口创建失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def connect_ports(
        self,
        source: str,
        destination: str,
        name: str | None = None,
        is_interface: bool = False,
    ) -> dict:
        """
        连接端口

        Args:
            source: 源端口
            destination: 目标端口
            name: 连接名称（可选）
            is_interface: 是否为接口连接

        Returns:
            执行结果字典
        """
        connection = BDConnection(
            name=name,
            source=source,
            destination=destination,
        )

        if is_interface:
            command = BlockDesignTclGenerator.connect_bd_intf_net_tcl(connection)
        else:
            command = BlockDesignTclGenerator.connect_bd_net_tcl(source, [destination])

        result = await self.engine.execute_async(command)

        if result.success:
            if self.current_design:
                self.current_design.connections.append(connection)
            logger.info(f"端口连接成功: {source} -> {destination}")
        else:
            logger.error(f"端口连接失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"端口连接成功: {source} -> {destination}" if result.success else "端口连接失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def connect_interface(
        self,
        source: str,
        destination: str,
        name: str | None = None,
    ) -> dict:
        """
        连接接口端口

        Args:
            source: 源接口端口
            destination: 目标接口端口
            name: 连接名称（可选）

        Returns:
            执行结果字典
        """
        return await self.connect_ports(source, destination, name, is_interface=True)

    async def apply_automation(self, rule: str = "all") -> dict:
        """
        应用自动连接

        Args:
            rule: 自动连接规则

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.apply_bd_automation_tcl(rule)
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info(f"自动连接应用成功: {rule}")
        else:
            logger.error(f"自动连接应用失败: {result.errors}")

        return format_result(
            success=result.success,
            message=f"自动连接应用成功: {rule}" if result.success else "自动连接应用失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def validate_design(self) -> dict:
        """
        验证设计

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.validate_bd_design_tcl()
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info("Block Design 验证成功")
        else:
            logger.error(f"Block Design 验证失败: {result.errors}")

        return format_result(
            success=result.success,
            message="Block Design 验证成功" if result.success else "Block Design 验证失败",
            errors=result.errors,
            warnings=result.warnings,
            raw_report=result.output,
        )

    async def generate_wrapper(self) -> dict:
        """
        生成 HDL Wrapper

        Returns:
            执行结果字典
        """
        if not self.current_design:
            return format_result(
                success=False,
                message="HDL Wrapper 生成失败",
                errors=['没有打开的 Block Design'],
            )

        command = BlockDesignTclGenerator.generate_bd_wrapper_tcl(
            self.current_design.name
        )
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info("HDL Wrapper 生成成功")
        else:
            logger.error(f"HDL Wrapper 生成失败: {result.errors}")

        return format_result(
            success=result.success,
            message="HDL Wrapper 生成成功" if result.success else "HDL Wrapper 生成失败",
            errors=result.errors,
            warnings=result.warnings,
            artifacts={"wrapper_name": f"{self.current_design.name}_wrapper"} if result.success else {},
        )

    async def save_design(self) -> dict:
        """
        保存设计

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.save_bd_design_tcl()
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info("Block Design 保存成功")
        else:
            logger.error(f"Block Design 保存失败: {result.errors}")

        return format_result(
            success=result.success,
            message="Block Design 保存成功" if result.success else "Block Design 保存失败",
            errors=result.errors,
            warnings=result.warnings,
        )

    async def get_cells(self) -> list[dict]:
        """
        获取所有 IP 实例

        Returns:
            IP 实例列表
        """
        command = BlockDesignTclGenerator.get_bd_cells_tcl()
        result = await self.engine.execute_async(command)

        if result.success:
            # 解析输出获取实例列表
            cells = []
            for line in result.output.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    cells.append({'name': line})
            return cells
        else:
            logger.error(f"获取 IP 实例失败: {result.errors}")
            return []

    async def get_connections(self) -> list[dict]:
        """
        获取所有连接

        Returns:
            连接列表
        """
        # 获取接口连接
        intf_command = 'get_bd_intf_nets'
        intf_result = await self.engine.execute_async(intf_command)

        # 获取普通连接
        net_command = 'get_bd_nets'
        net_result = await self.engine.execute_async(net_command)

        connections = []

        if intf_result.success:
            for line in intf_result.output.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    connections.append({'name': line, 'type': 'interface'})

        if net_result.success:
            for line in net_result.output.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    connections.append({'name': line, 'type': 'net'})

        return connections

    async def create_zynq_ps(
        self,
        name: str = "processing_system7_0",
        config: ZynqPSConfig | None = None,
    ) -> dict:
        """
        创建 Zynq PS 实例

        Args:
            name: 实例名称
            config: PS 配置

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_zynq_ps_tcl(name, config)
        result = await self.engine.execute_async(commands)

        if result.success:
            # 创建实例对象并添加到当前设计
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:processing_system7:5.5",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"Zynq PS 创建成功: {name}")
        else:
            logger.error(f"Zynq PS 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_zynq_ultra_ps(
        self,
        name: str = "zynq_ultra_ps_e_0",
        preset: str = "zu7ev",
    ) -> dict:
        """
        创建 Zynq UltraScale+ PS 实例

        Args:
            name: 实例名称
            preset: 预设名称

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_zynq_ultra_ps_tcl(name, preset)
        result = await self.engine.execute_async(commands)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:zynq_ultra_ps_e:3.5",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"Zynq UltraScale+ PS 创建成功: {name}")
        else:
            logger.error(f"Zynq UltraScale+ PS 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_axi_interconnect(
        self,
        name: str = "axi_interconnect_0",
        num_mi: int = 1,
        num_si: int = 1,
    ) -> dict:
        """
        创建 AXI Interconnect 实例

        Args:
            name: 实例名称
            num_mi: 主接口数量
            num_si: 从接口数量

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_axi_interconnect_tcl(
            name, num_mi, num_si
        )
        result = await self.engine.execute_async(commands)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:axi_interconnect:2.1",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"AXI Interconnect 创建成功: {name}")
        else:
            logger.error(f"AXI Interconnect 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_clock_wizard(
        self,
        name: str = "clk_wiz_0",
        input_freq: float = 100.0,
        output_freqs: list[float] | None = None,
    ) -> dict:
        """
        创建 Clock Wizard 实例

        Args:
            name: 实例名称
            input_freq: 输入频率 (MHz)
            output_freqs: 输出频率列表 (MHz)

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_clock_wizard_tcl(
            name, input_freq, output_freqs
        )
        result = await self.engine.execute_async(commands)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:clk_wiz:6.0",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"Clock Wizard 创建成功: {name}")
        else:
            logger.error(f"Clock Wizard 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_processor_reset(
        self,
        name: str = "proc_sys_reset_0",
    ) -> dict:
        """
        创建 Processor System Reset 实例

        Args:
            name: 实例名称

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.create_processor_reset_tcl(name)
        result = await self.engine.execute_async(command)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:proc_sys_reset:5.0",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"Processor Reset 创建成功: {name}")
        else:
            logger.error(f"Processor Reset 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_axi_gpio(
        self,
        name: str = "axi_gpio_0",
        width: int = 32,
        is_dual: bool = False,
    ) -> dict:
        """
        创建 AXI GPIO 实例

        Args:
            name: 实例名称
            width: GPIO 宽度
            is_dual: 是否双通道

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_axi_gpio_tcl(name, width, is_dual)
        result = await self.engine.execute_async(commands)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:axi_gpio:2.0",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"AXI GPIO 创建成功: {name}")
        else:
            logger.error(f"AXI GPIO 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def create_axi_dma(
        self,
        name: str = "axi_dma_0",
        include_sg: bool = False,
    ) -> dict:
        """
        创建 AXI DMA 实例

        Args:
            name: 实例名称
            include_sg: 是否包含 Scatter-Gather

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.create_axi_dma_tcl(name, include_sg)
        result = await self.engine.execute_async(commands)

        if result.success:
            instance = BDIPInstance(
                name=name,
                ip_type="xilinx.com:ip:axi_dma:7.1",
            )
            if self.current_design:
                self.current_design.ip_instances.append(instance)
            logger.info(f"AXI DMA 创建成功: {name}")
        else:
            logger.error(f"AXI DMA 创建失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def auto_connect_axi(
        self,
        axi_cell: str,
        clock_source: str = "processing_system7_0/FCLK_CLK0",
        reset_source: str = "proc_sys_reset_0/peripheral_aresetn",
    ) -> dict:
        """
        自动连接 AXI 时钟和复位

        Args:
            axi_cell: AXI 单元名称
            clock_source: 时钟源
            reset_source: 复位源

        Returns:
            执行结果字典
        """
        commands = BlockDesignTclGenerator.auto_connect_axi_clock_reset_tcl(
            axi_cell, clock_source, reset_source
        )
        result = await self.engine.execute_async(commands)

        if result.success:
            logger.info(f"AXI 自动连接成功: {axi_cell}")
        else:
            logger.error(f"AXI 自动连接失败: {result.errors}")

        return {
            'success': result.success,
            'errors': result.errors,
            'warnings': result.warnings,
        }

    async def build_zynq_design(
        self,
        ps_config: ZynqPSConfig | None = None,
        axi_peripherals: list[str] | None = None,
    ) -> dict:
        """
        快速构建 Zynq Block Design

        Args:
            ps_config: PS 配置
            axi_peripherals: AXI 外设列表

        Returns:
            执行结果字典
        """
        results = {
            'success': True,
            'errors': [],
            'warnings': [],
        }

        # 创建 Zynq PS
        ps_result = await self.create_zynq_ps("processing_system7_0", ps_config)
        if not ps_result['success']:
            results['success'] = False
            results['errors'].extend(ps_result['errors'])
            return results

        # 创建 Processor Reset
        reset_result = await self.create_processor_reset("proc_sys_reset_0")
        if not reset_result['success']:
            results['success'] = False
            results['errors'].extend(reset_result['errors'])
            return results

        # 连接 PS 时钟和复位到 Processor Reset
        await self.connect_ports(
            "processing_system7_0/FCLK_CLK0",
            "proc_sys_reset_0/slowest_sync_clk"
        )
        await self.connect_ports(
            "processing_system7_0/FCLK_RESET0_N",
            "proc_sys_reset_0/ext_reset_in"
        )

        # 创建 AXI Interconnect
        num_peripherals = len(axi_peripherals) if axi_peripherals else 1
        interconnect_result = await self.create_axi_interconnect(
            "axi_interconnect_0",
            num_mi=num_peripherals,
            num_si=1,
        )
        if not interconnect_result['success']:
            results['success'] = False
            results['errors'].extend(interconnect_result['errors'])
            return results

        # 连接 PS 到 AXI Interconnect
        await self.connect_interface(
            "processing_system7_0/M_AXI_GP0",
            "axi_interconnect_0/S00_AXI"
        )

        # 连接时钟
        await self.connect_ports(
            "processing_system7_0/FCLK_CLK0",
            "axi_interconnect_0/ACLK"
        )
        await self.connect_ports(
            "processing_system7_0/FCLK_CLK0",
            "axi_interconnect_0/S00_ACLK"
        )

        # 连接复位
        await self.connect_ports(
            "proc_sys_reset_0/peripheral_aresetn",
            "axi_interconnect_0/ARESETN"
        )
        await self.connect_ports(
            "proc_sys_reset_0/peripheral_aresetn",
            "axi_interconnect_0/S00_ARESETN"
        )

        # 应用自动连接
        auto_result = await self.apply_automation("all")
        results['warnings'].extend(auto_result.get('warnings', []))

        # 验证设计
        validate_result = await self.validate_design()
        if not validate_result['success']:
            results['success'] = False
            results['errors'].extend(validate_result['errors'])

        # 保存设计
        save_result = await self.save_design()
        if not save_result['success']:
            results['success'] = False
            results['errors'].extend(save_result['errors'])

        return results

    async def export_bd_tcl(self, output_path: Path) -> dict:
        """
        导出 Block Design 为 Tcl 脚本

        Args:
            output_path: 输出文件路径

        Returns:
            执行结果字典
        """
        if not self.current_design:
            return format_result(
                success=False,
                message="Block Design 导出失败",
                errors=['没有打开的 Block Design'],
            )

        command = BlockDesignTclGenerator.export_bd_tcl(
            self.current_design.name,
            output_path
        )
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info(f"Block Design 导出成功: {output_path}")
        else:
            logger.error(f"Block Design 导出失败: {result.errors}")

        return format_result(
            success=result.success,
            message="Block Design 导出成功" if result.success else "Block Design 导出失败",
            errors=result.errors,
            warnings=result.warnings,
            artifacts=path_artifact(output_path),
        )

    async def import_bd_tcl(self, tcl_path: Path) -> dict:
        """
        从 Tcl 脚本导入 Block Design

        Args:
            tcl_path: Tcl 脚本路径

        Returns:
            执行结果字典
        """
        command = BlockDesignTclGenerator.import_bd_tcl(tcl_path)
        result = await self.engine.execute_async(command)

        if result.success:
            logger.info(f"Block Design 导入成功: {tcl_path}")
        else:
            logger.error(f"Block Design 导入失败: {result.errors}")

        return format_result(
            success=result.success,
            message="Block Design 导入成功" if result.success else "Block Design 导入失败",
            errors=result.errors,
            warnings=result.warnings,
            artifacts=path_artifact(tcl_path),
        )
