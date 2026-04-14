"""
智能连接 API 测试。

测试 GateFlow.smart_connect 方法及其辅助方法。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from gateflow.api import GateFlow


class TestSmartConnect:
    """智能连接测试。"""

    @pytest.fixture
    def gateflow(self):
        """创建 GateFlow 实例。"""
        return GateFlow()

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的引擎。"""
        engine = MagicMock()
        engine.execute = AsyncMock()
        engine.execute_batch = AsyncMock()
        return engine

    # ==================== 接口连接测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_interface_auto(self, gateflow, mock_engine):
        """测试自动检测接口连接。"""
        # 模拟引擎返回
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": "axi_interconnect_0/M00_AXI"},
            # _is_interface_pin 检查源（接口端口）- 不会执行因为已经返回 True
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查源（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查目标（接口端口）
            {"success": True, "result": ""},
            # connect_bd_intf_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "axi_interconnect_0/M00_AXI",
                "axi_gpio_0/S_AXI"
            )

        assert result["success"] is True
        assert result["connect_type"] == "interface"
        assert result["source"] == "axi_interconnect_0/M00_AXI"
        assert result["target"] == "axi_gpio_0/S_AXI"

    @pytest.mark.asyncio
    async def test_smart_connect_interface_forced(self, gateflow, mock_engine):
        """测试强制接口连接。"""
        mock_engine.execute.side_effect = [
            # _get_interface_get_command 检查源
            {"success": True, "result": ""},
            # _get_interface_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_intf_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "interconnect_0/M00_AXI",
                "gpio_0/S_AXI",
                connect_type="interface"
            )

        assert result["success"] is True
        assert result["connect_type"] == "interface"

    # ==================== 信号连接测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_signal_auto(self, gateflow, mock_engine):
        """测试自动检测信号连接。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查源（接口端口）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _object_exists 检查源（普通引脚）
            {"success": True, "result": "clk_wiz_0/clk_out1"},
            # _object_exists 检查目标（普通引脚）
            {"success": True, "result": "gpio_0/s_axi_aclk"},
            # _get_signal_get_command 检查源（端口）
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标（端口）
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "clk_wiz_0/clk_out1",
                "gpio_0/s_axi_aclk"
            )

        assert result["success"] is True
        assert result["connect_type"] == "signal"
        assert result["source"] == "clk_wiz_0/clk_out1"
        assert result["target"] == "gpio_0/s_axi_aclk"

    @pytest.mark.asyncio
    async def test_smart_connect_signal_forced(self, gateflow, mock_engine):
        """测试强制信号连接。"""
        mock_engine.execute.side_effect = [
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "clk_wiz_0/clk_out1",
                "gpio_0/s_axi_aclk",
                connect_type="signal"
            )

        assert result["success"] is True
        assert result["connect_type"] == "signal"

    # ==================== 常量连接测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_gnd(self, gateflow, mock_engine):
        """测试连接到 GND。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},  # LEFT
            {"success": True, "result": "0"},  # RIGHT
            # 检查常量是否存在
            {"success": True, "result": ""},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": True, "errors": []},
            {"success": True, "errors": []},
        ]

        # 后续的信号连接
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在
            {"success": True, "result": ""},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("GND", "gpio_0/gpio_io_i")

        assert result["success"] is True
        assert result["connect_type"] == "constant"
        assert result["source"] == "GND"
        assert "gnd_const_" in result.get("constant_ip", "")

    @pytest.mark.asyncio
    async def test_smart_connect_vcc(self, gateflow, mock_engine):
        """测试连接到 VCC。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "7"},  # LEFT (8-bit)
            {"success": True, "result": "0"},  # RIGHT
            # 检查常量是否存在
            {"success": True, "result": ""},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": True, "errors": []},
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("VCC", "ip_0/enable")

        assert result["success"] is True
        assert result["connect_type"] == "constant"
        assert result["source"] == "VCC"
        assert result["constant_width"] == 8

    @pytest.mark.asyncio
    async def test_smart_connect_constant_numeric(self, gateflow, mock_engine):
        """测试使用数字表示常量。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在
            {"success": True, "result": ""},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": True, "errors": []},
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("0", "ip_0/reset")

        assert result["success"] is True
        assert result["connect_type"] == "constant"

    # ==================== 端口连接测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_external_port(self, gateflow, mock_engine):
        """测试连接到外部端口。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查源（接口端口）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _object_exists 检查源（普通引脚）
            {"success": True, "result": ""},
            # _object_exists 检查源（端口）
            {"success": True, "result": "clk"},
            # _object_exists 检查目标（普通引脚）
            {"success": True, "result": "gpio_0/s_axi_aclk"},
            # _get_signal_get_command 检查源（端口）
            {"success": True, "result": "clk"},
            # _get_signal_get_command 检查目标（端口）
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("clk", "gpio_0/s_axi_aclk")

        assert result["success"] is True
        assert result["connect_type"] == "signal"

    # ==================== 错误处理测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_invalid_objects(self, gateflow, mock_engine):
        """测试无效对象连接。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查源（接口端口）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _object_exists 检查源（普通引脚）
            {"success": True, "result": ""},
            # _object_exists 检查源（端口）
            {"success": True, "result": ""},
            # _object_exists 检查目标（普通引脚）
            {"success": True, "result": ""},
            # _object_exists 检查目标（端口）
            {"success": True, "result": ""},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("invalid_source", "invalid_target")

        assert result["success"] is False
        assert result["error"] == "源对象或目标对象不存在"

    @pytest.mark.asyncio
    async def test_smart_connect_interface_failure(self, gateflow, mock_engine):
        """测试接口连接失败。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": "interconnect_0/M00_AXI"},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查源（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查目标（接口端口）
            {"success": True, "result": ""},
            # connect_bd_intf_net 失败
            {"success": False, "errors": ["Connection failed"]},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "interconnect_0/M00_AXI",
                "gpio_0/S_AXI"
            )

        assert result["success"] is False
        assert result["error"] == "Connection failed"

    @pytest.mark.asyncio
    async def test_smart_connect_signal_failure(self, gateflow, mock_engine):
        """测试信号连接失败。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查源（接口端口）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _object_exists 检查源（普通引脚）
            {"success": True, "result": "clk"},
            # _object_exists 检查目标（普通引脚）
            {"success": True, "result": "gpio_0/s_axi_aclk"},
            # _get_signal_get_command 检查源（端口）
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标（端口）
            {"success": True, "result": ""},
            # connect_bd_net 失败
            {"success": False, "errors": ["Net connection failed"]},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("clk", "gpio_0/s_axi_aclk")

        assert result["success"] is False
        assert "Net connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_smart_connect_constant_creation_failure(self, gateflow, mock_engine):
        """测试常量创建失败。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在
            {"success": True, "result": ""},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": False, "errors": ["Failed to create constant"]},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("GND", "gpio_0/input")

        assert result["success"] is False
        assert "创建常量 IP 失败" in result["message"]

    # ==================== 辅助方法测试 ====================

    @pytest.mark.asyncio
    async def test_detect_connection_type_interface(self, gateflow, mock_engine):
        """测试检测接口连接类型。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）- 找到了，返回 True
            {"success": True, "result": "interconnect_0/M00_AXI"},
            # _is_interface_pin 检查目标（接口引脚）- 没找到
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）- 没找到
            {"success": True, "result": ""},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            conn_type = await gateflow._detect_connection_type(
                "interconnect_0/M00_AXI",
                "gpio_0/S_AXI",
                mock_engine
            )

        assert conn_type == "interface"

    @pytest.mark.asyncio
    async def test_detect_connection_type_signal(self, gateflow, mock_engine):
        """测试检测信号连接类型。"""
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查源（接口端口）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _object_exists 检查源（普通引脚）
            {"success": True, "result": "clk"},
            # _object_exists 检查目标（普通引脚）
            {"success": True, "result": "gpio_0/s_axi_aclk"},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            conn_type = await gateflow._detect_connection_type(
                "clk",
                "gpio_0/s_axi_aclk",
                mock_engine
            )

        assert conn_type == "signal"

    @pytest.mark.asyncio
    async def test_is_interface_pin_true(self, gateflow, mock_engine):
        """测试检测接口引脚（真）。"""
        mock_engine.execute.return_value = {"success": True, "result": "interconnect_0/M00_AXI"}

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow._is_interface_pin("interconnect_0/M00_AXI", mock_engine)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_interface_pin_false(self, gateflow, mock_engine):
        """测试检测接口引脚（假）。"""
        mock_engine.execute.return_value = {"success": True, "result": ""}

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow._is_interface_pin("gpio_0/gpio_io_o", mock_engine)

        assert result is False

    @pytest.mark.asyncio
    async def test_object_exists_pin(self, gateflow, mock_engine):
        """测试检测对象存在（引脚）。"""
        mock_engine.execute.return_value = {"success": True, "result": "gpio_0/gpio_io_o"}

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow._object_exists("gpio_0/gpio_io_o", mock_engine)

        assert result is True

    @pytest.mark.asyncio
    async def test_object_exists_port(self, gateflow, mock_engine):
        """测试检测对象存在（端口）。"""
        mock_engine.execute.side_effect = [
            # get_bd_pins
            {"success": True, "result": ""},
            # get_bd_ports
            {"success": True, "result": "clk"},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow._object_exists("clk", mock_engine)

        assert result is True

    @pytest.mark.asyncio
    async def test_get_pin_width_single_bit(self, gateflow, mock_engine):
        """测试获取引脚宽度（单比特）。"""
        mock_engine.execute.side_effect = [
            {"success": True, "result": "0"},  # LEFT
            {"success": True, "result": "0"},  # RIGHT
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            width = await gateflow._get_pin_width("gpio_0/gpio_io_o", mock_engine)

        assert width == 1

    @pytest.mark.asyncio
    async def test_get_pin_width_multi_bit(self, gateflow, mock_engine):
        """测试获取引脚宽度（多比特）。"""
        mock_engine.execute.side_effect = [
            {"success": True, "result": "7"},  # LEFT
            {"success": True, "result": "0"},  # RIGHT
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            width = await gateflow._get_pin_width("gpio_0/gpio_io_o", mock_engine)

        assert width == 8

    @pytest.mark.asyncio
    async def test_get_pin_width_32bit(self, gateflow, mock_engine):
        """测试获取引脚宽度（32比特）。"""
        mock_engine.execute.side_effect = [
            {"success": True, "result": "31"},  # LEFT
            {"success": True, "result": "0"},   # RIGHT
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            width = await gateflow._get_pin_width("data_bus", mock_engine)

        assert width == 32

    # ==================== 边界情况测试 ====================

    @pytest.mark.asyncio
    async def test_smart_connect_case_insensitive_constants(self, gateflow, mock_engine):
        """测试常量名称大小写不敏感。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在
            {"success": True, "result": ""},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": True, "errors": []},
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            # 测试小写
            result = await gateflow.smart_connect("gnd", "pin_0")
            assert result["success"] is True
            assert result["source"] == "GND"

    @pytest.mark.asyncio
    async def test_smart_connect_reuse_constant(self, gateflow, mock_engine):
        """测试重用已存在的常量。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在（已存在）
            {"success": True, "result": "gnd_const_pin_0"},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("GND", "pin_0")

        assert result["success"] is True
        # 不应该调用 execute_batch 创建新常量
        assert not mock_engine.execute_batch.called

    @pytest.mark.asyncio
    async def test_smart_connect_reverse_constant(self, gateflow, mock_engine):
        """测试反向常量连接（目标为常量）。"""
        mock_engine.execute.side_effect = [
            # _get_pin_width
            {"success": True, "result": "0"},
            {"success": True, "result": "0"},
            # 检查常量是否存在
            {"success": True, "result": ""},
            # _get_signal_get_command 检查源
            {"success": True, "result": ""},
            # _get_signal_get_command 检查目标
            {"success": True, "result": ""},
            # connect_bd_net
            {"success": True, "errors": []},
        ]

        mock_engine.execute_batch.return_value = [
            {"success": True, "errors": []},
            {"success": True, "errors": []},
        ]

        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect("pin_0", "GND")

        assert result["success"] is True
        assert result["connect_type"] == "constant"


@pytest.mark.integration
class TestSmartConnectIntegration:
    """智能连接集成测试。"""

    @pytest.mark.asyncio
    async def test_full_connection_workflow(self):
        """测试完整的连接工作流。"""
        gateflow = GateFlow()
        
        # 模拟完整的连接场景
        mock_engine = MagicMock()
        mock_engine.execute = AsyncMock()
        mock_engine.execute_batch = AsyncMock()
        
        # 设置模拟返回值
        mock_engine.execute.side_effect = [
            # _is_interface_pin 检查源（接口引脚）
            {"success": True, "result": "interconnect_0/M00_AXI"},
            # _is_interface_pin 检查目标（接口引脚）
            {"success": True, "result": ""},
            # _is_interface_pin 检查目标（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查源（接口端口）
            {"success": True, "result": ""},
            # _get_interface_get_command 检查目标（接口端口）
            {"success": True, "result": ""},
            # connect_bd_intf_net
            {"success": True, "errors": []},
        ]
        
        with patch.object(gateflow, '_get_engine', return_value=mock_engine):
            result = await gateflow.smart_connect(
                "interconnect_0/M00_AXI",
                "gpio_0/S_AXI"
            )
        
        assert result["success"] is True
        assert "接口连接成功" in result["message"]
