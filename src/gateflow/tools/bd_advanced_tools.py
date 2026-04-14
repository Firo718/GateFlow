"""
高级 Block Design MCP 工具。

提供细粒度的 Block Design 操作，包括 PS7 配置、IP 创建、连接管理等。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.vivado.block_design import BlockDesignManager, BlockDesignTclGenerator
from gateflow.vivado.tcl_engine import TclEngine

logger = logging.getLogger(__name__)

# 全局状态管理
_engine: TclEngine | None = None


def _get_engine() -> TclEngine:
    """获取或创建 Tcl 引擎实例。"""
    global _engine
    if _engine is None:
        _engine = TclEngine()
    return _engine


# ==================== 结果模型 ====================


class BDResult(BaseModel):
    """通用 Block Design 操作结果模型。"""

    success: bool = Field(description="操作是否成功")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    data: dict[str, Any] | None = Field(default=None, description="返回数据")


class PS7PresetResult(BaseModel):
    """PS7 预设配置结果模型。"""

    success: bool = Field(description="操作是否成功")
    presets: list[dict[str, str]] = Field(default_factory=list, description="预设配置列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class IPPropertiesResult(BaseModel):
    """IP 属性结果模型。"""

    success: bool = Field(description="操作是否成功")
    ip_name: str | None = Field(default=None, description="IP 名称")
    properties: dict[str, Any] = Field(default_factory=dict, description="属性字典")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class AddressMapResult(BaseModel):
    """地址映射结果模型。"""

    success: bool = Field(description="操作是否成功")
    address_map: list[dict[str, Any]] = Field(default_factory=list, description="地址映射列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class OutputStatusResult(BaseModel):
    """输出状态结果模型。"""

    success: bool = Field(description="操作是否成功")
    needs_update: bool = Field(default=False, description="是否需要更新")
    products: list[dict[str, Any]] = Field(default_factory=list, description="输出产品列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


# ==================== PS7 相关工具 ====================

# PS7 预设配置列表（常见开发板）
_PS7_PRESETS = [
    {"name": "ZC702", "description": "Xilinx ZC702 评估板 (Zynq-7020)"},
    {"name": "ZC706", "description": "Xilinx ZC706 评估板 (Zynq-7045)"},
    {"name": "ZedBoard", "description": "Digilent ZedBoard (Zynq-7020)"},
    {"name": "MicroZed", "description": "Avnet MicroZed (Zynq-7010/7020)"},
    {"name": "PicoZed", "description": "Avnet PicoZed (Zynq-7010/7020/7030/7035)"},
    {"name": "Zybo", "description": "Digilent Zybo (Zynq-7010)"},
    {"name": "Zybo-Z7", "description": "Digilent Zybo Z7 (Zynq-7010/7020)"},
    {"name": "Coraz7", "description": "Digilent Cora Z7 (Zynq-7010)"},
    {"name": "RedPitaya", "description": "Red Pitaya (Zynq-7010)"},
    {"name": "SNPS", "description": "Synopsys ARC 评估板"},
    {"name": "Custom", "description": "自定义配置"},
]


def register_bd_advanced_tools(mcp: FastMCP) -> None:
    """注册高级 Block Design 工具"""

    # ==================== PS7 相关工具 ====================

    @mcp.tool()
    async def bd_list_ps7_presets() -> PS7PresetResult:
        """
        列出所有可用的 Zynq PS7 预设配置。

        返回常见开发板的预设配置列表，可用于快速配置 PS7。

        Returns:
            PS7PresetResult 包含预设配置列表。

        Example:
            ```
            result = bd_list_ps7_presets()
            for preset in result.presets:
                print(f"{preset['name']}: {preset['description']}")
            ```
        """
        logger.info("列出 PS7 预设配置")

        return PS7PresetResult(
            success=True,
            presets=_PS7_PRESETS,
            message=f"找到 {len(_PS7_PRESETS)} 个预设配置",
            error=None,
        )

    @mcp.tool()
    async def bd_create_ps7(
        name: str = "ps7_0",
        preset: str | None = None,
    ) -> BDResult:
        """
        创建 Zynq PS7 IP 实例。

        创建 Processing System7 IP，可选择应用预设配置。

        Args:
            name: 实例名称，默认 "ps7_0"。
            preset: 预设配置名称（可选），如 "ZC702"、"ZedBoard" 等。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建默认 PS7:
            ```
            result = bd_create_ps7()
            ```

            创建带预设的 PS7:
            ```
            result = bd_create_ps7(name="ps7_0", preset="ZedBoard")
            ```
        """
        logger.info(f"创建 PS7: name={name}, preset={preset}")

        try:
            engine = _get_engine()

            # 创建 PS7 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 {name}']

            # 应用预设
            if preset and preset != "Custom":
                commands.append(
                    f'set_property -dict [list CONFIG.preset {{preset_{preset}}}] [get_bd_cells {name}]'
                )

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"PS7 '{name}' 创建成功" or "PS7 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "preset": preset} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 PS7 失败: {e}")
            return BDResult(
                success=False,
                message="PS7 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_ps7_set_fclk(
        fclk_id: int,
        frequency: float,
        enable: bool = True,
    ) -> BDResult:
        """
        设置 PS7 的 Fabric 时钟。

        配置 PS7 的 FCLK (Fabric Clock) 输出。

        Args:
            fclk_id: 时钟 ID，范围 0-3，对应 FCLK_CLK0 到 FCLK_CLK3。
            frequency: 频率 (MHz)，范围 10-250。
            enable: 是否启用该时钟，默认 True。

        Returns:
            BDResult 包含设置结果。

        Example:
            设置 FCLK0 为 100MHz:
            ```
            result = bd_ps7_set_fclk(fclk_id=0, frequency=100.0)
            ```

            禁用 FCLK1:
            ```
            result = bd_ps7_set_fclk(fclk_id=1, frequency=0, enable=False)
            ```
        """
        logger.info(f"设置 PS7 FCLK: id={fclk_id}, freq={frequency}, enable={enable}")

        if fclk_id not in range(4):
            return BDResult(
                success=False,
                message="FCLK ID 无效",
                error=f"fclk_id 必须在 0-3 范围内，当前值: {fclk_id}",
            )

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            # 构建配置属性
            props = {}

            if enable:
                props[f'CONFIG.PCW_FPGA{fclk_id}_PERIPHERAL_FREQMHZ'] = str(frequency)
                props[f'CONFIG.PCW_FPGA_FCLK{fclk_id}_ENABLE'] = '1'
                # 启用对应的 AXI GP 接口（如果需要）
                if fclk_id == 0:
                    props['CONFIG.PCW_USE_M_AXI_GP0'] = '1'
                elif fclk_id == 1:
                    props['CONFIG.PCW_USE_M_AXI_GP1'] = '1'
            else:
                props[f'CONFIG.PCW_FPGA_FCLK{fclk_id}_ENABLE'] = '0'

            # 设置属性
            prop_list = []
            for key, value in props.items():
                prop_list.append(f'{key} "{value}"')

            props_str = ' '.join(prop_list)
            cmd = f'set_property -dict [list {props_str}] [get_bd_cells {ps7_name}]'

            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"FCLK{fclk_id} 设置成功 ({frequency} MHz)" or "FCLK 设置失败",
                error=result.errors[0] if result.errors else None,
                data={"fclk_id": fclk_id, "frequency": frequency, "enabled": enable} if result.success else None,
            )

        except Exception as e:
            logger.error(f"设置 PS7 FCLK 失败: {e}")
            return BDResult(
                success=False,
                message="FCLK 设置失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_ps7_enable_axi_port(
        port_type: str,
    ) -> BDResult:
        """
        启用 PS7 的 AXI 端口。

        启用指定的 AXI 主/从接口。

        Args:
            port_type: 端口类型，支持:
                - "M_AXI_GP0": AXI General Purpose Master 0
                - "M_AXI_GP1": AXI General Purpose Master 1
                - "S_AXI_GP0": AXI General Purpose Slave 0
                - "S_AXI_GP1": AXI General Purpose Slave 1
                - "S_AXI_ACP": AXI Accelerator Coherency Port
                - "S_AXI_HP0": AXI High Performance Slave 0
                - "S_AXI_HP1": AXI High Performance Slave 1
                - "S_AXI_HP2": AXI High Performance Slave 2
                - "S_AXI_HP3": AXI High Performance Slave 3

        Returns:
            BDResult 包含启用结果。

        Example:
            启用 AXI GP0 主接口:
            ```
            result = bd_ps7_enable_axi_port(port_type="M_AXI_GP0")
            ```

            启用 AXI ACP 接口:
            ```
            result = bd_ps7_enable_axi_port(port_type="S_AXI_ACP")
            ```
        """
        logger.info(f"启用 PS7 AXI 端口: {port_type}")

        valid_ports = [
            "M_AXI_GP0", "M_AXI_GP1",
            "S_AXI_GP0", "S_AXI_GP1",
            "S_AXI_ACP",
            "S_AXI_HP0", "S_AXI_HP1", "S_AXI_HP2", "S_AXI_HP3",
        ]

        if port_type not in valid_ports:
            return BDResult(
                success=False,
                message="无效的 AXI 端口类型",
                error=f"支持的端口: {', '.join(valid_ports)}",
            )

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            # 构建属性名
            prop_name = f'CONFIG.PCW_USE_{port_type}'

            cmd = f'set_property -dict [list {prop_name} "1"] [get_bd_cells {ps7_name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"AXI 端口 {port_type} 启用成功" or "AXI 端口启用失败",
                error=result.errors[0] if result.errors else None,
                data={"port_type": port_type} if result.success else None,
            )

        except Exception as e:
            logger.error(f"启用 PS7 AXI 端口失败: {e}")
            return BDResult(
                success=False,
                message="AXI 端口启用失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_ps7_enable_uart(uart_id: int = 0) -> BDResult:
        """
        启用 PS7 的 UART。

        启用指定的 UART 外设。

        Args:
            uart_id: UART ID，0 或 1，默认 0。

        Returns:
            BDResult 包含启用结果。

        Example:
            启用 UART0:
            ```
            result = bd_ps7_enable_uart(uart_id=0)
            ```
        """
        logger.info(f"启用 PS7 UART: {uart_id}")

        if uart_id not in [0, 1]:
            return BDResult(
                success=False,
                message="无效的 UART ID",
                error="uart_id 必须是 0 或 1",
            )

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            # 配置 UART
            props = [
                f'CONFIG.PCW_UART{uart_id}_PERIPHERAL_ENABLE "1"',
                f'CONFIG.PCW_UART{uart_id}_UART{uart_id}_IO "MIO {14 + uart_id * 2} .. {15 + uart_id * 2}"',
            ]

            props_str = ' '.join(props)
            cmd = f'set_property -dict [list {props_str}] [get_bd_cells {ps7_name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"UART{uart_id} 启用成功" or "UART 启用失败",
                error=result.errors[0] if result.errors else None,
                data={"uart_id": uart_id} if result.success else None,
            )

        except Exception as e:
            logger.error(f"启用 PS7 UART 失败: {e}")
            return BDResult(
                success=False,
                message="UART 启用失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_ps7_enable_gpio(emio_width: int = 0) -> BDResult:
        """
        启用 PS7 的 GPIO。

        启用 PS7 的 GPIO 功能，包括 MIO GPIO 和可选的 EMIO。

        Args:
            emio_width: EMIO GPIO 位宽，0 表示不使用 EMIO。

        Returns:
            BDResult 包含启用结果。

        Example:
            启用 MIO GPIO:
            ```
            result = bd_ps7_enable_gpio()
            ```

            启用 8 位 EMIO GPIO:
            ```
            result = bd_ps7_enable_gpio(emio_width=8)
            ```
        """
        logger.info(f"启用 PS7 GPIO: emio_width={emio_width}")

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            # 配置 GPIO
            props = ['CONFIG.PCW_GPIO_MIO_GPIO_ENABLE "1"']

            if emio_width > 0:
                props.append(f'CONFIG.PCW_GPIO_EMIO_GPIO_ENABLE "1"')
                props.append(f'CONFIG.PCW_GPIO_EMIO_GPIO_WIDTH "{emio_width}"')

            props_str = ' '.join(props)
            cmd = f'set_property -dict [list {props_str}] [get_bd_cells {ps7_name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"GPIO 启用成功 (EMIO: {emio_width} 位)" or "GPIO 启用失败",
                error=result.errors[0] if result.errors else None,
                data={"emio_width": emio_width} if result.success else None,
            )

        except Exception as e:
            logger.error(f"启用 PS7 GPIO 失败: {e}")
            return BDResult(
                success=False,
                message="GPIO 启用失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_ps7_enable_interrupt() -> BDResult:
        """
        启用 PS7 的 Fabric 中断 (IRQ_F2P)。

        启用从 FPGA 到 PS 的中断输入。

        Returns:
            BDResult 包含启用结果。

        Example:
            ```
            result = bd_ps7_enable_interrupt()
            if result.success:
                print("Fabric 中断已启用")
            ```
        """
        logger.info("启用 PS7 Fabric 中断")

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            cmd = f'set_property -dict [list CONFIG.PCW_IRQ_F2P_MODE "DIRECT"] [get_bd_cells {ps7_name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and "Fabric 中断启用成功" or "Fabric 中断启用失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"启用 PS7 中断失败: {e}")
            return BDResult(
                success=False,
                message="Fabric 中断启用失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_get_ps7_config() -> BDResult:
        """
        获取 PS7 当前配置。

        返回 PS7 的主要配置信息。

        Returns:
            BDResult 包含 PS7 配置信息。

        Example:
            ```
            result = bd_get_ps7_config()
            if result.success:
                config = result.data
                print(f"FCLK0: {config['fclk0_freq']} MHz")
            ```
        """
        logger.info("获取 PS7 配置")

        try:
            engine = _get_engine()

            # 查找 PS7 实例
            find_result = await engine.execute_async("get_bd_cells -filter {VLNV =~ *processing_system7*}")
            if not find_result.success or not find_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 PS7 实例",
                    error="请先创建 PS7 实例",
                )

            ps7_name = find_result.output.strip().split('\n')[0].strip()

            # 获取关键配置
            config_props = [
                "CONFIG.PCW_FPGA0_PERIPHERAL_FREQMHZ",
                "CONFIG.PCW_FPGA1_PERIPHERAL_FREQMHZ",
                "CONFIG.PCW_FPGA2_PERIPHERAL_FREQMHZ",
                "CONFIG.PCW_FPGA3_PERIPHERAL_FREQMHZ",
                "CONFIG.PCW_USE_M_AXI_GP0",
                "CONFIG.PCW_USE_M_AXI_GP1",
                "CONFIG.PCW_USE_S_AXI_GP0",
                "CONFIG.PCW_USE_S_AXI_GP1",
                "CONFIG.PCW_USE_S_AXI_ACP",
                "CONFIG.PCW_USE_S_AXI_HP0",
                "CONFIG.PCW_USE_S_AXI_HP1",
                "CONFIG.PCW_USE_S_AXI_HP2",
                "CONFIG.PCW_USE_S_AXI_HP3",
            ]

            config = {"name": ps7_name}

            for prop in config_props:
                prop_short = prop.replace("CONFIG.PCW_", "").replace("CONFIG.", "")
                cmd = f'get_property {prop} [get_bd_cells {ps7_name}]'
                result = await engine.execute_async(cmd)
                if result.success:
                    config[prop_short] = result.output.strip()

            return BDResult(
                success=True,
                message="获取 PS7 配置成功",
                data=config,
            )

        except Exception as e:
            logger.error(f"获取 PS7 配置失败: {e}")
            return BDResult(
                success=False,
                message="获取 PS7 配置失败",
                error=str(e),
            )

    # ==================== AXI GPIO 工具 ====================

    @mcp.tool()
    async def bd_create_axi_gpio(
        name: str,
        width: int = 32,
        direction: str = "inout",
        enable_interrupt: bool = False,
        is_dual: bool = False,
    ) -> BDResult:
        """
        创建 AXI GPIO IP。

        创建并配置 AXI GPIO IP 实例。

        Args:
            name: 实例名称。
            width: GPIO 位宽，范围 1-32，默认 32。
            direction: 方向，可选 "in"（输入）、"out"（输出）、"inout"（双向），默认 "inout"。
            enable_interrupt: 是否启用中断，默认 False。
            is_dual: 是否双通道，默认 False。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 8 位双向 GPIO:
            ```
            result = bd_create_axi_gpio(name="gpio_led", width=8)
            ```

            创建带中断的输入 GPIO:
            ```
            result = bd_create_axi_gpio(
                name="gpio_btn",
                width=4,
                direction="in",
                enable_interrupt=True
            )
            ```
        """
        logger.info(f"创建 AXI GPIO: name={name}, width={width}, direction={direction}")

        if width < 1 or width > 32:
            return BDResult(
                success=False,
                message="GPIO 位宽无效",
                error="位宽必须在 1-32 范围内",
            )

        if direction not in ["in", "out", "inout"]:
            return BDResult(
                success=False,
                message="GPIO 方向无效",
                error="方向必须是 in、out 或 inout",
            )

        try:
            engine = _get_engine()

            # 创建 AXI GPIO 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_GPIO_WIDTH': str(width),
                'CONFIG.C_IS_DUAL': '1' if is_dual else '0',
            }

            # 配置方向
            if direction == "in":
                props['CONFIG.C_ALL_INPUTS'] = '1'
                props['CONFIG.C_ALL_OUTPUTS'] = '0'
            elif direction == "out":
                props['CONFIG.C_ALL_INPUTS'] = '0'
                props['CONFIG.C_ALL_OUTPUTS'] = '1'
            else:
                props['CONFIG.C_ALL_INPUTS'] = '0'
                props['CONFIG.C_ALL_OUTPUTS'] = '0'

            # 配置中断
            if enable_interrupt:
                props['CONFIG.C_INTERRUPT_PRESENT'] = '1'

            prop_list = []
            for key, value in props.items():
                prop_list.append(f'{key} "{value}"')

            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"AXI GPIO '{name}' 创建成功" or "AXI GPIO 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "width": width, "direction": direction} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 AXI GPIO 失败: {e}")
            return BDResult(
                success=False,
                message="AXI GPIO 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_gpio_set_width(name: str, width: int, channel: int = 1) -> BDResult:
        """
        设置 GPIO 位宽。

        修改已创建的 GPIO IP 的位宽。

        Args:
            name: GPIO 实例名称。
            width: 新的位宽，范围 1-32。
            channel: 通道号，1 或 2，默认 1。

        Returns:
            BDResult 包含设置结果。

        Example:
            ```
            result = bd_gpio_set_width(name="gpio_led", width=16)
            ```
        """
        logger.info(f"设置 GPIO 位宽: name={name}, width={width}, channel={channel}")

        if width < 1 or width > 32:
            return BDResult(
                success=False,
                message="GPIO 位宽无效",
                error="位宽必须在 1-32 范围内",
            )

        if channel not in [1, 2]:
            return BDResult(
                success=False,
                message="通道号无效",
                error="通道号必须是 1 或 2",
            )

        try:
            engine = _get_engine()

            prop_name = f'CONFIG.C_GPIO{"" if channel == 1 else "2"}_WIDTH'
            cmd = f'set_property -dict [list {prop_name} "{width}"] [get_bd_cells {name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"GPIO '{name}' 位宽设置为 {width}" or "GPIO 位宽设置失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"设置 GPIO 位宽失败: {e}")
            return BDResult(
                success=False,
                message="GPIO 位宽设置失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_gpio_set_direction(name: str, direction: str, channel: int = 1) -> BDResult:
        """
        设置 GPIO 方向。

        修改已创建的 GPIO IP 的方向配置。

        Args:
            name: GPIO 实例名称。
            direction: 方向，可选 "in"、"out"、"inout"。
            channel: 通道号，1 或 2，默认 1。

        Returns:
            BDResult 包含设置结果。

        Example:
            设置为输出:
            ```
            result = bd_gpio_set_direction(name="gpio_led", direction="out")
            ```
        """
        logger.info(f"设置 GPIO 方向: name={name}, direction={direction}")

        if direction not in ["in", "out", "inout"]:
            return BDResult(
                success=False,
                message="GPIO 方向无效",
                error="方向必须是 in、out 或 inout",
            )

        try:
            engine = _get_engine()

            props = {}
            suffix = "" if channel == 1 else "2"

            if direction == "in":
                props[f'CONFIG.C_ALL_INPUTS{suffix}'] = '1'
                props[f'CONFIG.C_ALL_OUTPUTS{suffix}'] = '0'
            elif direction == "out":
                props[f'CONFIG.C_ALL_INPUTS{suffix}'] = '0'
                props[f'CONFIG.C_ALL_OUTPUTS{suffix}'] = '1'
            else:
                props[f'CONFIG.C_ALL_INPUTS{suffix}'] = '0'
                props[f'CONFIG.C_ALL_OUTPUTS{suffix}'] = '0'

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            cmd = f'set_property -dict [list {props_str}] [get_bd_cells {name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"GPIO '{name}' 方向设置为 {direction}" or "GPIO 方向设置失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"设置 GPIO 方向失败: {e}")
            return BDResult(
                success=False,
                message="GPIO 方向设置失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_gpio_enable_interrupt(name: str, channel: int = 1) -> BDResult:
        """
        启用 GPIO 中断。

        为 GPIO IP 启用中断功能。

        Args:
            name: GPIO 实例名称。
            channel: 通道号，1 或 2，默认 1。

        Returns:
            BDResult 包含启用结果。

        Example:
            ```
            result = bd_gpio_enable_interrupt(name="gpio_btn")
            ```
        """
        logger.info(f"启用 GPIO 中断: name={name}")

        try:
            engine = _get_engine()

            cmd = f'set_property -dict [list CONFIG.C_INTERRUPT_PRESENT "1"] [get_bd_cells {name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"GPIO '{name}' 中断已启用" or "GPIO 中断启用失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"启用 GPIO 中断失败: {e}")
            return BDResult(
                success=False,
                message="GPIO 中断启用失败",
                error=str(e),
            )

    # ==================== AXI UART Lite 工具 ====================

    @mcp.tool()
    async def bd_create_axi_uartlite(
        name: str,
        baud_rate: int = 115200,
        data_bits: int = 8,
        parity: str = "none",
    ) -> BDResult:
        """
        创建 AXI UART Lite IP。

        创建并配置 AXI UART Lite IP 实例。

        Args:
            name: 实例名称。
            baud_rate: 波特率，默认 115200。
            data_bits: 数据位，可选 5、6、7、8，默认 8。
            parity: 校验，可选 "none"、"even"、"odd"，默认 "none"。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建默认配置的 UART:
            ```
            result = bd_create_axi_uartlite(name="uart_lite_0")
            ```

            创建 9600 波特率的 UART:
            ```
            result = bd_create_axi_uartlite(name="uart_debug", baud_rate=9600)
            ```
        """
        logger.info(f"创建 AXI UART Lite: name={name}, baud_rate={baud_rate}")

        if data_bits not in [5, 6, 7, 8]:
            return BDResult(
                success=False,
                message="数据位无效",
                error="数据位必须是 5、6、7 或 8",
            )

        if parity not in ["none", "even", "odd"]:
            return BDResult(
                success=False,
                message="校验类型无效",
                error="校验必须是 none、even 或 odd",
            )

        try:
            engine = _get_engine()

            # 创建 AXI UART Lite 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite:2.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_BAUDRATE': str(baud_rate),
                'CONFIG.C_DATA_BITS': str(data_bits),
            }

            if parity == "even":
                props['CONFIG.C_USE_PARITY'] = '1'
                props['CONFIG.C_PARITY'] = '0'
            elif parity == "odd":
                props['CONFIG.C_USE_PARITY'] = '1'
                props['CONFIG.C_PARITY'] = '1'
            else:
                props['CONFIG.C_USE_PARITY'] = '0'

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"AXI UART Lite '{name}' 创建成功" or "AXI UART Lite 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "baud_rate": baud_rate} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 AXI UART Lite 失败: {e}")
            return BDResult(
                success=False,
                message="AXI UART Lite 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_uartlite_set_baudrate(name: str, baud_rate: int) -> BDResult:
        """
        设置 UART 波特率。

        修改已创建的 UART Lite IP 的波特率。

        Args:
            name: UART 实例名称。
            baud_rate: 新的波特率。

        Returns:
            BDResult 包含设置结果。

        Example:
            ```
            result = bd_uartlite_set_baudrate(name="uart_lite_0", baud_rate=9600)
            ```
        """
        logger.info(f"设置 UART 波特率: name={name}, baud_rate={baud_rate}")

        try:
            engine = _get_engine()

            cmd = f'set_property -dict [list CONFIG.C_BAUDRATE "{baud_rate}"] [get_bd_cells {name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"UART '{name}' 波特率设置为 {baud_rate}" or "UART 波特率设置失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"设置 UART 波特率失败: {e}")
            return BDResult(
                success=False,
                message="UART 波特率设置失败",
                error=str(e),
            )

    # ==================== AXI Timer 工具 ====================

    @mcp.tool()
    async def bd_create_axi_timer(
        name: str,
        count_width: int = 32,
        is_dual: bool = False,
        enable_interrupt: bool = True,
    ) -> BDResult:
        """
        创建 AXI Timer IP。

        创建并配置 AXI Timer IP 实例。

        Args:
            name: 实例名称。
            count_width: 计数器位宽，可选 8、16、32，默认 32。
            is_dual: 是否双定时器，默认 False。
            enable_interrupt: 是否启用中断，默认 True。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 32 位定时器:
            ```
            result = bd_create_axi_timer(name="timer_0")
            ```

            创建双定时器:
            ```
            result = bd_create_axi_timer(name="dual_timer", is_dual=True)
            ```
        """
        logger.info(f"创建 AXI Timer: name={name}, count_width={count_width}")

        if count_width not in [8, 16, 32]:
            return BDResult(
                success=False,
                message="计数器位宽无效",
                error="位宽必须是 8、16 或 32",
            )

        try:
            engine = _get_engine()

            # 创建 AXI Timer 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_timer:2.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_COUNT_WIDTH': str(count_width),
                'CONFIG.C_IS_DUAL': '1' if is_dual else '0',
                'CONFIG.C_ENABLE_ONE_PULSE': '0',
            }

            if enable_interrupt:
                props['CONFIG.C_ENABLE_INTERRUPT'] = '1'

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"AXI Timer '{name}' 创建成功" or "AXI Timer 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "count_width": count_width} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 AXI Timer 失败: {e}")
            return BDResult(
                success=False,
                message="AXI Timer 创建失败",
                error=str(e),
            )

    # ==================== AXI BRAM 工具 ====================

    @mcp.tool()
    async def bd_create_axi_bram_ctrl_with_mem(
        name: str,
        data_width: int = 32,
        memory_depth: int = 1024,
    ) -> BDResult:
        """
        创建 AXI BRAM Controller + Block Memory 组合。

        创建 AXI BRAM Controller 和 Block Memory Generator IP，并自动连接。

        Args:
            name: BRAM Controller 实例名称。
            data_width: 数据宽度，可选 32、64，默认 32。
            memory_depth: 存储深度（字数），默认 1024。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 32 位 4KB BRAM:
            ```
            result = bd_create_axi_bram_ctrl_with_mem(name="bram_ctrl_0", memory_depth=1024)
            ```

            创建 64 位 8KB BRAM:
            ```
            result = bd_create_axi_bram_ctrl_with_mem(name="bram_ctrl_0", data_width=64, memory_depth=1024)
            ```
        """
        logger.info(f"创建 AXI BRAM: name={name}, data_width={data_width}, depth={memory_depth}")

        if data_width not in [32, 64]:
            return BDResult(
                success=False,
                message="数据宽度无效",
                error="数据宽度必须是 32 或 64",
            )

        try:
            engine = _get_engine()

            # 创建 BRAM Controller
            commands = [
                f'create_bd_cell -type ip -vlnv xilinx.com:ip:axi_bram_ctrl:4.1 {name}',
            ]

            # 配置 BRAM Controller
            props = {
                'CONFIG.DATA_WIDTH': str(data_width),
                'CONFIG.ECC_TYPE': '0',
                'CONFIG.SINGLE_PORT_BRAM': '1',
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            # 创建 Block Memory Generator
            mem_name = f"{name}_mem"
            commands.append(f'create_bd_cell -type ip -vlnv xilinx.com:ip:blk_mem_gen:8.4 {mem_name}')

            # 配置 Block Memory
            mem_props = {
                'CONFIG.Memory_Type': 'True_Dual_Port_RAM',
                'CONFIG.Write_Width_A': str(data_width),
                'CONFIG.Read_Width_A': str(data_width),
                'CONFIG.Write_Width_B': str(data_width),
                'CONFIG.Read_Width_B': str(data_width),
                'CONFIG.Write_Depth_A': str(memory_depth),
                'CONFIG.Read_Depth_A': str(memory_depth),
                'CONFIG.Enable_32bit_Address': 'true',
                'CONFIG.Register_PortA_Output_of_Memory_Primitives': 'false',
                'CONFIG.Register_PortB_Output_of_Memory_Primitives': 'false',
            }

            mem_prop_list = [f'{k} "{v}"' for k, v in mem_props.items()]
            mem_props_str = ' '.join(mem_prop_list)
            commands.append(f'set_property -dict [list {mem_props_str}] [get_bd_cells {mem_name}]')

            # 连接 BRAM Controller 和 Memory
            commands.append(
                f'connect_bd_intf_net [get_bd_intf_pins {name}/BRAM_PORTA] [get_bd_intf_pins {mem_name}/BRAM_PORTA]'
            )

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"AXI BRAM '{name}' 创建成功" or "AXI BRAM 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "mem_name": mem_name, "data_width": data_width, "depth": memory_depth} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 AXI BRAM 失败: {e}")
            return BDResult(
                success=False,
                message="AXI BRAM 创建失败",
                error=str(e),
            )

    # ==================== 工具 IP ====================

    @mcp.tool()
    async def bd_create_concat(
        name: str,
        num_ports: int,
        in_width: int = 1,
    ) -> BDResult:
        """
        创建 Concat IP（信号合并）。

        创建用于合并多个信号的 Concat IP。

        Args:
            name: 实例名称。
            num_ports: 输入端口数量。
            in_width: 每个输入端口的位宽，默认 1。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 4 路 1 位信号合并器:
            ```
            result = bd_create_concat(name="concat_irq", num_ports=4)
            ```
        """
        logger.info(f"创建 Concat: name={name}, num_ports={num_ports}")

        if num_ports < 2:
            return BDResult(
                success=False,
                message="端口数量无效",
                error="端口数量必须大于等于 2",
            )

        try:
            engine = _get_engine()

            # 创建 Concat 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 {name}']

            # 配置端口数量
            commands.append(
                f'set_property -dict [list CONFIG.NUM_PORTS "{num_ports}"] [get_bd_cells {name}]'
            )

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"Concat '{name}' 创建成功" or "Concat 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "num_ports": num_ports} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 Concat 失败: {e}")
            return BDResult(
                success=False,
                message="Concat 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_slice(
        name: str,
        din_width: int,
        dout_width: int,
        din_from: int = 0,
    ) -> BDResult:
        """
        创建 Slice IP（信号切片）。

        创建用于提取信号位的 Slice IP。

        Args:
            name: 实例名称。
            din_width: 输入信号位宽。
            dout_width: 输出信号位宽。
            din_from: 起始位，默认 0。

        Returns:
            BDResult 包含创建结果。

        Example:
            提取低 4 位:
            ```
            result = bd_create_slice(name="slice_low", din_width=8, dout_width=4, din_from=0)
            ```

            提取高 4 位:
            ```
            result = bd_create_slice(name="slice_high", din_width=8, dout_width=4, din_from=4)
            ```
        """
        logger.info(f"创建 Slice: name={name}, din={din_width}, dout={dout_width}")

        if dout_width > din_width:
            return BDResult(
                success=False,
                message="输出位宽无效",
                error="输出位宽不能大于输入位宽",
            )

        try:
            engine = _get_engine()

            din_to = din_from + dout_width - 1

            # 创建 Slice 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:xlslice:1.0 {name}']

            # 配置属性
            props = {
                'CONFIG.DIN_WIDTH': str(din_width),
                'CONFIG.DOUT_WIDTH': str(dout_width),
                'CONFIG.DIN_FROM': str(din_from),
                'CONFIG.DIN_TO': str(din_to),
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"Slice '{name}' 创建成功" or "Slice 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "din_width": din_width, "dout_width": dout_width} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 Slice 失败: {e}")
            return BDResult(
                success=False,
                message="Slice 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_inverter(name: str, width: int = 1) -> BDResult:
        """
        创建 Inverter IP（信号反相）。

        创建用于信号取反的 Inverter IP。

        Args:
            name: 实例名称。
            width: 信号位宽，默认 1。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 1 位反相器:
            ```
            result = bd_create_inverter(name="inv_reset")
            ```
        """
        logger.info(f"创建 Inverter: name={name}, width={width}")

        try:
            engine = _get_engine()

            # 创建 Inverter 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:util_vector_logic:2.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_OPERATION': 'not',
                'CONFIG.C_SIZE': str(width),
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"Inverter '{name}' 创建成功" or "Inverter 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "width": width} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 Inverter 失败: {e}")
            return BDResult(
                success=False,
                message="Inverter 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_vector_logic(
        name: str,
        operation: str,
        width: int = 1,
    ) -> BDResult:
        """
        创建 Vector Logic IP。

        创建用于位运算的 Vector Logic IP。

        Args:
            name: 实例名称。
            operation: 运算类型，支持: AND, OR, XOR, NOT, NAND, NOR, XNOR。
            width: 信号位宽，默认 1。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 AND 门:
            ```
            result = bd_create_vector_logic(name="and_gate", operation="AND", width=4)
            ```
        """
        logger.info(f"创建 Vector Logic: name={name}, operation={operation}")

        valid_ops = ["AND", "OR", "XOR", "NOT", "NAND", "NOR", "XNOR"]
        if operation.upper() not in valid_ops:
            return BDResult(
                success=False,
                message="运算类型无效",
                error=f"支持的运算: {', '.join(valid_ops)}",
            )

        try:
            engine = _get_engine()

            # 创建 Vector Logic 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:util_vector_logic:2.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_OPERATION': operation.lower(),
                'CONFIG.C_SIZE': str(width),
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"Vector Logic '{name}' 创建成功" or "Vector Logic 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "operation": operation, "width": width} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 Vector Logic 失败: {e}")
            return BDResult(
                success=False,
                message="Vector Logic 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_constant(
        name: str,
        width: int = 1,
        value: int = 0,
    ) -> BDResult:
        """
        创建 Constant IP。

        创建输出常量值的 IP。

        Args:
            name: 实例名称。
            width: 输出位宽，默认 1。
            value: 常量值，默认 0。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 32 位常量 0x12345678:
            ```
            result = bd_create_constant(name="const_val", width=32, value=0x12345678)
            ```
        """
        logger.info(f"创建 Constant: name={name}, width={width}, value={value}")

        try:
            engine = _get_engine()

            # 创建 Constant 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 {name}']

            # 配置属性
            props = {
                'CONFIG.CONST_WIDTH': str(width),
                'CONFIG.CONST_VAL': str(value),
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"Constant '{name}' 创建成功" or "Constant 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "width": width, "value": value} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 Constant 失败: {e}")
            return BDResult(
                success=False,
                message="Constant 创建失败",
                error=str(e),
            )

    # ==================== 调试 IP ====================

    @mcp.tool()
    async def bd_create_ila(
        name: str,
        num_probes: int,
        depth: int = 1024,
    ) -> BDResult:
        """
        创建 ILA (Integrated Logic Analyzer) IP。

        创建用于硬件调试的 ILA IP。

        Args:
            name: 实例名称。
            num_probes: 探针数量。
            depth: 采样深度，默认 1024。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建 4 探针 ILA:
            ```
            result = bd_create_ila(name="ila_0", num_probes=4)
            ```
        """
        logger.info(f"创建 ILA: name={name}, num_probes={num_probes}, depth={depth}")

        if num_probes < 1 or num_probes > 16:
            return BDResult(
                success=False,
                message="探针数量无效",
                error="探针数量必须在 1-16 范围内",
            )

        try:
            engine = _get_engine()

            # 创建 ILA 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:ila:6.2 {name}']

            # 配置属性
            props = {
                'CONFIG.C_NUM_OF_PROBES': str(num_probes),
                'CONFIG.C_DATA_DEPTH': str(depth),
            }

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"ILA '{name}' 创建成功" or "ILA 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "num_probes": num_probes, "depth": depth} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 ILA 失败: {e}")
            return BDResult(
                success=False,
                message="ILA 创建失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_connect_ila_clock(ila_name: str, clock_net: str) -> BDResult:
        """
        连接 ILA 时钟。

        将 ILA 的时钟端口连接到指定的时钟网络。

        Args:
            ila_name: ILA 实例名称。
            clock_net: 时钟网络，格式 "instance/port"。

        Returns:
            BDResult 包含连接结果。

        Example:
            ```
            result = bd_connect_ila_clock(ila_name="ila_0", clock_net="ps7_0/FCLK_CLK0")
            ```
        """
        logger.info(f"连接 ILA 时钟: ila={ila_name}, clock={clock_net}")

        try:
            engine = _get_engine()

            cmd = f'connect_bd_net [get_bd_pins {clock_net}] [get_bd_pins {ila_name}/clk]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"ILA '{ila_name}' 时钟连接成功" or "ILA 时钟连接失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"连接 ILA 时钟失败: {e}")
            return BDResult(
                success=False,
                message="ILA 时钟连接失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_connect_ila_probe(
        ila_name: str,
        probe_index: int,
        signal_name: str,
    ) -> BDResult:
        """
        连接 ILA 探针。

        将 ILA 的探针端口连接到指定的信号。

        Args:
            ila_name: ILA 实例名称。
            probe_index: 探针索引，从 0 开始。
            signal_name: 信号名称，格式 "instance/port"。

        Returns:
            BDResult 包含连接结果。

        Example:
            ```
            result = bd_connect_ila_probe(ila_name="ila_0", probe_index=0, signal_name="gpio_0/gpio_io_o")
            ```
        """
        logger.info(f"连接 ILA 探针: ila={ila_name}, probe={probe_index}, signal={signal_name}")

        try:
            engine = _get_engine()

            cmd = f'connect_bd_net [get_bd_pins {signal_name}] [get_bd_pins {ila_name}/probe{probe_index}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"ILA 探针 {probe_index} 连接成功" or "ILA 探针连接失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"连接 ILA 探针失败: {e}")
            return BDResult(
                success=False,
                message="ILA 探针连接失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_vio(
        name: str,
        num_probe_in: int = 0,
        num_probe_out: int = 0,
        probe_in_width: list[int] | None = None,
        probe_out_width: list[int] | None = None,
    ) -> BDResult:
        """
        创建 VIO (Virtual Input/Output) IP。

        创建用于硬件调试的 VIO IP。

        Args:
            name: 实例名称。
            num_probe_in: 输入探针数量，默认 0。
            num_probe_out: 输出探针数量，默认 0。
            probe_in_width: 输入探针位宽列表，如 [8, 4]。
            probe_out_width: 输出探针位宽列表，如 [1, 8]。

        Returns:
            BDResult 包含创建结果。

        Example:
            创建带 2 个输出探针的 VIO:
            ```
            result = bd_create_vio(name="vio_0", num_probe_out=2, probe_out_width=[1, 8])
            ```
        """
        logger.info(f"创建 VIO: name={name}, probe_in={num_probe_in}, probe_out={num_probe_out}")

        try:
            engine = _get_engine()

            # 创建 VIO 实例
            commands = [f'create_bd_cell -type ip -vlnv xilinx.com:ip:vio:3.0 {name}']

            # 配置属性
            props = {
                'CONFIG.C_NUM_PROBE_IN': str(num_probe_in),
                'CONFIG.C_NUM_PROBE_OUT': str(num_probe_out),
            }

            # 配置输入探针位宽
            if probe_in_width and len(probe_in_width) == num_probe_in:
                for i, width in enumerate(probe_in_width):
                    props[f'CONFIG.C_PROBE_IN{i}_WIDTH'] = str(width)

            # 配置输出探针位宽
            if probe_out_width and len(probe_out_width) == num_probe_out:
                for i, width in enumerate(probe_out_width):
                    props[f'CONFIG.C_PROBE_OUT{i}_WIDTH'] = str(width)

            prop_list = [f'{k} "{v}"' for k, v in props.items()]
            props_str = ' '.join(prop_list)
            commands.append(f'set_property -dict [list {props_str}] [get_bd_cells {name}]')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and f"VIO '{name}' 创建成功" or "VIO 创建失败",
                error=result.errors[0] if result.errors else None,
                data={"name": name, "num_probe_in": num_probe_in, "num_probe_out": num_probe_out} if result.success else None,
            )

        except Exception as e:
            logger.error(f"创建 VIO 失败: {e}")
            return BDResult(
                success=False,
                message="VIO 创建失败",
                error=str(e),
            )

    # ==================== 连接工具 ====================

    @mcp.tool()
    async def bd_connect_pins(
        source: str,
        destination: str,
    ) -> BDResult:
        """
        连接两个引脚。

        连接 Block Design 中的两个引脚。

        Args:
            source: 源引脚，格式 "instance/port"。
            destination: 目标引脚，格式 "instance/port"。

        Returns:
            BDResult 包含连接结果。

        Example:
            连接时钟:
            ```
            result = bd_connect_pins(source="ps7_0/FCLK_CLK0", destination="gpio_0/s_axi_aclk")
            ```
        """
        logger.info(f"连接引脚: {source} -> {destination}")

        try:
            engine = _get_engine()

            cmd = f'connect_bd_net [get_bd_pins {source}] [get_bd_pins {destination}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"引脚连接成功: {source} -> {destination}" or "引脚连接失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"连接引脚失败: {e}")
            return BDResult(
                success=False,
                message="引脚连接失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_make_pin_external(
        pin: str,
        port_name: str | None = None,
    ) -> BDResult:
        """
        将引脚导出为外部端口。

        将 IP 实例的引脚导出为 Block Design 的外部端口。

        Args:
            pin: 引脚，格式 "instance/port"。
            port_name: 外部端口名称（可选），默认使用引脚名称。

        Returns:
            BDResult 包含导出结果。

        Example:
            导出 GPIO 引脚:
            ```
            result = bd_make_pin_external(pin="gpio_0/gpio_io_o", port_name="led")
            ```
        """
        logger.info(f"导出引脚: {pin}, port_name={port_name}")

        try:
            engine = _get_engine()

            if port_name:
                cmd = f'create_bd_port -dir O -from 31 -to 0 {port_name}; connect_bd_net [get_bd_pins {pin}] [get_bd_ports {port_name}]'
            else:
                cmd = f'make_bd_pins_external [get_bd_pins {pin}]'

            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"引脚 '{pin}' 已导出" or "引脚导出失败",
                error=result.errors[0] if result.errors else None,
                data={"pin": pin, "port_name": port_name} if result.success else None,
            )

        except Exception as e:
            logger.error(f"导出引脚失败: {e}")
            return BDResult(
                success=False,
                message="引脚导出失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_make_intf_pin_external(
        intf_pin: str,
        port_name: str | None = None,
    ) -> BDResult:
        """
        将接口引脚导出为外部接口端口。

        将 IP 实例的接口引脚导出为 Block Design 的外部接口端口。

        Args:
            intf_pin: 接口引脚，格式 "instance/interface"。
            port_name: 外部接口端口名称（可选）。

        Returns:
            BDResult 包含导出结果。

        Example:
            导出 AXI 接口:
            ```
            result = bd_make_intf_pin_external(intf_pin="interconnect_0/M00_AXI", port_name="M_AXI")
            ```
        """
        logger.info(f"导出接口引脚: {intf_pin}")

        try:
            engine = _get_engine()

            if port_name:
                cmd = f'create_bd_intf_port -mode Master -vlnv xilinx.com:interface:aximm_rtl:1.0 {port_name}; connect_bd_intf_net [get_bd_intf_pins {intf_pin}] [get_bd_intf_ports {port_name}]'
            else:
                cmd = f'make_bd_intf_pins_external [get_bd_intf_pins {intf_pin}]'

            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"接口引脚 '{intf_pin}' 已导出" or "接口引脚导出失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"导出接口引脚失败: {e}")
            return BDResult(
                success=False,
                message="接口引脚导出失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_disconnect_net(net_name: str) -> BDResult:
        """
        断开网络连接。

        删除指定的网络连接。

        Args:
            net_name: 网络名称。

        Returns:
            BDResult 包含断开结果。

        Example:
            ```
            result = bd_disconnect_net(net_name="clk_net")
            ```
        """
        logger.info(f"断开网络: {net_name}")

        try:
            engine = _get_engine()

            cmd = f'delete_bd_objs [get_bd_nets {net_name}]'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"网络 '{net_name}' 已断开" or "网络断开失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"断开网络失败: {e}")
            return BDResult(
                success=False,
                message="网络断开失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_get_unconnected_pins() -> BDResult:
        """
        获取未连接的引脚列表。

        返回当前 Block Design 中所有未连接的引脚。

        Returns:
            BDResult 包含未连接引脚列表。

        Example:
            ```
            result = bd_get_unconnected_pins()
            for pin in result.data.get('pins', []):
                print(f"未连接: {pin}")
            ```
        """
        logger.info("获取未连接引脚")

        try:
            engine = _get_engine()

            # 获取所有引脚
            all_pins_result = await engine.execute_async("get_bd_pins -of_objects [get_bd_cells]")

            unconnected = []

            if all_pins_result.success:
                for line in all_pins_result.output.split('\n'):
                    pin = line.strip()
                    if pin:
                        # 检查是否连接
                        check_result = await engine.execute_async(f"get_bd_nets -of_objects [get_bd_pins {pin}]")
                        if check_result.success and not check_result.output.strip():
                            unconnected.append(pin)

            return BDResult(
                success=True,
                message=f"找到 {len(unconnected)} 个未连接引脚",
                data={"pins": unconnected, "count": len(unconnected)},
            )

        except Exception as e:
            logger.error(f"获取未连接引脚失败: {e}")
            return BDResult(
                success=False,
                message="获取未连接引脚失败",
                error=str(e),
            )

    # ==================== 自动化工具 ====================

    @mcp.tool()
    async def bd_run_automation(
        rule: str = "all",
    ) -> BDResult:
        """
        运行 Block Design 自动化。

        自动创建和连接 AXI Interconnect、Processor System Reset、时钟和复位网络。

        Args:
            rule: 自动化规则，可选:
                - "all": 应用所有自动连接规则
                - "axi": 仅自动连接 AXI 总线
                - "clock": 仅自动连接时钟
                - "reset": 仅自动连接复位

        Returns:
            BDResult 包含自动化结果。

        Example:
            ```
            result = bd_run_automation(rule="all")
            ```
        """
        logger.info(f"运行自动化: rule={rule}")

        try:
            engine = _get_engine()

            cmd = f'apply_bd_automation -rule {rule}'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and f"自动化 '{rule}' 执行成功" or "自动化执行失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"运行自动化失败: {e}")
            return BDResult(
                success=False,
                message="自动化执行失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_assign_addresses() -> BDResult:
        """
        自动分配 AXI 地址。

        自动为 AXI 从设备分配地址空间。

        Returns:
            BDResult 包含分配结果。

        Example:
            ```
            result = bd_assign_addresses()
            ```
        """
        logger.info("自动分配地址")

        try:
            engine = _get_engine()

            cmd = 'assign_bd_address'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and "地址分配成功" or "地址分配失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"自动分配地址失败: {e}")
            return BDResult(
                success=False,
                message="地址分配失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_get_address_map() -> AddressMapResult:
        """
        获取地址映射表。

        返回当前 Block Design 的 AXI 地址映射信息。

        Returns:
            AddressMapResult 包含地址映射列表。

        Example:
            ```
            result = bd_get_address_map()
            for addr in result.address_map:
                print(f"{addr['slave']}: 0x{addr['offset']:08X} - 0x{addr['high']:08X}")
            ```
        """
        logger.info("获取地址映射")

        try:
            engine = _get_engine()

            # 获取所有地址段
            cmd = 'get_bd_addr_segs'
            result = await engine.execute_async(cmd)

            address_map = []

            if result.success:
                for line in result.output.split('\n'):
                    seg = line.strip()
                    if seg:
                        # 获取地址段信息
                        info_result = await engine.execute_async(f'get_property OFFSET [get_bd_addr_segs {seg}]')
                        offset = info_result.output.strip() if info_result.success else "0"

                        range_result = await engine.execute_async(f'get_property RANGE [get_bd_addr_segs {seg}]')
                        range_val = range_result.output.strip() if range_result.success else "0"

                        address_map.append({
                            "segment": seg,
                            "offset": offset,
                            "range": range_val,
                        })

            return AddressMapResult(
                success=True,
                address_map=address_map,
                message=f"找到 {len(address_map)} 个地址段",
            )

        except Exception as e:
            logger.error(f"获取地址映射失败: {e}")
            return AddressMapResult(
                success=False,
                message="获取地址映射失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_regenerate_layout() -> BDResult:
        """
        重新生成布局。

        重新排列 Block Design 中的 IP 实例位置。

        Returns:
            BDResult 包含重新布局结果。

        Example:
            ```
            result = bd_regenerate_layout()
            ```
        """
        logger.info("重新生成布局")

        try:
            engine = _get_engine()

            cmd = 'regenerate_bd_layout'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and "布局重新生成成功" or "布局重新生成失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"重新生成布局失败: {e}")
            return BDResult(
                success=False,
                message="布局重新生成失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_validate_design() -> BDResult:
        """
        验证设计。

        验证当前 Block Design 的完整性和正确性。

        Returns:
            BDResult 包含验证结果。

        Example:
            ```
            result = bd_validate_design()
            if result.success:
                print("设计验证通过")
            ```
        """
        logger.info("验证设计")

        try:
            engine = _get_engine()

            cmd = 'validate_bd_design'
            result = await engine.execute_async(cmd)

            return BDResult(
                success=result.success,
                message=result.success and "设计验证通过" or "设计验证失败",
                error=result.errors[0] if result.errors else None,
            )

        except Exception as e:
            logger.error(f"验证设计失败: {e}")
            return BDResult(
                success=False,
                message="设计验证失败",
                error=str(e),
            )

    # ==================== 查询工具 ====================

    @mcp.tool()
    async def bd_list_ips() -> BDResult:
        """
        列出所有 IP 实例。

        返回当前 Block Design 中所有 IP 实例的列表。

        Returns:
            BDResult 包含 IP 实例列表。

        Example:
            ```
            result = bd_list_ips()
            for ip in result.data.get('ips', []):
                print(f"{ip['name']}: {ip['type']}")
            ```
        """
        logger.info("列出 IP 实例")

        try:
            engine = _get_engine()

            cmd = 'get_bd_cells'
            result = await engine.execute_async(cmd)

            ips = []

            if result.success:
                for line in result.output.split('\n'):
                    name = line.strip()
                    if name:
                        # 获取 IP 类型
                        type_result = await engine.execute_async(f'get_property VLNV [get_bd_cells {name}]')
                        ip_type = type_result.output.strip() if type_result.success else "unknown"

                        ips.append({
                            "name": name,
                            "type": ip_type,
                        })

            return BDResult(
                success=True,
                message=f"找到 {len(ips)} 个 IP 实例",
                data={"ips": ips, "count": len(ips)},
            )

        except Exception as e:
            logger.error(f"列出 IP 实例失败: {e}")
            return BDResult(
                success=False,
                message="列出 IP 实例失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_list_ports() -> BDResult:
        """
        列出所有端口。

        返回当前 Block Design 中所有外部端口的列表。

        Returns:
            BDResult 包含端口列表。

        Example:
            ```
            result = bd_list_ports()
            for port in result.data.get('ports', []):
                print(f"{port['name']}: {port['direction']}")
            ```
        """
        logger.info("列出端口")

        try:
            engine = _get_engine()

            cmd = 'get_bd_ports'
            result = await engine.execute_async(cmd)

            ports = []

            if result.success:
                for line in result.output.split('\n'):
                    name = line.strip()
                    if name:
                        # 获取端口方向
                        dir_result = await engine.execute_async(f'get_property DIR [get_bd_ports {name}]')
                        direction = dir_result.output.strip() if dir_result.success else "unknown"

                        ports.append({
                            "name": name,
                            "direction": direction,
                        })

            return BDResult(
                success=True,
                message=f"找到 {len(ports)} 个端口",
                data={"ports": ports, "count": len(ports)},
            )

        except Exception as e:
            logger.error(f"列出端口失败: {e}")
            return BDResult(
                success=False,
                message="列出端口失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_list_interface_ports() -> BDResult:
        """
        列出所有接口端口。

        返回当前 Block Design 中所有外部接口端口的列表。

        Returns:
            BDResult 包含接口端口列表。

        Example:
            ```
            result = bd_list_interface_ports()
            for port in result.data.get('ports', []):
                print(f"{port['name']}: {port['mode']}")
            ```
        """
        logger.info("列出接口端口")

        try:
            engine = _get_engine()

            cmd = 'get_bd_intf_ports'
            result = await engine.execute_async(cmd)

            ports = []

            if result.success:
                for line in result.output.split('\n'):
                    name = line.strip()
                    if name:
                        # 获取端口模式
                        mode_result = await engine.execute_async(f'get_property MODE [get_bd_intf_ports {name}]')
                        mode = mode_result.output.strip() if mode_result.success else "unknown"

                        # 获取 VLNV
                        vlnv_result = await engine.execute_async(f'get_property VLNV [get_bd_intf_ports {name}]')
                        vlnv = vlnv_result.output.strip() if vlnv_result.success else "unknown"

                        ports.append({
                            "name": name,
                            "mode": mode,
                            "vlnv": vlnv,
                        })

            return BDResult(
                success=True,
                message=f"找到 {len(ports)} 个接口端口",
                data={"ports": ports, "count": len(ports)},
            )

        except Exception as e:
            logger.error(f"列出接口端口失败: {e}")
            return BDResult(
                success=False,
                message="列出接口端口失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_list_nets() -> BDResult:
        """
        列出所有网络。

        返回当前 Block Design 中所有网络连接的列表。

        Returns:
            BDResult 包含网络列表。

        Example:
            ```
            result = bd_list_nets()
            for net in result.data.get('nets', []):
                print(f"{net['name']}: {net['type']}")
            ```
        """
        logger.info("列出网络")

        try:
            engine = _get_engine()

            nets = []

            # 获取普通网络
            net_result = await engine.execute_async('get_bd_nets')
            if net_result.success:
                for line in net_result.output.split('\n'):
                    name = line.strip()
                    if name:
                        nets.append({"name": name, "type": "net"})

            # 获取接口网络
            intf_result = await engine.execute_async('get_bd_intf_nets')
            if intf_result.success:
                for line in intf_result.output.split('\n'):
                    name = line.strip()
                    if name:
                        nets.append({"name": name, "type": "interface"})

            return BDResult(
                success=True,
                message=f"找到 {len(nets)} 个网络",
                data={"nets": nets, "count": len(nets)},
            )

        except Exception as e:
            logger.error(f"列出网络失败: {e}")
            return BDResult(
                success=False,
                message="列出网络失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_get_ip_properties(ip_name: str) -> IPPropertiesResult:
        """
        获取 IP 属性。

        返回指定 IP 实例的所有属性。

        Args:
            ip_name: IP 实例名称。

        Returns:
            IPPropertiesResult 包含 IP 属性。

        Example:
            ```
            result = bd_get_ip_properties(ip_name="gpio_0")
            for key, value in result.properties.items():
                print(f"{key}: {value}")
            ```
        """
        logger.info(f"获取 IP 属性: {ip_name}")

        try:
            engine = _get_engine()

            # 获取所有属性
            cmd = f'report_property [get_bd_cells {ip_name}]'
            result = await engine.execute_async(cmd)

            properties = {}

            if result.success:
                # 解析属性报告
                for line in result.output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            # 格式: property_name value
                            key = parts[0]
                            value = ' '.join(parts[1:])
                            properties[key] = value

            return IPPropertiesResult(
                success=True,
                ip_name=ip_name,
                properties=properties,
                message=f"获取 IP '{ip_name}' 属性成功",
            )

        except Exception as e:
            logger.error(f"获取 IP 属性失败: {e}")
            return IPPropertiesResult(
                success=False,
                ip_name=ip_name,
                message="获取 IP 属性失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_list_ip_pins(ip_name: str) -> BDResult:
        """
        列出 IP 引脚。

        返回指定 IP 实例的所有引脚。

        Args:
            ip_name: IP 实例名称。

        Returns:
            BDResult 包含引脚列表。

        Example:
            ```
            result = bd_list_ip_pins(ip_name="gpio_0")
            for pin in result.data.get('pins', []):
                print(f"{pin['name']}: {pin['direction']}")
            ```
        """
        logger.info(f"列出 IP 引脚: {ip_name}")

        try:
            engine = _get_engine()

            cmd = f'get_bd_pins -of_objects [get_bd_cells {ip_name}]'
            result = await engine.execute_async(cmd)

            pins = []

            if result.success:
                for line in result.output.split('\n'):
                    name = line.strip()
                    if name:
                        # 获取引脚方向
                        dir_result = await engine.execute_async(f'get_property DIR [get_bd_pins {name}]')
                        direction = dir_result.output.strip() if dir_result.success else "unknown"

                        # 获取引脚位宽
                        left_result = await engine.execute_async(f'get_property LEFT [get_bd_pins {name}]')
                        left = left_result.output.strip() if left_result.success else "0"

                        pins.append({
                            "name": name,
                            "direction": direction,
                            "width": int(left) + 1 if left.isdigit() else 1,
                        })

            return BDResult(
                success=True,
                message=f"找到 {len(pins)} 个引脚",
                data={"pins": pins, "count": len(pins)},
            )

        except Exception as e:
            logger.error(f"列出 IP 引脚失败: {e}")
            return BDResult(
                success=False,
                message="列出 IP 引脚失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_list_ip_interfaces(ip_name: str) -> BDResult:
        """
        列出 IP 接口。

        返回指定 IP 实例的所有接口。

        Args:
            ip_name: IP 实例名称。

        Returns:
            BDResult 包含接口列表。

        Example:
            ```
            result = bd_list_ip_interfaces(ip_name="gpio_0")
            for intf in result.data.get('interfaces', []):
                print(f"{intf['name']}: {intf['mode']}")
            ```
        """
        logger.info(f"列出 IP 接口: {ip_name}")

        try:
            engine = _get_engine()

            cmd = f'get_bd_intf_pins -of_objects [get_bd_cells {ip_name}]'
            result = await engine.execute_async(cmd)

            interfaces = []

            if result.success:
                for line in result.output.split('\n'):
                    name = line.strip()
                    if name:
                        # 获取接口模式
                        mode_result = await engine.execute_async(f'get_property MODE [get_bd_intf_pins {name}]')
                        mode = mode_result.output.strip() if mode_result.success else "unknown"

                        # 获取 VLNV
                        vlnv_result = await engine.execute_async(f'get_property VLNV [get_bd_intf_pins {name}]')
                        vlnv = vlnv_result.output.strip() if vlnv_result.success else "unknown"

                        interfaces.append({
                            "name": name,
                            "mode": mode,
                            "vlnv": vlnv,
                        })

            return BDResult(
                success=True,
                message=f"找到 {len(interfaces)} 个接口",
                data={"interfaces": interfaces, "count": len(interfaces)},
            )

        except Exception as e:
            logger.error(f"列出 IP 接口失败: {e}")
            return BDResult(
                success=False,
                message="列出 IP 接口失败",
                error=str(e),
            )

    # ==================== 输出生成 ====================

    @mcp.tool()
    async def bd_generate_output_and_wrapper() -> BDResult:
        """
        生成输出产品和 HDL Wrapper。

        为当前 Block Design 生成所有输出产品（HDL、约束等）和顶层 Wrapper。

        Returns:
            BDResult 包含生成结果。

        Example:
            ```
            result = bd_generate_output_and_wrapper()
            if result.success:
                print("输出产品和 Wrapper 生成成功")
            ```
        """
        logger.info("生成输出产品和 Wrapper")

        try:
            engine = _get_engine()

            # 获取当前 BD 设计
            bd_result = await engine.execute_async('current_bd_design')
            if not bd_result.success or not bd_result.output.strip():
                return BDResult(
                    success=False,
                    message="未找到 Block Design",
                    error="请先打开或创建 Block Design",
                )

            bd_name = bd_result.output.strip()

            # 生成输出产品
            commands = [
                'generate_target all [get_files [get_property FILE_NAME [current_bd_design]]]',
                'catch { export_ip_user_files -of_objects [get_files [get_property FILE_NAME [current_bd_design]]] -no_scripts -ip_user_files_dir [get_property IP_USER_FILES_DIR [current_project]] -ipstatic_source_dir [get_property IP_STATIC_FILES_DIR [current_project]] -silent -force }',
                'create_bd_cell -type ip -vlnv xilinx.com:ip:processing_system7:5.5 temp_ps7_check 2>/dev/null || true',
            ]

            # 生成 Wrapper
            commands.append(f'make_wrapper -files [get_files {bd_name}.bd] -top -import -force')

            result = await engine.execute_async(commands)

            return BDResult(
                success=result.success,
                message=result.success and "输出产品和 Wrapper 生成成功" or "输出产品和 Wrapper 生成失败",
                error=result.errors[0] if result.errors else None,
                data={"bd_name": bd_name} if result.success else None,
            )

        except Exception as e:
            logger.error(f"生成输出产品和 Wrapper 失败: {e}")
            return BDResult(
                success=False,
                message="输出产品和 Wrapper 生成失败",
                error=str(e),
            )

    @mcp.tool()
    async def bd_create_zynq_gpio_uart_bram_system(
        design_name: str = "system",
        gpio_width: int = 8,
        include_uart: bool = True,
        include_bram: bool = True,
        generate_wrapper: bool = True,
    ) -> BDResult:
        """
        一键创建常见 Zynq 基础系统模板。

        模板包含：
        - PS7
        - AXI Interconnect
        - Processor Reset
        - AXI GPIO
        - 可选 AXI UART Lite
        - 可选 AXI BRAM Controller + Memory
        - 地址分配、验证与可选 Wrapper 生成

        Args:
            design_name: Block Design 名称。
            gpio_width: GPIO 位宽，默认 8。
            include_uart: 是否包含 AXI UART Lite，默认 True。
            include_bram: 是否包含 AXI BRAM Controller + Memory，默认 True。
            generate_wrapper: 是否生成输出产品与 Wrapper，默认 True。

        Returns:
            BDResult 包含模板创建结果。
        """
        logger.info(
            "创建 Zynq 常见系统模板: "
            f"design={design_name}, gpio_width={gpio_width}, "
            f"include_uart={include_uart}, include_bram={include_bram}, "
            f"generate_wrapper={generate_wrapper}"
        )

        if gpio_width < 1 or gpio_width > 32:
            return BDResult(
                success=False,
                message="GPIO 位宽无效",
                error="gpio_width 必须在 1-32 范围内",
            )

        manager = BlockDesignManager(_get_engine())
        created_cells = ["processing_system7_0", "proc_sys_reset_0", "axi_interconnect_0", "axi_gpio_0"]
        warnings: list[str] = []

        async def _require(step: str, result: dict[str, Any]) -> str | None:
            if result.get("success"):
                warnings.extend(result.get("warnings", []))
                return None
            errors = result.get("errors", [])
            error_text = "; ".join(errors) if errors else f"{step} 失败"
            return f"{step} 失败: {error_text}"

        create_result = await manager.create_design(design_name)
        error = await _require("创建 Block Design", create_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        base_result = await manager.build_zynq_design()
        error = await _require("构建 Zynq 基础骨架", base_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_result = await manager.create_axi_gpio("axi_gpio_0", width=gpio_width)
        error = await _require("创建 AXI GPIO", gpio_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_intf_result = await manager.connect_interface(
            "axi_interconnect_0/M00_AXI",
            "axi_gpio_0/S_AXI",
        )
        error = await _require("连接 AXI GPIO 接口", gpio_intf_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_axi_result = await manager.auto_connect_axi("axi_gpio_0")
        error = await _require("连接 AXI GPIO 时钟复位", gpio_axi_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_external_result = await bd_make_pin_external("axi_gpio_0/gpio_io_o")
        if not gpio_external_result.success:
            warnings.append(gpio_external_result.error or "GPIO 外部端口导出失败")

        if include_uart:
            created_cells.append("axi_uartlite_0")
            uart_result = await bd_create_axi_uartlite("axi_uartlite_0")
            if not uart_result.success:
                return BDResult(
                    success=False,
                    message="模板创建失败",
                    error=f"创建 AXI UART Lite 失败: {uart_result.error}",
                )

            uart_axi_result = await manager.connect_interface(
                "axi_interconnect_0/M01_AXI",
                "axi_uartlite_0/S_AXI",
            )
            error = await _require("连接 AXI UART Lite 接口", uart_axi_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            uart_clk_result = await manager.connect_ports(
                "processing_system7_0/FCLK_CLK0",
                "axi_uartlite_0/s_axi_aclk",
            )
            error = await _require("连接 AXI UART Lite 时钟", uart_clk_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            uart_rst_result = await manager.connect_ports(
                "proc_sys_reset_0/peripheral_aresetn",
                "axi_uartlite_0/s_axi_aresetn",
            )
            error = await _require("连接 AXI UART Lite 复位", uart_rst_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            for pin in ("axi_uartlite_0/tx", "axi_uartlite_0/rx"):
                ext_result = await bd_make_pin_external(pin)
                if not ext_result.success:
                    warnings.append(ext_result.error or f"{pin} 导出失败")

        if include_bram:
            created_cells.extend(["axi_bram_ctrl_0", "axi_bram_ctrl_0_mem"])
            bram_result = await bd_create_axi_bram_ctrl_with_mem("axi_bram_ctrl_0")
            if not bram_result.success:
                return BDResult(
                    success=False,
                    message="模板创建失败",
                    error=f"创建 AXI BRAM 失败: {bram_result.error}",
                )

            bram_axi_result = await manager.connect_interface(
                "axi_interconnect_0/M02_AXI",
                "axi_bram_ctrl_0/S_AXI",
            )
            error = await _require("连接 AXI BRAM 接口", bram_axi_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            bram_clk_result = await manager.connect_ports(
                "processing_system7_0/FCLK_CLK0",
                "axi_bram_ctrl_0/s_axi_aclk",
            )
            error = await _require("连接 AXI BRAM 时钟", bram_clk_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            bram_rst_result = await manager.connect_ports(
                "proc_sys_reset_0/peripheral_aresetn",
                "axi_bram_ctrl_0/s_axi_aresetn",
            )
            error = await _require("连接 AXI BRAM 复位", bram_rst_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

        assign_result = await bd_assign_addresses()
        if not assign_result.success:
            return BDResult(
                success=False,
                message="模板创建失败",
                error=f"地址分配失败: {assign_result.error}",
            )

        validate_result = await manager.validate_design()
        error = await _require("验证模板设计", validate_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        save_result = await manager.save_design()
        error = await _require("保存模板设计", save_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        if generate_wrapper:
            wrapper_result = await bd_generate_output_and_wrapper()
            if not wrapper_result.success:
                return BDResult(
                    success=False,
                    message="模板创建失败",
                    error=f"生成输出产品与 Wrapper 失败: {wrapper_result.error}",
                )

        return BDResult(
            success=True,
            message="Zynq 常见系统模板创建成功",
            error=None,
            data={
                "design_name": design_name,
                "cells": created_cells,
                "gpio_width": gpio_width,
                "include_uart": include_uart,
                "include_bram": include_bram,
                "generate_wrapper": generate_wrapper,
                "warnings": warnings,
            },
        )

    @mcp.tool()
    async def bd_create_zynq_gpio_uart_timer_dma_system(
        design_name: str = "system_io",
        gpio_width: int = 8,
        include_timer: bool = True,
        include_dma: bool = True,
        dma_include_sg: bool = False,
        generate_wrapper: bool = True,
    ) -> BDResult:
        """
        一键创建带 GPIO/UART/Timer/DMA 的 Zynq 系统模板。

        模板包含：
        - PS7
        - AXI Interconnect
        - Processor Reset
        - AXI GPIO
        - AXI UART Lite
        - 可选 AXI Timer
        - 可选 AXI DMA
        - 地址分配、验证与可选 Wrapper 生成

        Args:
            design_name: Block Design 名称。
            gpio_width: GPIO 位宽，默认 8。
            include_timer: 是否包含 AXI Timer，默认 True。
            include_dma: 是否包含 AXI DMA，默认 True。
            dma_include_sg: DMA 是否启用 Scatter-Gather，默认 False。
            generate_wrapper: 是否生成输出产品与 Wrapper，默认 True。

        Returns:
            BDResult 包含模板创建结果。
        """
        logger.info(
            "创建 Zynq GPIO/UART/Timer/DMA 模板: "
            f"design={design_name}, gpio_width={gpio_width}, "
            f"include_timer={include_timer}, include_dma={include_dma}, "
            f"dma_include_sg={dma_include_sg}, generate_wrapper={generate_wrapper}"
        )

        if gpio_width < 1 or gpio_width > 32:
            return BDResult(
                success=False,
                message="GPIO 位宽无效",
                error="gpio_width 必须在 1-32 范围内",
            )

        manager = BlockDesignManager(_get_engine())
        created_cells = [
            "processing_system7_0",
            "proc_sys_reset_0",
            "axi_interconnect_0",
            "axi_gpio_0",
            "axi_uartlite_0",
        ]
        warnings: list[str] = []

        async def _require(step: str, result: dict[str, Any]) -> str | None:
            if result.get("success"):
                warnings.extend(result.get("warnings", []))
                return None
            errors = result.get("errors", [])
            error_text = "; ".join(errors) if errors else f"{step} 失败"
            return f"{step} 失败: {error_text}"

        create_result = await manager.create_design(design_name)
        error = await _require("创建 Block Design", create_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        base_result = await manager.build_zynq_design()
        error = await _require("构建 Zynq 基础骨架", base_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_result = await manager.create_axi_gpio("axi_gpio_0", width=gpio_width)
        error = await _require("创建 AXI GPIO", gpio_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_intf_result = await manager.connect_interface(
            "axi_interconnect_0/M00_AXI",
            "axi_gpio_0/S_AXI",
        )
        error = await _require("连接 AXI GPIO 接口", gpio_intf_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_axi_result = await manager.auto_connect_axi("axi_gpio_0")
        error = await _require("连接 AXI GPIO 时钟复位", gpio_axi_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        gpio_external_result = await bd_make_pin_external("axi_gpio_0/gpio_io_o")
        if not gpio_external_result.success:
            warnings.append(gpio_external_result.error or "GPIO 外部端口导出失败")

        uart_result = await bd_create_axi_uartlite("axi_uartlite_0")
        if not uart_result.success:
            return BDResult(
                success=False,
                message="模板创建失败",
                error=f"创建 AXI UART Lite 失败: {uart_result.error}",
            )

        uart_axi_result = await manager.connect_interface(
            "axi_interconnect_0/M01_AXI",
            "axi_uartlite_0/S_AXI",
        )
        error = await _require("连接 AXI UART Lite 接口", uart_axi_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        uart_clk_result = await manager.connect_ports(
            "processing_system7_0/FCLK_CLK0",
            "axi_uartlite_0/s_axi_aclk",
        )
        error = await _require("连接 AXI UART Lite 时钟", uart_clk_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        uart_rst_result = await manager.connect_ports(
            "proc_sys_reset_0/peripheral_aresetn",
            "axi_uartlite_0/s_axi_aresetn",
        )
        error = await _require("连接 AXI UART Lite 复位", uart_rst_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        for pin in ("axi_uartlite_0/tx", "axi_uartlite_0/rx"):
            ext_result = await bd_make_pin_external(pin)
            if not ext_result.success:
                warnings.append(ext_result.error or f"{pin} 导出失败")

        next_axi_index = 2

        if include_timer:
            created_cells.append("axi_timer_0")
            timer_result = await bd_create_axi_timer("axi_timer_0")
            if not timer_result.success:
                return BDResult(
                    success=False,
                    message="模板创建失败",
                    error=f"创建 AXI Timer 失败: {timer_result.error}",
                )

            timer_intf_result = await manager.connect_interface(
                f"axi_interconnect_0/M0{next_axi_index}_AXI",
                "axi_timer_0/S_AXI",
            )
            error = await _require("连接 AXI Timer 接口", timer_intf_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            timer_clk_result = await manager.connect_ports(
                "processing_system7_0/FCLK_CLK0",
                "axi_timer_0/s_axi_aclk",
            )
            error = await _require("连接 AXI Timer 时钟", timer_clk_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            timer_rst_result = await manager.connect_ports(
                "proc_sys_reset_0/peripheral_aresetn",
                "axi_timer_0/s_axi_aresetn",
            )
            error = await _require("连接 AXI Timer 复位", timer_rst_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            next_axi_index += 1

        if include_dma:
            created_cells.append("axi_dma_0")
            dma_result = await manager.create_axi_dma(
                "axi_dma_0",
                include_sg=dma_include_sg,
            )
            error = await _require("创建 AXI DMA", dma_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            dma_intf_result = await manager.connect_interface(
                f"axi_interconnect_0/M0{next_axi_index}_AXI",
                "axi_dma_0/S_AXI_LITE",
            )
            error = await _require("连接 AXI DMA Lite 接口", dma_intf_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            dma_clk_result = await manager.connect_ports(
                "processing_system7_0/FCLK_CLK0",
                "axi_dma_0/s_axi_lite_aclk",
            )
            error = await _require("连接 AXI DMA 时钟", dma_clk_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

            dma_rst_result = await manager.connect_ports(
                "proc_sys_reset_0/peripheral_aresetn",
                "axi_dma_0/axi_resetn",
            )
            error = await _require("连接 AXI DMA 复位", dma_rst_result)
            if error:
                return BDResult(success=False, message="模板创建失败", error=error)

        assign_result = await bd_assign_addresses()
        if not assign_result.success:
            return BDResult(
                success=False,
                message="模板创建失败",
                error=f"地址分配失败: {assign_result.error}",
            )

        validate_result = await manager.validate_design()
        error = await _require("验证模板设计", validate_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        save_result = await manager.save_design()
        error = await _require("保存模板设计", save_result)
        if error:
            return BDResult(success=False, message="模板创建失败", error=error)

        if generate_wrapper:
            wrapper_result = await bd_generate_output_and_wrapper()
            if not wrapper_result.success:
                return BDResult(
                    success=False,
                    message="模板创建失败",
                    error=f"生成输出产品与 Wrapper 失败: {wrapper_result.error}",
                )

        return BDResult(
            success=True,
            message="Zynq GPIO/UART/Timer/DMA 模板创建成功",
            error=None,
            data={
                "design_name": design_name,
                "cells": created_cells,
                "gpio_width": gpio_width,
                "include_timer": include_timer,
                "include_dma": include_dma,
                "dma_include_sg": dma_include_sg,
                "generate_wrapper": generate_wrapper,
                "warnings": warnings,
            },
        )

    @mcp.tool()
    async def bd_check_output_status() -> OutputStatusResult:
        """
        检查输出状态。

        检查当前 Block Design 的输出产品是否需要更新。

        Returns:
            OutputStatusResult 包含输出状态信息。

        Example:
            ```
            result = bd_check_output_status()
            if result.needs_update:
                print("输出产品需要更新")
            ```
        """
        logger.info("检查输出状态")

        try:
            engine = _get_engine()

            # 获取当前 BD 设计
            bd_result = await engine.execute_async('current_bd_design')
            if not bd_result.success or not bd_result.output.strip():
                return OutputStatusResult(
                    success=False,
                    message="未找到 Block Design",
                    error="请先打开或创建 Block Design",
                )

            bd_name = bd_result.output.strip()

            # 检查输出产品状态
            status_result = await engine.execute_async(
                'report_ip_status [get_files [get_property FILE_NAME [current_bd_design]]]'
            )

            needs_update = False
            products = []

            if status_result.success:
                output = status_result.output.lower()
                if 'out-of-date' in output or 'needs update' in output:
                    needs_update = True

                # 解析产品列表
                for line in status_result.output.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        products.append({"description": line})

            return OutputStatusResult(
                success=True,
                needs_update=needs_update,
                products=products,
                message="输出状态检查完成",
            )

        except Exception as e:
            logger.error(f"检查输出状态失败: {e}")
            return OutputStatusResult(
                success=False,
                message="检查输出状态失败",
                error=str(e),
            )
