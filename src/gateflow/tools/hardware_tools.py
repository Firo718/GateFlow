"""
硬件编程 MCP 工具。

提供 Vivado 硬件服务器连接和 FPGA 编程相关的 MCP 工具接口。
"""

import logging
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.vivado.hardware import HardwareTclGenerator
from gateflow.vivado.tcl_engine import TclEngine

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None
_hw_server_connected: bool = False
_hw_server_url: str | None = None
_hw_devices: list[dict[str, Any]] = []
_current_hw_target: str | None = None
_device_probe_files: dict[str, str] = {}


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if _engine is None:
        _engine = TclEngine()
    return _engine


# ==================== 结果模型 ====================


class ConnectServerResult(BaseModel):
    """连接硬件服务器结果模型。"""

    success: bool = Field(description="操作是否成功")
    server_url: str | None = Field(default=None, description="服务器地址")
    devices: list[dict[str, Any]] = Field(default_factory=list, description="设备列表")
    device_count: int = Field(default=0, description="设备数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class DisconnectResult(BaseModel):
    """断开连接结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class GetDevicesResult(BaseModel):
    """获取设备列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    devices: list[dict[str, Any]] = Field(default_factory=list, description="设备列表")
    device_count: int = Field(default=0, description="设备数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ProgramResult(BaseModel):
    """编程 FPGA 结果模型。"""

    success: bool = Field(description="操作是否成功")
    device_index: int | None = Field(default=None, description="设备索引")
    device_name: str | None = Field(default=None, description="设备名称")
    bitstream_path: str | None = Field(default=None, description="比特流文件路径")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class RefreshResult(BaseModel):
    """刷新设备结果模型。"""

    success: bool = Field(description="操作是否成功")
    device_index: int | None = Field(default=None, description="设备索引")
    device_name: str | None = Field(default=None, description="设备名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ServerStatusResult(BaseModel):
    """服务器状态结果模型。"""

    success: bool = Field(description="操作是否成功")
    connected: bool = Field(default=False, description="是否已连接")
    server_url: str | None = Field(default=None, description="服务器地址")
    device_count: int = Field(default=0, description="设备数量")
    current_target: str | None = Field(default=None, description="当前硬件目标")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class HardwareTargetsResult(BaseModel):
    """硬件目标列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    targets: list[str] = Field(default_factory=list, description="目标列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class HardwareActionResult(BaseModel):
    """通用硬件动作结果。"""

    success: bool = Field(description="操作是否成功")
    name: str | None = Field(default=None, description="目标名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class HardwareValueResult(BaseModel):
    """硬件值读取结果。"""

    success: bool = Field(description="操作是否成功")
    name: str | None = Field(default=None, description="目标名称")
    value: str | None = Field(default=None, description="读取到的值")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class HardwareAxiResult(BaseModel):
    """AXI 调试结果。"""

    success: bool = Field(description="操作是否成功")
    axi_name: str | None = Field(default=None, description="AXI 接口名称")
    address: str | None = Field(default=None, description="访问地址")
    transaction_name: str | None = Field(default=None, description="事务名称")
    value: str | None = Field(default=None, description="读取或写入的数据")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


def _async_success(result: Any) -> bool:
    """兼容 execute_async 返回对象或 dict。"""
    if isinstance(result, dict):
        return bool(result.get("success", False))
    return bool(getattr(result, "success", False))


def _async_output(result: Any) -> str:
    """兼容 execute_async 返回对象或 dict 的输出文本。"""
    if isinstance(result, dict):
        return str(result.get("output", result.get("result", "")) or "")
    return str(getattr(result, "output", getattr(result, "result", "")) or "")


def _async_first_error(result: Any) -> str | None:
    """提取第一条错误信息。"""
    if isinstance(result, dict):
        errors = result.get("errors")
        if isinstance(errors, list) and errors:
            return str(errors[0])
        if errors:
            return str(errors)
        error = result.get("error")
        if error:
            return str(error)
        return None

    errors = getattr(result, "errors", None)
    if isinstance(errors, list) and errors:
        return str(errors[0])
    warnings = getattr(result, "warnings", None)
    if isinstance(warnings, list) and warnings:
        return str(warnings[0])
    return None


def _normalize_hex_value(value: str) -> str:
    """Normalize AXI value/address inputs."""
    text = value.strip()
    if text.lower().startswith("0x"):
        return text
    return f"0x{text}"


def _sanitize_txn_name(prefix: str, name: str, address: str) -> str:
    """Build a stable AXI transaction name."""
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_") or "axi"
    safe_addr = "".join(ch if ch.isalnum() else "_" for ch in address).strip("_") or "addr"
    return f"{prefix}_{safe_name}_{safe_addr}"


def _resolve_probe_file_path(
    bitstream_path: str | None,
    probe_file_path: str | None,
) -> str | None:
    """Resolve an explicit or sibling .ltx probe file."""
    if probe_file_path:
        return probe_file_path
    if not bitstream_path:
        return None

    bit_path = Path(bitstream_path)
    sibling = bit_path.with_suffix(".ltx")
    if sibling.exists():
        return str(sibling)
    return None


# ==================== 工具注册 ====================


def register_hardware_tools(mcp: FastMCP) -> None:
    """
    注册硬件编程相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def connect_hw_server(
        url: str = "localhost:3121",
    ) -> ConnectServerResult:
        """
        连接硬件服务器。

        此工具用于连接 Vivado 硬件服务器，建立与本地或远程 JTAG 设备的连接。
        连接成功后可以枚举设备、编程 FPGA 等操作。

        Args:
            url: 服务器地址，格式为 "host:port"。
                默认为 "localhost:3121" (本地硬件服务器)。
                远程服务器示例: "192.168.1.100:3121"

        Returns:
            ConnectServerResult 包含连接结果和设备列表。

        Example:
            连接本地硬件服务器:
            ```
            result = connect_hw_server()
            if result.success:
                print(f"连接成功，发现 {result.device_count} 个设备")
                for device in result.devices:
                    print(f"设备: {device['name']}")
            ```

            连接远程硬件服务器:
            ```
            result = connect_hw_server(url="192.168.1.100:3121")
            ```
        """
        global _hw_server_connected, _hw_server_url, _hw_devices, _current_hw_target, _device_probe_files

        logger.info(f"连接硬件服务器: url={url}")

        try:
            # 构建 Tcl 命令
            tcl_cmd = f"open_hw_target -url {url}"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            if result.get("success", False):
                # 更新全局状态
                _hw_server_connected = True
                _hw_server_url = url
                _current_hw_target = None
                _device_probe_files = {}

                # 获取设备列表
                devices_result = await engine.execute("get_hw_devices")
                devices = devices_result.get("devices", [])

                # 解析设备信息
                _hw_devices = []
                for i, dev_name in enumerate(devices):
                    device_info = {
                        "index": i,
                        "name": dev_name,
                        "type": "FPGA",  # 默认类型
                    }
                    _hw_devices.append(device_info)

                return ConnectServerResult(
                    success=True,
                    server_url=url,
                    devices=_hw_devices,
                    device_count=len(_hw_devices),
                    message=f"成功连接到硬件服务器 {url}，发现 {len(_hw_devices)} 个设备",
                    error=None,
                )
            else:
                return ConnectServerResult(
                    success=False,
                    server_url=url,
                    devices=[],
                    device_count=0,
                    message="连接硬件服务器失败",
                    error=result.get("error", "未知错误"),
                )

        except Exception as e:
            logger.error(f"连接硬件服务器失败: {e}")
            return ConnectServerResult(
                success=False,
                server_url=url,
                devices=[],
                device_count=0,
                message="连接硬件服务器失败",
                error=str(e),
            )

    @mcp.tool()
    async def disconnect_hw_server() -> DisconnectResult:
        """
        断开硬件服务器连接。

        此工具用于断开与 Vivado 硬件服务器的连接。
        断开连接后，将无法访问 JTAG 设备。

        Returns:
            DisconnectResult 包含断开连接结果。

        Example:
            断开连接:
            ```
            result = disconnect_hw_server()
            if result.success:
                print("已断开硬件服务器连接")
            ```
        """
        global _hw_server_connected, _hw_server_url, _hw_devices, _current_hw_target, _device_probe_files

        logger.info("断开硬件服务器连接")

        try:
            # 构建 Tcl 命令
            tcl_cmd = "close_hw_target"

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            # 更新全局状态
            _hw_server_connected = False
            _hw_server_url = None
            _hw_devices = []
            _current_hw_target = None
            _device_probe_files = {}

            return DisconnectResult(
                success=result.get("success", False),
                message="已断开硬件服务器连接",
                error=result.get("error"),
            )

        except Exception as e:
            logger.error(f"断开硬件服务器连接失败: {e}")
            return DisconnectResult(
                success=False,
                message="断开硬件服务器连接失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_hw_devices() -> GetDevicesResult:
        """
        获取硬件设备列表。

        此工具返回当前连接的所有 JTAG 设备信息，包括:
        - 设备名称
        - 设备型号
        - JTAG 位置
        - 设备状态

        使用此工具前需要先连接硬件服务器。

        Returns:
            GetDevicesResult 包含设备列表。

        Example:
            获取设备列表:
            ```
            result = get_hw_devices()
            if result.success:
                for device in result.devices:
                    print(f"设备 {device['index']}: {device['name']}")
            ```
        """
        global _hw_devices

        logger.info("获取硬件设备列表")

        try:
            # 检查是否已连接
            if not _hw_server_connected:
                return GetDevicesResult(
                    success=False,
                    devices=[],
                    device_count=0,
                    message="未连接硬件服务器，请先调用 connect_hw_server",
                    error="未连接硬件服务器",
                )

            # 执行 Tcl 命令获取设备列表
            engine = _get_engine()
            result = await engine.execute("get_hw_devices")

            # 解析设备信息
            devices = []
            device_names = result.get("devices", [])

            for i, dev_name in enumerate(device_names):
                # 获取设备详细信息
                device_info = {
                    "index": i,
                    "name": dev_name,
                    "type": "FPGA",
                }

                # 尝试获取更多设备信息
                try:
                    part_result = await engine.execute(f"get_property PART {dev_name}")
                    if part_result.get("success"):
                        device_info["part"] = part_result.get("value", "")
                except Exception:
                    pass

                devices.append(device_info)

            _hw_devices = devices

            return GetDevicesResult(
                success=True,
                devices=devices,
                device_count=len(devices),
                message=f"找到 {len(devices)} 个硬件设备",
                error=None,
            )

        except Exception as e:
            logger.error(f"获取硬件设备列表失败: {e}")
            return GetDevicesResult(
                success=False,
                devices=[],
                device_count=0,
                message="获取硬件设备列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def program_fpga(
        device_index: int = 0,
        bitstream_path: str | None = None,
    ) -> ProgramResult:
        """
        编程 FPGA 设备。

        此工具将比特流文件下载到指定的 FPGA 设备。
        编程前需要先连接硬件服务器并确保设备可用。

        Args:
            device_index: 设备索引，默认为 0 (第一个设备)。
                         如果连接了多个设备，可以指定要编程的设备索引。
            bitstream_path: 比特流文件路径 (.bit)，可选。
                           如果未提供，将使用当前项目生成的比特流文件。

        Returns:
            ProgramResult 包含编程结果。

        Example:
            使用默认比特流编程第一个设备:
            ```
            result = program_fpga()
            if result.success:
                print(f"设备 {result.device_name} 编程成功")
            ```

            使用指定比特流编程:
            ```
            result = program_fpga(
                device_index=0,
                bitstream_path="/home/user/project/bitstream/top.bit"
            )
            ```

            编程第二个设备:
            ```
            result = program_fpga(device_index=1)
            ```
        """
        global _hw_devices

        logger.info(f"编程 FPGA: device_index={device_index}, bitstream={bitstream_path}")

        try:
            # 检查是否已连接
            if not _hw_server_connected:
                return ProgramResult(
                    success=False,
                    device_index=device_index,
                    message="未连接硬件服务器，请先调用 connect_hw_server",
                    error="未连接硬件服务器",
                )

            # 检查设备索引是否有效
            if device_index < 0 or device_index >= len(_hw_devices):
                return ProgramResult(
                    success=False,
                    device_index=device_index,
                    message=f"设备索引 {device_index} 无效，可用设备数量: {len(_hw_devices)}",
                    error="设备索引无效",
                )

            device = _hw_devices[device_index]
            device_name = device.get("name", f"device_{device_index}")

            # 构建编程命令
            if bitstream_path:
                # 使用指定的比特流文件
                tcl_cmd = f"""
                set device [get_hw_devices {device_name}]
                current_hw_device $device
                set_property PROGRAM.FILE {{{bitstream_path}}} $device
                program_hw_devices $device
                """
            else:
                # 使用当前项目的比特流
                tcl_cmd = f"""
                set device [get_hw_devices {device_name}]
                current_hw_device $device
                set bitstream [get_property PROGRAM.FILE [current_hw_device]]
                if {{$bitstream eq ""}} {{
                    error "未找到比特流文件，请指定 bitstream_path 参数"
                }}
                program_hw_devices $device
                """

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            return ProgramResult(
                success=result.get("success", False),
                device_index=device_index,
                device_name=device_name,
                bitstream_path=bitstream_path,
                message=result.get("message", f"设备 {device_name} 编程成功"),
                error=result.get("error"),
            )

        except Exception as e:
            logger.error(f"编程 FPGA 失败: {e}")
            return ProgramResult(
                success=False,
                device_index=device_index,
                message="编程 FPGA 失败",
                error=str(e),
            )

    @mcp.tool()
    async def refresh_hw_device(device_index: int = 0) -> RefreshResult:
        """
        刷新设备状态。

        此工具刷新指定 FPGA 设备的状态信息，包括:
        - JTAG 状态
        - 配置状态
        - 器件 ID

        Args:
            device_index: 设备索引，默认为 0 (第一个设备)。

        Returns:
            RefreshResult 包含刷新结果。

        Example:
            刷新第一个设备:
            ```
            result = refresh_hw_device()
            if result.success:
                print(f"设备 {result.device_name} 状态已刷新")
            ```

            刷新指定设备:
            ```
            result = refresh_hw_device(device_index=1)
            ```
        """
        global _hw_devices

        logger.info(f"刷新设备状态: device_index={device_index}")

        try:
            # 检查是否已连接
            if not _hw_server_connected:
                return RefreshResult(
                    success=False,
                    device_index=device_index,
                    message="未连接硬件服务器，请先调用 connect_hw_server",
                    error="未连接硬件服务器",
                )

            # 检查设备索引是否有效
            if device_index < 0 or device_index >= len(_hw_devices):
                return RefreshResult(
                    success=False,
                    device_index=device_index,
                    message=f"设备索引 {device_index} 无效",
                    error="设备索引无效",
                )

            device = _hw_devices[device_index]
            device_name = device.get("name", f"device_{device_index}")

            # 构建 Tcl 命令
            tcl_cmd = f"""
            set device [get_hw_devices {device_name}]
            refresh_hw_device $device
            """

            # 执行 Tcl 命令
            engine = _get_engine()
            result = await engine.execute(tcl_cmd)

            return RefreshResult(
                success=result.get("success", False),
                device_index=device_index,
                device_name=device_name,
                message=result.get("message", f"设备 {device_name} 状态已刷新"),
                error=result.get("error"),
            )

        except Exception as e:
            logger.error(f"刷新设备状态失败: {e}")
            return RefreshResult(
                success=False,
                device_index=device_index,
                message="刷新设备状态失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_hw_server_status() -> ServerStatusResult:
        """
        获取硬件服务器状态。

        此工具返回当前硬件服务器的连接状态，包括:
        - 连接状态
        - 服务器地址
        - 已连接设备数量

        Returns:
            ServerStatusResult 包含服务器状态信息。

        Example:
            检查服务器状态:
            ```
            result = get_hw_server_status()
            if result.connected:
                print(f"已连接到 {result.server_url}")
                print(f"设备数量: {result.device_count}")
            else:
                print("未连接硬件服务器")
            ```
        """
        global _hw_server_connected, _hw_server_url, _hw_devices, _current_hw_target

        logger.info("获取硬件服务器状态")

        try:
            return ServerStatusResult(
                success=True,
                connected=_hw_server_connected,
                server_url=_hw_server_url,
                device_count=len(_hw_devices),
                current_target=_current_hw_target,
                message="硬件服务器状态获取成功",
                error=None,
            )

        except Exception as e:
            logger.error(f"获取硬件服务器状态失败: {e}")
            return ServerStatusResult(
                success=False,
                connected=False,
                server_url=None,
                device_count=0,
                current_target=None,
                message="获取硬件服务器状态失败",
                error=str(e),
            )

    @mcp.tool()
    async def list_hardware_targets() -> HardwareTargetsResult:
        """列出当前硬件服务器可见的硬件目标。"""
        logger.info("列出硬件目标")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.get_hw_targets_tcl())
            success = _async_success(result)
            output = _async_output(result).strip() if success else ""
            targets = [line.strip() for line in output.splitlines() if line.strip()]
            return HardwareTargetsResult(
                success=success,
                targets=targets,
                message=f"找到 {len(targets)} 个硬件目标" if success else "获取硬件目标失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"列出硬件目标异常: {e}")
            return HardwareTargetsResult(
                success=False,
                targets=[],
                message="获取硬件目标失败",
                error=str(e),
            )

    @mcp.tool()
    async def open_hardware_target(target: str | None = None) -> HardwareActionResult:
        """打开指定硬件目标。"""
        logger.info(f"打开硬件目标: {target}")
        try:
            global _current_hw_target
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.open_hw_target_tcl(target))
            success = _async_success(result)
            if success:
                _current_hw_target = target or "default"
            return HardwareActionResult(
                success=success,
                name=target,
                message=f"硬件目标已打开: {target or 'default'}" if success else "打开硬件目标失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"打开硬件目标异常: {e}")
            return HardwareActionResult(
                success=False,
                name=target,
                message="打开硬件目标失败",
                error=str(e),
            )

    @mcp.tool()
    async def quick_program(
        bitstream_path: str | None = None,
        device_index: int = 0,
        url: str = "localhost:3121",
        probe_file_path: str | None = None,
    ) -> ProgramResult:
        """一键连接硬件服务器并下载 bitstream。"""
        logger.info(f"一键编程 FPGA: device_index={device_index}, bitstream={bitstream_path}")

        connect_result = await connect_hw_server(url=url)
        if not connect_result.success:
            return ProgramResult(
                success=False,
                device_index=device_index,
                message="一键编程失败：连接硬件服务器失败",
                error=connect_result.error,
            )

        program_result = await program_fpga(device_index=device_index, bitstream_path=bitstream_path)
        if not program_result.success:
            return program_result

        resolved_probe = _resolve_probe_file_path(bitstream_path, probe_file_path)
        if resolved_probe:
            probe_result = await set_probe_file(device_index=device_index, probe_file_path=resolved_probe)
            if not probe_result.success:
                return ProgramResult(
                    success=False,
                    device_index=device_index,
                    device_name=program_result.device_name,
                    bitstream_path=bitstream_path,
                    message="一键编程成功，但探针文件绑定失败",
                    error=probe_result.error,
                )

        return program_result

    @mcp.tool()
    async def set_probe_file(
        device_index: int = 0,
        probe_file_path: str | None = None,
    ) -> HardwareActionResult:
        """将 .ltx 探针文件绑定到指定硬件设备。"""
        logger.info(f"绑定探针文件: device_index={device_index}, probe_file={probe_file_path}")
        try:
            global _device_probe_files
            if not _hw_server_connected:
                return HardwareActionResult(
                    success=False,
                    name=None,
                    message="未连接硬件服务器，请先调用 connect_hw_server",
                    error="未连接硬件服务器",
                )
            if device_index < 0 or device_index >= len(_hw_devices):
                return HardwareActionResult(
                    success=False,
                    name=None,
                    message=f"设备索引 {device_index} 无效",
                    error="设备索引无效",
                )
            if not probe_file_path:
                return HardwareActionResult(
                    success=False,
                    name=None,
                    message="未提供探针文件路径",
                    error="probe_file_path 不能为空",
                )

            probe_path = Path(probe_file_path)
            if not probe_path.exists():
                return HardwareActionResult(
                    success=False,
                    name=str(probe_path),
                    message="探针文件不存在",
                    error=f"探针文件不存在: {probe_path}",
                )

            device = _hw_devices[device_index]
            device_name = device.get("name", f"device_{device_index}")
            engine = _get_engine()
            result = await engine.execute_async(
                HardwareTclGenerator.set_probe_file_tcl(device_name, probe_path)
            )
            success = _async_success(result)
            if success:
                _device_probe_files[device_name] = str(probe_path)
            return HardwareActionResult(
                success=success,
                name=device_name,
                message=f"探针文件已绑定到设备: {device_name}" if success else "绑定探针文件失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"绑定探针文件异常: {e}")
            return HardwareActionResult(
                success=False,
                name=None,
                message="绑定探针文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_ila_list() -> HardwareTargetsResult:
        """列出当前硬件会话中的 ILA 核。"""
        logger.info("列出 ILA 核")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.get_hw_ila_tcl())
            success = _async_success(result)
            output = _async_output(result).strip() if success else ""
            ilas = [line.strip() for line in output.splitlines() if line.strip()]
            return HardwareTargetsResult(
                success=success,
                targets=ilas,
                message=f"找到 {len(ilas)} 个 ILA 核" if success else "获取 ILA 列表失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"列出 ILA 核异常: {e}")
            return HardwareTargetsResult(
                success=False,
                targets=[],
                message="获取 ILA 列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_vio_list() -> HardwareTargetsResult:
        """列出当前硬件会话中的 VIO 核。"""
        logger.info("列出 VIO 核")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.get_hw_vio_tcl())
            success = _async_success(result)
            output = _async_output(result).strip() if success else ""
            vios = [line.strip() for line in output.splitlines() if line.strip()]
            return HardwareTargetsResult(
                success=success,
                targets=vios,
                message=f"找到 {len(vios)} 个 VIO 核" if success else "获取 VIO 列表失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"列出 VIO 核异常: {e}")
            return HardwareTargetsResult(
                success=False,
                targets=[],
                message="获取 VIO 列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_ila_run(ila: str) -> HardwareActionResult:
        """触发指定 ILA 核开始采集。"""
        logger.info(f"触发 ILA 采集: {ila}")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.run_hw_ila_tcl(ila))
            success = _async_success(result)
            return HardwareActionResult(
                success=success,
                name=ila,
                message=f"ILA 已触发: {ila}" if success else "ILA 触发失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"触发 ILA 采集异常: {e}")
            return HardwareActionResult(
                success=False,
                name=ila,
                message="ILA 触发失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_ila_upload(ila: str) -> HardwareActionResult:
        """上传指定 ILA 核的采集数据。"""
        logger.info(f"上传 ILA 数据: {ila}")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.upload_hw_ila_tcl(ila))
            success = _async_success(result)
            return HardwareActionResult(
                success=success,
                name=ila,
                message=f"ILA 数据已上传: {ila}" if success else "ILA 数据上传失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"上传 ILA 数据异常: {e}")
            return HardwareActionResult(
                success=False,
                name=ila,
                message="ILA 数据上传失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_vio_set_output(vio: str, probe: str, value: str) -> HardwareActionResult:
        """设置 VIO 输出探针值并提交到硬件。"""
        logger.info(f"设置 VIO 输出: vio={vio}, probe={probe}, value={value}")
        try:
            engine = _get_engine()
            command = "\n".join(
                [
                    HardwareTclGenerator.set_vio_output_tcl(vio, probe, value),
                    f"commit_hw_vio [get_hw_vios {vio}]",
                ]
            )
            result = await engine.execute_async(command)
            success = _async_success(result)
            return HardwareActionResult(
                success=success,
                name=f"{vio}:{probe}",
                message=f"VIO 输出已设置: {probe}={value}" if success else "设置 VIO 输出失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"设置 VIO 输出异常: {e}")
            return HardwareActionResult(
                success=False,
                name=f"{vio}:{probe}",
                message="设置 VIO 输出失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_vio_get_input(vio: str, probe: str) -> HardwareValueResult:
        """读取 VIO 输入探针值。"""
        logger.info(f"读取 VIO 输入: vio={vio}, probe={probe}")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.get_vio_input_tcl(vio, probe))
            success = _async_success(result)
            value = _async_output(result).strip() if success else None
            return HardwareValueResult(
                success=success,
                name=f"{vio}:{probe}",
                value=value,
                message="读取 VIO 输入成功" if success else "读取 VIO 输入失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"读取 VIO 输入异常: {e}")
            return HardwareValueResult(
                success=False,
                name=f"{vio}:{probe}",
                value=None,
                message="读取 VIO 输入失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_vio_refresh(vio: str) -> HardwareActionResult:
        """刷新指定 VIO 核。"""
        logger.info(f"刷新 VIO: {vio}")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.refresh_hw_vio_tcl(vio))
            success = _async_success(result)
            return HardwareActionResult(
                success=success,
                name=vio,
                message=f"VIO 已刷新: {vio}" if success else "刷新 VIO 失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"刷新 VIO 异常: {e}")
            return HardwareActionResult(
                success=False,
                name=vio,
                message="刷新 VIO 失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_axi_list() -> HardwareTargetsResult:
        """列出当前硬件会话中的 AXI 调试接口。"""
        logger.info("列出 HW AXI 接口")
        try:
            engine = _get_engine()
            result = await engine.execute_async(HardwareTclGenerator.get_hw_axis_tcl())
            success = _async_success(result)
            output = _async_output(result).strip() if success else ""
            axis = [line.strip() for line in output.splitlines() if line.strip()]
            return HardwareTargetsResult(
                success=success,
                targets=axis,
                message=f"找到 {len(axis)} 个 HW AXI 接口" if success else "获取 HW AXI 列表失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"列出 HW AXI 接口异常: {e}")
            return HardwareTargetsResult(
                success=False,
                targets=[],
                message="获取 HW AXI 列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_axi_read(axi_name: str, address: str, length: int = 1) -> HardwareAxiResult:
        """通过硬件 AXI 调试接口读取寄存器/内存。"""
        logger.info(f"HW AXI 读取: axi={axi_name}, address={address}, length={length}")
        txn_name = _sanitize_txn_name("axi_read", axi_name, address)
        try:
            engine = _get_engine()
            normalized_address = _normalize_hex_value(address)
            command = "\n".join(
                [
                    HardwareTclGenerator.create_hw_axi_txn_tcl(
                        txn_name=txn_name,
                        axi_name=axi_name,
                        address=normalized_address,
                        txn_type="read",
                        length=length,
                    ),
                    HardwareTclGenerator.run_hw_axi_txn_tcl(txn_name),
                    HardwareTclGenerator.get_hw_axi_data_tcl(txn_name),
                    HardwareTclGenerator.delete_hw_axi_txn_tcl(txn_name),
                ]
            )
            result = await engine.execute_async(command)
            success = _async_success(result)
            value = _async_output(result).strip() if success else None
            return HardwareAxiResult(
                success=success,
                axi_name=axi_name,
                address=normalized_address,
                transaction_name=txn_name,
                value=value,
                message="HW AXI 读取成功" if success else "HW AXI 读取失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"HW AXI 读取异常: {e}")
            return HardwareAxiResult(
                success=False,
                axi_name=axi_name,
                address=address,
                transaction_name=txn_name,
                value=None,
                message="HW AXI 读取失败",
                error=str(e),
            )

    @mcp.tool()
    async def hw_axi_write(
        axi_name: str,
        address: str,
        value: str,
        length: int = 1,
    ) -> HardwareAxiResult:
        """通过硬件 AXI 调试接口写寄存器/内存。"""
        logger.info(f"HW AXI 写入: axi={axi_name}, address={address}, value={value}, length={length}")
        txn_name = _sanitize_txn_name("axi_write", axi_name, address)
        try:
            engine = _get_engine()
            normalized_address = _normalize_hex_value(address)
            normalized_value = _normalize_hex_value(value)
            command = "\n".join(
                [
                    HardwareTclGenerator.create_hw_axi_txn_tcl(
                        txn_name=txn_name,
                        axi_name=axi_name,
                        address=normalized_address,
                        txn_type="write",
                        data=normalized_value,
                        length=length,
                    ),
                    HardwareTclGenerator.run_hw_axi_txn_tcl(txn_name),
                    HardwareTclGenerator.delete_hw_axi_txn_tcl(txn_name),
                ]
            )
            result = await engine.execute_async(command)
            success = _async_success(result)
            return HardwareAxiResult(
                success=success,
                axi_name=axi_name,
                address=normalized_address,
                transaction_name=txn_name,
                value=normalized_value,
                message="HW AXI 写入成功" if success else "HW AXI 写入失败",
                error=_async_first_error(result),
            )
        except Exception as e:
            logger.exception(f"HW AXI 写入异常: {e}")
            return HardwareAxiResult(
                success=False,
                axi_name=axi_name,
                address=address,
                transaction_name=txn_name,
                value=value,
                message="HW AXI 写入失败",
                error=str(e),
            )
