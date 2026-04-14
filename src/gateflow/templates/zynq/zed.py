"""
Zedboard 平台模板

Zedboard 是一款基于 Xilinx Zynq-7000 的开发板，适合嵌入式系统开发和学习。

硬件规格:
- SoC: Xilinx Zynq-7000 (XC7Z020-CLG484-1)
- PS DDR3: 512MB
- PL DDR3: 256MB (通过 FMC)
- 时钟: 100MHz (PL 端)
- 外设: UART, USB, Ethernet, SD Card, GPIO, LEDs, Buttons, Switches
"""

from typing import Any

from gateflow.templates.common.base import (
    PeripheralConfig,
    PlatformInfo,
    PlatformTemplate,
    PSConfig,
    PSType,
)


class ZedboardTemplate(PlatformTemplate):
    """
    Zedboard 平台模板
    
    Zedboard 是一款流行的 Zynq-7000 开发板，广泛用于教学和原型开发。
    
    Features:
        - Zynq-7000 XC7Z020-CLG484-1
        - 512MB DDR3 (PS 端)
        - 100MHz PL 时钟
        - 丰富的外设接口
    
    Example:
        ```python
        from gateflow.templates import get_platform
        
        # 获取 Zedboard 模板
        platform = get_platform("zed")
        
        # 获取平台信息
        info = platform.get_info()
        print(f"器件: {info.device}")
        print(f"PS 类型: {info.ps_type}")
        ```
    """
    
    @classmethod
    def get_info(cls) -> PlatformInfo:
        """获取 Zedboard 平台信息"""
        return PlatformInfo(
            name="zed",
            display_name="Zedboard",
            device="xc7z020clg484-1",
            board_part="xilinx.com:zed:part0",
            ps_type=PSType.ZYNQ,
            default_clock=100.0,
            description="Zedboard Zynq-7000 开发板，适合嵌入式系统开发和学习",
            vendor="avnet",
            family="zynq-7000",
            speed_grade="1",
            package="clg484",
        )
    
    @classmethod
    def get_default_ps_config(cls) -> PSConfig:
        """获取 Zedboard 默认 PS 配置"""
        return PSConfig(
            # PL 时钟配置
            fpga_clk0=100.0,  # FCLK_CLK0: 100MHz
            fpga_clk1=100.0,  # FCLK_CLK1: 100MHz
            fpga_clk2=50.0,   # FCLK_CLK2: 50MHz (可选)
            fpga_clk3=50.0,   # FCLK_CLK3: 50MHz (可选)
            
            # DDR 配置
            ddr_enabled=True,
            ddr_type="DDR3",
            ddr_clock=533.0,  # 533MHz
            
            # UART 配置
            uart_enabled=True,
            uart_baud_rate=115200,
            
            # Ethernet 配置 (Zedboard 有以太网接口)
            ethernet_enabled=True,
            ethernet_type="GMII",
            
            # USB 配置
            usb_enabled=True,
            usb_type="USB2.0",
            
            # SD 卡配置
            sd_enabled=True,
            sd_type="SD2.0",
            
            # GPIO 配置
            gpio_enabled=True,
            gpio_inputs=8,   # 8 个按钮和开关
            gpio_outputs=8,  # 8 个 LED
            
            # 中断配置
            irq_enabled=True,
        )
    
    @classmethod
    def get_default_peripherals(cls) -> list[PeripheralConfig]:
        """获取 Zedboard 默认外设配置"""
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
        ]
    
    @classmethod
    def _get_zynq_ps_config_commands(cls, config: PSConfig) -> list[str]:
        """生成 Zedboard 特定的 PS 配置命令"""
        commands = []
        
        # Zedboard 特定配置
        ps_config = {
            # PL 时钟配置
            'PCW_FPGA0_PERIPHERAL_FREQMHZ': config.fpga_clk0,
            'PCW_FPGA1_PERIPHERAL_FREQMHZ': config.fpga_clk1,
            'PCW_FPGA2_PERIPHERAL_FREQMHZ': config.fpga_clk2 if config.fpga_clk2 else 50,
            'PCW_FPGA3_PERIPHERAL_FREQMHZ': config.fpga_clk3 if config.fpga_clk3 else 50,
            
            # PL 时钟使能
            'PCW_FPGA_FCLK0_ENABLE': 1,
            'PCW_FPGA_FCLK1_ENABLE': 1,
            'PCW_FPGA_FCLK2_ENABLE': 1 if config.fpga_clk2 else 0,
            'PCW_FPGA_FCLK3_ENABLE': 1 if config.fpga_clk3 else 0,
            
            # UART 配置
            'PCW_UART1_PERIPHERAL_ENABLE': 1 if config.uart_enabled else 0,
            'PCW_UART1_UART1_IO': 'MIO 8 .. 9',
            
            # Ethernet 配置
            'PCW_ENET0_PERIPHERAL_ENABLE': 1 if config.ethernet_enabled else 0,
            'PCW_ENET0_ENET0_IO': 'MIO 16 .. 27',
            'PCW_ENET0_GRP_MDIO_ENABLE': 1,
            'PCW_ENET0_GRP_MDIO_IO': 'MIO 52 .. 53',
            
            # USB 配置
            'PCW_USB0_PERIPHERAL_ENABLE': 1 if config.usb_enabled else 0,
            'PCW_USB0_USB0_IO': 'MIO 28 .. 39',
            
            # SD 卡配置
            'PCW_SD0_PERIPHERAL_ENABLE': 1 if config.sd_enabled else 0,
            'PCW_SD0_SD0_IO': 'MIO 40 .. 45',
            'PCW_SD0_GRP_CD_ENABLE': 1,
            'PCW_SD0_GRP_CD_IO': 'MIO 46',
            'PCW_SD0_GRP_WP_ENABLE': 0,
            
            # GPIO 配置 (MIO GPIO)
            'PCW_GPIO_MIO_GPIO_ENABLE': 1,
            'PCW_GPIO_PERIPHERAL_ENABLE': 1,
            
            # DDR 配置
            'PCW_DDR_DDR3L_MEMORY_FREQUENCY': 533,
            'PCW_UIPARAM_DDR_PARTNO': 'MT41J128M16 HA-15E',
            'PCW_UIPARAM_DDR_DRAM_WIDTH': '16 Bits',
            'PCW_UIPARAM_DDR_DEVICE_CAPACITY': '4096 MBits',
            'PCW_UIPARAM_DDR_SPEED_BIN': 'DDR3L_1066',
            
            # 中断配置
            'PCW_IRQ_F2P_INTR': 1 if config.irq_enabled else 0,
            
            # 其他配置
            'PCW_TTC0_PERIPHERAL_ENABLE': 0,
            'PCW_I2C0_PERIPHERAL_ENABLE': 0,
            'PCW_I2C1_PERIPHERAL_ENABLE': 0,
            'PCW_SPI0_PERIPHERAL_ENABLE': 0,
            'PCW_SPI1_PERIPHERAL_ENABLE': 0,
            'PCW_CAN0_PERIPHERAL_ENABLE': 0,
        }
        
        # 构建配置字典命令
        config_items = [f'{k} {{{v}}}' for k, v in ps_config.items()]
        config_str = ' '.join(config_items)
        commands.append(f'set_property -dict [list {config_str}] [get_bd_cells processing_system7_0]')
        
        return commands
    
    @classmethod
    def get_tcl_complete_bd_commands(cls) -> list[str]:
        """生成 Zedboard 完整的 Block Design Tcl 命令"""
        commands = [
            # 应用 AXI 自动连接
            'apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {Auto} Slave {Auto} ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}} [get_bd_intf_pins processing_system7_0/M_AXI_GP0]',
            
            # 连接 PL 时钟
            'connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins processing_system7_0/M_AXI_GP0_ACLK]',
            'connect_bd_net [get_bd_pins processing_system7_0/FCLK_CLK0] [get_bd_pins processing_system7_0/S_AXI_HP0_ACLK]',
            
            # 连接复位
            'connect_bd_net [get_bd_pins processing_system7_0/FCLK_RESET0_N] [get_bd_pins rst_processing_system7_0_100M/ext_reset_in]',
            
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
