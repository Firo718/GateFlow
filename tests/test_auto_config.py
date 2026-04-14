"""
自动配置模块测试。

测试 ClockManager 和 InterruptManager 的功能。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.utils.auto_config import (
    ClockManager,
    InterruptManager,
    ClockSourceType,
    ResetSourceType,
    ClockInfo,
    ResetInfo,
    InterruptInfo,
)


# ==================== ClockManager 测试 ====================


class TestClockManager:
    """ClockManager 测试类。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎。"""
        engine = MagicMock()
        engine.execute = AsyncMock()
        return engine

    @pytest.fixture
    def clock_manager(self, mock_engine):
        """创建时钟管理器实例。"""
        return ClockManager(mock_engine)

    @pytest.mark.asyncio
    async def test_create_clock(self, clock_manager, mock_engine):
        """测试创建时钟。"""
        # 模拟源引脚存在
        mock_engine.execute.return_value = {
            "success": True,
            "result": "ps7_0/FCLK_CLK0",
        }

        result = await clock_manager.create_clock(
            name="fclk0",
            period=10.0,
            source="ps7_0/FCLK_CLK0",
        )

        assert result["success"] is True
        assert result["clock"].name == "fclk0"
        assert result["clock"].period == 10.0
        assert result["clock"].frequency == 100.0  # 1000/10

    @pytest.mark.asyncio
    async def test_create_clock_without_source(self, clock_manager):
        """测试创建不带源的时钟。"""
        result = await clock_manager.create_clock(
            name="custom_clk",
            period=5.0,
        )

        assert result["success"] is True
        assert result["clock"].name == "custom_clk"
        assert result["clock"].source_pin is None

    @pytest.mark.asyncio
    async def test_create_clock_already_exists(self, clock_manager, mock_engine):
        """测试创建已存在的时钟。"""
        # 第一次创建
        mock_engine.execute.return_value = {"success": True, "result": "source"}
        await clock_manager.create_clock("fclk0", 10.0, "source")

        # 第二次创建同名时钟
        result = await clock_manager.create_clock("fclk0", 10.0, "source")

        assert result["success"] is True
        assert "已存在" in result["message"]

    @pytest.mark.asyncio
    async def test_connect_clock(self, clock_manager, mock_engine):
        """测试连接时钟。"""
        # 先创建时钟
        mock_engine.execute.return_value = {"success": True, "result": "source"}
        await clock_manager.create_clock("fclk0", 10.0, "ps7_0/FCLK_CLK0")

        # 连接时钟
        mock_engine.execute.return_value = {"success": True}
        result = await clock_manager.connect_clock(
            "fclk0",
            ["gpio_0/s_axi_aclk", "timer_0/s_axi_aclk"],
        )

        assert result["success"] is True
        assert len(result["connected_pins"]) == 2

    @pytest.mark.asyncio
    async def test_connect_clock_not_found(self, clock_manager):
        """测试连接不存在的时钟。"""
        result = await clock_manager.connect_clock(
            "nonexistent",
            ["gpio_0/s_axi_aclk"],
        )

        assert result["success"] is False
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_create_reset(self, clock_manager, mock_engine):
        """测试创建复位。"""
        # 先创建时钟
        mock_engine.execute.return_value = {"success": True, "result": "source"}
        await clock_manager.create_clock("fclk0", 10.0, "ps7_0/FCLK_CLK0")

        # 创建复位
        result = await clock_manager.create_reset(
            name="fclk0_reset",
            clock_name="fclk0",
            active_low=True,
            source="ps7_0/FCLK_RESET0_N",
        )

        assert result["success"] is True
        assert result["reset"].name == "fclk0_reset"
        assert result["reset"].active_low is True

    @pytest.mark.asyncio
    async def test_create_reset_clock_not_found(self, clock_manager):
        """测试创建复位但关联时钟不存在。"""
        result = await clock_manager.create_reset(
            name="reset",
            clock_name="nonexistent",
        )

        assert result["success"] is False
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_connect_reset(self, clock_manager, mock_engine):
        """测试连接复位。"""
        # 创建时钟和复位
        mock_engine.execute.return_value = {"success": True, "result": "source"}
        await clock_manager.create_clock("fclk0", 10.0, "ps7_0/FCLK_CLK0")
        await clock_manager.create_reset("fclk0_reset", "fclk0", True, "ps7_0/FCLK_RESET0_N")

        # 连接复位
        mock_engine.execute.return_value = {"success": True}
        result = await clock_manager.connect_reset(
            "fclk0_reset",
            ["gpio_0/s_axi_aresetn"],
        )

        assert result["success"] is True
        assert len(result["connected_pins"]) == 1

    @pytest.mark.asyncio
    async def test_auto_connect_clock_reset(self, clock_manager, mock_engine):
        """测试自动连接时钟和复位。"""
        # 创建时钟和复位
        mock_engine.execute.return_value = {"success": True, "result": "source"}
        await clock_manager.create_clock("fclk0", 10.0, "ps7_0/FCLK_CLK0")
        await clock_manager.create_reset("fclk0_reset", "fclk0", True, "ps7_0/FCLK_RESET0_N")

        # 模拟获取引脚列表
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/s_axi_aclk\ngpio_0/s_axi_aresetn",
        }

        result = await clock_manager.auto_connect_clock_reset("gpio_0")

        assert result["success"] is True
        assert "clock_pins_found" in result
        assert "reset_pins_found" in result

    @pytest.mark.asyncio
    async def test_create_ps7_clocks(self, clock_manager, mock_engine):
        """测试创建 PS7 时钟。"""
        mock_engine.execute.return_value = {"success": True, "result": "source"}

        result = await clock_manager.create_ps7_clocks(
            ps7_name="ps7_0",
            frequencies={0: 100.0, 1: 200.0},
        )

        assert result["success"] is True
        assert len(result["clocks"]) == 2
        assert len(result["resets"]) == 2

    def test_list_clocks(self, clock_manager, mock_engine):
        """测试列出时钟。"""
        # 手动添加时钟
        clock_manager._clocks["fclk0"] = ClockInfo(
            name="fclk0",
            period=10.0,
            frequency=100.0,
            source_type=ClockSourceType.PS7_FCLK,
            source_pin="ps7_0/FCLK_CLK0",
        )

        clocks = clock_manager.list_clocks()

        assert len(clocks) == 1
        assert clocks[0]["name"] == "fclk0"
        assert clocks[0]["frequency"] == 100.0

    def test_list_resets(self, clock_manager):
        """测试列出复位。"""
        # 手动添加时钟和复位
        clock_manager._clocks["fclk0"] = ClockInfo(
            name="fclk0",
            period=10.0,
            frequency=100.0,
            source_type=ClockSourceType.PS7_FCLK,
        )
        clock_manager._resets["fclk0_reset"] = ResetInfo(
            name="fclk0_reset",
            clock_name="fclk0",
            active_low=True,
        )

        resets = clock_manager.list_resets()

        assert len(resets) == 1
        assert resets[0]["name"] == "fclk0_reset"
        assert resets[0]["active_low"] is True


# ==================== InterruptManager 测试 ====================


class TestInterruptManager:
    """InterruptManager 测试类。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎。"""
        engine = MagicMock()
        engine.execute = AsyncMock()
        return engine

    @pytest.fixture
    def interrupt_manager(self, mock_engine):
        """创建中断管理器实例。"""
        return InterruptManager(mock_engine)

    @pytest.mark.asyncio
    async def test_get_available_irq(self, interrupt_manager):
        """测试获取可用中断号。"""
        irq = await interrupt_manager.get_available_irq()
        assert irq == 0

        # 添加一个中断
        interrupt_manager._interrupts[0] = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
        )

        irq = await interrupt_manager.get_available_irq()
        assert irq == 1

    @pytest.mark.asyncio
    async def test_connect_interrupt(self, interrupt_manager, mock_engine):
        """测试连接中断。"""
        # 模拟源引脚存在
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/ip2intc_irpt",
        }

        # 模拟查找 PS7
        with patch.object(interrupt_manager, '_find_ps7', return_value="ps7_0"):
            with patch.object(interrupt_manager, '_enable_ps7_interrupt', return_value=True):
                with patch.object(interrupt_manager, '_ensure_concat_ip', return_value={"success": True}):
                    result = await interrupt_manager.connect_interrupt(
                        source_pin="gpio_0/ip2intc_irpt",
                        irq_number=0,
                    )

        assert result["success"] is True
        assert result["irq_number"] == 0

    @pytest.mark.asyncio
    async def test_connect_interrupt_auto_assign(self, interrupt_manager, mock_engine):
        """测试自动分配中断号。"""
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/ip2intc_irpt",
        }

        with patch.object(interrupt_manager, '_find_ps7', return_value="ps7_0"):
            with patch.object(interrupt_manager, '_enable_ps7_interrupt', return_value=True):
                with patch.object(interrupt_manager, '_ensure_concat_ip', return_value={"success": True}):
                    result = await interrupt_manager.connect_interrupt(
                        source_pin="gpio_0/ip2intc_irpt",
                    )

        assert result["success"] is True
        assert result["irq_number"] == 0

    @pytest.mark.asyncio
    async def test_connect_interrupt_source_not_found(self, interrupt_manager, mock_engine):
        """测试中断源不存在。"""
        mock_engine.execute.return_value = {"success": False, "result": ""}

        result = await interrupt_manager.connect_interrupt(
            source_pin="nonexistent/irq",
        )

        assert result["success"] is False
        assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_connect_interrupt_already_used(self, interrupt_manager, mock_engine):
        """测试中断号已被使用。"""
        # 添加已存在的中断
        interrupt_manager._interrupts[0] = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
        )

        mock_engine.execute.return_value = {
            "success": True,
            "result": "timer_0/interrupt",
        }

        result = await interrupt_manager.connect_interrupt(
            source_pin="timer_0/interrupt",
            irq_number=0,
        )

        assert result["success"] is False
        assert "已被使用" in result["message"]

    @pytest.mark.asyncio
    async def test_connect_interrupt_out_of_range(self, interrupt_manager, mock_engine):
        """测试中断号超出范围。"""
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/ip2intc_irpt",
        }

        result = await interrupt_manager.connect_interrupt(
            source_pin="gpio_0/ip2intc_irpt",
            irq_number=100,
        )

        assert result["success"] is False
        assert "范围" in result["message"]

    @pytest.mark.asyncio
    async def test_auto_connect_interrupts(self, interrupt_manager, mock_engine):
        """测试自动连接中断。"""
        # 模拟获取引脚列表
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/ip2intc_irpt\ngpio_0/gpio_io_o",
        }

        with patch.object(interrupt_manager, 'connect_interrupt') as mock_connect:
            mock_connect.return_value = {
                "success": True,
                "irq_number": 0,
            }

            result = await interrupt_manager.auto_connect_interrupts("gpio_0")

        assert result["success"] is True
        assert "interrupt_pins_found" in result

    @pytest.mark.asyncio
    async def test_auto_connect_interrupts_no_irq_pins(self, interrupt_manager, mock_engine):
        """测试自动连接但没有中断引脚。"""
        mock_engine.execute.return_value = {
            "success": True,
            "result": "gpio_0/gpio_io_o\ngpio_0/gpio_io_i",
        }

        result = await interrupt_manager.auto_connect_interrupts("gpio_0")

        assert result["success"] is True
        assert len(result["connected_interrupts"]) == 0

    @pytest.mark.asyncio
    async def test_list_interrupts(self, interrupt_manager):
        """测试列出中断。"""
        interrupt_manager._interrupts[0] = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
            connected=True,
        )
        interrupt_manager._interrupts[1] = InterruptInfo(
            irq_number=1,
            source_pin="timer_0/interrupt",
            source_ip="timer_0",
            connected=True,
        )

        interrupts = await interrupt_manager.list_interrupts()

        assert len(interrupts) == 2
        assert interrupts[0]["irq_number"] == 0
        assert interrupts[1]["irq_number"] == 1

    @pytest.mark.asyncio
    async def test_remove_interrupt(self, interrupt_manager, mock_engine):
        """测试移除中断。"""
        interrupt_manager._interrupts[0] = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
        )
        interrupt_manager._concat_ip = "concat_irq"

        mock_engine.execute.return_value = {"success": True, "result": "net_name"}

        result = await interrupt_manager.remove_interrupt(0)

        assert result["success"] is True
        assert 0 not in interrupt_manager._interrupts

    @pytest.mark.asyncio
    async def test_remove_interrupt_not_found(self, interrupt_manager):
        """测试移除不存在的中断。"""
        result = await interrupt_manager.remove_interrupt(0)

        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_get_interrupt_summary(self, interrupt_manager):
        """测试获取中断摘要。"""
        interrupt_manager._interrupts[0] = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
        )
        interrupt_manager._concat_ip = "concat_irq"
        interrupt_manager._ps7_name = "ps7_0"

        summary = interrupt_manager.get_interrupt_summary()

        assert summary["total_interrupts"] == 1
        assert summary["concat_ip"] == "concat_irq"
        assert summary["ps7_name"] == "ps7_0"


# ==================== 数据类测试 ====================


class TestDataClasses:
    """数据类测试。"""

    def test_clock_info(self):
        """测试 ClockInfo 数据类。"""
        clock = ClockInfo(
            name="fclk0",
            period=10.0,
            frequency=100.0,
            source_type=ClockSourceType.PS7_FCLK,
            source_pin="ps7_0/FCLK_CLK0",
        )

        assert clock.name == "fclk0"
        assert clock.period == 10.0
        assert clock.frequency == 100.0
        assert clock.source_type == ClockSourceType.PS7_FCLK
        assert clock.connected_pins == []

    def test_reset_info(self):
        """测试 ResetInfo 数据类。"""
        reset = ResetInfo(
            name="fclk0_reset",
            clock_name="fclk0",
            active_low=True,
            source_type=ResetSourceType.PS7_RESET,
        )

        assert reset.name == "fclk0_reset"
        assert reset.clock_name == "fclk0"
        assert reset.active_low is True
        assert reset.source_type == ResetSourceType.PS7_RESET

    def test_interrupt_info(self):
        """测试 InterruptInfo 数据类。"""
        irq = InterruptInfo(
            irq_number=0,
            source_pin="gpio_0/ip2intc_irpt",
            source_ip="gpio_0",
            connected=True,
        )

        assert irq.irq_number == 0
        assert irq.source_pin == "gpio_0/ip2intc_irpt"
        assert irq.connected is True


# ==================== 枚举测试 ====================


class TestEnums:
    """枚举测试。"""

    def test_clock_source_type(self):
        """测试时钟源类型枚举。"""
        assert ClockSourceType.PS7_FCLK.value == "ps7_fclk"
        assert ClockSourceType.EXTERNAL.value == "external"
        assert ClockSourceType.CLOCK_WIZARD.value == "clock_wizard"
        assert ClockSourceType.CUSTOM.value == "custom"

    def test_reset_source_type(self):
        """测试复位源类型枚举。"""
        assert ResetSourceType.PS7_RESET.value == "ps7_reset"
        assert ResetSourceType.PROC_SYS_RESET.value == "proc_sys_reset"
        assert ResetSourceType.EXTERNAL.value == "external"
        assert ResetSourceType.CUSTOM.value == "custom"
