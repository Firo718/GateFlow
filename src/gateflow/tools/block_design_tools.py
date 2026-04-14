"""
Block Design MCP 工具。

提供 Vivado Block Design 相关的 MCP 工具接口。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.vivado.block_design import (
    BDIPInstance,
    BDPort,
    BlockDesignManager,
    BlockDesignTclGenerator,
)
from gateflow.vivado.tcl_engine import TclEngine
from gateflow.tools.context_utils import AsyncContextBlockedProxy, project_context_error_message
from gateflow.tools.result_utils import clean_artifacts

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None
_bd_manager: BlockDesignManager | None = None


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if _engine is None:
        _engine = TclEngine()
    return _engine


def _get_bd_manager() -> BlockDesignManager:
    """获取或创建 Block Design 管理器实例。"""
    global _bd_manager
    if project_context_error_message("block_design"):
        return AsyncContextBlockedProxy("block_design")  # type: ignore[return-value]
    if _bd_manager is None:
        _bd_manager = BlockDesignManager(_get_engine())
    return _bd_manager


# ==================== 结果模型 ====================


class CreateBDDesignResult(BaseModel):
    """创建 Block Design 结果模型。"""

    success: bool = Field(description="操作是否成功")
    design_name: str | None = Field(default=None, description="Block Design 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class OpenBDDesignResult(BaseModel):
    """打开 Block Design 结果模型。"""

    success: bool = Field(description="操作是否成功")
    design_name: str | None = Field(default=None, description="Block Design 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class AddBDIPResult(BaseModel):
    """添加 Block Design IP 实例结果模型。"""

    success: bool = Field(description="操作是否成功")
    instance_name: str | None = Field(default=None, description="实例名称")
    ip_type: str | None = Field(default=None, description="IP 类型")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CreateBDPortResult(BaseModel):
    """创建 Block Design 端口结果模型。"""

    success: bool = Field(description="操作是否成功")
    port_name: str | None = Field(default=None, description="端口名称")
    direction: str | None = Field(default=None, description="端口方向")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ConnectBDPortsResult(BaseModel):
    """连接 Block Design 端口结果模型。"""

    success: bool = Field(description="操作是否成功")
    source: str | None = Field(default=None, description="源端口")
    destination: str | None = Field(default=None, description="目标端口")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ApplyAutomationResult(BaseModel):
    """应用自动连接结果模型。"""

    success: bool = Field(description="操作是否成功")
    rule: str | None = Field(default=None, description="自动连接规则")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ValidateBDDesignResult(BaseModel):
    """验证 Block Design 结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GenerateWrapperResult(BaseModel):
    """生成 HDL Wrapper 结果模型。"""

    success: bool = Field(description="操作是否成功")
    wrapper_name: str | None = Field(default=None, description="Wrapper 名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GetBDCellsResult(BaseModel):
    """获取 Block Design IP 实例列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    cells: list[dict[str, Any]] = Field(default_factory=list, description="IP 实例列表")
    cell_count: int = Field(default=0, description="IP 实例数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class RemoveBDCellResult(BaseModel):
    """移除 IP 实例结果模型。"""

    success: bool = Field(description="操作是否成功")
    instance_name: str | None = Field(default=None, description="实例名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class SaveBDDesignResult(BaseModel):
    """保存 Block Design 结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class CloseBDDesignResult(BaseModel):
    """关闭 Block Design 结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GetBDPortsResult(BaseModel):
    """获取 Block Design 端口列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    ports: list[dict[str, Any]] = Field(default_factory=list, description="端口列表")
    port_count: int = Field(default=0, description="端口数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class GetBDConnectionsResult(BaseModel):
    """获取 Block Design 连接列表结果模型。"""

    success: bool = Field(description="操作是否成功")
    connections: list[dict[str, Any]] = Field(default_factory=list, description="连接列表")
    connection_count: int = Field(default=0, description="连接数量")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


# ==================== 工具注册 ====================


def register_block_design_tools(mcp: FastMCP) -> None:
    """
    注册 Block Design 相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def create_bd_design(name: str) -> CreateBDDesignResult:
        """
        创建新的 Block Design。

        此工具用于创建一个新的 Vivado Block Design。Block Design 是 Vivado 中
        用于图形化设计 IP 集成的主要方式。

        Args:
            name: Block Design 名称，建议使用有意义的名称如 "system"、"design_1" 等。

        Returns:
            CreateBDDesignResult 包含创建结果。

        Example:
            创建名为 "system" 的 Block Design:
            ```
            result = create_bd_design(name="system")
            if result.success:
                print(f"Block Design '{result.design_name}' 创建成功")
            ```
        """
        logger.info(f"创建 Block Design: name={name}")

        try:
            manager = _get_bd_manager()
            result = await manager.create_design(name)

            return CreateBDDesignResult(
                success=result.get("success", False),
                design_name=name if result.get("success") else None,
                message=result.get("success") and "Block Design 创建成功" or "Block Design 创建失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"design_name": name if result.get("success") else None}),
            )

        except Exception as e:
            logger.error(f"创建 Block Design 失败: {e}")
            return CreateBDDesignResult(
                success=False,
                design_name=None,
                message="Block Design 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def open_bd_design(name: str) -> OpenBDDesignResult:
        """
        打开现有的 Block Design。

        此工具用于打开一个已存在的 Block Design 进行编辑。

        Args:
            name: Block Design 名称。

        Returns:
            OpenBDDesignResult 包含打开结果。

        Example:
            打开名为 "system" 的 Block Design:
            ```
            result = open_bd_design(name="system")
            if result.success:
                print(f"Block Design '{result.design_name}' 打开成功")
            ```
        """
        logger.info(f"打开 Block Design: name={name}")

        try:
            manager = _get_bd_manager()
            result = await manager.open_design(name)

            return OpenBDDesignResult(
                success=result.get("success", False),
                design_name=name if result.get("success") else None,
                message=result.get("success") and "Block Design 打开成功" or "Block Design 打开失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"design_name": name if result.get("success") else None}),
            )

        except Exception as e:
            logger.error(f"打开 Block Design 失败: {e}")
            return OpenBDDesignResult(
                success=False,
                design_name=None,
                message="Block Design 打开失败",
                error=str(e),
            )

    @mcp.tool()
    async def close_bd_design() -> CloseBDDesignResult:
        """
        关闭当前 Block Design。

        此工具用于关闭当前打开的 Block Design。

        Returns:
            CloseBDDesignResult 包含关闭结果。

        Example:
            关闭当前 Block Design:
            ```
            result = close_bd_design()
            if result.success:
                print("Block Design 已关闭")
            ```
        """
        logger.info("关闭 Block Design")

        try:
            manager = _get_bd_manager()
            result = await manager.close_design()

            return CloseBDDesignResult(
                success=result.get("success", False),
                message=result.get("success") and "Block Design 已关闭" or "Block Design 关闭失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts={},
            )

        except Exception as e:
            logger.error(f"关闭 Block Design 失败: {e}")
            return CloseBDDesignResult(
                success=False,
                message="Block Design 关闭失败",
                error=str(e),
            )

    @mcp.tool()
    async def save_bd_design() -> SaveBDDesignResult:
        """
        保存当前 Block Design。

        此工具用于保存当前打开的 Block Design。

        Returns:
            SaveBDDesignResult 包含保存结果。

        Example:
            保存当前 Block Design:
            ```
            result = save_bd_design()
            if result.success:
                print("Block Design 已保存")
            ```
        """
        logger.info("保存 Block Design")

        try:
            manager = _get_bd_manager()
            result = await manager.save_design()

            return SaveBDDesignResult(
                success=result.get("success", False),
                message=result.get("success") and "Block Design 保存成功" or "Block Design 保存失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts={},
            )

        except Exception as e:
            logger.error(f"保存 Block Design 失败: {e}")
            return SaveBDDesignResult(
                success=False,
                message="Block Design 保存失败",
                error=str(e),
            )

    @mcp.tool()
    async def add_bd_ip(
        ip_type: str,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> AddBDIPResult:
        """
        向 Block Design 添加 IP 实例。

        此工具将指定的 IP 核添加到当前 Block Design 中。支持所有 Vivado IP 核。

        Args:
            ip_type: IP 类型，格式为 "vendor:library:name:version"，
                例如 "xilinx.com:ip:axi_gpio:2.0.0"。
            instance_name: 实例名称，用于在 Block Design 中标识此 IP 实例。
            config: IP 配置属性字典，可选。键为属性名，值为属性值。

        Returns:
            AddBDIPResult 包含添加结果。

        Example:
            添加 AXI GPIO IP:
            ```
            result = add_bd_ip(
                ip_type="xilinx.com:ip:axi_gpio:2.0.0",
                instance_name="axi_gpio_0",
                config={"CONFIG.C_GPIO_WIDTH": "8"}
            )
            ```

            添加 AXI Interconnect:
            ```
            result = add_bd_ip(
                ip_type="xilinx.com:ip:axi_interconnect:2.1.0",
                instance_name="axi_interconnect_0",
                config={"CONFIG.NUM_MI": "2"}
            )
            ```
        """
        logger.info(f"添加 IP 实例: ip_type={ip_type}, instance_name={instance_name}")

        try:
            manager = _get_bd_manager()

            # 创建 IP 实例配置
            instance = BDIPInstance(
                name=instance_name,
                ip_type=ip_type,
                config=config or {},
            )

            result = await manager.add_ip_instance(instance)

            return AddBDIPResult(
                success=result.get("success", False),
                instance_name=instance_name if result.get("success") else None,
                ip_type=ip_type if result.get("success") else None,
                message=result.get("success") and f"IP 实例 '{instance_name}' 添加成功" or "IP 实例添加失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"instance_name": instance_name, "ip_type": ip_type}),
            )

        except Exception as e:
            logger.error(f"添加 IP 实例失败: {e}")
            return AddBDIPResult(
                success=False,
                instance_name=None,
                ip_type=None,
                message="IP 实例添加失败",
                error=str(e),
            )

    @mcp.tool()
    async def create_bd_port(
        name: str,
        direction: str,
        interface_type: str | None = None,
        width: int = 1,
    ) -> CreateBDPortResult:
        """
        创建 Block Design 外部端口。

        此工具用于创建 Block Design 的外部端口，用于与顶层模块或其他模块连接。

        Args:
            name: 端口名称。
            direction: 端口方向，可选值:
                - "input": 输入端口
                - "output": 输出端口
                - "inout": 双向端口
            interface_type: 接口类型，可选。支持的类型:
                - "axi4lite": AXI4-Lite 接口
                - "axi4mm": AXI4 内存映射接口
                - "axi4stream": AXI4-Stream 接口
                - "clock": 时钟接口
                - "reset": 复位接口
                - "interrupt": 中断接口
                - "gpio": GPIO 接口
            width: 端口位宽，默认为 1。仅对非接口端口有效。

        Returns:
            CreateBDPortResult 包含创建结果。

        Example:
            创建简单输入端口:
            ```
            result = create_bd_port(name="clk", direction="input")
            ```

            创建多位输出端口:
            ```
            result = create_bd_port(name="led", direction="output", width=8)
            ```

            创建 AXI4-Lite 接口端口:
            ```
            result = create_bd_port(
                name="s_axi",
                direction="input",
                interface_type="axi4lite"
            )
            ```
        """
        logger.info(f"创建端口: name={name}, direction={direction}, interface_type={interface_type}")

        try:
            manager = _get_bd_manager()

            # 创建端口配置
            port = BDPort(
                name=name,
                direction=direction,
                width=width,
            )

            result = await manager.create_external_port(port)

            return CreateBDPortResult(
                success=result.get("success", False),
                port_name=name if result.get("success") else None,
                direction=direction if result.get("success") else None,
                message=result.get("success") and f"端口 '{name}' 创建成功" or "端口创建失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"port_name": name, "direction": direction}),
            )

        except Exception as e:
            logger.error(f"创建端口失败: {e}")
            return CreateBDPortResult(
                success=False,
                port_name=None,
                direction=None,
                message="端口创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def connect_bd_ports(
        source: str,
        destination: str,
        is_interface: bool = False,
    ) -> ConnectBDPortsResult:
        """
        连接 Block Design 端口。

        此工具用于连接 Block Design 中的两个端口。支持普通端口连接和接口端口连接。

        Args:
            source: 源端口，格式为 "instance_name/port_name"。
                对于外部端口，使用 "external/port_name" 格式。
            destination: 目标端口，格式同 source。
            is_interface: 是否为接口连接，默认为 False。
                对于 AXI、时钟、复位等接口，应设置为 True。

        Returns:
            ConnectBDPortsResult 包含连接结果。

        Example:
            连接普通端口:
            ```
            result = connect_bd_ports(
                source="clk_wiz_0/clk_out1",
                destination="axi_gpio_0/s_axi_aclk"
            )
            ```

            连接外部端口到实例端口:
            ```
            result = connect_bd_ports(
                source="external/clk",
                destination="clk_wiz_0/clk_in1"
            )
            ```

            连接 AXI 接口:
            ```
            result = connect_bd_ports(
                source="axi_interconnect_0/M00_AXI",
                destination="axi_gpio_0/S_AXI",
                is_interface=True
            )
            ```
        """
        logger.info(f"连接端口: {source} -> {destination}")

        try:
            manager = _get_bd_manager()
            result = await manager.connect_ports(source, destination, is_interface=is_interface)

            return ConnectBDPortsResult(
                success=result.get("success", False),
                source=source if result.get("success") else None,
                destination=destination if result.get("success") else None,
                message=result.get("success") and f"端口连接成功: {source} -> {destination}" or "端口连接失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"source": source, "destination": destination}),
            )

        except Exception as e:
            logger.error(f"连接端口失败: {e}")
            return ConnectBDPortsResult(
                success=False,
                source=None,
                destination=None,
                message="端口连接失败",
                error=str(e),
            )

    @mcp.tool()
    async def apply_bd_automation(rule: str = "all") -> ApplyAutomationResult:
        """
        应用 Block Design 自动连接。

        此工具使用 Vivado 的自动化功能自动连接 Block Design 中的 IP。
        可以自动连接时钟、复位、AXI 总线等。

        Args:
            rule: 自动连接规则，可选值:
                - "all": 应用所有自动连接规则（推荐）
                - "axi": 仅自动连接 AXI 总线
                - "clock": 仅自动连接时钟
                - "reset": 仅自动连接复位
                - "interrupt": 仅自动连接中断

        Returns:
            ApplyAutomationResult 包含自动连接结果。

        Example:
            应用所有自动连接:
            ```
            result = apply_bd_automation(rule="all")
            if result.success:
                print("自动连接应用成功")
            ```

            仅自动连接 AXI 总线:
            ```
            result = apply_bd_automation(rule="axi")
            ```
        """
        logger.info(f"应用自动连接: rule={rule}")

        try:
            manager = _get_bd_manager()
            result = await manager.apply_automation(rule)

            return ApplyAutomationResult(
                success=result.get("success", False),
                rule=rule if result.get("success") else None,
                message=result.get("success") and f"自动连接 '{rule}' 应用成功" or "自动连接应用失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"rule": rule if result.get("success") else None}),
            )

        except Exception as e:
            logger.error(f"应用自动连接失败: {e}")
            return ApplyAutomationResult(
                success=False,
                rule=None,
                message="自动连接应用失败",
                error=str(e),
            )

    @mcp.tool()
    async def validate_bd_design() -> ValidateBDDesignResult:
        """
        验证 Block Design。

        此工具验证当前 Block Design 的完整性和正确性。
        验证通过后才能生成 HDL Wrapper。

        Returns:
            ValidateBDDesignResult 包含验证结果。

        Example:
            验证 Block Design:
            ```
            result = validate_bd_design()
            if result.success:
                print("Block Design 验证通过")
            else:
                print(f"验证失败: {result.error}")
                for warning in result.warnings:
                    print(f"警告: {warning}")
            ```
        """
        logger.info("验证 Block Design")

        try:
            manager = _get_bd_manager()
            result = await manager.validate_design()

            return ValidateBDDesignResult(
                success=result.get("success", False),
                message=result.get("success") and "Block Design 验证通过" or "Block Design 验证失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                warnings=result.get("warnings", []),
                artifacts={},
            )

        except Exception as e:
            logger.error(f"验证 Block Design 失败: {e}")
            return ValidateBDDesignResult(
                success=False,
                message="Block Design 验证失败",
                error=str(e),
                warnings=[],
            )

    @mcp.tool()
    async def generate_bd_wrapper() -> GenerateWrapperResult:
        """
        生成 Block Design HDL Wrapper。

        此工具为当前 Block Design 生成 HDL Wrapper 文件。
        Wrapper 是 Block Design 与顶层模块之间的接口。

        注意: 生成 Wrapper 前需要先验证 Block Design。

        Returns:
            GenerateWrapperResult 包含生成结果。

        Example:
            生成 HDL Wrapper:
            ```
            # 先验证
            validate_result = validate_bd_design()
            if validate_result.success:
                # 再生成 Wrapper
                result = generate_bd_wrapper()
                if result.success:
                    print(f"Wrapper '{result.wrapper_name}' 生成成功")
            ```
        """
        logger.info("生成 HDL Wrapper")

        try:
            manager = _get_bd_manager()
            result = await manager.generate_wrapper()

            # 获取 wrapper 名称
            wrapper_name = None
            if result.get("success") and manager.current_design:
                wrapper_name = f"{manager.current_design.name}_wrapper"

            return GenerateWrapperResult(
                success=result.get("success", False),
                wrapper_name=wrapper_name,
                message=result.get("success") and "HDL Wrapper 生成成功" or "HDL Wrapper 生成失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"wrapper_name": wrapper_name}),
            )

        except Exception as e:
            logger.error(f"生成 HDL Wrapper 失败: {e}")
            return GenerateWrapperResult(
                success=False,
                wrapper_name=None,
                message="HDL Wrapper 生成失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_bd_cells() -> GetBDCellsResult:
        """
        获取 Block Design 中的所有 IP 实例。

        此工具返回当前 Block Design 中所有 IP 实例的列表，
        包括实例名称、IP 类型等信息。

        Returns:
            GetBDCellsResult 包含 IP 实例列表。

        Example:
            获取所有 IP 实例:
            ```
            result = get_bd_cells()
            if result.success:
                print(f"共有 {result.cell_count} 个 IP 实例")
                for cell in result.cells:
                    print(f"实例: {cell['name']}")
            ```
        """
        logger.info("获取 IP 实例列表")

        try:
            manager = _get_bd_manager()
            cells = await manager.get_cells()

            return GetBDCellsResult(
                success=True,
                cells=cells,
                cell_count=len(cells),
                message=f"找到 {len(cells)} 个 IP 实例",
                error=None,
                artifacts={"count": len(cells)},
            )

        except Exception as e:
            logger.error(f"获取 IP 实例列表失败: {e}")
            return GetBDCellsResult(
                success=False,
                cells=[],
                cell_count=0,
                message="获取 IP 实例列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def remove_bd_cell(instance_name: str) -> RemoveBDCellResult:
        """
        移除 Block Design 中的 IP 实例。

        此工具从当前 Block Design 中删除指定的 IP 实例。
        删除实例会同时删除相关的连接。

        Args:
            instance_name: 要移除的 IP 实例名称。

        Returns:
            RemoveBDCellResult 包含移除结果。

        Example:
            移除 IP 实例:
            ```
            result = remove_bd_cell(instance_name="axi_gpio_0")
            if result.success:
                print(f"实例 '{result.instance_name}' 已移除")
            ```
        """
        logger.info(f"移除 IP 实例: instance_name={instance_name}")

        try:
            manager = _get_bd_manager()
            result = await manager.remove_ip_instance(instance_name)

            return RemoveBDCellResult(
                success=result.get("success", False),
                instance_name=instance_name if result.get("success") else None,
                message=result.get("success") and f"IP 实例 '{instance_name}' 移除成功" or "IP 实例移除失败",
                error=result.get("errors", [None])[0] if result.get("errors") else None,
                artifacts=clean_artifacts({"instance_name": instance_name if result.get("success") else None}),
            )

        except Exception as e:
            logger.error(f"移除 IP 实例失败: {e}")
            return RemoveBDCellResult(
                success=False,
                instance_name=None,
                message="IP 实例移除失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_bd_ports() -> GetBDPortsResult:
        """
        获取 Block Design 中的所有端口。

        此工具返回当前 Block Design 中所有外部端口的列表。

        Returns:
            GetBDPortsResult 包含端口列表。

        Example:
            获取所有端口:
            ```
            result = get_bd_ports()
            if result.success:
                print(f"共有 {result.port_count} 个端口")
                for port in result.ports:
                    print(f"端口: {port['name']}, 方向: {port['direction']}")
            ```
        """
        logger.info("获取端口列表")

        try:
            engine = _get_engine()

            # 获取普通端口
            ports_result = await engine.execute_async("get_bd_ports")
            ports = []
            if ports_result.success:
                for line in ports_result.output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ports.append({'name': line, 'type': 'port'})

            # 获取接口端口
            intf_ports_result = await engine.execute_async("get_bd_intf_ports")
            if intf_ports_result.success:
                for line in intf_ports_result.output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        ports.append({'name': line, 'type': 'interface'})

            return GetBDPortsResult(
                success=True,
                ports=ports,
                port_count=len(ports),
                message=f"找到 {len(ports)} 个端口",
                error=None,
                artifacts={"count": len(ports)},
            )

        except Exception as e:
            logger.error(f"获取端口列表失败: {e}")
            return GetBDPortsResult(
                success=False,
                ports=[],
                port_count=0,
                message="获取端口列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def get_bd_connections() -> GetBDConnectionsResult:
        """
        获取 Block Design 中的所有连接。

        此工具返回当前 Block Design 中所有连接的列表，
        包括普通网络连接和接口连接。

        Returns:
            GetBDConnectionsResult 包含连接列表。

        Example:
            获取所有连接:
            ```
            result = get_bd_connections()
            if result.success:
                print(f"共有 {result.connection_count} 个连接")
                for conn in result.connections:
                    print(f"连接: {conn['name']}, 类型: {conn['type']}")
            ```
        """
        logger.info("获取连接列表")

        try:
            manager = _get_bd_manager()
            connections = await manager.get_connections()

            return GetBDConnectionsResult(
                success=True,
                connections=connections,
                connection_count=len(connections),
                message=f"找到 {len(connections)} 个连接",
                error=None,
                artifacts={"count": len(connections)},
            )

        except Exception as e:
            logger.error(f"获取连接列表失败: {e}")
            return GetBDConnectionsResult(
                success=False,
                connections=[],
                connection_count=0,
                message="获取连接列表失败",
                error=str(e),
            )

    @mcp.tool()
    async def set_bd_cell_property(
        cell_name: str,
        properties: dict[str, Any],
    ) -> AddBDIPResult:
        """
        设置 Block Design IP 实例的属性。

        此工具用于配置已添加的 IP 实例的属性。

        Args:
            cell_name: IP 实例名称。
            properties: 属性字典，键为属性名，值为属性值。

        Returns:
            AddBDIPResult 包含设置结果。

        Example:
            设置 AXI GPIO 属性:
            ```
            result = set_bd_cell_property(
                cell_name="axi_gpio_0",
                properties={
                    "CONFIG.C_GPIO_WIDTH": "16",
                    "CONFIG.C_IS_DUAL": "1"
                }
            )
            ```
        """
        logger.info(f"设置 IP 属性: cell_name={cell_name}")

        try:
            engine = _get_engine()

            # 生成设置属性的 Tcl 命令
            tcl_cmd = BlockDesignTclGenerator.set_bd_property_tcl(cell_name, properties)
            result = await engine.execute_async(tcl_cmd)

            return AddBDIPResult(
                success=result.success,
                instance_name=cell_name if result.success else None,
                ip_type=None,
                message=result.success and f"IP 属性设置成功" or "IP 属性设置失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"设置 IP 属性失败: {e}")
            return AddBDIPResult(
                success=False,
                instance_name=None,
                ip_type=None,
                message="IP 属性设置失败",
                error=str(e),
            )
