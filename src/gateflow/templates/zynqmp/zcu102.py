"""
ZCU102 平台模板

ZCU102 是 Xilinx 官方的 Zynq UltraScale+ MPSoC 评估板，具有强大的处理能力和丰富的接口。

硬件规格:
- SoC: Xilinx Zynq UltraScale+ MPSoC (XCUZU9EG-FFVB1156-2-E)
- PS DDR4: 2GB
- PL DDR4: 1GB (通过 FMC)
- 时钟: 100MHz (PL 端)
- 外设: UART, USB3.0, Ethernet (x4), SD Card, PCIe Gen3 x8, FMC, DisplayPort
"""

from typing import Any

from gateflow.templates.common.base import (
    PeripheralConfig,
    PlatformInfo,
    PlatformTemplate,
    PSConfig,
    PSType,
)


class ZCU102Template(PlatformTemplate):
    """
    ZCU102 平台模板
    
    ZCU102 是 Xilinx 官方的 Zynq UltraScale+ MPSoC 评估板，具有强大的处理能力和丰富的接口。
    
    Features:
        - Zynq UltraScale+ MPSoC XCUZU9EG-FFVB1156-2-E
        - 2GB DDR4 (PS 端)
        - 100MHz PL 时钟
        - 四核 ARM Cortex-A53 + 双核 ARM Cortex-R5
        - 四以太网接口
        - PCIe Gen3 x8
        - USB3.0
        - DisplayPort
        - FMC 连接器
    
    Example:
        ```python
        from gateflow.templates import get_platform
        
        # 获取 ZCU102 模板
        platform = get_platform("zcu102")
        
        # 获取平台信息
        info = platform.get_info()
        print(f"器件: {info.device}")
        print(f"PS 类型: {info.ps_type}")
        ```
    """
    
    @classmethod
    def get_info(cls) -> PlatformInfo:
        """获取 ZCU102 平台信息"""
        return PlatformInfo(
            name="zcu102",
            display_name="ZCU102",
            device="xczu9eg-ffvb1156-2-e",
            board_part="xilinx.com:zcu102:part0",
            ps_type=PSType.ZYNQMP,
            default_clock=100.0,
            description="Xilinx ZCU102 Zynq UltraScale+ MPSoC 评估板，高性能嵌入式开发平台",
            vendor="xilinx",
            family="zynq-ultrascale+",
            speed_grade="2",
            package="ffvb1156",
        )
    
    @classmethod
    def get_default_ps_config(cls) -> PSConfig:
        """获取 ZCU102 默认 PS 配置"""
        return PSConfig(
            # PL 时钟配置
            fpga_clk0=100.0,  # PL_CLK0: 100MHz
            fpga_clk1=100.0,  # PL_CLK1: 100MHz
            fpga_clk2=200.0,  # PL_CLK2: 200MHz (用于高速接口)
            fpga_clk3=300.0,  # PL_CLK3: 300MHz (用于高速接口)
            
            # DDR 配置
            ddr_enabled=True,
            ddr_type="DDR4",
            ddr_clock=600.0,  # 600MHz (DDR4-2400)
            
            # UART 配置
            uart_enabled=True,
            uart_baud_rate=115200,
            
            # Ethernet 配置 (ZCU102 有四个以太网接口)
            ethernet_enabled=True,
            ethernet_type="GMII",
            
            # USB 配置
            usb_enabled=True,
            usb_type="USB3.0",
            
            # SD 卡配置
            sd_enabled=True,
            sd_type="SD3.0",
            
            # GPIO 配置
            gpio_enabled=True,
            gpio_inputs=8,   # 8 个按钮和开关
            gpio_outputs=8,  # 8 个 LED
            
            # 中断配置
            irq_enabled=True,
        )
    
    @classmethod
    def get_default_peripherals(cls) -> list[PeripheralConfig]:
        """获取 ZCU102 默认外设配置"""
        return [
            # AXI GPIO 用于 LED
            PeripheralConfig(
                name="leds",
                ip_type="xilinx.com:ip:axi_gpio:2.0",
                config={
                    "C_GPIO_WIDTH": 8,
                    "C_ALL_OUTPUTS": 1,
                    "C_GPIO_DATA_WIDTH": 8,
                },
            ),
            # AXI GPIO 用于按钮
            PeripheralConfig(
                name="buttons",
                ip_type="xilinx.com:ip:axi_gpio:2.0",
                config={
                    "C_GPIO_WIDTH": 5,
                    "C_ALL_INPUTS": 1,
                    "C_GPIO_DATA_WIDTH": 5,
                },
            ),
            # AXI GPIO 用于开关
            PeripheralConfig(
                name="switches",
                ip_type="xilinx.com:ip:axi_gpio:2.0",
                config={
                    "C_GPIO_WIDTH": 8,
                    "C_ALL_INPUTS": 1,
                    "C_GPIO_DATA_WIDTH": 8,
                },
            ),
            # AXI Timer
            PeripheralConfig(
                name="timer",
                ip_type="xilinx.com:ip:axi_timer:2.0",
                config={
                    "C_COUNT_WIDTH": 32,
                },
            ),
            # AXI DMA (用于高速数据传输)
            PeripheralConfig(
                name="dma",
                ip_type="xilinx.com:ip:axi_dma:7.1",
                config={
                    "c_include_sg": 1,
                    "c_sg_length_width": 16,
                },
                enabled=False,  # 默认不启用
            ),
            # AXI Ethernet (额外以太网)
            PeripheralConfig(
                name="ethernet",
                ip_type="xilinx.com:ip:axi_ethernet:7.1",
                config={
                    "C_PHY_TYPE": 2,  # SGMII
                    "C_RXCSUM": 0,
                },
                enabled=False,  # 默认不启用
            ),
            # AXI PCIe (PCIe 接口)
            PeripheralConfig(
                name="pcie",
                ip_type="xilinx.com:ip:axi_pcie:2.9",
                config={
                    "C_INCLUDE_BAR": 1,
                    "C_NUM_MSI_REQ": 4,
                },
                enabled=False,  # 默认不启用
            ),
        ]
    
    @classmethod
    def _get_zynqmp_ps_config_commands(cls, config: PSConfig) -> list[str]:
        """生成 ZCU102 特定的 PS 配置命令"""
        commands = []
        
        # ZCU102 特定配置 (ZynqMP PS)
        ps_config = {
            # PL 时钟配置
            'CRL.PL0_REF_CTRL_FREQMHZ': config.fpga_clk0,
            'CRL.PL1_REF_CTRL_FREQMHZ': config.fpga_clk1,
            'CRL.PL2_REF_CTRL_FREQMHZ': config.fpga_clk2 if config.fpga_clk2 else 200,
            'CRL.PL3_REF_CTRL_FREQMHZ': config.fpga_clk3 if config.fpga_clk3 else 300,
            
            # PL 时钟使能
            'CRL.PL0_REF_CTRL_CLKACT': 1,
            'CRL.PL1_REF_CTRL_CLKACT': 1,
            'CRL.PL2_REF_CTRL_CLKACT': 1,
            'CRL.PL3_REF_CTRL_CLKACT': 1,
            
            # UART 配置
            'PSU__UART0__PERIPHERAL__ENABLE': 1 if config.uart_enabled else 0,
            'PSU__UART0__PERIPHERAL__IO': 'MIO 18 .. 19',
            'PSU__UART1__PERIPHERAL__ENABLE': 1,
            'PSU__UART1__PERIPHERAL__IO': 'MIO 20 .. 21',
            
            # Ethernet 配置 (ZCU102 有四个以太网)
            'PSU__GEM0__PERIPHERAL__ENABLE': 1 if config.ethernet_enabled else 0,
            'PSU__GEM0__PERIPHERAL__IO': 'MIO 0 .. 11',
            'PSU__GEM1__PERIPHERAL__ENABLE': 0,
            'PSU__GEM2__PERIPHERAL__ENABLE': 0,
            'PSU__GEM3__PERIPHERAL__ENABLE': 0,
            
            # USB 配置
            'PSU__USB0__PERIPHERAL__ENABLE': 1 if config.usb_enabled else 0,
            'PSU__USB0__PERIPHERAL__IO': 'MIO 52 .. 63',
            'PSU__USB1__PERIPHERAL__ENABLE': 0,
            
            # SD 卡配置
            'PSU__SD0__PERIPHERAL__ENABLE': 1 if config.sd_enabled else 0,
            'PSU__SD0__PERIPHERAL__IO': 'MIO 13 .. 16',
            'PSU__SD0__SLOT_TYPE': 'SD 3.0',
            'PSU__SD0__RESET__ENABLE': 1,
            
            # GPIO 配置
            'PSU__GPIO0__PERIPHERAL__ENABLE': 1,
            'PSU__GPIO1__PERIPHERAL__ENABLE': 1,
            
            # DDR 配置 (ZCU102 使用 2GB DDR4)
            'PSU__DDRC__MEMORY_DEVICE_TYPE': 'DDR4',
            'PSU__DDRC__DRAM_WIDTH': '16 Bits',
            'PSU__DDRC__MEMORY_DENSITY': '8192 MBits',
            'PSU__DDRC__SPEED_BIN': 'DDR4_2400',
            'PSU__DDRC__CLOCK_STOP': 0,
            
            # 中断配置
            'PSU__FPGA_PL0_ENABLE': 1 if config.irq_enabled else 0,
            'PSU__FPGA_PL1_ENABLE': 1 if config.irq_enabled else 0,
            
            # I2C 配置
            'PSU__I2C0__PERIPHERAL__ENABLE': 1,
            'PSU__I2C0__PERIPHERAL__IO': 'MIO 14 .. 15',
            'PSU__I2C1__PERIPHERAL__ENABLE': 1,
            'PSU__I2C1__PERIPHERAL__IO': 'MIO 16 .. 17',
            
            # SPI 配置
            'PSU__SPI0__PERIPHERAL__ENABLE': 0,
            'PSU__SPI1__PERIPHERAL__ENABLE': 0,
            
            # CAN 配置
            'PSU__CAN0__PERIPHERAL__ENABLE': 0,
            'PSU__CAN1__PERIPHERAL__ENABLE': 0,
        }
        
        # 构建配置字典命令
        config_items = [f'{k} {{{v}}}' for k, v in ps_config.items()]
        config_str = ' '.join(config_items)
        commands.append(f'set_property -dict [list {config_str}] [get_bd_cells zynq_ultra_ps_e_0]')
        
        return commands
    
    @classmethod
    def get_tcl_setup_ps_commands(cls, config: PSConfig | None = None) -> list[str]:
        """生成配置 ZCU102 PS 的 Tcl 命令"""
        if config is None:
            config = cls.get_default_ps_config()
        
        commands = []
        
        # 创建 Block Design
        commands.append('create_bd_design "system"')
        
        # 添加 ZynqMP PS IP
        commands.append('create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 zynq_ultra_ps_e_0')
        
        # 应用预设
        commands.append('set_property -dict [list CONFIG.preset {ZCU102}] [get_bd_cells zynq_ultra_ps_e_0]')
        
        # 应用自定义配置
        commands.extend(cls._get_zynqmp_ps_config_commands(config))
        
        return commands
    
    @classmethod
    def get_tcl_complete_bd_commands(cls) -> list[str]:
        """生成 ZCU102 完整的 Block Design Tcl 命令"""
        commands = [
            # 应用 AXI 自动连接
            'apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {Auto} Slave {Auto} ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} [get_bd_intf_pins zynq_ultra_ps_e_0/M_AXI_HPM0_FPD]',
            
            # 连接 PL 时钟
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/maxihpm0_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxihp0_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxihp1_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxihp2_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxihp3_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxigp2_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxigp3_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxigp4_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxigp5_fpd_aclk]',
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_clk0] [get_bd_pins zynq_ultra_ps_e_0/saxigp6_fpd_aclk]',
            
            # 连接复位
            'connect_bd_net [get_bd_pins zynq_ultra_ps_e_0/pl_resetn0] [get_bd_pins rst_zynq_ultra_ps_e_0_100M/ext_reset_in]',
            
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
    def get_info_dict(cls) -> dict[str, Any]:
        """获取平台信息的字典格式"""
        info = cls.get_info()
        ps_config = cls.get_default_ps_config()
        peripherals = cls.get_default_peripherals()
        
        return {
            "platform": info.to_dict(),
            "ps_config": ps_config.to_dict(),
            "peripherals": [p.to_dict() for p in peripherals],
        }
