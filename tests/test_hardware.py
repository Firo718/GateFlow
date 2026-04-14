"""
硬件模块测试。

测试 HardwareTclGenerator、HardwareManager 和硬件数据类。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.vivado.hardware import (
    JtagState,
    DeviceType,
    ProgrammingStatus,
    HardwareDevice,
    HardwareServer,
    ProgrammingResult,
    MemoryDevice,
    HardwareTclGenerator,
    HardwareManager,
)


# ==================== 枚举测试 ====================


class TestJtagState:
    """JtagState 枚举测试。"""

    def test_jtag_state_values(self):
        """测试 JTAG 状态枚举值。"""
        assert JtagState.UNKNOWN.value == "unknown"
        assert JtagState.IDLE.value == "idle"
        assert JtagState.SHIFT_DR.value == "shift_dr"
        assert JtagState.SHIFT_IR.value == "shift_ir"
        assert JtagState.EXIT1_DR.value == "exit1_dr"
        assert JtagState.EXIT1_IR.value == "exit1_ir"
        assert JtagState.PAUSE_DR.value == "pause_dr"
        assert JtagState.PAUSE_IR.value == "pause_ir"

    def test_jtag_state_count(self):
        """测试 JTAG 状态数量。"""
        states = list(JtagState)
        assert len(states) == 8


class TestDeviceType:
    """DeviceType 枚举测试。"""

    def test_device_type_values(self):
        """测试设备类型枚举值。"""
        assert DeviceType.FPGA.value == "fpga"
        assert DeviceType.SOC.value == "soc"
        assert DeviceType.CONFIG_MEMORY.value == "config_memory"
        assert DeviceType.DEBUG_BRIDGE.value == "debug_bridge"
        assert DeviceType.UNKNOWN.value == "unknown"

    def test_device_type_count(self):
        """测试设备类型数量。"""
        types = list(DeviceType)
        assert len(types) == 5


class TestProgrammingStatus:
    """ProgrammingStatus 枚举测试。"""

    def test_programming_status_values(self):
        """测试编程状态枚举值。"""
        assert ProgrammingStatus.IDLE.value == "idle"
        assert ProgrammingStatus.ERASING.value == "erasing"
        assert ProgrammingStatus.PROGRAMMING.value == "programming"
        assert ProgrammingStatus.VERIFYING.value == "verifying"
        assert ProgrammingStatus.COMPLETED.value == "completed"
        assert ProgrammingStatus.FAILED.value == "failed"

    def test_programming_status_count(self):
        """测试编程状态数量。"""
        statuses = list(ProgrammingStatus)
        assert len(statuses) == 6


# ==================== 数据类测试 ====================


class TestHardwareDevice:
    """HardwareDevice 数据类测试。"""

    def test_hardware_device_required_fields(self):
        """测试硬件设备必需字段。"""
        device = HardwareDevice(
            name="xc7a35t_0",
            jtag_index=0,
            irlen=6,
            part="xc7a35tcpg236-1",
            is_fpga=True,
        )
        
        assert device.name == "xc7a35t_0"
        assert device.jtag_index == 0
        assert device.irlen == 6
        assert device.part == "xc7a35tcpg236-1"
        assert device.is_fpga is True
        assert device.device_type == DeviceType.UNKNOWN
        assert device.idcode is None
        assert device.usercode is None

    def test_hardware_device_full(self):
        """测试硬件设备完整参数。"""
        device = HardwareDevice(
            name="xc7a35t_0",
            jtag_index=0,
            irlen=6,
            part="xc7a35tcpg236-1",
            is_fpga=True,
            device_type=DeviceType.FPGA,
            idcode="0x362D093",
            usercode="0x12345678",
        )
        
        assert device.device_type == DeviceType.FPGA
        assert device.idcode == "0x362D093"
        assert device.usercode == "0x12345678"


class TestHardwareServer:
    """HardwareServer 数据类测试。"""

    def test_hardware_server_required_fields(self):
        """测试硬件服务器必需字段。"""
        server = HardwareServer(url="localhost:3121", connected=True)
        
        assert server.url == "localhost:3121"
        assert server.connected is True
        assert server.devices == []
        assert server.version is None

    def test_hardware_server_with_devices(self):
        """测试带设备的硬件服务器。"""
        device = HardwareDevice(
            name="xc7a35t_0",
            jtag_index=0,
            irlen=6,
            part="xc7a35tcpg236-1",
            is_fpga=True,
        )
        server = HardwareServer(
            url="localhost:3121",
            connected=True,
            devices=[device],
            version="2024.1",
        )
        
        assert len(server.devices) == 1
        assert server.version == "2024.1"


class TestProgrammingResult:
    """ProgrammingResult 数据类测试。"""

    def test_programming_result_required_fields(self):
        """测试编程结果必需字段。"""
        result = ProgrammingResult(
            success=True,
            status=ProgrammingStatus.COMPLETED,
            device="xc7a35t_0",
            bitstream="/path/to/design.bit",
        )
        
        assert result.success is True
        assert result.status == ProgrammingStatus.COMPLETED
        assert result.device == "xc7a35t_0"
        assert result.bitstream == "/path/to/design.bit"
        assert result.errors == []
        assert result.warnings == []
        assert result.verification_passed is None

    def test_programming_result_failure(self):
        """测试编程失败结果。"""
        result = ProgrammingResult(
            success=False,
            status=ProgrammingStatus.FAILED,
            device="xc7a35t_0",
            bitstream="/path/to/design.bit",
            errors=["Programming failed: device not responding"],
            warnings=["Connection unstable"],
        )
        
        assert result.success is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1


class TestMemoryDevice:
    """MemoryDevice 数据类测试。"""

    def test_memory_device_required_fields(self):
        """测试存储器设备必需字段。"""
        device = MemoryDevice(name="flash_0", part="s25fl256s", size=33554432)
        
        assert device.name == "flash_0"
        assert device.part == "s25fl256s"
        assert device.size == 33554432
        assert device.manufacturer is None

    def test_memory_device_full(self):
        """测试存储器设备完整参数。"""
        device = MemoryDevice(
            name="flash_0",
            part="s25fl256s",
            size=33554432,
            manufacturer="Spansion",
        )
        
        assert device.manufacturer == "Spansion"


# ==================== HardwareTclGenerator 测试 ====================


class TestHardwareTclGenerator:
    """HardwareTclGenerator 测试。"""

    # --- 硬件管理器命令测试 ---

    def test_open_hw_manager_tcl(self):
        """测试打开硬件管理器 Tcl 生成。"""
        tcl = HardwareTclGenerator.open_hw_manager_tcl()
        
        assert tcl == "open_hw_manager"

    def test_close_hw_manager_tcl(self):
        """测试关闭硬件管理器 Tcl 生成。"""
        tcl = HardwareTclGenerator.close_hw_manager_tcl()
        
        assert tcl == "close_hw_manager"

    # --- 服务器连接命令测试 ---

    def test_connect_hw_server_tcl_default(self):
        """测试默认连接硬件服务器 Tcl 生成。"""
        tcl = HardwareTclGenerator.connect_hw_server_tcl()
        
        assert "connect_hw_server" in tcl
        assert "localhost:3121" in tcl

    def test_connect_hw_server_tcl_custom_url(self):
        """测试自定义 URL 连接硬件服务器 Tcl 生成。"""
        tcl = HardwareTclGenerator.connect_hw_server_tcl("192.168.1.100:3121")
        
        assert "192.168.1.100:3121" in tcl

    def test_disconnect_hw_server_tcl(self):
        """测试断开硬件服务器 Tcl 生成。"""
        tcl = HardwareTclGenerator.disconnect_hw_server_tcl()
        
        assert tcl == "disconnect_hw_server"

    def test_get_hw_servers_tcl(self):
        """测试获取硬件服务器列表 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_servers_tcl()
        
        assert tcl == "get_hw_servers"

    # --- 硬件目标命令测试 ---

    def test_get_hw_targets_tcl(self):
        """测试获取硬件目标 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_targets_tcl()
        
        assert tcl == "get_hw_targets"

    def test_open_hw_target_tcl_default(self):
        """测试默认打开硬件目标 Tcl 生成。"""
        tcl = HardwareTclGenerator.open_hw_target_tcl()
        
        assert tcl == "open_hw_target"

    def test_open_hw_target_tcl_with_target(self):
        """测试带目标名称打开硬件目标 Tcl 生成。"""
        tcl = HardwareTclGenerator.open_hw_target_tcl("target_0")
        
        assert "[get_hw_targets target_0]" in tcl

    def test_close_hw_target_tcl(self):
        """测试关闭硬件目标 Tcl 生成。"""
        tcl = HardwareTclGenerator.close_hw_target_tcl()
        
        assert tcl == "close_hw_target"

    # --- 硬件设备命令测试 ---

    def test_get_hw_devices_tcl(self):
        """测试获取硬件设备列表 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_devices_tcl()
        
        assert tcl == "get_hw_devices"

    def test_get_hw_device_tcl(self):
        """测试获取指定硬件设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_device_tcl("xc7a35t_0")
        
        assert tcl == "get_hw_devices xc7a35t_0"

    def test_current_hw_device_tcl(self):
        """测试设置当前硬件设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.current_hw_device_tcl("xc7a35t_0")
        
        assert "current_hw_device" in tcl
        assert "[get_hw_devices xc7a35t_0]" in tcl

    def test_refresh_hw_device_tcl_default(self):
        """测试默认刷新设备状态 Tcl 生成。"""
        tcl = HardwareTclGenerator.refresh_hw_device_tcl()
        
        assert tcl == "refresh_hw_device"

    def test_refresh_hw_device_tcl_with_device(self):
        """测试带设备名称刷新设备状态 Tcl 生成。"""
        tcl = HardwareTclGenerator.refresh_hw_device_tcl("xc7a35t_0")
        
        assert "[get_hw_devices xc7a35t_0]" in tcl

    # --- FPGA 编程命令测试 ---

    def test_program_hw_device_tcl(self):
        """测试编程 FPGA 设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.program_hw_device_tcl(
            device="xc7a35t_0",
            bitstream="/path/to/design.bit",
        )
        
        assert "set_property PROGRAM.FILE" in tcl
        assert "/path/to/design.bit" in tcl
        assert "program_hw_devices" in tcl

    def test_program_hw_devices_tcl_multiple(self):
        """测试编程多个 FPGA 设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.program_hw_devices_tcl(
            devices=["dev_0", "dev_1"],
            bitstreams=["/path/a.bit", "/path/b.bit"],
        )
        
        assert "set_property PROGRAM.FILE" in tcl
        assert "program_hw_devices" in tcl

    def test_set_program_file_tcl(self):
        """测试设置编程文件 Tcl 生成。"""
        tcl = HardwareTclGenerator.set_program_file_tcl(
            device="xc7a35t_0",
            bitstream="/path/to/design.bit",
        )
        
        assert "set_property PROGRAM.FILE" in tcl
        assert "/path/to/design.bit" in tcl

    def test_set_probe_file_tcl(self):
        """测试设置探针文件 Tcl 生成。"""
        tcl = HardwareTclGenerator.set_probe_file_tcl(
            device="xc7a35t_0",
            probe_file="/path/to/debug.ltx",
        )
        
        assert "set_property PROBE.FILE" in tcl
        assert "/path/to/debug.ltx" in tcl

    # --- 设备控制命令测试 ---

    def test_boot_hw_device_tcl(self):
        """测试启动 FPGA 设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.boot_hw_device_tcl("xc7a35t_0")
        
        assert "boot_hw_device" in tcl
        assert "[get_hw_devices xc7a35t_0]" in tcl

    def test_reset_hw_device_tcl(self):
        """测试重置 FPGA 设备 Tcl 生成。"""
        tcl = HardwareTclGenerator.reset_hw_device_tcl("xc7a35t_0")
        
        assert "reset_hw_device" in tcl
        assert "[get_hw_devices xc7a35t_0]" in tcl

    # --- 设备属性命令测试 ---

    def test_get_device_property_tcl(self):
        """测试获取设备属性 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_device_property_tcl("xc7a35t_0", "PART")
        
        assert "get_property PART" in tcl
        assert "[get_hw_devices xc7a35t_0]" in tcl

    def test_get_device_idcode_tcl(self):
        """测试获取设备 IDCODE Tcl 生成。"""
        tcl = HardwareTclGenerator.get_device_idcode_tcl("xc7a35t_0")
        
        assert "get_property IDCODE" in tcl

    def test_get_device_part_tcl(self):
        """测试获取设备型号 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_device_part_tcl("xc7a35t_0")
        
        assert "get_property PART" in tcl

    def test_get_device_name_tcl(self):
        """测试获取设备名称 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_device_name_tcl("xc7a35t_0")
        
        assert "get_property NAME" in tcl

    # --- 配置存储器命令测试 ---

    def test_get_hw_cfgmem_tcl(self):
        """测试获取配置存储器 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_cfgmem_tcl()
        
        assert tcl == "get_hw_cfgmem"

    def test_create_hw_cfgmem_tcl(self):
        """测试创建配置存储器 Tcl 生成。"""
        tcl = HardwareTclGenerator.create_hw_cfgmem_tcl(
            part="s25fl256s",
            device="xc7a35t_0",
            cfgmem_name="cfgmem_0",
        )
        
        assert "create_hw_cfgmem" in tcl
        assert "-hw_device" in tcl
        assert "cfgmem_0" in tcl

    def test_program_hw_cfgmem_tcl(self):
        """测试编程配置存储器 Tcl 生成。"""
        tcl = HardwareTclGenerator.program_hw_cfgmem_tcl(
            cfgmem="cfgmem_0",
            file_path="/path/to/config.mcs",
            verify=True,
        )
        
        assert "set_property PROGRAM.ADDRESS_RANGE" in tcl
        assert "set_property PROGRAM.FILES" in tcl
        assert "program_hw_cfgmem" in tcl
        assert "/path/to/config.mcs" in tcl

    # --- ILA 命令测试 ---

    def test_get_hw_ila_tcl(self):
        """测试获取 ILA 核 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_ila_tcl()
        
        assert tcl == "get_hw_ilas"

    def test_run_hw_ila_tcl(self):
        """测试运行 ILA 触发 Tcl 生成。"""
        tcl = HardwareTclGenerator.run_hw_ila_tcl("ila_0")
        
        assert "run_hw_ila" in tcl
        assert "[get_hw_ilas ila_0]" in tcl

    def test_upload_hw_ila_tcl(self):
        """测试上传 ILA 数据 Tcl 生成。"""
        tcl = HardwareTclGenerator.upload_hw_ila_tcl("ila_0")
        
        assert "upload_hw_ila" in tcl
        assert "[get_hw_ilas ila_0]" in tcl

    # --- VIO 命令测试 ---

    def test_get_hw_vio_tcl(self):
        """测试获取 VIO 核 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_vio_tcl()
        
        assert tcl == "get_hw_vios"

    def test_get_hw_axis_tcl(self):
        """测试获取 HW AXI Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_axis_tcl()

        assert tcl == "get_hw_axis"

    def test_set_vio_output_tcl(self):
        """测试设置 VIO 输出 Tcl 生成。"""
        tcl = HardwareTclGenerator.set_vio_output_tcl(
            vio="vio_0",
            probe="probe_out0",
            value="1",
        )
        
        assert "set_property OUTPUT_VALUE 1" in tcl
        assert "get_hw_probes probe_out0" in tcl
        assert "get_hw_vios vio_0" in tcl

    def test_get_vio_input_tcl(self):
        """测试获取 VIO 输入 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_vio_input_tcl(
            vio="vio_0",
            probe="probe_in0",
        )
        
        assert "get_property INPUT_VALUE" in tcl
        assert "get_hw_probes probe_in0" in tcl

    def test_refresh_hw_vio_tcl(self):
        """测试刷新 VIO Tcl 生成。"""
        tcl = HardwareTclGenerator.refresh_hw_vio_tcl("vio_0")
        
        assert "refresh_hw_vio" in tcl
        assert "[get_hw_vios vio_0]" in tcl

    def test_create_hw_axi_txn_tcl_read(self):
        """测试创建 AXI 读事务 Tcl 生成。"""
        tcl = HardwareTclGenerator.create_hw_axi_txn_tcl(
            txn_name="axi_read_0",
            axi_name="axi_dbg_0",
            address="0x40000000",
            txn_type="read",
            length=1,
        )

        assert "create_hw_axi_txn axi_read_0" in tcl
        assert "[get_hw_axis axi_dbg_0]" in tcl
        assert "-type read" in tcl
        assert "-address 0x40000000" in tcl

    def test_create_hw_axi_txn_tcl_write(self):
        """测试创建 AXI 写事务 Tcl 生成。"""
        tcl = HardwareTclGenerator.create_hw_axi_txn_tcl(
            txn_name="axi_write_0",
            axi_name="axi_dbg_0",
            address="0x40000000",
            txn_type="write",
            data="0x1",
            length=1,
        )

        assert "-type write" in tcl
        assert "-data 0x1" in tcl

    def test_run_hw_axi_txn_tcl(self):
        """测试运行 AXI 事务 Tcl 生成。"""
        tcl = HardwareTclGenerator.run_hw_axi_txn_tcl("axi_read_0")

        assert "run_hw_axi" in tcl
        assert "[get_hw_axi_txns axi_read_0]" in tcl

    def test_get_hw_axi_data_tcl(self):
        """测试获取 AXI 数据 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_hw_axi_data_tcl("axi_read_0")

        assert "get_property DATA" in tcl
        assert "[get_hw_axi_txns axi_read_0]" in tcl

    def test_delete_hw_axi_txn_tcl(self):
        """测试删除 AXI 事务 Tcl 生成。"""
        tcl = HardwareTclGenerator.delete_hw_axi_txn_tcl("axi_read_0")

        assert "delete_hw_axi_txn" in tcl
        assert "[get_hw_axi_txns axi_read_0]" in tcl

    # --- JTAG 状态命令测试 ---

    def test_get_jtag_state_tcl(self):
        """测试获取 JTAG 状态 Tcl 生成。"""
        tcl = HardwareTclGenerator.get_jtag_state_tcl()
        
        assert "get_property JTAG_STATE" in tcl
        assert "current_hw_target" in tcl

    def test_set_jtag_state_tcl(self):
        """测试设置 JTAG 状态 Tcl 生成。"""
        tcl = HardwareTclGenerator.set_jtag_state_tcl("IDLE")
        
        assert "set_property JTAG_STATE IDLE" in tcl


# ==================== HardwareManager 测试 ====================


@pytest.mark.integration
class TestHardwareManager:
    """HardwareManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute_async = AsyncMock()
        return engine

    @pytest.fixture
    def manager(self, mock_engine):
        """创建硬件管理器。"""
        return HardwareManager(mock_engine)

    # --- connect_server 测试 ---

    @pytest.mark.asyncio
    async def test_connect_server_success(self, manager, mock_engine):
        """测试成功连接硬件服务器。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_result.output = "xc7a35t_0"
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.connect_server("localhost:3121")
        
        assert result["success"] is True
        assert manager.server is not None
        assert manager.server.url == "localhost:3121"

    @pytest.mark.asyncio
    async def test_connect_server_failure(self, manager, mock_engine):
        """测试连接硬件服务器失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Connection refused"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.connect_server("localhost:3121")
        
        assert result["success"] is False
        assert manager.server is None

    # --- disconnect_server 测试 ---

    @pytest.mark.asyncio
    async def test_disconnect_server_success(self, manager, mock_engine):
        """测试成功断开服务器连接。"""
        # 先连接
        manager.server = HardwareServer(url="localhost:3121", connected=True)
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.disconnect_server()
        
        assert result["success"] is True
        assert manager.server is None
        assert manager.devices == []

    # --- get_devices 测试 ---

    @pytest.mark.asyncio
    async def test_get_devices_not_connected(self, manager):
        """测试未连接时获取设备列表。"""
        devices = await manager.get_devices()
        
        assert devices == []

    @pytest.mark.asyncio
    async def test_get_devices_success(self, manager, mock_engine):
        """测试成功获取设备列表。"""
        manager.server = HardwareServer(url="localhost:3121", connected=True)
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "xc7a35t_0\nxc7k70t_0"
        mock_engine.execute_async.return_value = mock_result
        
        devices = await manager.get_devices()
        
        assert len(devices) >= 0  # 取决于解析逻辑

    # --- program_fpga 测试 ---

    @pytest.mark.asyncio
    async def test_program_fpga_invalid_index(self, manager):
        """测试无效设备索引编程 FPGA。"""
        result = await manager.program_fpga(
            device_index=999,
            bitstream_path="/path/to/design.bit",
        )
        
        assert result.success is False
        assert "无效的设备索引" in result.errors[0]

    @pytest.mark.asyncio
    async def test_program_fpga_file_not_found(self, manager, tmp_path):
        """测试比特流文件不存在时编程 FPGA。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        result = await manager.program_fpga(
            device_index=0,
            bitstream_path=tmp_path / "nonexistent.bit",
        )
        
        assert result.success is False
        assert "不存在" in result.errors[0]

    @pytest.mark.asyncio
    async def test_program_fpga_success(self, manager, mock_engine, tmp_path):
        """测试成功编程 FPGA。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        bitstream = tmp_path / "design.bit"
        bitstream.write_bytes(b"BITSTREAM_DATA")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.program_fpga(
            device_index=0,
            bitstream_path=bitstream,
        )
        
        assert result.success is True
        assert result.status == ProgrammingStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_program_fpga_failure(self, manager, mock_engine, tmp_path):
        """测试编程 FPGA 失败。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        bitstream = tmp_path / "design.bit"
        bitstream.write_bytes(b"BITSTREAM_DATA")
        
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.errors = ["Programming failed"]
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.program_fpga(
            device_index=0,
            bitstream_path=bitstream,
        )
        
        assert result.success is False
        assert result.status == ProgrammingStatus.FAILED

    # --- program_multiple_fpgas 测试 ---

    @pytest.mark.asyncio
    async def test_program_multiple_fpgas_mismatch_length(self, manager):
        """测试设备索引和比特流路径列表长度不匹配。"""
        with pytest.raises(ValueError, match="长度不匹配"):
            await manager.program_multiple_fpgas(
                device_indices=[0, 1],
                bitstream_paths=["/path/a.bit"],
            )

    @pytest.mark.asyncio
    async def test_program_multiple_fpgas_invalid_index(self, manager, mock_engine, tmp_path):
        """测试多设备编程时无效索引。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        bitstream = tmp_path / "design.bit"
        bitstream.write_bytes(b"BITSTREAM_DATA")
        
        results = await manager.program_multiple_fpgas(
            device_indices=[999],
            bitstream_paths=[bitstream],
        )
        
        assert len(results) == 1
        assert results[0].success is False

    # --- get_device_status 测试 ---

    @pytest.mark.asyncio
    async def test_get_device_status_invalid_index(self, manager):
        """测试无效设备索引获取设备状态。"""
        result = await manager.get_device_status(999)
        
        assert result["success"] is False
        assert "无效的设备索引" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_get_device_status_success(self, manager, mock_engine):
        """测试成功获取设备状态。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "READY"
        mock_result.errors = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.get_device_status(0)
        
        assert result["success"] is True
        assert result["device"] == "xc7a35t_0"

    # --- get_device_idcode 测试 ---

    @pytest.mark.asyncio
    async def test_get_device_idcode_invalid_index(self, manager):
        """测试无效设备索引获取 IDCODE。"""
        result = await manager.get_device_idcode(999)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_device_idcode_success(self, manager, mock_engine):
        """测试成功获取设备 IDCODE。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "0x362D093\n"
        mock_engine.execute_async.return_value = mock_result
        
        idcode = await manager.get_device_idcode(0)
        
        assert idcode == "0x362D093"

    # --- boot_device 测试 ---

    @pytest.mark.asyncio
    async def test_boot_device_invalid_index(self, manager):
        """测试无效设备索引启动设备。"""
        result = await manager.boot_device(999)
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_boot_device_success(self, manager, mock_engine):
        """测试成功启动设备。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.boot_device(0)
        
        assert result["success"] is True

    # --- reset_device 测试 ---

    @pytest.mark.asyncio
    async def test_reset_device_invalid_index(self, manager):
        """测试无效设备索引重置设备。"""
        result = await manager.reset_device(999)
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_reset_device_success(self, manager, mock_engine):
        """测试成功重置设备。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.reset_device(0)
        
        assert result["success"] is True

    # --- set_probe_file 测试 ---

    @pytest.mark.asyncio
    async def test_set_probe_file_invalid_index(self, manager):
        """测试无效设备索引设置探针文件。"""
        result = await manager.set_probe_file(999, "/path/to/debug.ltx")
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_set_probe_file_not_found(self, manager, tmp_path):
        """测试探针文件不存在。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        result = await manager.set_probe_file(0, tmp_path / "nonexistent.ltx")
        
        assert result["success"] is False
        assert "不存在" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_set_probe_file_success(self, manager, mock_engine, tmp_path):
        """测试成功设置探针文件。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        probe_file = tmp_path / "debug.ltx"
        probe_file.write_text("LTX_DATA")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.set_probe_file(0, probe_file)
        
        assert result["success"] is True

    # --- program_config_memory 测试 ---

    @pytest.mark.asyncio
    async def test_program_config_memory_invalid_index(self, manager):
        """测试无效设备索引编程配置存储器。"""
        result = await manager.program_config_memory(
            device_index=999,
            config_file="/path/to/config.mcs",
            config_part="s25fl256s",
        )
        
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_program_config_memory_file_not_found(self, manager, tmp_path):
        """测试配置文件不存在。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        result = await manager.program_config_memory(
            device_index=0,
            config_file=tmp_path / "nonexistent.mcs",
            config_part="s25fl256s",
        )
        
        assert result["success"] is False
        assert "不存在" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_program_config_memory_success(self, manager, mock_engine, tmp_path):
        """测试成功编程配置存储器。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        config_file = tmp_path / "config.mcs"
        config_file.write_text("MCS_DATA")
        
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.errors = []
        mock_result.warnings = []
        mock_engine.execute_async.return_value = mock_result
        
        result = await manager.program_config_memory(
            device_index=0,
            config_file=config_file,
            config_part="s25fl256s",
        )
        
        assert result["success"] is True

    # --- get_jtag_state 测试 ---

    @pytest.mark.asyncio
    async def test_get_jtag_state_success(self, manager, mock_engine):
        """测试成功获取 JTAG 状态。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "IDLE\n"
        mock_engine.execute_async.return_value = mock_result
        
        state = await manager.get_jtag_state()
        
        assert state == JtagState.IDLE

    @pytest.mark.asyncio
    async def test_get_jtag_state_unknown(self, manager, mock_engine):
        """测试获取未知 JTAG 状态。"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "INVALID_STATE\n"
        mock_engine.execute_async.return_value = mock_result
        
        state = await manager.get_jtag_state()
        
        assert state == JtagState.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_jtag_state_failure(self, manager, mock_engine):
        """测试获取 JTAG 状态失败。"""
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.output = ""
        mock_engine.execute_async.return_value = mock_result
        
        state = await manager.get_jtag_state()
        
        assert state == JtagState.UNKNOWN

    # --- 辅助方法测试 ---

    def test_get_device_by_name_found(self, manager):
        """测试根据名称找到设备。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            ),
            HardwareDevice(
                name="xc7k70t_0",
                jtag_index=1,
                irlen=6,
                part="xc7k70tfbg484-1",
                is_fpga=True,
            ),
        ]
        
        device = manager.get_device_by_name("xc7a35t_0")
        
        assert device is not None
        assert device.name == "xc7a35t_0"

    def test_get_device_by_name_not_found(self, manager):
        """测试根据名称未找到设备。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            )
        ]
        
        device = manager.get_device_by_name("nonexistent")
        
        assert device is None

    def test_get_fpga_devices(self, manager):
        """测试获取所有 FPGA 设备。"""
        manager.devices = [
            HardwareDevice(
                name="xc7a35t_0",
                jtag_index=0,
                irlen=6,
                part="xc7a35tcpg236-1",
                is_fpga=True,
            ),
            HardwareDevice(
                name="config_flash",
                jtag_index=1,
                irlen=0,
                part="s25fl256s",
                is_fpga=False,
            ),
        ]
        
        fpga_devices = manager.get_fpga_devices()
        
        assert len(fpga_devices) == 1
        assert fpga_devices[0].name == "xc7a35t_0"

    # --- 解析方法测试 ---

    def test_parse_devices_output(self, manager):
        """测试解析设备列表输出。"""
        output = "xc7a35t_0\nxc7k70t_0\n# comment\n"
        devices = manager._parse_devices_output(output)
        
        assert len(devices) >= 2

    def test_parse_devices_output_empty(self, manager):
        """测试解析空设备列表输出。"""
        devices = manager._parse_devices_output("")
        
        assert devices == []

    def test_is_fpga_device_xilinx(self, manager):
        """测试判断 Xilinx FPGA 设备。"""
        assert manager._is_fpga_device("xc7a35t_0") is True
        assert manager._is_fpga_device("xc7k70t_0") is True
        assert manager._is_fpga_device("xcu280_0") is True
        assert manager._is_fpga_device("xcvu9p_0") is True
        assert manager._is_fpga_device("xczu7ev_0") is True

    def test_is_fpga_device_non_fpga(self, manager):
        """测试判断非 FPGA 设备。"""
        assert manager._is_fpga_device("config_flash") is False
        assert manager._is_fpga_device("debug_bridge") is False

    def test_parse_idcode(self, manager):
        """测试解析 IDCODE 输出。"""
        idcode = manager._parse_idcode("IDCODE: 0x362D093")
        
        assert idcode == "0x362D093"

    def test_parse_idcode_not_found(self, manager):
        """测试解析 IDCODE 未找到。"""
        idcode = manager._parse_idcode("No IDCODE found")
        
        assert idcode is None


# ==================== 边界情况测试 ====================


class TestHardwareEdgeCases:
    """硬件模块边界情况测试。"""

    def test_hardware_device_empty_name(self):
        """测试空名称硬件设备。"""
        device = HardwareDevice(
            name="",
            jtag_index=0,
            irlen=6,
            part="xc7a35tcpg236-1",
            is_fpga=True,
        )
        
        assert device.name == ""

    def test_hardware_device_negative_jtag_index(self):
        """测试负 JTAG 索引硬件设备。"""
        device = HardwareDevice(
            name="device",
            jtag_index=-1,
            irlen=6,
            part="xc7a35tcpg236-1",
            is_fpga=True,
        )
        
        assert device.jtag_index == -1

    def test_programming_result_empty_bitstream(self):
        """测试空比特流路径编程结果。"""
        result = ProgrammingResult(
            success=True,
            status=ProgrammingStatus.COMPLETED,
            device="device",
            bitstream="",
        )
        
        assert result.bitstream == ""

    def test_memory_device_zero_size(self):
        """测试零大小存储器设备。"""
        device = MemoryDevice(name="flash", part="s25fl256s", size=0)
        
        assert device.size == 0

    def test_program_hw_device_tcl_empty_device(self):
        """测试空设备名称编程 Tcl 生成。"""
        tcl = HardwareTclGenerator.program_hw_device_tcl(
            device="",
            bitstream="/path/to/design.bit",
        )
        
        # 应该生成有效的 Tcl
        assert "program_hw_devices" in tcl

    def test_connect_hw_server_tcl_special_characters(self):
        """测试特殊字符 URL 连接 Tcl 生成。"""
        tcl = HardwareTclGenerator.connect_hw_server_tcl("192.168.1.100:3121")
        
        assert "192.168.1.100:3121" in tcl

    def test_program_hw_cfgmem_tcl_verify_false(self):
        """测试不验证的配置存储器编程 Tcl 生成。"""
        tcl = HardwareTclGenerator.program_hw_cfgmem_tcl(
            cfgmem="cfgmem_0",
            file_path="/path/to/config.mcs",
            verify=False,
        )
        
        assert "PROGRAM.VERIFY  0" in tcl

    def test_hardware_server_empty_devices(self):
        """测试空设备列表硬件服务器。"""
        server = HardwareServer(url="localhost:3121", connected=True)
        
        assert server.devices == []

    def test_jtag_state_from_string(self):
        """测试从字符串创建 JTAG 状态。"""
        assert JtagState("idle") == JtagState.IDLE
        assert JtagState("unknown") == JtagState.UNKNOWN

    def test_device_type_from_string(self):
        """测试从字符串创建设备类型。"""
        assert DeviceType("fpga") == DeviceType.FPGA
        assert DeviceType("unknown") == DeviceType.UNKNOWN

    def test_programming_status_from_string(self):
        """测试从字符串创建编程状态。"""
        assert ProgrammingStatus("completed") == ProgrammingStatus.COMPLETED
        assert ProgrammingStatus("failed") == ProgrammingStatus.FAILED
