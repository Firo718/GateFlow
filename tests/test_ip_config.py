"""
IP 配置模块测试。

测试 IPType、IPInterfaceType、MemoryType 枚举，
各种 IP 配置数据类，IPTclGenerator 和 IPManager。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.vivado.ip_config import (
    IPType,
    IPInterfaceType,
    MemoryType,
    IPConfig,
    ClockingWizardConfig,
    FIFOConfig,
    BRAMConfig,
    AXIInterconnectConfig,
    DMAConfig,
    ZynqPSConfig,
    XADCConfig,
    ILAConfig,
    IPTclGenerator,
    IPManager,
    create_clocking_wizard_config,
    create_fifo_config,
    create_bram_config,
)


# ==================== 枚举测试 ====================


class TestIPType:
    """IPType 枚举测试。"""

    def test_ip_type_values(self):
        """测试 IP 类型枚举值。"""
        assert IPType.CLOCKING_WIZARD.value == "clk_wiz"
        assert IPType.FIFO_GENERATOR.value == "fifo_generator"
        assert IPType.BLOCK_MEMORY.value == "blk_mem_gen"
        assert IPType.DISTRIBUTED_MEMORY.value == "dist_mem_gen"
        assert IPType.DDS_COMPILER.value == "dds_compiler"
        assert IPType.XADC.value == "xadc_wiz"
        assert IPType.DMA.value == "axi_dma"
        assert IPType.AXI_INTERCONNECT.value == "axi_interconnect"
        assert IPType.AXI_BRAM_CTRL.value == "axi_bram_ctrl"
        assert IPType.PROCESSOR_SYSTEM.value == "processing_system7"
        assert IPType.AXI_GPIO.value == "axi_gpio"
        assert IPType.AXI_UART.value == "axi_uartlite"
        assert IPType.AXI_TIMER.value == "axi_timer"
        assert IPType.AXI_IIC.value == "axi_iic"
        assert IPType.AXI_SPI.value == "axi_quad_spi"
        assert IPType.MIG.value == "mig_7series"
        assert IPType.ILA.value == "ila"
        assert IPType.VIO.value == "vio"
        assert IPType.JTAG_TO_AXI.value == "jtag_axi"

    def test_ip_type_pll_mmcm_alias(self):
        """测试 PLL 和 MMCM 别名。"""
        assert IPType.PLL.value == "clk_wiz"
        assert IPType.MMCM.value == "clk_wiz"

    def test_ip_type_count(self):
        """测试 IP 类型数量。"""
        types = list(IPType)
        assert len(types) >= 19


class TestIPInterfaceType:
    """IPInterfaceType 枚举测试。"""

    def test_interface_type_values(self):
        """测试接口类型枚举值。"""
        assert IPInterfaceType.NATIVE.value == "Native"
        assert IPInterfaceType.AXI4_STREAM.value == "AXI4Stream"
        assert IPInterfaceType.AXI4_LITE.value == "AXI4Lite"
        assert IPInterfaceType.AXI4.value == "AXI4"

    def test_interface_type_count(self):
        """测试接口类型数量。"""
        types = list(IPInterfaceType)
        assert len(types) == 4


class TestMemoryType:
    """MemoryType 枚举测试。"""

    def test_memory_type_values(self):
        """测试存储器类型枚举值。"""
        assert MemoryType.RAM.value == "RAM"
        assert MemoryType.ROM.value == "ROM"
        assert MemoryType.DUAL_PORT.value == "DualPort"
        assert MemoryType.SIMPLE_DUAL_PORT.value == "SimpleDualPort"

    def test_memory_type_count(self):
        """测试存储器类型数量。"""
        types = list(MemoryType)
        assert len(types) == 4


# ==================== 数据类测试 ====================


class TestIPConfig:
    """IPConfig 基类测试。"""

    def test_ip_config_required_fields(self):
        """测试 IP 配置必需字段。"""
        config = IPConfig(name="test_ip")
        
        assert config.name == "test_ip"
        assert config.ip_type == IPType.CLOCKING_WIZARD
        assert config.vendor == "xilinx.com"
        assert config.library == "ip"
        assert config.module_name == "test_ip"

    def test_ip_config_custom_module_name(self):
        """测试自定义模块名称。"""
        config = IPConfig(name="test_ip", module_name="custom_module")
        
        assert config.module_name == "custom_module"

    def test_get_ip_vlnv_without_version(self):
        """测试不带版本的 VLNV 生成。"""
        config = IPConfig(name="test_ip", ip_type=IPType.FIFO_GENERATOR)
        vlnv = config.get_ip_vlnv()
        
        assert vlnv == "xilinx.com:ip:fifo_generator"

    def test_get_ip_vlnv_with_version(self):
        """测试带版本的 VLNV 生成。"""
        config = IPConfig(
            name="test_ip",
            ip_type=IPType.FIFO_GENERATOR,
            version="13.2"
        )
        vlnv = config.get_ip_vlnv()
        
        assert vlnv == "xilinx.com:ip:fifo_generator:13.2"


class TestClockingWizardConfig:
    """ClockingWizardConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = ClockingWizardConfig(name="clk_wiz_0")
        
        assert config.name == "clk_wiz_0"
        assert config.ip_type == IPType.CLOCKING_WIZARD
        assert config.input_frequency == 100.0
        assert config.output_clocks == []
        assert config.reset_type == "ACTIVE_HIGH"
        assert config.locked_output is True
        assert config.use_pll is False

    def test_custom_values(self):
        """测试自定义值。"""
        config = ClockingWizardConfig(
            name="clk_wiz_0",
            input_frequency=200.0,
            output_clocks=[
                {"name": "clk_out1", "frequency": 100.0, "phase": 0.0, "duty_cycle": 0.5},
                {"name": "clk_out2", "frequency": 200.0, "phase": 90.0, "duty_cycle": 0.5},
            ],
            reset_type="ACTIVE_LOW",
            use_pll=True,
            locked_output=False,
        )
        
        assert config.input_frequency == 200.0
        assert len(config.output_clocks) == 2
        assert config.reset_type == "ACTIVE_LOW"
        assert config.use_pll is True


class TestFIFOConfig:
    """FIFOConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = FIFOConfig(name="fifo_0")
        
        assert config.name == "fifo_0"
        assert config.ip_type == IPType.FIFO_GENERATOR
        assert config.interface_type == IPInterfaceType.NATIVE
        assert config.data_width == 32
        assert config.depth == 1024

    def test_is_synchronous(self):
        """测试同步 FIFO 判断。"""
        sync_config = FIFOConfig(name="sync_fifo")
        assert sync_config.is_synchronous() is True
        
        async_config = FIFOConfig(
            name="async_fifo",
            read_clock="clk_rd",
            write_clock="clk_wr",
        )
        assert async_config.is_synchronous() is False

    def test_custom_values(self):
        """测试自定义值。"""
        config = FIFOConfig(
            name="fifo_0",
            data_width=64,
            depth=2048,
            interface_type=IPInterfaceType.AXI4_STREAM,
            enable_data_count=True,
            enable_almost_flags=True,
        )
        
        assert config.data_width == 64
        assert config.depth == 2048
        assert config.interface_type == IPInterfaceType.AXI4_STREAM
        assert config.enable_data_count is True


class TestBRAMConfig:
    """BRAMConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = BRAMConfig(name="bram_0")
        
        assert config.name == "bram_0"
        assert config.ip_type == IPType.BLOCK_MEMORY
        assert config.memory_type == MemoryType.RAM
        assert config.data_width == 32
        assert config.depth == 1024

    def test_custom_values(self):
        """测试自定义值。"""
        config = BRAMConfig(
            name="bram_0",
            memory_type=MemoryType.DUAL_PORT,
            data_width=64,
            depth=4096,
            init_file="/path/to/init.coe",
            enable_ecc=True,
            port_a_width=64,
            port_b_width=32,
        )
        
        assert config.memory_type == MemoryType.DUAL_PORT
        assert config.init_file == "/path/to/init.coe"
        assert config.enable_ecc is True


class TestAXIInterconnectConfig:
    """AXIInterconnectConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = AXIInterconnectConfig(name="axi_interconnect_0")
        
        assert config.name == "axi_interconnect_0"
        assert config.ip_type == IPType.AXI_INTERCONNECT
        assert config.num_master_interfaces == 1
        assert config.num_slave_interfaces == 1
        assert config.data_width == 32

    def test_custom_values(self):
        """测试自定义值。"""
        config = AXIInterconnectConfig(
            name="axi_interconnect_0",
            num_master_interfaces=4,
            num_slave_interfaces=2,
            data_width=64,
            enable_protocol_checker=True,
            enable_register_slice=True,
        )
        
        assert config.num_master_interfaces == 4
        assert config.num_slave_interfaces == 2


class TestDMAConfig:
    """DMAConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = DMAConfig(name="axi_dma_0")
        
        assert config.name == "axi_dma_0"
        assert config.ip_type == IPType.DMA
        assert config.data_width == 32
        assert config.enable_sg is False
        assert config.enable_mm2s is True
        assert config.enable_s2mm is True

    def test_custom_values(self):
        """测试自定义值。"""
        config = DMAConfig(
            name="axi_dma_0",
            data_width=64,
            enable_sg=True,
            mm2s_burst_size=32,
            s2mm_burst_size=32,
        )
        
        assert config.enable_sg is True
        assert config.mm2s_burst_size == 32


class TestZynqPSConfig:
    """ZynqPSConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = ZynqPSConfig(name="processing_system7_0")
        
        assert config.name == "processing_system7_0"
        assert config.ip_type == IPType.PROCESSOR_SYSTEM
        assert config.enable_fabric_clock is True
        assert config.enable_fabric_reset is True
        assert config.enable_ddr is True
        assert config.enable_uart is True

    def test_custom_values(self):
        """测试自定义值。"""
        config = ZynqPSConfig(
            name="ps7_0",
            enable_ethernet=True,
            enable_usb=True,
            enable_sd=True,
            preset="ZedBoard",
        )
        
        assert config.enable_ethernet is True
        assert config.preset == "ZedBoard"


class TestXADCConfig:
    """XADCConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = XADCConfig(name="xadc_0")
        
        assert config.name == "xadc_0"
        assert config.ip_type == IPType.XADC
        assert config.enable_temperature is True
        assert config.enable_vccint is True
        assert config.sample_rate == 96

    def test_custom_values(self):
        """测试自定义值。"""
        config = XADCConfig(
            name="xadc_0",
            enable_auxiliary_channels=True,
            sample_rate=192,
            enable_axi=True,
        )
        
        assert config.enable_auxiliary_channels is True
        assert config.sample_rate == 192


class TestILAConfig:
    """ILAConfig 测试。"""

    def test_default_values(self):
        """测试默认值。"""
        config = ILAConfig(name="ila_0")
        
        assert config.name == "ila_0"
        assert config.ip_type == IPType.ILA
        assert config.num_probes == 1
        assert config.data_depth == 1024
        assert config.probe_widths == [1]

    def test_custom_values(self):
        """测试自定义值。"""
        config = ILAConfig(
            name="ila_0",
            num_probes=4,
            data_depth=4096,
            probe_widths=[32, 16, 8, 1],
            enable_trigger=True,
        )
        
        assert config.num_probes == 4
        assert config.data_depth == 4096
        assert config.probe_widths == [32, 16, 8, 1]


# ==================== IPTclGenerator 测试 ====================


class TestIPTclGenerator:
    """IPTclGenerator 测试。"""

    # --- 创建 IP 命令测试 ---

    def test_create_ip_tcl(self):
        """测试创建 IP Tcl 命令生成。"""
        config = IPConfig(name="test_ip", ip_type=IPType.FIFO_GENERATOR)
        tcl = IPTclGenerator.create_ip_tcl(config)
        
        assert "create_ip" in tcl
        assert "-vlnv xilinx.com:ip:fifo_generator" in tcl
        assert "-module_name test_ip" in tcl

    def test_create_ip_with_config_tcl(self):
        """测试创建并配置 IP Tcl 命令生成。"""
        config = IPConfig(name="test_ip")
        properties = {"CONFIG.Data_Width": 32}
        
        commands = IPTclGenerator.create_ip_with_config_tcl(config, properties)
        
        assert len(commands) == 2
        assert "create_ip" in commands[0]

    def test_set_property_tcl_boolean(self):
        """测试布尔类型属性设置。"""
        commands = IPTclGenerator.set_property_tcl("test_ip", {"ENABLE": True, "DISABLE": False})
        
        assert len(commands) == 2
        assert "true" in commands[0]
        assert "false" in commands[1]

    def test_set_property_tcl_string(self):
        """测试字符串类型属性设置。"""
        commands = IPTclGenerator.set_property_tcl("test_ip", {"NAME": "test_value"})
        
        assert len(commands) == 1
        assert "test_value" in commands[0]

    def test_set_property_tcl_list(self):
        """测试列表类型属性设置。"""
        commands = IPTclGenerator.set_property_tcl("test_ip", {"VALUES": [1, 2, 3]})
        
        assert len(commands) == 1
        assert "1 2 3" in commands[0]

    def test_set_property_tcl_number(self):
        """测试数字类型属性设置。"""
        commands = IPTclGenerator.set_property_tcl("test_ip", {"WIDTH": 32, "FREQ": 100.5})
        
        assert len(commands) == 2
        assert "32" in commands[0]
        assert "100.5" in commands[1]

    # --- IP 管理命令测试 ---

    def test_get_ip_report_tcl(self):
        """测试获取 IP 报告 Tcl 生成。"""
        tcl = IPTclGenerator.get_ip_report_tcl("test_ip")
        
        assert "report_property" in tcl
        assert "[get_ips test_ip]" in tcl

    def test_get_ip_info_tcl(self):
        """测试获取 IP 详细信息 Tcl 生成。"""
        commands = IPTclGenerator.get_ip_info_tcl("test_ip")
        
        assert len(commands) == 7
        assert "get_ips test_ip" in commands[0]

    def test_upgrade_ip_tcl(self):
        """测试升级 IP Tcl 生成。"""
        tcl = IPTclGenerator.upgrade_ip_tcl("test_ip")
        
        assert "upgrade_ip" in tcl
        assert "[get_ips test_ip]" in tcl

    def test_generate_output_products_tcl(self):
        """测试生成输出产品 Tcl 生成。"""
        tcl = IPTclGenerator.generate_output_products_tcl("test_ip")
        assert "generate_target all" in tcl
        assert "test_ip" in tcl
        
        tcl_force = IPTclGenerator.generate_output_products_tcl("test_ip", force=True)
        assert "-force" in tcl_force

    def test_reset_target_tcl(self):
        """测试重置目标 Tcl 生成。"""
        tcl = IPTclGenerator.reset_target_tcl("test_ip")
        
        assert "reset_target all" in tcl

    def test_remove_ip_tcl(self):
        """测试移除 IP Tcl 生成。"""
        tcl = IPTclGenerator.remove_ip_tcl("test_ip")
        
        assert "remove_ip" in tcl

    def test_list_ips_tcl(self):
        """测试列出 IP Tcl 生成。"""
        tcl = IPTclGenerator.list_ips_tcl()
        
        assert tcl == "get_ips"

    def test_get_ip_properties_tcl(self):
        """测试获取 IP 属性 Tcl 生成。"""
        commands = IPTclGenerator.get_ip_properties_tcl("test_ip", ["NAME", "VERSION"])
        
        assert len(commands) == 2
        assert "get_property NAME" in commands[0]
        assert "get_property VERSION" in commands[1]

    def test_get_ip_properties_tcl_all(self):
        """测试获取所有 IP 属性 Tcl 生成。"""
        commands = IPTclGenerator.get_ip_properties_tcl("test_ip")
        
        assert len(commands) == 1
        assert "report_property" in commands[0]

    # --- 属性生成测试 ---

    def test_generate_clocking_wizard_properties(self):
        """测试 Clocking Wizard 属性生成。"""
        config = ClockingWizardConfig(
            name="clk_wiz_0",
            input_frequency=100.0,
            output_clocks=[
                {"frequency": 50.0, "phase": 0.0, "duty_cycle": 0.5},
                {"frequency": 200.0, "phase": 90.0, "duty_cycle": 0.5},
            ],
            use_pll=True,
        )
        
        props = IPTclGenerator.generate_clocking_wizard_properties(config)
        
        assert props["PRIMITIVE"] == "PLL"
        assert props["PRIM_IN_FREQ"] == 100.0
        assert props["CLKOUT1_USED"] is True
        assert props["CLKOUT2_USED"] is True
        assert props["CLKOUT1_REQUESTED_OUT_FREQ"] == 50.0
        assert props["CLKOUT2_REQUESTED_OUT_FREQ"] == 200.0

    def test_generate_fifo_properties(self):
        """测试 FIFO 属性生成。"""
        config = FIFOConfig(
            name="fifo_0",
            data_width=64,
            depth=2048,
            enable_data_count=True,
        )
        
        props = IPTclGenerator.generate_fifo_properties(config)
        
        assert props["Data_Width"] == 64
        assert props["Write_Data_Count"] is True

    def test_generate_bram_properties(self):
        """测试 BRAM 属性生成。"""
        config = BRAMConfig(
            name="bram_0",
            data_width=64,
            depth=4096,
            memory_type=MemoryType.DUAL_PORT,
            enable_ecc=True,
        )
        
        props = IPTclGenerator.generate_bram_properties(config)
        
        assert props["Memory_Type"] == "True_Dual_Port_RAM"
        assert props["Write_Width_A"] == 64
        assert props["ECC_Type"] == "Hamming"

    def test_generate_bram_properties_with_init_file(self):
        """测试带初始化文件的 BRAM 属性生成。"""
        config = BRAMConfig(
            name="rom_0",
            memory_type=MemoryType.ROM,
            init_file="/path/to/init.coe",
        )
        
        props = IPTclGenerator.generate_bram_properties(config)
        
        assert props["Coe_File"] == "/path/to/init.coe"
        assert props["Load_Init_File"] is True

    def test_generate_axi_interconnect_properties(self):
        """测试 AXI Interconnect 属性生成。"""
        config = AXIInterconnectConfig(
            name="axi_interconnect_0",
            num_master_interfaces=4,
            num_slave_interfaces=2,
            enable_register_slice=True,
        )
        
        props = IPTclGenerator.generate_axi_interconnect_properties(config)
        
        assert props["NUM_MI"] == 4
        assert props["NUM_SI"] == 2
        assert props["MI0_ENABLE_REGISTER_SLICE"] is True
        assert props["SI0_ENABLE_REGISTER_SLICE"] is True

    def test_generate_dma_properties(self):
        """测试 DMA 属性生成。"""
        config = DMAConfig(
            name="axi_dma_0",
            data_width=64,
            enable_sg=True,
            mm2s_burst_size=32,
        )
        
        props = IPTclGenerator.generate_dma_properties(config)
        
        assert props["c_include_sg"] is True
        assert props["c_m_axi_mm2s_data_width"] == 64
        assert props["c_mm2s_burst_size"] == 32

    def test_generate_zynq_ps_properties(self):
        """测试 Zynq PS 属性生成。"""
        config = ZynqPSConfig(
            name="processing_system7_0",
            enable_fabric_clock=True,
            enable_ddr=True,
            enable_ethernet=True,
            preset="ZedBoard",
        )
        
        props = IPTclGenerator.generate_zynq_ps_properties(config)
        
        assert props["CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ"] == 100
        assert props["CONFIG.PCW_EN_ETH0"] is True
        assert props["CONFIG.preset"] == "ZedBoard"

    def test_generate_xadc_properties(self):
        """测试 XADC 属性生成。"""
        config = XADCConfig(
            name="xadc_0",
            enable_auxiliary_channels=True,
            sample_rate=192,
            enable_axi=True,
        )
        
        props = IPTclGenerator.generate_xadc_properties(config)
        
        assert props["CONFIG.ENABLE_AUXILIARY"] is True
        assert props["CONFIG.SAMPLE_RATE"] == 192
        assert props["CONFIG.ENABLE_AXI4"] is True

    def test_generate_ila_properties(self):
        """测试 ILA 属性生成。"""
        config = ILAConfig(
            name="ila_0",
            num_probes=4,
            data_depth=4096,
            probe_widths=[32, 16, 8, 1],
        )
        
        props = IPTclGenerator.generate_ila_properties(config)
        
        assert props["CONFIG.C_NUM_OF_PROBES"] == 4
        assert props["CONFIG.C_DATA_DEPTH"] == 4096
        assert props["CONFIG.C_PROBE0_WIDTH"] == 32
        assert props["CONFIG.C_PROBE1_WIDTH"] == 16


# ==================== IPManager 测试 ====================


@pytest.mark.integration
class TestIPManager:
    """IPManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """创建 IP 管理器。"""
        return IPManager(mock_engine)

    # --- create_clocking_wizard 测试 ---

    @pytest.mark.asyncio
    async def test_create_clocking_wizard_success(self, manager, mock_engine):
        """测试成功创建 Clocking Wizard。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = ClockingWizardConfig(
            name="clk_wiz_0",
            input_frequency=100.0,
            output_clocks=[{"frequency": 50.0}],
        )
        
        result = await manager.create_clocking_wizard(config)
        
        assert result["success"] is True
        assert result["ip_name"] == "clk_wiz_0"
        assert "clk_wiz_0" in manager.list_created_ips()

    @pytest.mark.asyncio
    async def test_create_clocking_wizard_failure(self, manager, mock_engine):
        """测试创建 Clocking Wizard 失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["IP creation failed"]
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = ClockingWizardConfig(name="clk_wiz_0")
        result = await manager.create_clocking_wizard(config)
        
        assert result["success"] is False
        assert "clk_wiz_0" not in manager.list_created_ips()

    # --- create_fifo 测试 ---

    @pytest.mark.asyncio
    async def test_create_fifo_success(self, manager, mock_engine):
        """测试成功创建 FIFO。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = FIFOConfig(name="fifo_0", data_width=64, depth=2048)
        result = await manager.create_fifo(config)
        
        assert result["success"] is True

    # --- create_bram 测试 ---

    @pytest.mark.asyncio
    async def test_create_bram_success(self, manager, mock_engine):
        """测试成功创建 BRAM。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = BRAMConfig(name="bram_0", memory_type=MemoryType.DUAL_PORT)
        result = await manager.create_bram(config)
        
        assert result["success"] is True

    # --- create_axi_interconnect 测试 ---

    @pytest.mark.asyncio
    async def test_create_axi_interconnect_success(self, manager, mock_engine):
        """测试成功创建 AXI Interconnect。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = AXIInterconnectConfig(
            name="axi_interconnect_0",
            num_master_interfaces=2,
        )
        result = await manager.create_axi_interconnect(config)
        
        assert result["success"] is True

    # --- create_dma 测试 ---

    @pytest.mark.asyncio
    async def test_create_dma_success(self, manager, mock_engine):
        """测试成功创建 DMA。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = DMAConfig(name="axi_dma_0", enable_sg=True)
        result = await manager.create_dma(config)
        
        assert result["success"] is True

    # --- create_zynq_ps 测试 ---

    @pytest.mark.asyncio
    async def test_create_zynq_ps_success(self, manager, mock_engine):
        """测试成功创建 Zynq PS。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = ZynqPSConfig(name="processing_system7_0", preset="ZedBoard")
        result = await manager.create_zynq_ps(config)
        
        assert result["success"] is True

    # --- create_xadc 测试 ---

    @pytest.mark.asyncio
    async def test_create_xadc_success(self, manager, mock_engine):
        """测试成功创建 XADC。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = XADCConfig(name="xadc_0")
        result = await manager.create_xadc(config)
        
        assert result["success"] is True

    # --- create_ila 测试 ---

    @pytest.mark.asyncio
    async def test_create_ila_success(self, manager, mock_engine):
        """测试成功创建 ILA。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = ILAConfig(name="ila_0", num_probes=4)
        result = await manager.create_ila(config)
        
        assert result["success"] is True

    # --- create_ip 通用方法测试 ---

    @pytest.mark.asyncio
    async def test_create_ip_clocking_wizard(self, manager, mock_engine):
        """测试通用创建 IP 方法 - Clocking Wizard。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = ClockingWizardConfig(name="clk_wiz_0")
        result = await manager.create_ip(config)
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_ip_fifo(self, manager, mock_engine):
        """测试通用创建 IP 方法 - FIFO。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = FIFOConfig(name="fifo_0")
        result = await manager.create_ip(config)
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_ip_unknown_type(self, manager, mock_engine):
        """测试通用创建 IP 方法 - 未知类型。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        # 使用基类 IPConfig
        config = IPConfig(name="unknown_ip", ip_type=IPType.CLOCKING_WIZARD)
        result = await manager.create_ip(config)
        
        assert result["success"] is True

    # --- get_ip_info 测试 ---

    @pytest.mark.asyncio
    async def test_get_ip_info_success(self, manager, mock_engine):
        """测试成功获取 IP 信息。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.output = "IP Name: clk_wiz_0\nIP VLNV: xilinx.com:ip:clk_wiz:6.0\nIP Version: 6.0"
        mock_engine.execute_async.return_value = mock_result
        
        info = await manager.get_ip_info("clk_wiz_0")
        
        assert info["exists"] is True
        assert info["name"] == "clk_wiz_0"
        assert info["vlnv"] == "xilinx.com:ip:clk_wiz:6.0"

    @pytest.mark.asyncio
    async def test_get_ip_info_not_found(self, manager, mock_engine):
        """测试 IP 不存在时获取信息。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["IP not found"]
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        info = await manager.get_ip_info("nonexistent")
        
        assert info["exists"] is False

    # --- list_ips 测试 ---

    @pytest.mark.asyncio
    async def test_list_ips_success(self, manager, mock_engine):
        """测试成功列出 IP。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.output = "clk_wiz_0\nfifo_0\nbram_0"
        mock_engine.execute_async.return_value = mock_result
        
        ips = await manager.list_ips()
        
        assert len(ips) == 3

    @pytest.mark.asyncio
    async def test_list_ips_failure(self, manager, mock_engine):
        """测试列出 IP 失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Error"]
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        ips = await manager.list_ips()
        
        assert ips == []

    # --- upgrade_ip 测试 ---

    @pytest.mark.asyncio
    async def test_upgrade_ip_success(self, manager, mock_engine):
        """测试成功升级 IP。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.upgrade_ip("clk_wiz_0")
        
        assert result["success"] is True

    # --- generate_output_products 测试 ---

    @pytest.mark.asyncio
    async def test_generate_output_products_success(self, manager, mock_engine):
        """测试成功生成输出产品。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.generate_output_products("clk_wiz_0")
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_output_products_force(self, manager, mock_engine):
        """测试强制生成输出产品。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.generate_output_products("clk_wiz_0", force=True)
        
        assert result["success"] is True

    # --- reset_target 测试 ---

    @pytest.mark.asyncio
    async def test_reset_target_success(self, manager, mock_engine):
        """测试成功重置目标。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.reset_target("clk_wiz_0")
        
        assert result["success"] is True

    # --- remove_ip 测试 ---

    @pytest.mark.asyncio
    async def test_remove_ip_success(self, manager, mock_engine):
        """测试成功移除 IP。"""
        # 先添加一个 IP
        manager._created_ips["test_ip"] = IPConfig(name="test_ip")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.remove_ip("test_ip")
        
        assert result["success"] is True
        assert "test_ip" not in manager._created_ips

    # --- set_ip_properties 测试 ---

    @pytest.mark.asyncio
    async def test_set_ip_properties_success(self, manager, mock_engine):
        """测试成功设置 IP 属性。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_ip_properties("clk_wiz_0", {"CONFIG.FREQ": 100.0})
        
        assert result["success"] is True

    # --- get_ip_report 测试 ---

    @pytest.mark.asyncio
    async def test_get_ip_report_success(self, manager, mock_engine):
        """测试成功获取 IP 报告。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.output = "IP Report..."
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.get_ip_report("clk_wiz_0")
        
        assert result["success"] is True
        assert result["report"] == "IP Report..."

    # --- get_ip_properties 测试 ---

    @pytest.mark.asyncio
    async def test_get_ip_properties_success(self, manager, mock_engine):
        """测试成功获取 IP 属性。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.output = "NAME: test\nVERSION: 1.0"
        mock_engine.execute_async.return_value = mock_result
        
        props = await manager.get_ip_properties("clk_wiz_0")
        
        assert "NAME" in props or props.get("errors") is None

    # --- 辅助方法测试 ---

    def test_get_created_ip(self, manager):
        """测试获取已创建的 IP 配置。"""
        config = IPConfig(name="test_ip")
        manager._created_ips["test_ip"] = config
        
        result = manager.get_created_ip("test_ip")
        
        assert result == config

    def test_get_created_ip_not_found(self, manager):
        """测试获取不存在的 IP 配置。"""
        result = manager.get_created_ip("nonexistent")
        
        assert result is None

    def test_list_created_ips(self, manager):
        """测试列出已创建的 IP。"""
        manager._created_ips["ip1"] = IPConfig(name="ip1")
        manager._created_ips["ip2"] = IPConfig(name="ip2")
        
        ips = manager.list_created_ips()
        
        assert len(ips) == 2
        assert "ip1" in ips
        assert "ip2" in ips

    # --- create_ip_instance 测试 ---

    @pytest.mark.asyncio
    async def test_create_ip_instance_success(self, manager, mock_engine):
        """测试成功创建 IP 实例。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        config = FIFOConfig(name="fifo_0")
        result = await manager.create_ip_instance(config, "fifo_inst_0")
        
        assert result["success"] is True
        assert result["instance_name"] == "fifo_inst_0"

    # --- batch_create_ips 测试 ---

    @pytest.mark.asyncio
    async def test_batch_create_ips_success(self, manager, mock_engine):
        """测试成功批量创建 IP。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        configs = [
            FIFOConfig(name="fifo_0"),
            BRAMConfig(name="bram_0"),
        ]
        
        result = await manager.batch_create_ips(configs)
        
        assert result["success"] is True
        assert len(result["created"]) == 2
        assert len(result["failed"]) == 0

    @pytest.mark.asyncio
    async def test_batch_create_ips_partial_failure(self, manager, mock_engine):
        """测试批量创建 IP 部分失败。"""
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_result.success = call_count[0] == 1  # 第一个成功，第二个失败
            mock_result.errors = [] if call_count[0] == 1 else ["Error"]
            mock_result.warnings = []
            mock_result.output = ""
            return mock_result
        
        mock_engine.execute_async.side_effect = side_effect
        
        configs = [
            FIFOConfig(name="fifo_0"),
            BRAMConfig(name="bram_0"),
        ]
        
        result = await manager.batch_create_ips(configs)
        
        assert result["success"] is False
        assert len(result["created"]) == 1
        assert len(result["failed"]) == 1

    # --- batch_generate_output_products 测试 ---

    @pytest.mark.asyncio
    async def test_batch_generate_output_products_success(self, manager, mock_engine):
        """测试成功批量生成输出产品。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.batch_generate_output_products(["ip1", "ip2"])
        
        assert result["success"] is True
        assert len(result["generated"]) == 2


# ==================== 便捷函数测试 ====================


class TestConvenienceFunctions:
    """便捷函数测试。"""

    def test_create_clocking_wizard_config(self):
        """测试创建 Clocking Wizard 配置便捷函数。"""
        config = create_clocking_wizard_config(
            name="clk_wiz_0",
            input_freq=200.0,
            output_clocks=[{"frequency": 100.0}],
            use_pll=True,
        )
        
        assert isinstance(config, ClockingWizardConfig)
        assert config.name == "clk_wiz_0"
        assert config.input_frequency == 200.0
        assert config.use_pll is True

    def test_create_fifo_config(self):
        """测试创建 FIFO 配置便捷函数。"""
        config = create_fifo_config(
            name="fifo_0",
            data_width=64,
            depth=2048,
            synchronous=True,
        )
        
        assert isinstance(config, FIFOConfig)
        assert config.name == "fifo_0"
        assert config.data_width == 64
        assert config.depth == 2048

    def test_create_bram_config(self):
        """测试创建 BRAM 配置便捷函数。"""
        config = create_bram_config(
            name="bram_0",
            data_width=64,
            depth=4096,
            memory_type=MemoryType.DUAL_PORT,
        )
        
        assert isinstance(config, BRAMConfig)
        assert config.name == "bram_0"
        assert config.memory_type == MemoryType.DUAL_PORT


# ==================== 边界情况测试 ====================


class TestIPConfigEdgeCases:
    """IP 配置边界情况测试。"""

    def test_empty_name(self):
        """测试空名称。"""
        config = IPConfig(name="")
        assert config.name == ""

    def test_special_characters_in_name(self):
        """测试名称中的特殊字符。"""
        config = IPConfig(name="test_ip_123")
        assert config.name == "test_ip_123"

    def test_very_long_name(self):
        """测试超长名称。"""
        long_name = "a" * 1000
        config = IPConfig(name=long_name)
        assert config.name == long_name

    def test_zero_values(self):
        """测试零值。"""
        config = FIFOConfig(name="fifo_0", data_width=0, depth=0)
        assert config.data_width == 0
        assert config.depth == 0

    def test_negative_values(self):
        """测试负值。"""
        # 数据类不验证，但可以设置
        config = FIFOConfig(name="fifo_0", data_width=-1)
        assert config.data_width == -1

    def test_empty_output_clocks(self):
        """测试空输出时钟列表。"""
        config = ClockingWizardConfig(name="clk_wiz_0", output_clocks=[])
        assert config.output_clocks == []

    def test_many_output_clocks(self):
        """测试多个输出时钟。"""
        clocks = [{"frequency": 100.0 * i} for i in range(1, 8)]
        config = ClockingWizardConfig(name="clk_wiz_0", output_clocks=clocks)
        assert len(config.output_clocks) == 7

    def test_unicode_in_name(self):
        """测试 Unicode 名称。"""
        config = IPConfig(name="测试IP")
        assert config.name == "测试IP"

    def test_path_in_init_file(self):
        """测试初始化文件路径。"""
        config = BRAMConfig(
            name="rom_0",
            init_file="C:/path/to/init.coe",
        )
        assert config.init_file == "C:/path/to/init.coe"
