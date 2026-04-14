"""
自动时钟和中断管理模块。

参考 ADI hdl-main 项目的设计模式，提供自动化的时钟、复位和中断管理功能。
支持自动创建时钟网络、复位信号，以及自动连接中断信号到中断控制器。

主要功能：
- ClockManager: 自动管理时钟信号创建和连接
- InterruptManager: 自动管理中断信号连接和分配
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from gateflow.engine import EngineManager

logger = logging.getLogger(__name__)


class ClockSourceType(Enum):
    """时钟源类型"""
    PS7_FCLK = "ps7_fclk"      # Zynq PS7 Fabric Clock
    EXTERNAL = "external"       # 外部时钟端口
    CLOCK_WIZARD = "clock_wizard"  # 时钟向导 IP
    CUSTOM = "custom"           # 自定义时钟


class ResetSourceType(Enum):
    """复位源类型"""
    PS7_RESET = "ps7_reset"     # Zynq PS7 复位
    PROC_SYS_RESET = "proc_sys_reset"  # Processor System Reset IP
    EXTERNAL = "external"        # 外部复位端口
    CUSTOM = "custom"            # 自定义复位


@dataclass
class ClockInfo:
    """时钟信息"""
    name: str
    period: float  # 纳秒
    frequency: float  # MHz
    source_type: ClockSourceType
    source_pin: str | None = None
    connected_pins: list[str] = field(default_factory=list)


@dataclass
class ResetInfo:
    """复位信息"""
    name: str
    clock_name: str
    active_low: bool = True
    source_type: ResetSourceType = ResetSourceType.CUSTOM
    source_pin: str | None = None
    connected_pins: list[str] = field(default_factory=list)


@dataclass
class InterruptInfo:
    """中断信息"""
    irq_number: int
    source_pin: str
    source_ip: str
    connected: bool = False


class ClockManager:
    """
    时钟管理器
    
    提供自动化的时钟信号创建和连接功能，支持多种时钟源类型。
    
    Example:
        ```python
        manager = ClockManager(engine)
        
        # 创建 PS7 FCLK 时钟
        await manager.create_clock("fclk0", period=10.0, source="ps7_0/FCLK_CLK0")
        
        # 连接时钟到多个目标
        await manager.connect_clock("fclk0", ["ip0/s_axi_aclk", "ip1/s_axi_aclk"])
        
        # 自动连接 IP 实例的时钟和复位
        await manager.auto_connect_clock_reset("my_ip", "fclk0", "reset0")
        ```
    """
    
    def __init__(self, engine: EngineManager):
        """
        初始化时钟管理器。
        
        Args:
            engine: 执行引擎实例
        """
        self._engine = engine
        self._clocks: dict[str, ClockInfo] = {}
        self._resets: dict[str, ResetInfo] = {}
        self._default_clock: str | None = None
        self._default_reset: str | None = None
    
    async def create_clock(
        self,
        name: str,
        period: float,
        source: str | None = None,
        source_type: ClockSourceType = ClockSourceType.CUSTOM,
    ) -> dict[str, Any]:
        """
        创建时钟
        
        Args:
            name: 时钟名称
            period: 时钟周期（纳秒）
            source: 时钟源引脚（可选）
            source_type: 时钟源类型
        
        Returns:
            创建结果，包含时钟信息
        """
        logger.info(f"创建时钟: name={name}, period={period}ns, source={source}")
        
        frequency = 1000.0 / period  # MHz
        
        # 检查是否已存在
        if name in self._clocks:
            logger.warning(f"时钟 '{name}' 已存在")
            return {
                "success": True,
                "clock": self._clocks[name],
                "message": f"时钟 '{name}' 已存在",
            }
        
        # 如果指定了源，验证源是否存在
        if source:
            check_result = await self._engine.execute(f"get_bd_pins -quiet {source}")
            if not check_result.get("success") or not check_result.get("result", "").strip():
                # 尝试检查接口引脚
                check_result = await self._engine.execute(f"get_bd_intf_pins -quiet {source}")
                if not check_result.get("success") or not check_result.get("result", "").strip():
                    return {
                        "success": False,
                        "clock": None,
                        "message": f"时钟源 '{source}' 不存在",
                    }
        
        # 创建时钟信息
        clock_info = ClockInfo(
            name=name,
            period=period,
            frequency=frequency,
            source_type=source_type,
            source_pin=source,
        )
        
        self._clocks[name] = clock_info
        
        # 如果是第一个时钟，设为默认
        if self._default_clock is None:
            self._default_clock = name
        
        return {
            "success": True,
            "clock": clock_info,
            "message": f"时钟 '{name}' 创建成功 ({frequency:.2f} MHz)",
        }
    
    async def connect_clock(
        self,
        clock_name: str,
        target_pins: list[str],
    ) -> dict[str, Any]:
        """
        将时钟连接到多个目标
        
        Args:
            clock_name: 时钟名称
            target_pins: 目标引脚列表
        
        Returns:
            连接结果
        """
        logger.info(f"连接时钟: clock={clock_name}, targets={target_pins}")
        
        if clock_name not in self._clocks:
            return {
                "success": False,
                "connected_pins": [],
                "message": f"时钟 '{clock_name}' 不存在",
            }
        
        clock_info = self._clocks[clock_name]
        if not clock_info.source_pin:
            return {
                "success": False,
                "connected_pins": [],
                "message": f"时钟 '{clock_name}' 没有指定时钟源",
            }
        
        connected = []
        errors = []
        
        for target in target_pins:
            # 执行连接
            cmd = f"connect_bd_net [get_bd_pins {clock_info.source_pin}] [get_bd_pins {target}]"
            result = await self._engine.execute(cmd)
            
            if result.get("success"):
                connected.append(target)
                clock_info.connected_pins.append(target)
            else:
                errors.append(f"{target}: {result.get('errors', ['未知错误'])[0]}")
        
        return {
            "success": len(connected) > 0,
            "connected_pins": connected,
            "failed_pins": [p for p in target_pins if p not in connected],
            "errors": errors if errors else None,
            "message": f"成功连接 {len(connected)}/{len(target_pins)} 个引脚",
        }
    
    async def create_reset(
        self,
        name: str,
        clock_name: str,
        active_low: bool = True,
        source: str | None = None,
        source_type: ResetSourceType = ResetSourceType.CUSTOM,
    ) -> dict[str, Any]:
        """
        创建复位信号
        
        Args:
            name: 复位名称
            clock_name: 关联的时钟名称
            active_low: 是否为低电平有效
            source: 复位源引脚（可选）
            source_type: 复位源类型
        
        Returns:
            创建结果
        """
        logger.info(f"创建复位: name={name}, clock={clock_name}, active_low={active_low}")
        
        # 检查关联时钟是否存在
        if clock_name not in self._clocks:
            return {
                "success": False,
                "reset": None,
                "message": f"关联时钟 '{clock_name}' 不存在",
            }
        
        # 检查是否已存在
        if name in self._resets:
            logger.warning(f"复位 '{name}' 已存在")
            return {
                "success": True,
                "reset": self._resets[name],
                "message": f"复位 '{name}' 已存在",
            }
        
        # 如果指定了源，验证源是否存在
        if source:
            check_result = await self._engine.execute(f"get_bd_pins -quiet {source}")
            if not check_result.get("success") or not check_result.get("result", "").strip():
                return {
                    "success": False,
                    "reset": None,
                    "message": f"复位源 '{source}' 不存在",
                }
        
        # 创建复位信息
        reset_info = ResetInfo(
            name=name,
            clock_name=clock_name,
            active_low=active_low,
            source_type=source_type,
            source_pin=source,
        )
        
        self._resets[name] = reset_info
        
        # 如果是第一个复位，设为默认
        if self._default_reset is None:
            self._default_reset = name
        
        return {
            "success": True,
            "reset": reset_info,
            "message": f"复位 '{name}' 创建成功",
        }
    
    async def connect_reset(
        self,
        reset_name: str,
        target_pins: list[str],
    ) -> dict[str, Any]:
        """
        将复位连接到多个目标
        
        Args:
            reset_name: 复位名称
            target_pins: 目标引脚列表
        
        Returns:
            连接结果
        """
        logger.info(f"连接复位: reset={reset_name}, targets={target_pins}")
        
        if reset_name not in self._resets:
            return {
                "success": False,
                "connected_pins": [],
                "message": f"复位 '{reset_name}' 不存在",
            }
        
        reset_info = self._resets[reset_name]
        if not reset_info.source_pin:
            return {
                "success": False,
                "connected_pins": [],
                "message": f"复位 '{reset_name}' 没有指定复位源",
            }
        
        connected = []
        errors = []
        
        for target in target_pins:
            # 执行连接
            cmd = f"connect_bd_net [get_bd_pins {reset_info.source_pin}] [get_bd_pins {target}]"
            result = await self._engine.execute(cmd)
            
            if result.get("success"):
                connected.append(target)
                reset_info.connected_pins.append(target)
            else:
                errors.append(f"{target}: {result.get('errors', ['未知错误'])[0]}")
        
        return {
            "success": len(connected) > 0,
            "connected_pins": connected,
            "failed_pins": [p for p in target_pins if p not in connected],
            "errors": errors if errors else None,
            "message": f"成功连接 {len(connected)}/{len(target_pins)} 个引脚",
        }
    
    async def auto_connect_clock_reset(
        self,
        instance_name: str,
        clock_name: str | None = None,
        reset_name: str | None = None,
    ) -> dict[str, Any]:
        """
        自动连接 IP 实例的时钟和复位引脚
        
        自动检测 IP 实例的时钟和复位引脚，并连接到指定的时钟和复位网络。
        
        Args:
            instance_name: IP 实例名称
            clock_name: 时钟名称（可选，使用默认时钟）
            reset_name: 复位名称（可选，使用默认复位）
        
        Returns:
            连接结果
        """
        logger.info(f"自动连接时钟/复位: instance={instance_name}")
        
        # 使用默认时钟/复位
        clock_name = clock_name or self._default_clock
        reset_name = reset_name or self._default_reset
        
        # 获取 IP 实例的所有引脚
        pins_result = await self._engine.execute(f"get_bd_pins -of_objects [get_bd_cells {instance_name}]")
        if not pins_result.get("success"):
            return {
                "success": False,
                "clock_connected": [],
                "reset_connected": [],
                "message": f"无法获取 IP '{instance_name}' 的引脚",
            }
        
        pins = [p.strip() for p in pins_result.get("result", "").split('\n') if p.strip()]
        
        # 查找时钟引脚
        clock_pins = []
        reset_pins = []
        
        for pin in pins:
            pin_name = pin.split('/')[-1] if '/' in pin else pin
            
            # 常见的时钟引脚名称
            if any(clk in pin_name.lower() for clk in ['aclk', 's_axi_aclk', 'm_axi_aclk', 'clk', 'clock']):
                clock_pins.append(pin)
            
            # 常见的复位引脚名称
            if any(rst in pin_name.lower() for rst in ['aresetn', 's_axi_aresetn', 'm_axi_aresetn', 'resetn', 'rst', 'reset']):
                reset_pins.append(pin)
        
        result = {
            "success": True,
            "clock_connected": [],
            "reset_connected": [],
            "clock_pins_found": clock_pins,
            "reset_pins_found": reset_pins,
        }
        
        # 连接时钟
        if clock_pins and clock_name and clock_name in self._clocks:
            clock_result = await self.connect_clock(clock_name, clock_pins)
            result["clock_connected"] = clock_result.get("connected_pins", [])
        
        # 连接复位
        if reset_pins and reset_name and reset_name in self._resets:
            reset_result = await self.connect_reset(reset_name, reset_pins)
            result["reset_connected"] = reset_result.get("connected_pins", [])
        
        result["message"] = f"时钟连接: {len(result['clock_connected'])}, 复位连接: {len(result['reset_connected'])}"
        
        return result
    
    async def create_ps7_clocks(
        self,
        ps7_name: str = "ps7_0",
        frequencies: dict[int, float] | None = None,
    ) -> dict[str, Any]:
        """
        自动创建 PS7 的 Fabric 时钟
        
        Args:
            ps7_name: PS7 实例名称
            frequencies: FCLK 频率配置，key 为 FCLK ID (0-3)，value 为频率 (MHz)
        
        Returns:
            创建结果
        """
        logger.info(f"创建 PS7 时钟: ps7={ps7_name}")
        
        if frequencies is None:
            frequencies = {0: 100.0}  # 默认创建 100MHz FCLK0
        
        created_clocks = []
        created_resets = []
        
        for fclk_id, freq in frequencies.items():
            if fclk_id not in range(4):
                continue
            
            period = 1000.0 / freq  # ns
            
            # 创建时钟
            clock_name = f"fclk{fclk_id}"
            clock_source = f"{ps7_name}/FCLK_CLK{fclk_id}"
            
            clock_result = await self.create_clock(
                name=clock_name,
                period=period,
                source=clock_source,
                source_type=ClockSourceType.PS7_FCLK,
            )
            
            if clock_result.get("success"):
                created_clocks.append(clock_name)
            
            # 创建复位
            reset_name = f"fclk{fclk_id}_reset"
            reset_source = f"{ps7_name}/FCLK_RESET{fclk_id}_N"
            
            reset_result = await self.create_reset(
                name=reset_name,
                clock_name=clock_name,
                active_low=True,
                source=reset_source,
                source_type=ResetSourceType.PS7_RESET,
            )
            
            if reset_result.get("success"):
                created_resets.append(reset_name)
        
        return {
            "success": True,
            "clocks": created_clocks,
            "resets": created_resets,
            "message": f"创建 {len(created_clocks)} 个时钟, {len(created_resets)} 个复位",
        }
    
    async def create_proc_sys_reset(
        self,
        name: str,
        clock_name: str,
        ext_reset: str | None = None,
    ) -> dict[str, Any]:
        """
        创建 Processor System Reset IP 并自动连接
        
        Args:
            name: 复位 IP 实例名称
            clock_name: 关联的时钟名称
            ext_reset: 外部复位源（可选）
        
        Returns:
            创建结果
        """
        logger.info(f"创建 Processor System Reset: name={name}, clock={clock_name}")
        
        if clock_name not in self._clocks:
            return {
                "success": False,
                "message": f"时钟 '{clock_name}' 不存在",
            }
        
        clock_info = self._clocks[clock_name]
        
        # 创建 proc_sys_reset IP
        commands = [
            f"create_bd_cell -type ip -vlnv xilinx.com:ip:proc_sys_reset:5.0 {name}",
        ]
        
        result = await self._engine.execute(commands[0])
        if not result.get("success"):
            return {
                "success": False,
                "message": "创建 proc_sys_reset IP 失败",
                "error": result.get("errors", ["未知错误"])[0] if result.get("errors") else None,
            }
        
        # 连接时钟
        if clock_info.source_pin:
            await self._engine.execute(
                f"connect_bd_net [get_bd_pins {clock_info.source_pin}] [get_bd_pins {name}/slowest_sync_clk]"
            )
        
        # 连接外部复位
        if ext_reset:
            await self._engine.execute(
                f"connect_bd_net [get_bd_pins {ext_reset}] [get_bd_pins {name}/ext_reset_in]"
            )
        
        # 创建复位信息
        reset_name = f"{name}_peripheral_reset"
        self._resets[reset_name] = ResetInfo(
            name=reset_name,
            clock_name=clock_name,
            active_low=True,
            source_type=ResetSourceType.PROC_SYS_RESET,
            source_pin=f"{name}/peripheral_aresetn",
        )
        
        return {
            "success": True,
            "instance_name": name,
            "reset_name": reset_name,
            "message": f"Processor System Reset '{name}' 创建成功",
        }
    
    def get_clock(self, name: str) -> ClockInfo | None:
        """获取时钟信息"""
        return self._clocks.get(name)
    
    def get_reset(self, name: str) -> ResetInfo | None:
        """获取复位信息"""
        return self._resets.get(name)
    
    def list_clocks(self) -> list[dict[str, Any]]:
        """列出所有时钟"""
        return [
            {
                "name": c.name,
                "period": c.period,
                "frequency": c.frequency,
                "source_type": c.source_type.value,
                "source_pin": c.source_pin,
                "connected_count": len(c.connected_pins),
            }
            for c in self._clocks.values()
        ]
    
    def list_resets(self) -> list[dict[str, Any]]:
        """列出所有复位"""
        return [
            {
                "name": r.name,
                "clock_name": r.clock_name,
                "active_low": r.active_low,
                "source_type": r.source_type.value,
                "source_pin": r.source_pin,
                "connected_count": len(r.connected_pins),
            }
            for r in self._resets.values()
        ]


class InterruptManager:
    """
    中断管理器
    
    提供自动化的中断信号连接和分配功能，支持自动查找可用的中断号。
    
    Example:
        ```python
        manager = InterruptManager(engine)
        
        # 连接中断信号
        result = await manager.connect_interrupt("gpio_0/ip2intc_irpt", irq_number=0)
        
        # 自动分配中断号
        result = await manager.connect_interrupt("timer_0/interrupt")
        
        # 自动连接 IP 的所有中断引脚
        result = await manager.auto_connect_interrupts("my_ip")
        ```
    """
    
    # Zynq PS7 中断映射
    # IRQ_F2P[0] -> 中断号 61 (SPI 29)
    # IRQ_F2P[1] -> 中断号 62 (SPI 30)
    # ...
    MAX_IRQ_F2P = 16  # PS7 最多支持 16 个 Fabric 中断
    
    def __init__(self, engine: EngineManager):
        """
        初始化中断管理器。
        
        Args:
            engine: 执行引擎实例
        """
        self._engine = engine
        self._interrupts: dict[int, InterruptInfo] = {}
        self._next_irq = 0
        self._concat_ip: str | None = None
        self._ps7_name: str | None = None
    
    async def get_available_irq(self) -> int:
        """
        获取下一个可用的中断号
        
        Returns:
            可用的中断号
        """
        # 查找第一个未被使用的中断号
        while self._next_irq in self._interrupts:
            self._next_irq += 1
        
        return self._next_irq
    
    async def connect_interrupt(
        self,
        source_pin: str,
        irq_number: int | None = None,
        ps7_name: str | None = None,
    ) -> dict[str, Any]:
        """
        连接中断信号
        
        Args:
            source_pin: 中断源引脚
            irq_number: 指定中断号（可选，自动分配）
            ps7_name: PS7 实例名称（可选，自动检测）
        
        Returns:
            连接结果，包含分配的中断号
        """
        logger.info(f"连接中断: source={source_pin}, irq={irq_number}")
        
        # 验证中断源
        check_result = await self._engine.execute(f"get_bd_pins -quiet {source_pin}")
        if not check_result.get("success") or not check_result.get("result", "").strip():
            return {
                "success": False,
                "irq_number": None,
                "message": f"中断源 '{source_pin}' 不存在",
            }
        
        # 自动分配中断号
        if irq_number is None:
            irq_number = await self.get_available_irq()
        
        # 检查中断号是否已被使用
        if irq_number in self._interrupts:
            return {
                "success": False,
                "irq_number": irq_number,
                "message": f"中断号 {irq_number} 已被使用",
            }
        
        # 检查中断号范围
        if irq_number < 0 or irq_number >= self.MAX_IRQ_F2P:
            return {
                "success": False,
                "irq_number": irq_number,
                "message": f"中断号必须在 0-{self.MAX_IRQ_F2P - 1} 范围内",
            }
        
        # 查找 PS7 实例
        if ps7_name is None:
            ps7_name = await self._find_ps7()
        
        if ps7_name is None:
            return {
                "success": False,
                "irq_number": irq_number,
                "message": "未找到 PS7 实例",
            }
        
        self._ps7_name = ps7_name
        
        # 确保 PS7 的 Fabric 中断已启用
        await self._enable_ps7_interrupt(ps7_name)
        
        # 提取源 IP 名称
        source_ip = source_pin.split('/')[0] if '/' in source_pin else "unknown"
        
        # 创建或更新 Concat IP
        concat_result = await self._ensure_concat_ip(len(self._interrupts) + 1)
        if not concat_result.get("success"):
            return concat_result
        
        # 连接中断到 Concat IP
        concat_in_port = f"{self._concat_ip}/In{irq_number}"
        connect_result = await self._engine.execute(
            f"connect_bd_net [get_bd_pins {source_pin}] [get_bd_pins {concat_in_port}]"
        )
        
        if not connect_result.get("success"):
            return {
                "success": False,
                "irq_number": irq_number,
                "message": f"连接中断到 Concat 失败",
                "error": connect_result.get("errors", ["未知错误"])[0] if connect_result.get("errors") else None,
            }
        
        # 记录中断信息
        self._interrupts[irq_number] = InterruptInfo(
            irq_number=irq_number,
            source_pin=source_pin,
            source_ip=source_ip,
            connected=True,
        )
        
        # 更新下一个可用中断号
        self._next_irq = max(self._next_irq, irq_number + 1)
        
        return {
            "success": True,
            "irq_number": irq_number,
            "source_pin": source_pin,
            "source_ip": source_ip,
            "concat_ip": self._concat_ip,
            "message": f"中断 {irq_number} 连接成功",
        }
    
    async def auto_connect_interrupts(
        self,
        instance_name: str,
    ) -> dict[str, Any]:
        """
        自动连接 IP 实例的所有中断引脚
        
        Args:
            instance_name: IP 实例名称
        
        Returns:
            连接结果
        """
        logger.info(f"自动连接中断: instance={instance_name}")
        
        # 获取 IP 实例的所有引脚
        pins_result = await self._engine.execute(f"get_bd_pins -of_objects [get_bd_cells {instance_name}]")
        if not pins_result.get("success"):
            return {
                "success": False,
                "connected_interrupts": [],
                "message": f"无法获取 IP '{instance_name}' 的引脚",
            }
        
        pins = [p.strip() for p in pins_result.get("result", "").split('\n') if p.strip()]
        
        # 查找中断引脚
        interrupt_pins = []
        for pin in pins:
            pin_name = pin.split('/')[-1] if '/' in pin else pin
            
            # 常见的中断引脚名称
            if any(irq in pin_name.lower() for irq in ['irq', 'interrupt', 'irpt', 'intr']):
                interrupt_pins.append(pin)
        
        if not interrupt_pins:
            return {
                "success": True,
                "connected_interrupts": [],
                "interrupt_pins_found": [],
                "message": f"IP '{instance_name}' 没有找到中断引脚",
            }
        
        # 连接每个中断
        connected = []
        for pin in interrupt_pins:
            result = await self.connect_interrupt(pin)
            if result.get("success"):
                connected.append({
                    "pin": pin,
                    "irq_number": result["irq_number"],
                })
        
        return {
            "success": len(connected) > 0,
            "connected_interrupts": connected,
            "interrupt_pins_found": interrupt_pins,
            "message": f"成功连接 {len(connected)}/{len(interrupt_pins)} 个中断",
        }
    
    async def list_interrupts(self) -> list[dict]:
        """
        列出所有已连接的中断
        
        Returns:
            中断列表
        """
        return [
            {
                "irq_number": info.irq_number,
                "source_pin": info.source_pin,
                "source_ip": info.source_ip,
                "connected": info.connected,
            }
            for info in sorted(self._interrupts.values(), key=lambda x: x.irq_number)
        ]
    
    async def remove_interrupt(self, irq_number: int) -> dict[str, Any]:
        """
        移除中断连接
        
        Args:
            irq_number: 中断号
        
        Returns:
            移除结果
        """
        logger.info(f"移除中断: irq={irq_number}")
        
        if irq_number not in self._interrupts:
            return {
                "success": False,
                "message": f"中断号 {irq_number} 不存在",
            }
        
        info = self._interrupts[irq_number]
        
        # 断开连接
        if self._concat_ip:
            concat_in_port = f"{self._concat_ip}/In{irq_number}"
            # 获取网络
            net_result = await self._engine.execute(f"get_bd_nets -of_objects [get_bd_pins {concat_in_port}]")
            if net_result.get("success") and net_result.get("result", "").strip():
                net_name = net_result["result"].strip()
                await self._engine.execute(f"delete_bd_objs [get_bd_nets {net_name}]")
        
        # 移除记录
        del self._interrupts[irq_number]
        
        return {
            "success": True,
            "irq_number": irq_number,
            "message": f"中断 {irq_number} 已移除",
        }
    
    async def _find_ps7(self) -> str | None:
        """查找 PS7 实例"""
        result = await self._engine.execute("get_bd_cells -filter {VLNV =~ *processing_system7*}")
        if result.get("success") and result.get("result", "").strip():
            return result["result"].strip().split('\n')[0].strip()
        return None
    
    async def _enable_ps7_interrupt(self, ps7_name: str) -> bool:
        """启用 PS7 的 Fabric 中断"""
        # 检查是否已启用
        check_result = await self._engine.execute(
            f"get_property CONFIG.PCW_IRQ_F2P_MODE [get_bd_cells {ps7_name}]"
        )
        
        if check_result.get("success"):
            mode = check_result.get("result", "").strip()
            if mode and mode != "NONE":
                return True
        
        # 启用中断
        result = await self._engine.execute(
            f'set_property -dict [list CONFIG.PCW_IRQ_F2P_MODE "DIRECT"] [get_bd_cells {ps7_name}]'
        )
        
        return result.get("success", False)
    
    async def _ensure_concat_ip(self, num_ports: int) -> dict[str, Any]:
        """确保 Concat IP 存在且端口数量足够"""
        if self._concat_ip is None:
            # 创建 Concat IP
            concat_name = "concat_irq"
            result = await self._engine.execute(
                f"create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat:2.1 {concat_name}"
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "message": "创建 Concat IP 失败",
                }
            
            self._concat_ip = concat_name
        
        # 更新端口数量
        current_ports = len(self._interrupts) + 1
        if num_ports > current_ports:
            result = await self._engine.execute(
                f'set_property -dict [list CONFIG.NUM_PORTS "{num_ports}"] [get_bd_cells {self._concat_ip}]'
            )
            
            if not result.get("success"):
                return {
                    "success": False,
                    "message": "更新 Concat 端口数量失败",
                }
        
        # 连接 Concat 输出到 PS7 IRQ_F2P
        if self._ps7_name:
            # 检查是否已连接
            check_result = await self._engine.execute(
                f"get_bd_nets -of_objects [get_bd_pins {self._concat_ip}/dout]"
            )
            
            if not check_result.get("success") or not check_result.get("result", "").strip():
                await self._engine.execute(
                    f"connect_bd_net [get_bd_pins {self._concat_ip}/dout] [get_bd_pins {self._ps7_name}/IRQ_F2P]"
                )
        
        return {
            "success": True,
            "concat_ip": self._concat_ip,
        }
    
    def get_interrupt_summary(self) -> dict[str, Any]:
        """获取中断摘要"""
        return {
            "total_interrupts": len(self._interrupts),
            "next_available_irq": self._next_irq,
            "max_irq": self.MAX_IRQ_F2P,
            "concat_ip": self._concat_ip,
            "ps7_name": self._ps7_name,
        }
