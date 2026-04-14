"""
IP 配置 MCP 工具。

提供 Vivado IP 核配置相关的 MCP 工具接口。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.vivado.ip_config import (
    AXIInterconnectConfig,
    BRAMConfig,
    ClockingWizardConfig,
    FIFOConfig,
    IPInterfaceType,
    IPManager,
    MemoryType,
    ZynqPSConfig,
)
from gateflow.vivado.tcl_engine import TclEngine
from gateflow.tools.context_utils import AsyncContextBlockedProxy, project_context_error_message
from gateflow.tools.result_utils import clean_artifacts

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None
_ip_manager: IPManager | None = None


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if _engine is None:
        _engine = TclEngine()
    return _engine


def _get_ip_manager() -> IPManager:
    """获取或创建 IP 管理器实例。"""
    global _ip_manager
    if project_context_error_message("ip"):
        return AsyncContextBlockedProxy("ip")  # type: ignore[return-value]
    if _ip_manager is None:
        _ip_manager = IPManager(_get_engine())
    return _ip_manager


# ==================== 结果模型 ====================


class CreateClockingWizardResult(BaseModel):
    """创建 Clocking Wizard IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    module_name: str | None = Field(default=None, description="模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CreateFIFOResult(BaseModel):
    """创建 FIFO Generator IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    module_name: str | None = Field(default=None, description="模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CreateBRAMResult(BaseModel):
    """创建 Block Memory IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    module_name: str | None = Field(default=None, description="模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CreateAXIInterconnectResult(BaseModel):
    """创建 AXI Interconnect IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    module_name: str | None = Field(default=None, description="模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CreateZynqPSResult(BaseModel):
    """创建 Zynq Processing System IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    module_name: str | None = Field(default=None, description="模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ListIPsResult(BaseModel):
    """列出 IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ips: list[dict[str, Any]] = Field(default_factory=list, description="IP 列表")
    count: int = Field(default=0, description="IP 数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GetIPInfoResult(BaseModel):
    """获取 IP 信息结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_info: dict[str, Any] | None = Field(default=None, description="IP 详细信息")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class UpgradeIPResult(BaseModel):
    """升级 IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GenerateOutputsResult(BaseModel):
    """生成输出产品结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class RemoveIPResult(BaseModel):
    """移除 IP 结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


# ==================== 工具注册 ====================


def register_ip_tools(mcp: FastMCP) -> None:
    """
    注册 IP 配置相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def create_clocking_wizard(
        name: str,
        input_frequency: float,
        output_clocks: list[dict],
        reset_type: str = "ACTIVE_HIGH",
        use_pll: bool = False,
        locked_output: bool = True,
    ) -> CreateClockingWizardResult:
        """
        创建 Clocking Wizard IP。

        此工具用于创建时钟管理单元 IP，支持 PLL 和 MMCM 配置。
        可以生成多个不同频率、相位和占空比的输出时钟。

        Args:
            name: IP 实例名称，用于标识该 IP。
            input_frequency: 输入时钟频率，单位 MHz。
            output_clocks: 输出时钟列表，每个时钟为一个字典，格式:
                {"name": "clk_out1", "frequency": 100.0, "phase": 0.0, "duty_cycle": 0.5}
                - name: 时钟名称
                - frequency: 输出频率 (MHz)
                - phase: 相位偏移 (度)，可选，默认 0
                - duty_cycle: 占空比，可选，默认 0.5
            reset_type: 复位类型，可选值:
                - "ACTIVE_HIGH": 高电平复位 (默认)
                - "ACTIVE_LOW": 低电平复位
            use_pll: 是否使用 PLL。False 使用 MMCM (默认)，True 使用 PLL。
            locked_output: 是否输出 locked 信号，默认 True。

        Returns:
            CreateClockingWizardResult 包含创建结果。

        Example:
            创建一个 100MHz 输入，生成 50MHz 和 200MHz 两个输出时钟:
            ```
            create_clocking_wizard(
                name="clk_wiz_0",
                input_frequency=100.0,
                output_clocks=[
                    {"name": "clk_out1", "frequency": 50.0},
                    {"name": "clk_out2", "frequency": 200.0}
                ]
            )
            ```
        """
        logger.info(
            f"创建 Clocking Wizard IP: name={name}, input_freq={input_frequency}MHz, "
            f"outputs={len(output_clocks)}"
        )

        try:
            config = ClockingWizardConfig(
                name=name,
                input_frequency=input_frequency,
                output_clocks=output_clocks,
                reset_type=reset_type,
                use_pll=use_pll,
                locked_output=locked_output,
            )

            manager = _get_ip_manager()
            result = await manager.create_clocking_wizard(config)

            return CreateClockingWizardResult(
                success=result.get("success", False),
                ip_name=result.get("ip_name"),
                module_name=result.get("module_name"),
                message="Clocking Wizard IP 创建成功"
                if result.get("success")
                else "Clocking Wizard IP 创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts(
                    {
                        "ip_name": result.get("ip_name"),
                        "module_name": result.get("module_name"),
                    }
                ),
            )
        except Exception as e:
            logger.error(f"创建 Clocking Wizard IP 异常: {e}")
            return CreateClockingWizardResult(
                success=False,
                message="Clocking Wizard IP 创建异常",
                error=str(e),
            )

    @mcp.tool()
    async def create_fifo(
        name: str,
        data_width: int = 32,
        depth: int = 1024,
        interface_type: str = "Native",
        enable_data_count: bool = False,
        enable_almost_flags: bool = False,
    ) -> CreateFIFOResult:
        """
        创建 FIFO Generator IP。

        此工具用于创建 FIFO 缓冲器 IP，支持同步和异步模式，
        以及 Native、AXI4Stream、AXI4Lite 等多种接口类型。

        Args:
            name: IP 实例名称，用于标识该 IP。
            data_width: 数据宽度，单位位，默认 32。
            depth: FIFO 深度，默认 1024。
            interface_type: 接口类型，可选值:
                - "Native": 原生接口 (默认)
                - "AXI4Stream": AXI4 流接口
                - "AXI4Lite": AXI4 Lite 接口
            enable_data_count: 是否启用数据计数功能，默认 False。
            enable_almost_flags: 是否启用几乎满/空标志，默认 False。

        Returns:
            CreateFIFOResult 包含创建结果。

        Example:
            创建一个 32位宽、2048深度的 Native FIFO:
            ```
            create_fifo(
                name="fifo_0",
                data_width=32,
                depth=2048,
                interface_type="Native"
            )
            ```
        """
        logger.info(
            f"创建 FIFO IP: name={name}, data_width={data_width}, depth={depth}, "
            f"interface={interface_type}"
        )

        try:
            # 映射接口类型
            interface_map = {
                "Native": IPInterfaceType.NATIVE,
                "AXI4Stream": IPInterfaceType.AXI4_STREAM,
                "AXI4Lite": IPInterfaceType.AXI4_LITE,
            }
            interface_enum = interface_map.get(interface_type, IPInterfaceType.NATIVE)

            config = FIFOConfig(
                name=name,
                data_width=data_width,
                depth=depth,
                interface_type=interface_enum,
                enable_data_count=enable_data_count,
                enable_almost_flags=enable_almost_flags,
            )

            manager = _get_ip_manager()
            result = await manager.create_fifo(config)

            return CreateFIFOResult(
                success=result.get("success", False),
                ip_name=result.get("ip_name"),
                module_name=result.get("module_name"),
                message="FIFO IP 创建成功"
                if result.get("success")
                else "FIFO IP 创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts(
                    {
                        "ip_name": result.get("ip_name"),
                        "module_name": result.get("module_name"),
                    }
                ),
            )
        except Exception as e:
            logger.error(f"创建 FIFO IP 异常: {e}")
            return CreateFIFOResult(
                success=False,
                message="FIFO IP 创建异常",
                error=str(e),
            )

    @mcp.tool()
    async def create_bram(
        name: str,
        data_width: int = 32,
        depth: int = 1024,
        memory_type: str = "RAM",
        init_file: str | None = None,
        enable_ecc: bool = False,
    ) -> CreateBRAMResult:
        """
        创建 Block Memory IP。

        此工具用于创建块存储器 IP，支持单端口 RAM、双端口 RAM、ROM 等模式。
        可选择性地加载初始化文件 (.coe 或 .mif)。

        Args:
            name: IP 实例名称，用于标识该 IP。
            data_width: 数据宽度，单位位，默认 32。
            depth: 存储深度，默认 1024。
            memory_type: 存储器类型，可选值:
                - "RAM": 单端口 RAM (默认)
                - "ROM": 只读存储器
                - "DualPort": 双端口 RAM
                - "SimpleDualPort": 简单双端口 RAM
            init_file: 初始化文件路径 (.coe 或 .mif)，可选。
            enable_ecc: 是否启用 ECC (错误校正码)，默认 False。

        Returns:
            CreateBRAMResult 包含创建结果。

        Example:
            创建一个 32位宽、4096深度的双端口 BRAM:
            ```
            create_bram(
                name="bram_0",
                data_width=32,
                depth=4096,
                memory_type="DualPort"
            )
            ```

            创建一个带初始化文件的 ROM:
            ```
            create_bram(
                name="rom_0",
                data_width=8,
                depth=1024,
                memory_type="ROM",
                init_file="/path/to/init.coe"
            )
            ```
        """
        logger.info(
            f"创建 BRAM IP: name={name}, data_width={data_width}, depth={depth}, "
            f"type={memory_type}"
        )

        try:
            # 映射存储器类型
            memory_type_map = {
                "RAM": MemoryType.RAM,
                "ROM": MemoryType.ROM,
                "DualPort": MemoryType.DUAL_PORT,
                "SimpleDualPort": MemoryType.SIMPLE_DUAL_PORT,
            }
            memory_enum = memory_type_map.get(memory_type, MemoryType.RAM)

            config = BRAMConfig(
                name=name,
                data_width=data_width,
                depth=depth,
                memory_type=memory_enum,
                init_file=init_file,
                enable_ecc=enable_ecc,
            )

            manager = _get_ip_manager()
            result = await manager.create_bram(config)

            return CreateBRAMResult(
                success=result.get("success", False),
                ip_name=result.get("ip_name"),
                module_name=result.get("module_name"),
                message="BRAM IP 创建成功"
                if result.get("success")
                else "BRAM IP 创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts(
                    {
                        "ip_name": result.get("ip_name"),
                        "module_name": result.get("module_name"),
                    }
                ),
            )
        except Exception as e:
            logger.error(f"创建 BRAM IP 异常: {e}")
            return CreateBRAMResult(
                success=False,
                message="BRAM IP 创建异常",
                error=str(e),
            )

    @mcp.tool()
    async def create_axi_interconnect(
        name: str,
        num_mi: int = 1,
        num_si: int = 1,
        data_width: int = 32,
        enable_register_slice: bool = False,
        enable_data_fifo: bool = False,
    ) -> CreateAXIInterconnectResult:
        """
        创建 AXI Interconnect IP。

        此工具用于创建 AXI 互连 IP，支持多主多从拓扑结构。
        可配置主接口数量 (MI) 和从接口数量 (SI)。

        Args:
            name: IP 实例名称，用于标识该 IP。
            num_mi: 主接口数量，即连接的主设备数，默认 1。
            num_si: 从接口数量，即连接的从设备数，默认 1。
            data_width: 数据位宽，默认 32。
            enable_register_slice: 是否启用寄存器切片，默认 False。
            enable_data_fifo: 是否启用数据 FIFO，默认 False。

        Returns:
            CreateAXIInterconnectResult 包含创建结果。

        Example:
            创建一个 1主2从的 AXI 互连:
            ```
            create_axi_interconnect(
                name="axi_interconnect_0",
                num_mi=1,
                num_si=2,
                data_width=32
            )
            ```
        """
        logger.info(
            f"创建 AXI Interconnect IP: name={name}, num_mi={num_mi}, num_si={num_si}"
        )

        try:
            config = AXIInterconnectConfig(
                name=name,
                num_master_interfaces=num_mi,
                num_slave_interfaces=num_si,
                data_width=data_width,
                enable_register_slice=enable_register_slice,
                enable_data_fifo=enable_data_fifo,
            )

            manager = _get_ip_manager()
            result = await manager.create_axi_interconnect(config)

            return CreateAXIInterconnectResult(
                success=result.get("success", False),
                ip_name=result.get("ip_name"),
                module_name=result.get("module_name"),
                message="AXI Interconnect IP 创建成功"
                if result.get("success")
                else "AXI Interconnect IP 创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts(
                    {
                        "ip_name": result.get("ip_name"),
                        "module_name": result.get("module_name"),
                    }
                ),
            )
        except Exception as e:
            logger.error(f"创建 AXI Interconnect IP 异常: {e}")
            return CreateAXIInterconnectResult(
                success=False,
                message="AXI Interconnect IP 创建异常",
                error=str(e),
            )

    @mcp.tool()
    async def create_zynq_ps(
        name: str = "processing_system7_0",
        preset: str | None = None,
        enable_fabric_clock: bool = True,
        enable_fabric_reset: bool = True,
        enable_ddr: bool = True,
        enable_uart: bool = True,
        enable_ethernet: bool = False,
        enable_usb: bool = False,
        enable_sd: bool = False,
        enable_gpio: bool = False,
    ) -> CreateZynqPSResult:
        """
        创建 Zynq Processing System IP。

        此工具用于创建 Zynq 器件的 ARM 处理系统 IP。
        可配置各种外设的启用状态和预设开发板配置。

        Args:
            name: IP 实例名称，默认 "processing_system7_0"。
            preset: 预设开发板配置名称，如 "ZC702"、"ZedBoard" 等，可选。
            enable_fabric_clock: 是否启用 PL 时钟输出，默认 True。
            enable_fabric_reset: 是否启用 PL 复位输出，默认 True。
            enable_ddr: 是否启用 DDR 控制器，默认 True。
            enable_uart: 是否启用 UART，默认 True。
            enable_ethernet: 是否启用以太网，默认 False。
            enable_usb: 是否启用 USB，默认 False。
            enable_sd: 是否启用 SD 卡接口，默认 False。
            enable_gpio: 是否启用 GPIO，默认 False。

        Returns:
            CreateZynqPSResult 包含创建结果。

        Example:
            创建一个基本配置的 Zynq PS:
            ```
            create_zynq_ps(
                name="processing_system7_0",
                enable_uart=True,
                enable_ethernet=True
            )
            ```

            使用预设配置创建 Zynq PS:
            ```
            create_zynq_ps(
                preset="ZedBoard"
            )
            ```
        """
        logger.info(f"创建 Zynq PS IP: name={name}, preset={preset}")

        try:
            config = ZynqPSConfig(
                name=name,
                preset=preset,
                enable_fabric_clock=enable_fabric_clock,
                enable_fabric_reset=enable_fabric_reset,
                enable_ddr=enable_ddr,
                enable_uart=enable_uart,
                enable_ethernet=enable_ethernet,
                enable_usb=enable_usb,
                enable_sd=enable_sd,
                enable_gpio=enable_gpio,
            )

            manager = _get_ip_manager()
            result = await manager.create_zynq_ps(config)

            return CreateZynqPSResult(
                success=result.get("success", False),
                ip_name=result.get("ip_name"),
                module_name=result.get("module_name"),
                message="Zynq PS IP 创建成功"
                if result.get("success")
                else "Zynq PS IP 创建失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts(
                    {
                        "ip_name": result.get("ip_name"),
                        "module_name": result.get("module_name"),
                    }
                ),
            )
        except Exception as e:
            logger.error(f"创建 Zynq PS IP 异常: {e}")
            return CreateZynqPSResult(
                success=False,
                message="Zynq PS IP 创建异常",
                error=str(e),
            )

    @mcp.tool()
    async def list_ips() -> ListIPsResult:
        """
        列出项目中的所有 IP。

        此工具返回当前项目中所有已创建 IP 的列表，
        包括每个 IP 的名称和模块名称。

        Returns:
            ListIPsResult 包含 IP 列表和数量。

        Example:
            列出所有 IP:
            ```
            result = list_ips()
            for ip in result.ips:
                print(f"IP: {ip['name']}")
            ```
        """
        logger.info("列出所有 IP")

        try:
            manager = _get_ip_manager()
            ips = await manager.list_ips()

            return ListIPsResult(
                success=True,
                ips=ips,
                count=len(ips),
                message=f"找到 {len(ips)} 个 IP",
                error=None,
                artifacts={"count": len(ips)},
            )
        except Exception as e:
            logger.error(f"列出 IP 异常: {e}")
            return ListIPsResult(
                success=False,
                ips=[],
                count=0,
                message="列出 IP 失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_ip_info(ip_name: str) -> GetIPInfoResult:
        """
        获取 IP 详细信息。

        此工具返回指定 IP 的详细信息，包括名称、VLNV、版本等。

        Args:
            ip_name: IP 名称或模块名称。

        Returns:
            GetIPInfoResult 包含 IP 详细信息。

        Example:
            获取 IP 信息:
            ```
            result = get_ip_info("clk_wiz_0")
            print(result.ip_info)
            ```
        """
        logger.info(f"获取 IP 信息: {ip_name}")

        try:
            manager = _get_ip_manager()
            info = await manager.get_ip_info(ip_name)

            return GetIPInfoResult(
                success=info.get("exists", False),
                ip_info=info,
                message="获取 IP 信息成功" if info.get("exists") else "IP 不存在",
                error=info.get("errors")[0] if info.get("errors") else None,
                artifacts=clean_artifacts({"ip_name": info.get("name") or ip_name}),
            )
        except Exception as e:
            logger.error(f"获取 IP 信息异常: {e}")
            return GetIPInfoResult(
                success=False,
                ip_info=None,
                message="获取 IP 信息失败",
                error=str(e),
            )

    @mcp.tool()
    async def upgrade_ip(ip_name: str) -> UpgradeIPResult:
        """
        升级 IP 到最新版本。

        此工具将指定的 IP 升级到当前 Vivado 版本支持的最新版本。
        当项目在不同版本的 Vivado 之间迁移时，可能需要升级 IP。

        Args:
            ip_name: IP 名称或模块名称。

        Returns:
            UpgradeIPResult 包含升级结果。

        Example:
            升级 IP:
            ```
            result = upgrade_ip("clk_wiz_0")
            ```
        """
        logger.info(f"升级 IP: {ip_name}")

        try:
            manager = _get_ip_manager()
            result = await manager.upgrade_ip(ip_name)

            return UpgradeIPResult(
                success=result.get("success", False),
                ip_name=ip_name,
                message=f"IP {ip_name} 升级成功"
                if result.get("success")
                else f"IP {ip_name} 升级失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"ip_name": ip_name}),
            )
        except Exception as e:
            logger.error(f"升级 IP 异常: {e}")
            return UpgradeIPResult(
                success=False,
                ip_name=ip_name,
                message="升级 IP 异常",
                error=str(e),
            )

    @mcp.tool()
    async def generate_ip_outputs(ip_name: str, force: bool = False) -> GenerateOutputsResult:
        """
        生成 IP 输出产品。

        此工具生成 IP 的输出文件，包括实例化模板、综合文件、仿真文件等。
        创建 IP 后需要调用此工具才能在设计中使用该 IP。

        Args:
            ip_name: IP 名称或模块名称。
            force: 是否强制重新生成，默认 False。
                如果为 True，将覆盖已存在的输出文件。

        Returns:
            GenerateOutputsResult 包含生成结果。

        Example:
            生成 IP 输出:
            ```
            result = generate_ip_outputs("clk_wiz_0")
            ```

            强制重新生成:
            ```
            result = generate_ip_outputs("clk_wiz_0", force=True)
            ```
        """
        logger.info(f"生成 IP 输出: {ip_name}, force={force}")

        try:
            manager = _get_ip_manager()
            result = await manager.generate_output_products(ip_name, force)

            return GenerateOutputsResult(
                success=result.get("success", False),
                ip_name=ip_name,
                message=f"IP {ip_name} 输出产品生成成功"
                if result.get("success")
                else f"IP {ip_name} 输出产品生成失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"ip_name": ip_name}),
            )
        except Exception as e:
            logger.error(f"生成 IP 输出异常: {e}")
            return GenerateOutputsResult(
                success=False,
                ip_name=ip_name,
                message="生成 IP 输出异常",
                error=str(e),
            )

    @mcp.tool()
    async def remove_ip(ip_name: str) -> RemoveIPResult:
        """
        移除 IP。

        此工具从当前项目中删除指定的 IP。
        注意：此操作不可逆，IP 及其输出文件将被删除。

        Args:
            ip_name: IP 名称或模块名称。

        Returns:
            RemoveIPResult 包含移除结果。

        Example:
            移除 IP:
            ```
            result = remove_ip("clk_wiz_0")
            ```
        """
        logger.info(f"移除 IP: {ip_name}")

        try:
            manager = _get_ip_manager()
            result = await manager.remove_ip(ip_name)

            return RemoveIPResult(
                success=result.get("success", False),
                ip_name=ip_name,
                message=f"IP {ip_name} 移除成功"
                if result.get("success")
                else f"IP {ip_name} 移除失败",
                error=result.get("errors")[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"ip_name": ip_name}),
            )
        except Exception as e:
            logger.error(f"移除 IP 异常: {e}")
            return RemoveIPResult(
                success=False,
                ip_name=ip_name,
                message="移除 IP 异常",
                error=str(e),
            )
