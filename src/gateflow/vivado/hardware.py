"""
Vivado 硬件编程模块

该模块提供硬件服务器连接、设备检测、FPGA 编程等功能。
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from gateflow.vivado.result_utils import format_result, path_artifact


class JtagState(Enum):
    """JTAG 状态枚举"""
    UNKNOWN = "unknown"
    IDLE = "idle"
    SHIFT_DR = "shift_dr"
    SHIFT_IR = "shift_ir"
    EXIT1_DR = "exit1_dr"
    EXIT1_IR = "exit1_ir"
    PAUSE_DR = "pause_dr"
    PAUSE_IR = "pause_ir"


class DeviceType(Enum):
    """设备类型枚举"""
    FPGA = "fpga"
    SOC = "soc"
    CONFIG_MEMORY = "config_memory"
    DEBUG_BRIDGE = "debug_bridge"
    UNKNOWN = "unknown"


class ProgrammingStatus(Enum):
    """编程状态枚举"""
    IDLE = "idle"
    ERASING = "erasing"
    PROGRAMMING = "programming"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HardwareDevice:
    """硬件设备信息"""
    name: str  # 设备名称
    jtag_index: int  # JTAG 链索引
    irlen: int  # 指令寄存器长度
    part: str  # 器件型号
    is_fpga: bool  # 是否为 FPGA
    device_type: DeviceType = DeviceType.UNKNOWN  # 设备类型
    idcode: str | None = None  # 设备 IDCODE
    usercode: str | None = None  # 用户代码


@dataclass
class HardwareServer:
    """硬件服务器信息"""
    url: str  # 服务器 URL
    connected: bool  # 是否已连接
    devices: list[HardwareDevice] = field(default_factory=list)  # 设备列表
    version: str | None = None  # 服务器版本


@dataclass
class ProgrammingResult:
    """编程结果"""
    success: bool  # 是否成功
    status: ProgrammingStatus  # 编程状态
    device: str  # 设备名称
    bitstream: str  # 比特流路径
    errors: list[str] = field(default_factory=list)  # 错误列表
    warnings: list[str] = field(default_factory=list)  # 警告列表
    verification_passed: bool | None = None  # 验证是否通过


@dataclass
class MemoryDevice:
    """存储器设备信息"""
    name: str  # 设备名称
    part: str  # 器件型号
    size: int  # 大小（字节）
    manufacturer: str | None = None  # 制造商


class HardwareTclGenerator:
    """
    硬件 Tcl 命令生成器
    
    生成用于硬件服务器连接、设备检测、FPGA 编程等操作的 Tcl 命令。
    """
    
    @staticmethod
    def open_hw_manager_tcl() -> str:
        """
        打开硬件管理器的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'open_hw_manager'
    
    @staticmethod
    def close_hw_manager_tcl() -> str:
        """
        关闭硬件管理器的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_hw_manager'
    
    @staticmethod
    def connect_hw_server_tcl(url: str = "localhost:3121") -> str:
        """
        连接硬件服务器的 Tcl 命令
        
        Args:
            url: 服务器 URL（格式：host:port）
            
        Returns:
            Tcl 命令字符串
        """
        return f'connect_hw_server -url {url}'
    
    @staticmethod
    def disconnect_hw_server_tcl() -> str:
        """
        断开硬件服务器的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'disconnect_hw_server'
    
    @staticmethod
    def get_hw_servers_tcl() -> str:
        """
        获取硬件服务器列表的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_servers'
    
    @staticmethod
    def get_hw_targets_tcl() -> str:
        """
        获取硬件目标的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_targets'
    
    @staticmethod
    def open_hw_target_tcl(target: str | None = None) -> str:
        """
        打开硬件目标的 Tcl 命令
        
        Args:
            target: 目标名称（可选）
            
        Returns:
            Tcl 命令字符串
        """
        if target:
            return f'open_hw_target [get_hw_targets {target}]'
        return 'open_hw_target'
    
    @staticmethod
    def close_hw_target_tcl() -> str:
        """
        关闭硬件目标的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'close_hw_target'
    
    @staticmethod
    def get_hw_devices_tcl() -> str:
        """
        获取硬件设备列表的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_devices'
    
    @staticmethod
    def get_hw_device_tcl(device: str) -> str:
        """
        获取指定硬件设备的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_hw_devices {device}'
    
    @staticmethod
    def current_hw_device_tcl(device: str) -> str:
        """
        设置当前硬件设备的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'current_hw_device [get_hw_devices {device}]'
    
    @staticmethod
    def refresh_hw_device_tcl(device: str | None = None) -> str:
        """
        刷新设备状态的 Tcl 命令
        
        Args:
            device: 设备名称（可选）
            
        Returns:
            Tcl 命令字符串
        """
        if device:
            return f'refresh_hw_device [get_hw_devices {device}]'
        return 'refresh_hw_device'
    
    @staticmethod
    def program_hw_device_tcl(
        device: str,
        bitstream: str | Path,
        verify: bool = True,
        reset_device: bool = True,
    ) -> str:
        """
        编程 FPGA 设备的 Tcl 命令
        
        Args:
            device: 设备名称
            bitstream: 比特流文件路径
            verify: 是否验证
            reset_device: 是否重置设备
            
        Returns:
            Tcl 命令字符串
        """
        cmd_parts = ['program_hw_devices']
        
        if device:
            cmd_parts.append(f'[get_hw_devices {device}]')
        
        result = ' '.join(cmd_parts)
        
        # 设置比特流文件属性
        set_property_cmd = f'set_property PROGRAM.FILE "{bitstream}" [get_hw_devices {device}]'
        
        return f'{set_property_cmd}\n{result}'
    
    @staticmethod
    def program_hw_devices_tcl(
        devices: list[str],
        bitstreams: list[str | Path],
    ) -> str:
        """
        编程多个 FPGA 设备的 Tcl 命令
        
        Args:
            devices: 设备名称列表
            bitstreams: 比特流文件路径列表
            
        Returns:
            Tcl 命令字符串
        """
        commands = []
        
        for device, bitstream in zip(devices, bitstreams):
            commands.append(
                f'set_property PROGRAM.FILE "{bitstream}" [get_hw_devices {device}]'
            )
        
        device_list = ' '.join(f'[get_hw_devices {d}]' for d in devices)
        commands.append(f'program_hw_devices {device_list}')
        
        return '\n'.join(commands)
    
    @staticmethod
    def set_program_file_tcl(device: str, bitstream: str | Path) -> str:
        """
        设置编程文件的 Tcl 命令
        
        Args:
            device: 设备名称
            bitstream: 比特流文件路径
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property PROGRAM.FILE "{bitstream}" [get_hw_devices {device}]'
    
    @staticmethod
    def set_probe_file_tcl(device: str, probe_file: str | Path) -> str:
        """
        设置探针文件的 Tcl 命令
        
        Args:
            device: 设备名称
            probe_file: 探针文件路径（.ltx）
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property PROBE.FILE "{probe_file}" [get_hw_devices {device}]'
    
    @staticmethod
    def boot_hw_device_tcl(device: str) -> str:
        """
        启动 FPGA 设备的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'boot_hw_device [get_hw_devices {device}]'
    
    @staticmethod
    def reset_hw_device_tcl(device: str) -> str:
        """
        重置 FPGA 设备的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'reset_hw_device [get_hw_devices {device}]'
    
    @staticmethod
    def get_device_property_tcl(device: str, property_name: str) -> str:
        """
        获取设备属性的 Tcl 命令
        
        Args:
            device: 设备名称
            property_name: 属性名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property {property_name} [get_hw_devices {device}]'
    
    @staticmethod
    def get_device_idcode_tcl(device: str) -> str:
        """
        获取设备 IDCODE 的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property IDCODE [get_hw_devices {device}]'
    
    @staticmethod
    def get_device_part_tcl(device: str) -> str:
        """
        获取设备型号的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property PART [get_hw_devices {device}]'
    
    @staticmethod
    def get_device_name_tcl(device: str) -> str:
        """
        获取设备名称的 Tcl 命令
        
        Args:
            device: 设备名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property NAME [get_hw_devices {device}]'
    
    @staticmethod
    def get_hw_cfgmem_tcl() -> str:
        """
        获取配置存储器的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_cfgmem'
    
    @staticmethod
    def create_hw_cfgmem_tcl(
        part: str,
        device: str,
        cfgmem_name: str = "cfgmem_0",
    ) -> str:
        """
        创建配置存储器的 Tcl 命令
        
        Args:
            part: 存储器型号
            device: 关联设备
            cfgmem_name: 配置存储器名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'create_hw_cfgmem -hw_device [get_hw_devices {device}] {cfgmem_name}'
    
    @staticmethod
    def program_hw_cfgmem_tcl(
        cfgmem: str,
        file_path: str | Path,
        verify: bool = True,
    ) -> str:
        """
        编程配置存储器的 Tcl 命令
        
        Args:
            cfgmem: 配置存储器名称
            file_path: 编程文件路径
            verify: 是否验证
            
        Returns:
            Tcl 命令字符串
        """
        commands = [
            f'set_property PROGRAM.ADDRESS_RANGE {{use_file}} [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.FILES "{{{file_path}}}" [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.UNUSED_PIN_TERMINATION {{pull-none}} [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.BLANK_CHECK  0 [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.ERASE  1 [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.CFG_PROGRAM  1 [get_hw_cfgmem {cfgmem}]',
            f'set_property PROGRAM.VERIFY  {1 if verify else 0} [get_hw_cfgmem {cfgmem}]',
            f'program_hw_cfgmem [get_hw_cfgmem {cfgmem}]',
        ]
        
        return '\n'.join(commands)
    
    @staticmethod
    def get_hw_ila_tcl() -> str:
        """
        获取 ILA 核的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_ilas'
    
    @staticmethod
    def run_hw_ila_tcl(ila: str) -> str:
        """
        运行 ILA 触发的 Tcl 命令
        
        Args:
            ila: ILA 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'run_hw_ila [get_hw_ilas {ila}]'
    
    @staticmethod
    def upload_hw_ila_tcl(ila: str) -> str:
        """
        上传 ILA 数据的 Tcl 命令
        
        Args:
            ila: ILA 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'upload_hw_ila [get_hw_ilas {ila}]'
    
    @staticmethod
    def get_hw_vio_tcl() -> str:
        """
        获取 VIO 核的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_vios'

    @staticmethod
    def get_hw_axis_tcl() -> str:
        """
        获取 HW AXI 接口列表的 Tcl 命令

        Returns:
            Tcl 命令字符串
        """
        return 'get_hw_axis'
    
    @staticmethod
    def set_vio_output_tcl(vio: str, probe: str, value: str) -> str:
        """
        设置 VIO 输出的 Tcl 命令
        
        Args:
            vio: VIO 名称
            probe: 探针名称
            value: 值
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property OUTPUT_VALUE {value} [get_hw_probes {probe} -of_objects [get_hw_vios {vio}]]'
    
    @staticmethod
    def get_vio_input_tcl(vio: str, probe: str) -> str:
        """
        获取 VIO 输入的 Tcl 命令
        
        Args:
            vio: VIO 名称
            probe: 探针名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'get_property INPUT_VALUE [get_hw_probes {probe} -of_objects [get_hw_vios {vio}]]'
    
    @staticmethod
    def refresh_hw_vio_tcl(vio: str) -> str:
        """
        刷新 VIO 的 Tcl 命令
        
        Args:
            vio: VIO 名称
            
        Returns:
            Tcl 命令字符串
        """
        return f'refresh_hw_vio [get_hw_vios {vio}]'

    @staticmethod
    def create_hw_axi_txn_tcl(
        txn_name: str,
        axi_name: str,
        address: str,
        txn_type: str = "read",
        data: str | None = None,
        length: int = 1,
    ) -> str:
        """
        创建 HW AXI 事务的 Tcl 命令

        Args:
            txn_name: 事务名称
            axi_name: AXI 接口名称
            address: 访问地址
            txn_type: 事务类型，read 或 write
            data: 写事务数据
            length: 事务长度

        Returns:
            Tcl 命令字符串
        """
        command = (
            f'create_hw_axi_txn {txn_name} [get_hw_axis {axi_name}] '
            f'-type {txn_type} -address {address} -len {length}'
        )
        if data is not None:
            command += f' -data {data}'
        return command

    @staticmethod
    def run_hw_axi_txn_tcl(txn_name: str) -> str:
        """
        运行 HW AXI 事务的 Tcl 命令

        Args:
            txn_name: 事务名称

        Returns:
            Tcl 命令字符串
        """
        return f'run_hw_axi [get_hw_axi_txns {txn_name}]'

    @staticmethod
    def get_hw_axi_data_tcl(txn_name: str) -> str:
        """
        读取 HW AXI 事务数据的 Tcl 命令

        Args:
            txn_name: 事务名称

        Returns:
            Tcl 命令字符串
        """
        return f'get_property DATA [get_hw_axi_txns {txn_name}]'

    @staticmethod
    def delete_hw_axi_txn_tcl(txn_name: str) -> str:
        """
        删除 HW AXI 事务的 Tcl 命令

        Args:
            txn_name: 事务名称

        Returns:
            Tcl 命令字符串
        """
        return f'delete_hw_axi_txn [get_hw_axi_txns {txn_name}]'
    
    @staticmethod
    def get_jtag_state_tcl() -> str:
        """
        获取 JTAG 状态的 Tcl 命令
        
        Returns:
            Tcl 命令字符串
        """
        return 'get_property JTAG_STATE [current_hw_target]'
    
    @staticmethod
    def set_jtag_state_tcl(state: str) -> str:
        """
        设置 JTAG 状态的 Tcl 命令
        
        Args:
            state: 目标状态
            
        Returns:
            Tcl 命令字符串
        """
        return f'set_property JTAG_STATE {state} [current_hw_target]'


class HardwareManager:
    """
    硬件管理器
    
    提供高级的硬件管理接口，结合 TclEngine 执行 Tcl 命令。
    """
    
    def __init__(self, tcl_engine):
        """
        初始化硬件管理器
        
        Args:
            tcl_engine: TclEngine 实例
        """
        self.engine = tcl_engine
        self.server: HardwareServer | None = None
        self.devices: list[HardwareDevice] = []
        self.current_device: HardwareDevice | None = None
    
    async def connect_server(self, url: str = "localhost:3121") -> dict:
        """
        连接硬件服务器
        
        Args:
            url: 服务器 URL（格式：host:port）
            
        Returns:
            执行结果字典
        """
        commands = [
            HardwareTclGenerator.open_hw_manager_tcl(),
            HardwareTclGenerator.connect_hw_server_tcl(url),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            self.server = HardwareServer(
                url=url,
                connected=True,
                devices=[],
            )
            logger.info(f"硬件服务器连接成功: {url}")
            
            # 自动获取设备列表
            await self._refresh_devices()
        else:
            logger.error(f"硬件服务器连接失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message=f"硬件服务器连接成功: {url}" if result.success else "硬件服务器连接失败",
            errors=result.errors,
            warnings=result.warnings,
            url=url,
        )
    
    async def disconnect_server(self) -> dict:
        """
        断开服务器连接
        
        Returns:
            执行结果字典
        """
        commands = [
            HardwareTclGenerator.disconnect_hw_server_tcl(),
            HardwareTclGenerator.close_hw_manager_tcl(),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            self.server = None
            self.devices = []
            self.current_device = None
            logger.info("硬件服务器已断开")
        else:
            logger.error(f"硬件服务器断开失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message="硬件服务器断开成功" if result.success else "硬件服务器断开失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def get_devices(self) -> list[HardwareDevice]:
        """
        获取设备列表
        
        Returns:
            设备列表
        """
        if not self.server or not self.server.connected:
            logger.warning("未连接到硬件服务器")
            return []
        
        await self._refresh_devices()
        return self.devices
    
    async def _refresh_devices(self) -> None:
        """
        刷新设备列表
        """
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.get_hw_devices_tcl(),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            self.devices = self._parse_devices_output(result.output)
            if self.server:
                self.server.devices = self.devices
            logger.debug(f"发现 {len(self.devices)} 个设备")
    
    async def program_fpga(
        self,
        device_index: int,
        bitstream_path: str | Path,
        verify: bool = True,
        reset: bool = True,
    ) -> ProgrammingResult:
        """
        编程 FPGA
        
        Args:
            device_index: 设备索引
            bitstream_path: 比特流文件路径
            verify: 是否验证
            reset: 是否重置设备
            
        Returns:
            编程结果
        """
        if device_index < 0 or device_index >= len(self.devices):
            return ProgrammingResult(
                success=False,
                status=ProgrammingStatus.FAILED,
                device="",
                bitstream=str(bitstream_path),
                errors=[f"无效的设备索引: {device_index}"],
            )
        
        device = self.devices[device_index]
        bitstream_path = Path(bitstream_path)
        
        if not bitstream_path.exists():
            return ProgrammingResult(
                success=False,
                status=ProgrammingStatus.FAILED,
                device=device.name,
                bitstream=str(bitstream_path),
                errors=[f"比特流文件不存在: {bitstream_path}"],
            )
        
        # 构建编程命令
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.current_hw_device_tcl(device.name),
            HardwareTclGenerator.set_program_file_tcl(device.name, bitstream_path),
            HardwareTclGenerator.program_hw_device_tcl(device.name, bitstream_path, verify, reset),
        ]
        
        result = await self.engine.execute_async(commands)
        
        programming_result = ProgrammingResult(
            success=result.success,
            status=ProgrammingStatus.COMPLETED if result.success else ProgrammingStatus.FAILED,
            device=device.name,
            bitstream=str(bitstream_path),
            errors=result.errors,
            warnings=result.warnings,
        )
        
        if result.success:
            logger.info(f"FPGA 编程成功: {device.name}")
        else:
            logger.error(f"FPGA 编程失败: {result.errors}")
        
        return programming_result
    
    async def program_multiple_fpgas(
        self,
        device_indices: list[int],
        bitstream_paths: list[str | Path],
    ) -> list[ProgrammingResult]:
        """
        编程多个 FPGA
        
        Args:
            device_indices: 设备索引列表
            bitstream_paths: 比特流文件路径列表
            
        Returns:
            编程结果列表
        """
        if len(device_indices) != len(bitstream_paths):
            raise ValueError("设备索引列表和比特流路径列表长度不匹配")
        
        results = []
        
        # 构建批量编程命令
        commands = [HardwareTclGenerator.open_hw_target_tcl()]
        
        for device_index, bitstream_path in zip(device_indices, bitstream_paths):
            if device_index < 0 or device_index >= len(self.devices):
                results.append(ProgrammingResult(
                    success=False,
                    status=ProgrammingStatus.FAILED,
                    device="",
                    bitstream=str(bitstream_path),
                    errors=[f"无效的设备索引: {device_index}"],
                ))
                continue
            
            device = self.devices[device_index]
            bitstream_path = Path(bitstream_path)
            
            if not bitstream_path.exists():
                results.append(ProgrammingResult(
                    success=False,
                    status=ProgrammingStatus.FAILED,
                    device=device.name,
                    bitstream=str(bitstream_path),
                    errors=[f"比特流文件不存在: {bitstream_path}"],
                ))
                continue
            
            commands.append(
                HardwareTclGenerator.set_program_file_tcl(device.name, bitstream_path)
            )
        
        # 执行编程
        result = await self.engine.execute_async(commands)
        
        # 解析结果
        for i, (device_index, bitstream_path) in enumerate(zip(device_indices, bitstream_paths)):
            if device_index >= 0 and device_index < len(self.devices):
                device = self.devices[device_index]
                results.append(ProgrammingResult(
                    success=result.success,
                    status=ProgrammingStatus.COMPLETED if result.success else ProgrammingStatus.FAILED,
                    device=device.name,
                    bitstream=str(bitstream_path),
                    errors=result.errors,
                    warnings=result.warnings,
                ))
        
        return results
    
    async def get_device_status(self, device_index: int) -> dict:
        """
        获取设备状态
        
        Args:
            device_index: 设备索引
            
        Returns:
            设备状态字典
        """
        if device_index < 0 or device_index >= len(self.devices):
            return {
                'success': False,
                'errors': [f"无效的设备索引: {device_index}"],
            }
        
        device = self.devices[device_index]
        
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.refresh_hw_device_tcl(device.name),
            HardwareTclGenerator.get_device_property_tcl(device.name, 'REGISTER.STATUS'),
        ]
        
        result = await self.engine.execute_async(commands)
        
        status = format_result(
            success=result.success,
            message="获取设备状态成功" if result.success else "获取设备状态失败",
            errors=result.errors,
            warnings=result.warnings,
            device=device.name,
            part=device.part,
        )
        
        if result.success:
            # 解析状态信息
            status['raw_status'] = result.output
        
        return status
    
    async def get_device_idcode(self, device_index: int) -> str | None:
        """
        获取设备 IDCODE
        
        Args:
            device_index: 设备索引
            
        Returns:
            IDCODE 字符串
        """
        if device_index < 0 or device_index >= len(self.devices):
            return None
        
        device = self.devices[device_index]
        
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.get_device_idcode_tcl(device.name),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            return result.output.strip()
        
        return None
    
    async def boot_device(self, device_index: int) -> dict:
        """
        启动设备
        
        Args:
            device_index: 设备索引
            
        Returns:
            执行结果字典
        """
        if device_index < 0 or device_index >= len(self.devices):
            return {
                'success': False,
                'errors': [f"无效的设备索引: {device_index}"],
            }
        
        device = self.devices[device_index]
        
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.boot_hw_device_tcl(device.name),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            logger.info(f"设备启动成功: {device.name}")
        else:
            logger.error(f"设备启动失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message="设备启动成功" if result.success else "设备启动失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def reset_device(self, device_index: int) -> dict:
        """
        重置设备
        
        Args:
            device_index: 设备索引
            
        Returns:
            执行结果字典
        """
        if device_index < 0 or device_index >= len(self.devices):
            return {
                'success': False,
                'errors': [f"无效的设备索引: {device_index}"],
            }
        
        device = self.devices[device_index]
        
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.reset_hw_device_tcl(device.name),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            logger.info(f"设备重置成功: {device.name}")
        else:
            logger.error(f"设备重置失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message="设备重置成功" if result.success else "设备重置失败",
            errors=result.errors,
            warnings=result.warnings,
        )
    
    async def set_probe_file(
        self,
        device_index: int,
        probe_file_path: str | Path,
    ) -> dict:
        """
        设置探针文件
        
        Args:
            device_index: 设备索引
            probe_file_path: 探针文件路径（.ltx）
            
        Returns:
            执行结果字典
        """
        if device_index < 0 or device_index >= len(self.devices):
            return {
                'success': False,
                'errors': [f"无效的设备索引: {device_index}"],
            }
        
        device = self.devices[device_index]
        probe_file_path = Path(probe_file_path)
        
        if not probe_file_path.exists():
            return {
                'success': False,
                'errors': [f"探针文件不存在: {probe_file_path}"],
            }
        
        command = HardwareTclGenerator.set_probe_file_tcl(device.name, probe_file_path)
        result = await self.engine.execute_async(command)
        
        if result.success:
            logger.info(f"探针文件设置成功: {probe_file_path}")
        else:
            logger.error(f"探针文件设置失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message="探针文件设置成功" if result.success else "探针文件设置失败",
            errors=result.errors,
            warnings=result.warnings,
            artifacts=path_artifact(probe_file_path),
        )
    
    async def program_config_memory(
        self,
        device_index: int,
        config_file: str | Path,
        config_part: str,
    ) -> dict:
        """
        编程配置存储器
        
        Args:
            device_index: 设备索引
            config_file: 配置文件路径
            config_part: 存储器型号
            
        Returns:
            执行结果字典
        """
        if device_index < 0 or device_index >= len(self.devices):
            return {
                'success': False,
                'errors': [f"无效的设备索引: {device_index}"],
            }
        
        device = self.devices[device_index]
        config_file = Path(config_file)
        
        if not config_file.exists():
            return {
                'success': False,
                'errors': [f"配置文件不存在: {config_file}"],
            }
        
        cfgmem_name = f"cfgmem_{device.name}"
        
        commands = [
            HardwareTclGenerator.open_hw_target_tcl(),
            HardwareTclGenerator.create_hw_cfgmem_tcl(config_part, device.name, cfgmem_name),
            HardwareTclGenerator.program_hw_cfgmem_tcl(cfgmem_name, config_file),
        ]
        
        result = await self.engine.execute_async(commands)
        
        if result.success:
            logger.info(f"配置存储器编程成功: {device.name}")
        else:
            logger.error(f"配置存储器编程失败: {result.errors}")
        
        return format_result(
            success=result.success,
            message="配置存储器编程成功" if result.success else "配置存储器编程失败",
            errors=result.errors,
            warnings=result.warnings,
            artifacts=path_artifact(config_file),
        )
    
    async def get_jtag_state(self) -> JtagState:
        """
        获取 JTAG 状态
        
        Returns:
            JTAG 状态
        """
        command = HardwareTclGenerator.get_jtag_state_tcl()
        result = await self.engine.execute_async(command)
        
        if result.success:
            state_str = result.output.strip().lower()
            try:
                return JtagState(state_str)
            except ValueError:
                return JtagState.UNKNOWN
        
        return JtagState.UNKNOWN
    
    def get_device_by_name(self, name: str) -> HardwareDevice | None:
        """
        根据名称获取设备
        
        Args:
            name: 设备名称
            
        Returns:
            设备对象，如果未找到则返回 None
        """
        for device in self.devices:
            if device.name == name:
                return device
        return None
    
    def get_fpga_devices(self) -> list[HardwareDevice]:
        """
        获取所有 FPGA 设备
        
        Returns:
            FPGA 设备列表
        """
        return [d for d in self.devices if d.is_fpga]
    
    def _parse_devices_output(self, output: str) -> list[HardwareDevice]:
        """
        解析设备列表输出
        
        Args:
            output: 输出字符串
            
        Returns:
            设备列表
        """
        devices = []
        
        # 解析设备信息
        # Vivado 输出格式通常为设备名称列表
        lines = output.strip().split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('#'):
                # 提取设备名称
                device_name = line
                
                # 判断是否为 FPGA
                is_fpga = self._is_fpga_device(device_name)
                
                # 确定设备类型
                device_type = DeviceType.FPGA if is_fpga else DeviceType.UNKNOWN
                
                device = HardwareDevice(
                    name=device_name,
                    jtag_index=i,
                    irlen=0,  # 需要额外查询
                    part="",  # 需要额外查询
                    is_fpga=is_fpga,
                    device_type=device_type,
                )
                devices.append(device)
        
        return devices
    
    def _is_fpga_device(self, device_name: str) -> bool:
        """
        判断是否为 FPGA 设备
        
        Args:
            device_name: 设备名称
            
        Returns:
            是否为 FPGA
        """
        # 根据设备名称判断
        fpga_patterns = [
            'xc7', 'xcu', 'xcku', 'xcvu', 'xczu', 'xq', 'xa', 'xqr',
        ]
        
        device_lower = device_name.lower()
        for pattern in fpga_patterns:
            if pattern in device_lower:
                return True
        
        return False
    
    def _parse_idcode(self, output: str) -> str | None:
        """
        解析 IDCODE 输出
        
        Args:
            output: 输出字符串
            
        Returns:
            IDCODE
        """
        # IDCODE 通常是十六进制格式
        match = re.search(r'0x[0-9A-Fa-f]+', output)
        if match:
            return match.group(0)
        return None
