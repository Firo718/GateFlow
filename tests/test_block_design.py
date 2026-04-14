"""
Block Design 模块测试。

测试 BDInterfaceType、BDAutoConnectRule 枚举，
BDPort、BDIPInstance、BDConnection 数据类，
BlockDesignTclGenerator 和 BlockDesignManager。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.vivado.block_design import (
    BDInterfaceType,
    BDAutoConnectRule,
    BDPort,
    BDIPInstance,
    BDConnection,
    BlockDesignConfig,
    ZynqPSConfig,
    BlockDesignTclGenerator,
    BlockDesignManager,
)


# ==================== 枚举测试 ====================


class TestBDInterfaceType:
    """BDInterfaceType 枚举测试。"""

    def test_interface_type_values(self):
        """测试接口类型枚举值。"""
        assert BDInterfaceType.AXI4LITE.value == "axi4lite"
        assert BDInterfaceType.AXI4MM.value == "axi4mm"
        assert BDInterfaceType.AXI4STREAM.value == "axi4stream"
        assert BDInterfaceType.CLOCK.value == "clock"
        assert BDInterfaceType.RESET.value == "reset"
        assert BDInterfaceType.INTERRUPT.value == "interrupt"
        assert BDInterfaceType.GPIO.value == "gpio"

    def test_interface_type_count(self):
        """测试接口类型数量。"""
        types = list(BDInterfaceType)
        assert len(types) == 7


class TestBDAutoConnectRule:
    """BDAutoConnectRule 枚举测试。"""

    def test_auto_connect_rule_values(self):
        """测试自动连接规则枚举值。"""
        assert BDAutoConnectRule.ALL.value == "all"
        assert BDAutoConnectRule.AXI4.value == "axi4"
        assert BDAutoConnectRule.CLOCK.value == "clock"
        assert BDAutoConnectRule.RESET.value == "reset"
        assert BDAutoConnectRule.INTERRUPT.value == "interrupt"

    def test_auto_connect_rule_count(self):
        """测试自动连接规则数量。"""
        rules = list(BDAutoConnectRule)
        assert len(rules) == 5


# ==================== 数据类测试 ====================


class TestBDPort:
    """BDPort 数据类测试。"""

    def test_bd_port_required_fields(self):
        """测试端口必需字段。"""
        port = BDPort(name="clk", direction="input")
        
        assert port.name == "clk"
        assert port.direction == "input"
        assert port.interface_type is None
        assert port.width == 1

    def test_bd_port_custom_values(self):
        """测试端口自定义值。"""
        port = BDPort(
            name="data",
            direction="output",
            interface_type=BDInterfaceType.AXI4STREAM,
            width=32,
        )
        
        assert port.direction == "output"
        assert port.interface_type == BDInterfaceType.AXI4STREAM
        assert port.width == 32

    def test_bd_port_invalid_direction(self):
        """测试无效端口方向。"""
        with pytest.raises(ValueError, match="无效的端口方向"):
            BDPort(name="test", direction="invalid")

    def test_bd_port_invalid_width(self):
        """测试无效端口宽度。"""
        with pytest.raises(ValueError, match="端口宽度必须大于 0"):
            BDPort(name="test", direction="input", width=0)

    def test_bd_port_inout(self):
        """测试双向端口。"""
        port = BDPort(name="gpio", direction="inout", width=8)
        
        assert port.direction == "inout"
        assert port.width == 8


class TestBDIPInstance:
    """BDIPInstance 数据类测试。"""

    def test_bd_ip_instance_required_fields(self):
        """测试 IP 实例必需字段。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        
        assert instance.name == "axi_gpio_0"
        assert instance.ip_type == "xilinx.com:ip:axi_gpio:2.0"
        assert instance.config == {}
        assert instance.ports == []

    def test_bd_ip_instance_custom_values(self):
        """测试 IP 实例自定义值。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
            config={"CONFIG.C_GPIO_WIDTH": "8"},
            ports=[BDPort(name="gpio", direction="inout", width=8)],
        )
        
        assert instance.config == {"CONFIG.C_GPIO_WIDTH": "8"}
        assert len(instance.ports) == 1

    def test_bd_ip_instance_invalid_name(self):
        """测试无效实例名称。"""
        with pytest.raises(ValueError, match="无效的实例名称"):
            BDIPInstance(name="", ip_type="xilinx.com:ip:axi_gpio:2.0")

    def test_bd_ip_instance_special_chars_in_name(self):
        """测试名称中的特殊字符。"""
        # 只有字母数字和下划线是有效的
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        assert instance.name == "axi_gpio_0"


class TestBDConnection:
    """BDConnection 数据类测试。"""

    def test_bd_connection_required_fields(self):
        """测试连接必需字段。"""
        conn = BDConnection(
            name=None,
            source="axi_gpio_0/S_AXI",
            destination="axi_interconnect_0/M00_AXI",
        )
        
        assert conn.name is None
        assert conn.source == "axi_gpio_0/S_AXI"
        assert conn.destination == "axi_interconnect_0/M00_AXI"

    def test_bd_connection_with_name(self):
        """测试带名称的连接。"""
        conn = BDConnection(
            name="axi_conn_0",
            source="axi_gpio_0/S_AXI",
            destination="axi_interconnect_0/M00_AXI",
        )
        
        assert conn.name == "axi_conn_0"

    def test_bd_connection_invalid_source_format(self):
        """测试无效源端口格式。"""
        with pytest.raises(ValueError, match="源端口格式错误"):
            BDConnection(name=None, source="invalid", destination="a/b")

    def test_bd_connection_invalid_destination_format(self):
        """测试无效目标端口格式。"""
        with pytest.raises(ValueError, match="目标端口格式错误"):
            BDConnection(name=None, source="a/b", destination="invalid")


class TestBlockDesignConfig:
    """BlockDesignConfig 数据类测试。"""

    def test_block_design_config_required_fields(self):
        """测试 Block Design 配置必需字段。"""
        config = BlockDesignConfig(name="system")
        
        assert config.name == "system"
        assert config.ip_instances == []
        assert config.connections == []
        assert config.external_ports == []

    def test_block_design_config_with_instances(self):
        """测试带实例的 Block Design 配置。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        config = BlockDesignConfig(name="system", ip_instances=[instance])
        
        assert len(config.ip_instances) == 1


class TestZynqPSConfigBD:
    """ZynqPSConfig (Block Design) 测试。"""

    def test_zynq_ps_config_default_values(self):
        """测试 Zynq PS 配置默认值。"""
        config = ZynqPSConfig()
        
        assert config.enable_fabric_reset is True
        assert config.enable_fabric_clock is True
        assert config.enable_ddr is True
        assert config.enable_uart0 is True
        assert config.enable_enet0 is False

    def test_zynq_ps_config_custom_values(self):
        """测试 Zynq PS 配置自定义值。"""
        config = ZynqPSConfig(
            enable_fabric_reset=False,
            enable_enet0=True,
            enable_usb0=True,
            custom_config={"CONFIG.PCW_PRESET": "ZedBoard"},
        )
        
        assert config.enable_fabric_reset is False
        assert config.custom_config == {"CONFIG.PCW_PRESET": "ZedBoard"}


# ==================== BlockDesignTclGenerator 测试 ====================


class TestBlockDesignTclGenerator:
    """BlockDesignTclGenerator 测试。"""

    # --- Block Design 管理命令测试 ---

    def test_create_bd_design_tcl(self):
        """测试创建 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.create_bd_design_tcl("system")
        
        assert 'create_bd_design "system"' in tcl

    def test_open_bd_design_tcl(self):
        """测试打开 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.open_bd_design_tcl("system")
        
        assert 'open_bd_design' in tcl
        assert '"system"' in tcl

    def test_close_bd_design_tcl(self):
        """测试关闭 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.close_bd_design_tcl()
        
        assert 'close_bd_design' in tcl

    def test_save_bd_design_tcl(self):
        """测试保存 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.save_bd_design_tcl()
        
        assert tcl == 'save_bd_design'

    def test_save_bd_design_as_tcl(self):
        """测试另存为 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.save_bd_design_as_tcl("system_copy")
        
        assert 'save_bd_design_as' in tcl
        assert '"system_copy"' in tcl

    # --- IP 实例命令测试 ---

    def test_create_bd_cell_tcl(self):
        """测试创建 IP 实例 Tcl 生成。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        tcl = BlockDesignTclGenerator.create_bd_cell_tcl(instance)
        
        assert "create_bd_cell" in tcl
        assert "-type ip" in tcl
        assert "-vlnv xilinx.com:ip:axi_gpio:2.0" in tcl
        assert "axi_gpio_0" in tcl

    def test_create_bd_cell_with_config_tcl(self):
        """测试创建并配置 IP 实例 Tcl 生成。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
            config={"CONFIG.C_GPIO_WIDTH": "8"},
        )
        commands = BlockDesignTclGenerator.create_bd_cell_with_config_tcl(instance)
        
        assert len(commands) == 2
        assert "create_bd_cell" in commands[0]
        assert "set_property" in commands[1]

    def test_set_bd_property_tcl(self):
        """测试设置 IP 属性 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.set_bd_property_tcl(
            "axi_gpio_0",
            {"CONFIG.C_GPIO_WIDTH": "8", "CONFIG.C_IS_DUAL": True},
        )
        
        assert "set_property -dict" in tcl
        assert "get_bd_cells axi_gpio_0" in tcl

    def test_set_bd_property_tcl_string_value(self):
        """测试字符串属性值设置。"""
        tcl = BlockDesignTclGenerator.set_bd_property_tcl(
            "cell_0",
            {"NAME": "test_value"},
        )
        
        assert '"test_value"' in tcl

    def test_set_bd_property_tcl_boolean_value(self):
        """测试布尔属性值设置。"""
        tcl = BlockDesignTclGenerator.set_bd_property_tcl(
            "cell_0",
            {"ENABLE": True, "DISABLE": False},
        )
        
        assert "true" in tcl
        assert "false" in tcl

    # --- 端口命令测试 ---

    def test_create_bd_port_tcl_input(self):
        """测试创建输入端口 Tcl 生成。"""
        port = BDPort(name="clk", direction="input")
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        assert "create_bd_port" in tcl
        assert "-dir I" in tcl
        assert "clk" in tcl

    def test_create_bd_port_tcl_output(self):
        """测试创建输出端口 Tcl 生成。"""
        port = BDPort(name="led", direction="output", width=8)
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        assert "-dir O" in tcl
        assert "-from 7 -to 0" in tcl

    def test_create_bd_port_tcl_inout(self):
        """测试创建双向端口 Tcl 生成。"""
        port = BDPort(name="gpio", direction="inout")
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        assert "-dir IO" in tcl

    def test_create_bd_port_tcl_interface(self):
        """测试创建接口端口 Tcl 生成。"""
        port = BDPort(
            name="s_axi",
            direction="input",
            interface_type=BDInterfaceType.AXI4LITE,
        )
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        assert "create_bd_intf_port" in tcl
        assert "-mode Master" in tcl

    def test_create_bd_intf_port_tcl(self):
        """测试创建接口端口 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.create_bd_intf_port_tcl(
            name="M_AXI",
            mode="Master",
            vlnv="xilinx.com:interface:aximm_rtl:1.0",
        )
        
        assert "create_bd_intf_port" in tcl
        assert "-mode Master" in tcl
        assert "xilinx.com:interface:aximm_rtl:1.0" in tcl

    # --- 连接命令测试 ---

    def test_connect_bd_intf_net_tcl(self):
        """测试连接接口网络 Tcl 生成。"""
        conn = BDConnection(
            name=None,
            source="axi_interconnect_0/M00_AXI",
            destination="axi_gpio_0/S_AXI",
        )
        tcl = BlockDesignTclGenerator.connect_bd_intf_net_tcl(conn)
        
        assert "connect_bd_intf_net" in tcl
        assert "get_bd_intf_pins axi_interconnect_0/M00_AXI" in tcl

    def test_connect_bd_intf_net_tcl_with_name(self):
        """测试带名称的连接接口网络 Tcl 生成。"""
        conn = BDConnection(
            name="conn_0",
            source="axi_interconnect_0/M00_AXI",
            destination="axi_gpio_0/S_AXI",
        )
        tcl = BlockDesignTclGenerator.connect_bd_intf_net_tcl(conn)
        
        assert "conn_0" in tcl

    def test_connect_bd_intf_net_tcl_external_source(self):
        """测试外部源端口连接 Tcl 生成。"""
        conn = BDConnection(
            name=None,
            source="external/M_AXI",
            destination="axi_gpio_0/S_AXI",
        )
        tcl = BlockDesignTclGenerator.connect_bd_intf_net_tcl(conn)
        
        assert "get_bd_intf_ports M_AXI" in tcl

    def test_connect_bd_intf_net_tcl_external_destination(self):
        """测试外部目标端口连接 Tcl 生成。"""
        conn = BDConnection(
            name=None,
            source="axi_gpio_0/M_AXI",
            destination="external/S_AXI",
        )
        tcl = BlockDesignTclGenerator.connect_bd_intf_net_tcl(conn)
        
        assert "get_bd_intf_ports S_AXI" in tcl

    def test_connect_bd_net_tcl(self):
        """测试连接普通网络 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.connect_bd_net_tcl(
            source="clk_wiz_0/clk_out1",
            destinations=["axi_gpio_0/s_axi_aclk", "axi_interconnect_0/ACLK"],
        )
        
        assert "connect_bd_net" in tcl
        assert "get_bd_pins clk_wiz_0/clk_out1" in tcl

    def test_connect_bd_net_tcl_external_source(self):
        """测试外部源端口普通网络连接 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.connect_bd_net_tcl(
            source="external/clk",
            destinations=["clk_wiz_0/clk_in1"],
        )
        
        assert "get_bd_ports clk" in tcl

    # --- 自动化命令测试 ---

    def test_apply_bd_automation_tcl(self):
        """测试应用自动连接 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.apply_bd_automation_tcl("all")
        
        assert "apply_bd_automation -rule all" in tcl

    def test_apply_bd_automation_full_tcl(self):
        """测试完整自动连接 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.apply_bd_automation_full_tcl(
            rule="axi4",
            exclude_cells=["cell_0", "cell_1"],
        )
        
        assert "apply_bd_automation -rule axi4" in tcl
        assert "-exclude" in tcl

    # --- 验证和生成命令测试 ---

    def test_validate_bd_design_tcl(self):
        """测试验证 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.validate_bd_design_tcl()
        
        assert tcl == "validate_bd_design"

    def test_generate_bd_wrapper_tcl(self):
        """测试生成 HDL Wrapper Tcl 生成。"""
        tcl = BlockDesignTclGenerator.generate_bd_wrapper_tcl("system")
        
        assert "make_wrapper" in tcl
        assert "system.bd" in tcl

    def test_generate_bd_wrapper_tcl_with_path(self):
        """测试带路径的生成 HDL Wrapper Tcl 生成。"""
        tcl = BlockDesignTclGenerator.generate_bd_wrapper_tcl(
            "system",
            wrapper_path=Path("/path/to/wrapper"),
        )
        
        assert "make_wrapper" in tcl

    # --- 查询命令测试 ---

    def test_get_bd_cells_tcl(self):
        """测试获取所有 IP 实例 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_cells_tcl()
        
        assert tcl == "get_bd_cells"

    def test_get_bd_cell_tcl(self):
        """测试获取指定 IP 实例 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_cell_tcl("axi_gpio_0")
        
        assert "get_bd_cells axi_gpio_0" in tcl

    def test_get_bd_intf_pins_tcl(self):
        """测试获取接口引脚 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_intf_pins_tcl("axi_gpio_0")
        
        assert "get_bd_intf_pins" in tcl
        assert "get_bd_cells axi_gpio_0" in tcl

    def test_get_bd_pins_tcl(self):
        """测试获取普通引脚 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_pins_tcl("axi_gpio_0")
        
        assert "get_bd_pins" in tcl

    def test_get_bd_intf_ports_tcl(self):
        """测试获取所有接口端口 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_intf_ports_tcl()
        
        assert tcl == "get_bd_intf_ports"

    def test_get_bd_ports_tcl(self):
        """测试获取所有普通端口 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.get_bd_ports_tcl()
        
        assert tcl == "get_bd_ports"

    # --- 删除命令测试 ---

    def test_delete_bd_cell_tcl(self):
        """测试删除 IP 实例 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.delete_bd_cell_tcl("axi_gpio_0")
        
        assert "delete_bd_objs" in tcl
        assert "get_bd_cells axi_gpio_0" in tcl

    def test_delete_bd_port_tcl(self):
        """测试删除端口 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.delete_bd_port_tcl("clk")
        
        assert "delete_bd_objs" in tcl
        assert "get_bd_ports clk" in tcl

    def test_delete_bd_intf_port_tcl(self):
        """测试删除接口端口 Tcl 生成。"""
        tcl = BlockDesignTclGenerator.delete_bd_intf_port_tcl("M_AXI")
        
        assert "delete_bd_objs" in tcl
        assert "get_bd_intf_ports M_AXI" in tcl

    # --- 特定 IP 创建命令测试 ---

    def test_create_zynq_ps_tcl(self):
        """测试创建 Zynq PS Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_zynq_ps_tcl(
            name="processing_system7_0",
            config=None,
        )
        
        assert len(commands) == 1
        assert "create_bd_cell" in commands[0]
        assert "processing_system7:5.5" in commands[0]

    def test_create_zynq_ps_tcl_with_config(self):
        """测试带配置的创建 Zynq PS Tcl 生成。"""
        config = ZynqPSConfig(enable_fabric_reset=True, enable_ddr=True)
        commands = BlockDesignTclGenerator.create_zynq_ps_tcl(
            name="processing_system7_0",
            config=config,
        )
        
        assert len(commands) >= 1
        assert "create_bd_cell" in commands[0]

    def test_create_zynq_ultra_ps_tcl(self):
        """测试创建 Zynq UltraScale+ PS Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_zynq_ultra_ps_tcl(
            name="zynq_ultra_ps_e_0",
            preset="zu7ev",
        )
        
        assert len(commands) == 2
        assert "zynq_ultra_ps_e:3.5" in commands[0]
        assert "preset_zu7ev" in commands[1]

    def test_create_axi_interconnect_tcl(self):
        """测试创建 AXI Interconnect Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_axi_interconnect_tcl(
            name="axi_interconnect_0",
            num_mi=4,
            num_si=2,
        )
        
        assert len(commands) == 2
        assert "axi_interconnect:2.1" in commands[0]
        assert "NUM_MI" in commands[1]

    def test_create_clock_wizard_tcl(self):
        """测试创建 Clock Wizard Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_clock_wizard_tcl(
            name="clk_wiz_0",
            input_freq=100.0,
            output_freqs=[50.0, 100.0, 200.0],
        )
        
        assert len(commands) == 2
        assert "clk_wiz:6.0" in commands[0]
        assert "PRIM_IN_FREQ" in commands[1]

    def test_create_processor_reset_tcl(self):
        """测试创建 Processor System Reset Tcl 生成。"""
        tcl = BlockDesignTclGenerator.create_processor_reset_tcl("proc_sys_reset_0")
        
        assert "proc_sys_reset:5.0" in tcl

    def test_create_axi_gpio_tcl(self):
        """测试创建 AXI GPIO Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_axi_gpio_tcl(
            name="axi_gpio_0",
            width=16,
            is_dual=True,
        )
        
        assert len(commands) == 2
        assert "axi_gpio:2.0" in commands[0]
        assert "C_GPIO_WIDTH" in commands[1]

    def test_create_axi_bram_tcl(self):
        """测试创建 AXI BRAM Controller Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_axi_bram_tcl(
            name="axi_bram_ctrl_0",
            data_width=64,
            memory_depth=8192,
        )
        
        assert len(commands) == 2
        assert "axi_bram_ctrl:4.1" in commands[0]

    def test_create_axi_dma_tcl(self):
        """测试创建 AXI DMA Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_axi_dma_tcl(
            name="axi_dma_0",
            include_sg=True,
        )
        
        assert len(commands) == 2
        assert "axi_dma:7.1" in commands[0]
        assert "c_include_sg" in commands[1]

    def test_create_axis_data_fifo_tcl(self):
        """测试创建 AXI-Stream Data FIFO Tcl 生成。"""
        commands = BlockDesignTclGenerator.create_axis_data_fifo_tcl(
            name="axis_data_fifo_0",
            depth=2048,
            width=64,
        )
        
        assert len(commands) == 2
        assert "axis_data_fifo:2.0" in commands[0]

    # --- 自动连接命令测试 ---

    def test_auto_connect_axi_clock_reset_tcl(self):
        """测试自动连接 AXI 时钟和复位 Tcl 生成。"""
        commands = BlockDesignTclGenerator.auto_connect_axi_clock_reset_tcl(
            axi_cell="axi_gpio_0",
            clock_source="processing_system7_0/FCLK_CLK0",
            reset_source="proc_sys_reset_0/peripheral_aresetn",
        )
        
        assert len(commands) == 2
        assert "connect_bd_net" in commands[0]
        assert "s_axi_aclk" in commands[0]
        assert "s_axi_aresetn" in commands[1]

    # --- 导入导出命令测试 ---

    def test_export_bd_tcl(self):
        """测试导出 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.export_bd_tcl(
            "system",
            Path("/path/to/export.tcl"),
        )
        
        assert "write_bd_tcl" in tcl
        assert "-force" in tcl

    def test_import_bd_tcl(self):
        """测试导入 Block Design Tcl 生成。"""
        tcl = BlockDesignTclGenerator.import_bd_tcl(Path("/path/to/import.tcl"))
        
        assert 'source' in tcl
        assert 'import.tcl' in tcl


# ==================== BlockDesignManager 测试 ====================


@pytest.mark.integration
class TestBlockDesignManager:
    """BlockDesignManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """创建 Block Design 管理器。"""
        return BlockDesignManager(mock_engine)

    # --- create_design 测试 ---

    @pytest.mark.asyncio
    async def test_create_design_success(self, manager, mock_engine):
        """测试成功创建 Block Design。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_design("system")
        
        assert result["success"] is True
        assert manager.current_design is not None
        assert manager.current_design.name == "system"

    @pytest.mark.asyncio
    async def test_create_design_failure(self, manager, mock_engine):
        """测试创建 Block Design 失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Design already exists"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_design("system")
        
        assert result["success"] is False
        assert manager.current_design is None

    # --- open_design 测试 ---

    @pytest.mark.asyncio
    async def test_open_design_success(self, manager, mock_engine):
        """测试成功打开 Block Design。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.open_design("system")
        
        assert result["success"] is True
        assert manager.current_design is not None

    # --- close_design 测试 ---

    @pytest.mark.asyncio
    async def test_close_design_success(self, manager, mock_engine):
        """测试成功关闭 Block Design。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.close_design()
        
        assert result["success"] is True
        assert manager.current_design is None

    # --- add_ip_instance 测试 ---

    @pytest.mark.asyncio
    async def test_add_ip_instance_success(self, manager, mock_engine):
        """测试成功添加 IP 实例。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        result = await manager.add_ip_instance(instance)
        
        assert result["success"] is True
        assert len(manager.current_design.ip_instances) == 1

    @pytest.mark.asyncio
    async def test_add_ip_instance_failure(self, manager, mock_engine):
        """测试添加 IP 实例失败。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["IP not found"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:invalid:1.0",
        )
        result = await manager.add_ip_instance(instance)
        
        assert result["success"] is False

    # --- remove_ip_instance 测试 ---

    @pytest.mark.asyncio
    async def test_remove_ip_instance_success(self, manager, mock_engine):
        """测试成功移除 IP 实例。"""
        instance = BDIPInstance(
            name="axi_gpio_0",
            ip_type="xilinx.com:ip:axi_gpio:2.0",
        )
        manager.current_design = BlockDesignConfig(
            name="system",
            ip_instances=[instance],
        )
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.remove_ip_instance("axi_gpio_0")
        
        assert result["success"] is True
        assert len(manager.current_design.ip_instances) == 0

    # --- create_external_port 测试 ---

    @pytest.mark.asyncio
    async def test_create_external_port_success(self, manager, mock_engine):
        """测试成功创建外部端口。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        port = BDPort(name="clk", direction="input")
        result = await manager.create_external_port(port)
        
        assert result["success"] is True
        assert len(manager.current_design.external_ports) == 1

    # --- connect_ports 测试 ---

    @pytest.mark.asyncio
    async def test_connect_ports_success(self, manager, mock_engine):
        """测试成功连接端口。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.connect_ports(
            source="clk_wiz_0/clk_out1",
            destination="axi_gpio_0/s_axi_aclk",
        )
        
        assert result["success"] is True
        assert len(manager.current_design.connections) == 1

    # --- connect_interface 测试 ---

    @pytest.mark.asyncio
    async def test_connect_interface_success(self, manager, mock_engine):
        """测试成功连接接口。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.connect_interface(
            source="axi_interconnect_0/M00_AXI",
            destination="axi_gpio_0/S_AXI",
        )
        
        assert result["success"] is True

    # --- apply_automation 测试 ---

    @pytest.mark.asyncio
    async def test_apply_automation_success(self, manager, mock_engine):
        """测试成功应用自动连接。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.apply_automation("all")
        
        assert result["success"] is True

    # --- validate_design 测试 ---

    @pytest.mark.asyncio
    async def test_validate_design_success(self, manager, mock_engine):
        """测试成功验证设计。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.validate_design()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_validate_design_failure(self, manager, mock_engine):
        """测试验证设计失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Validation failed"]
        mock_result.warnings = ["Unconnected port"]
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.validate_design()
        
        assert result["success"] is False
        assert len(result["warnings"]) == 1

    # --- generate_wrapper 测试 ---

    @pytest.mark.asyncio
    async def test_generate_wrapper_no_design(self, manager):
        """测试没有打开设计时生成 Wrapper。"""
        result = await manager.generate_wrapper()
        
        assert result["success"] is False
        assert "没有打开的 Block Design" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_generate_wrapper_success(self, manager, mock_engine):
        """测试成功生成 Wrapper。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.generate_wrapper()
        
        assert result["success"] is True

    # --- save_design 测试 ---

    @pytest.mark.asyncio
    async def test_save_design_success(self, manager, mock_engine):
        """测试成功保存设计。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.save_design()
        
        assert result["success"] is True

    # --- get_cells 测试 ---

    @pytest.mark.asyncio
    async def test_get_cells_success(self, manager, mock_engine):
        """测试成功获取 IP 实例列表。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "axi_gpio_0\naxi_interconnect_0\n"
        mock_engine.execute_async.return_value = mock_result
        
        cells = await manager.get_cells()
        
        assert len(cells) >= 2

    @pytest.mark.asyncio
    async def test_get_cells_failure(self, manager, mock_engine):
        """测试获取 IP 实例列表失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Error"]
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        cells = await manager.get_cells()
        
        assert cells == []

    # --- get_connections 测试 ---

    @pytest.mark.asyncio
    async def test_get_connections_success(self, manager, mock_engine):
        """测试成功获取连接列表。"""
        mock_intf_result = MagicMock()
        mock_intf_result.success = True
        mock_intf_result.output = "conn_0\nconn_1\n"
        
        mock_net_result = MagicMock()
        mock_net_result.success = True
        mock_net_result.output = "net_0\n"
        
        mock_engine.execute_async.side_effect = [mock_intf_result, mock_net_result]
        
        connections = await manager.get_connections()
        
        assert len(connections) >= 2

    # --- create_zynq_ps 测试 ---

    @pytest.mark.asyncio
    async def test_create_zynq_ps_success(self, manager, mock_engine):
        """测试成功创建 Zynq PS。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_zynq_ps("processing_system7_0")
        
        assert result["success"] is True
        assert len(manager.current_design.ip_instances) == 1

    # --- create_zynq_ultra_ps 测试 ---

    @pytest.mark.asyncio
    async def test_create_zynq_ultra_ps_success(self, manager, mock_engine):
        """测试成功创建 Zynq UltraScale+ PS。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_zynq_ultra_ps("zynq_ultra_ps_e_0", "zu7ev")
        
        assert result["success"] is True

    # --- create_axi_interconnect 测试 ---

    @pytest.mark.asyncio
    async def test_create_axi_interconnect_success(self, manager, mock_engine):
        """测试成功创建 AXI Interconnect。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_axi_interconnect("axi_interconnect_0", num_mi=4)
        
        assert result["success"] is True

    # --- create_clock_wizard 测试 ---

    @pytest.mark.asyncio
    async def test_create_clock_wizard_success(self, manager, mock_engine):
        """测试成功创建 Clock Wizard。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_clock_wizard(
            "clk_wiz_0",
            input_freq=100.0,
            output_freqs=[50.0, 100.0],
        )
        
        assert result["success"] is True

    # --- create_processor_reset 测试 ---

    @pytest.mark.asyncio
    async def test_create_processor_reset_success(self, manager, mock_engine):
        """测试成功创建 Processor Reset。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_processor_reset("proc_sys_reset_0")
        
        assert result["success"] is True

    # --- create_axi_gpio 测试 ---

    @pytest.mark.asyncio
    async def test_create_axi_gpio_success(self, manager, mock_engine):
        """测试成功创建 AXI GPIO。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_axi_gpio("axi_gpio_0", width=16, is_dual=True)
        
        assert result["success"] is True

    # --- create_axi_dma 测试 ---

    @pytest.mark.asyncio
    async def test_create_axi_dma_success(self, manager, mock_engine):
        """测试成功创建 AXI DMA。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.create_axi_dma("axi_dma_0", include_sg=True)
        
        assert result["success"] is True

    # --- auto_connect_axi 测试 ---

    @pytest.mark.asyncio
    async def test_auto_connect_axi_success(self, manager, mock_engine):
        """测试成功自动连接 AXI。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.auto_connect_axi("axi_gpio_0")
        
        assert result["success"] is True

    # --- build_zynq_design 测试 ---

    @pytest.mark.asyncio
    async def test_build_zynq_design_success(self, manager, mock_engine):
        """测试成功构建 Zynq 设计。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.build_zynq_design()
        
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_build_zynq_design_ps_failure(self, manager, mock_engine):
        """测试构建 Zynq 设计时 PS 创建失败。"""
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()
            # 第一个调用失败
            mock_result.success = call_count[0] == 1
            mock_result.errors = [] if call_count[0] > 1 else ["PS creation failed"]
            mock_result.warnings = []
            mock_result.output = ""
            return mock_result
        
        mock_engine.execute_async.side_effect = side_effect
        
        result = await manager.build_zynq_design()
        
        assert result["success"] is False

    # --- export_bd_tcl 测试 ---

    @pytest.mark.asyncio
    async def test_export_bd_tcl_no_design(self, manager):
        """测试没有打开设计时导出。"""
        result = await manager.export_bd_tcl(Path("/path/to/export.tcl"))
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_export_bd_tcl_success(self, manager, mock_engine):
        """测试成功导出 Block Design。"""
        manager.current_design = BlockDesignConfig(name="system")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.export_bd_tcl(Path("/path/to/export.tcl"))
        
        assert result["success"] is True

    # --- import_bd_tcl 测试 ---

    @pytest.mark.asyncio
    async def test_import_bd_tcl_success(self, manager, mock_engine):
        """测试成功导入 Block Design。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.import_bd_tcl(Path("/path/to/import.tcl"))
        
        assert result["success"] is True


# ==================== 边界情况测试 ====================


class TestBlockDesignEdgeCases:
    """Block Design 边界情况测试。"""

    def test_bd_port_width_boundary(self):
        """测试端口宽度边界值。"""
        # 宽度为 1
        port = BDPort(name="single", direction="input", width=1)
        assert port.width == 1
        
        # 宽度为 0 应该失败
        with pytest.raises(ValueError):
            BDPort(name="zero", direction="input", width=0)

    def test_bd_ip_instance_empty_config(self):
        """测试空配置的 IP 实例。"""
        instance = BDIPInstance(
            name="test_ip",
            ip_type="xilinx.com:ip:test:1.0",
            config={},
        )
        
        assert instance.config == {}

    def test_bd_connection_external_ports(self):
        """测试外部端口连接。"""
        conn = BDConnection(
            name=None,
            source="external/clk",
            destination="external/rst",
        )
        
        assert conn.source == "external/clk"
        assert conn.destination == "external/rst"

    def test_block_design_config_empty_lists(self):
        """测试空列表的 Block Design 配置。"""
        config = BlockDesignConfig(
            name="empty",
            ip_instances=[],
            connections=[],
            external_ports=[],
        )
        
        assert config.ip_instances == []
        assert config.connections == []
        assert config.external_ports == []

    def test_bd_port_all_directions(self):
        """测试所有端口方向。"""
        input_port = BDPort(name="in", direction="input")
        output_port = BDPort(name="out", direction="output")
        inout_port = BDPort(name="io", direction="inout")
        
        assert input_port.direction == "input"
        assert output_port.direction == "output"
        assert inout_port.direction == "inout"

    def test_bd_port_all_interface_types(self):
        """测试所有接口类型。"""
        for iface_type in BDInterfaceType:
            port = BDPort(
                name=f"port_{iface_type.value}",
                direction="input",
                interface_type=iface_type,
            )
            assert port.interface_type == iface_type

    def test_bd_connection_with_long_names(self):
        """测试长名称连接。"""
        long_name = "a" * 100
        conn = BDConnection(
            name=long_name,
            source=f"instance_{long_name}/port",
            destination=f"instance2_{long_name}/port",
        )
        
        assert conn.name == long_name

    def test_zynq_ps_config_all_peripherals(self):
        """测试所有外设启用的 Zynq PS 配置。"""
        config = ZynqPSConfig(
            enable_fabric_reset=True,
            enable_fabric_clock=True,
            enable_ddr=True,
            enable_enet0=True,
            enable_enet1=True,
            enable_usb0=True,
            enable_usb1=True,
            enable_sd0=True,
            enable_sd1=True,
            enable_uart0=True,
            enable_uart1=True,
            enable_i2c0=True,
            enable_i2c1=True,
            enable_spi0=True,
            enable_spi1=True,
            enable_can0=True,
            enable_can1=True,
            enable_ttc0=True,
            enable_ttc1=True,
            enable_gpio=True,
        )
        
        assert config.enable_enet0 is True
        assert config.enable_usb0 is True
        assert config.enable_sd0 is True

    def test_set_bd_property_tcl_empty_properties(self):
        """测试空属性字典设置。"""
        tcl = BlockDesignTclGenerator.set_bd_property_tcl("cell_0", {})
        
        # 应该生成有效的 Tcl，即使属性为空
        assert "set_property" in tcl

    def test_create_bd_port_tcl_single_bit(self):
        """测试单比特端口 Tcl 生成。"""
        port = BDPort(name="single_bit", direction="output", width=1)
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        # 单比特端口不应该有 -from/-to
        assert "-from" not in tcl

    def test_create_bd_port_tcl_multi_bit(self):
        """测试多比特端口 Tcl 生成。"""
        port = BDPort(name="multi_bit", direction="output", width=32)
        tcl = BlockDesignTclGenerator.create_bd_port_tcl(port)
        
        # 多比特端口应该有 -from/-to
        assert "-from 31 -to 0" in tcl
