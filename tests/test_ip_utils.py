"""
IP 工具模块测试

测试 IPRegistry 和 IPInstanceHelper 的功能。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gateflow.vivado.ip_utils import (
    IPRegistry,
    IPInstanceHelper,
    IPInfo,
    IPQueryResult,
    find_ip_vlnv,
    create_ip_instance,
)


class MockTclResult:
    """模拟 Tcl 执行结果"""

    def __init__(self, success: bool, output: str = "", errors: list = None):
        self.success = success
        self.output = output
        self.errors = errors or []
        self.data = output


class TestIPRegistry:
    """测试 IPRegistry 类"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎"""
        engine = MagicMock()
        engine.execute = AsyncMock()
        return engine

    @pytest.fixture
    def registry(self, mock_engine):
        """创建 IPRegistry 实例"""
        return IPRegistry(mock_engine)

    @pytest.mark.asyncio
    async def test_find_ip_with_short_name(self, registry, mock_engine):
        """测试使用简称查找 IP"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:2.0\n"
        )

        vlnv = await registry.find_ip("axi_gpio")

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"
        mock_engine.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_ip_with_full_vlnv(self, registry, mock_engine):
        """测试使用完整 VLNV 查找"""
        vlnv = await registry.find_ip("xilinx.com:ip:axi_gpio:2.0")

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"
        mock_engine.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_find_ip_not_found(self, registry, mock_engine):
        """测试 IP 未找到的情况"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output=""
        )

        vlnv = await registry.find_ip("nonexistent_ip")

        assert vlnv is None

    @pytest.mark.asyncio
    async def test_find_ip_multiple_versions(self, registry, mock_engine):
        """测试多个版本时选择最新版本"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:1.0\nxilinx.com:ip:axi_gpio:2.0\n"
        )

        vlnv = await registry.find_ip("axi_gpio", prefer_latest=True)

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"

    @pytest.mark.asyncio
    async def test_query_ip_multiple_candidates(self, registry, mock_engine):
        """结构化查询应标识多候选场景。"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:1.0\nxilinx.com:ip:axi_gpio:2.0\n"
        )

        result = await registry.query_ip("axi_gpio")

        assert isinstance(result, IPQueryResult)
        assert result.success is False
        assert result.error == "multiple_candidates"
        assert result.selected_vlnv == "xilinx.com:ip:axi_gpio:2.0"
        assert len(result.candidates) == 2

    @pytest.mark.asyncio
    async def test_query_ip_catalog_unavailable(self, registry, mock_engine):
        """结构化查询应区分空 catalog。"""
        mock_engine.execute.side_effect = [
            MockTclResult(success=True, output=""),
            MockTclResult(success=True, output="0\n"),
        ]

        result = await registry.query_ip("axi_gpio")

        assert result.success is False
        assert result.error == "catalog_unavailable"

    @pytest.mark.asyncio
    async def test_list_available_ips(self, registry, mock_engine):
        """测试列出可用 IP"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:2.0|axi_gpio|2.0|AXI GPIO\n"
                   "xilinx.com:ip:axi_uart:2.0|axi_uart|2.0|AXI UART\n"
        )

        ips = await registry.list_available_ips("axi*")

        assert len(ips) == 2
        assert ips[0]["name"] == "axi_gpio"
        assert ips[1]["name"] == "axi_uart"

    @pytest.mark.asyncio
    async def test_query_available_ips_no_match_but_catalog_present(self, registry, mock_engine):
        """无匹配时应返回空列表，而不是 catalog_unavailable。"""
        mock_engine.execute.side_effect = [
            MockTclResult(success=True, output=""),
            MockTclResult(success=True, output="5\n"),
        ]

        result = await registry.query_available_ips("definitely_not_found*")

        assert result["success"] is True
        assert result["error"] is None
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_ip_versions(self, registry, mock_engine):
        """测试获取 IP 版本列表"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="2.0\n1.1\n1.0\n"
        )

        versions = await registry.get_ip_versions("axi_gpio")

        assert len(versions) == 3
        assert versions[0] == "2.0"

    @pytest.mark.asyncio
    async def test_get_ip_info(self, registry, mock_engine):
        """测试获取 IP 详细信息"""
        mock_engine.execute.side_effect = [
            MockTclResult(success=True, output="xilinx.com:ip:axi_gpio:2.0\n"),
            MockTclResult(success=True, output="AXI GPIO Interface|IPI\n"),
        ]

        info = await registry.get_ip_info("axi_gpio")

        assert info is not None
        assert info.vlnv == "xilinx.com:ip:axi_gpio:2.0"
        assert info.name == "axi_gpio"
        assert info.version == "2.0"
        assert info.vendor == "xilinx.com"
        assert info.library == "ip"

    @pytest.mark.asyncio
    async def test_ip_exists(self, registry, mock_engine):
        """测试检查 IP 是否存在"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:2.0\n"
        )

        exists = await registry.ip_exists("axi_gpio")
        assert exists is True

    def test_is_full_vlnv(self, registry):
        """测试 VLNV 格式检测"""
        assert registry._is_full_vlnv("xilinx.com:ip:axi_gpio:2.0") is True
        assert registry._is_full_vlnv("axi_gpio") is False
        assert registry._is_full_vlnv("xilinx.com:ip:axi_gpio") is False

    def test_parse_version(self, registry):
        """测试版本号解析"""
        assert registry._parse_version("2.0") == (2, 0)
        assert registry._parse_version("1.1.1") == (1, 1, 1)
        assert registry._parse_version("2023.1") == (2023, 1)
        assert registry._parse_version("invalid") == (0,)

    def test_sort_versions(self, registry):
        """测试版本号排序"""
        versions = ["1.0", "2.0", "1.1", "3.0"]
        sorted_versions = registry._sort_versions(versions)

        assert sorted_versions == ["3.0", "2.0", "1.1", "1.0"]

    def test_sort_vlnvs_by_version(self, registry):
        """测试 VLNV 按版本排序"""
        vlnvs = [
            "xilinx.com:ip:axi_gpio:1.0",
            "xilinx.com:ip:axi_gpio:2.0",
            "xilinx.com:ip:axi_gpio:1.1",
        ]
        sorted_vlnvs = registry._sort_vlnvs_by_version(vlnvs)

        assert sorted_vlnvs[0] == "xilinx.com:ip:axi_gpio:2.0"


class TestIPInstanceHelper:
    """测试 IPInstanceHelper 类"""

    @pytest.fixture
    def mock_registry(self):
        """创建模拟注册表"""
        registry = MagicMock(spec=IPRegistry)
        registry.find_ip = AsyncMock()
        return registry

    @pytest.fixture
    def helper(self, mock_registry):
        """创建 IPInstanceHelper 实例"""
        return IPInstanceHelper(mock_registry)

    @pytest.mark.asyncio
    async def test_create_bd_cell_with_short_name(self, helper, mock_registry):
        """测试使用简称创建 BD 单元"""
        mock_registry.find_ip.return_value = "xilinx.com:ip:axi_gpio:2.0"

        vlnv, commands = await helper.create_bd_cell(
            "axi_gpio",
            "gpio_0",
            {"C_GPIO_WIDTH": 8}
        )

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"
        assert "create_bd_cell" in commands["create"]
        assert "gpio_0" in commands["create"]
        assert len(commands["config"]) == 1
        assert "CONFIG.C_GPIO_WIDTH" in commands["config"][0]

    @pytest.mark.asyncio
    async def test_create_bd_cell_with_full_vlnv(self, helper, mock_registry):
        """测试使用完整 VLNV 创建 BD 单元"""
        mock_registry.find_ip.return_value = "xilinx.com:ip:axi_gpio:2.0"

        vlnv, commands = await helper.create_bd_cell(
            "xilinx.com:ip:axi_gpio:2.0",
            "gpio_0"
        )

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"

    @pytest.mark.asyncio
    async def test_create_bd_cell_ip_not_found(self, helper, mock_registry):
        """测试 IP 未找到时抛出异常"""
        mock_registry.find_ip.return_value = None

        with pytest.raises(ValueError, match="未找到 IP"):
            await helper.create_bd_cell("nonexistent_ip", "inst_0")

    def test_format_config_value(self, helper):
        """测试配置值格式化"""
        assert helper._format_config_value(True) == "1"
        assert helper._format_config_value(False) == "0"
        assert helper._format_config_value(42) == "42"
        assert helper._format_config_value("simple") == "simple"
        assert helper._format_config_value("with space") == "{with space}"
        assert helper._format_config_value([1, 2, 3]) == "{1 2 3}"


class TestConvenienceFunctions:
    """测试便捷函数"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎"""
        engine = MagicMock()
        engine.execute = AsyncMock()
        return engine

    @pytest.mark.asyncio
    async def test_find_ip_vlnv(self, mock_engine):
        """测试便捷查找函数"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:2.0\n"
        )

        vlnv = await find_ip_vlnv(mock_engine, "axi_gpio")

        assert vlnv == "xilinx.com:ip:axi_gpio:2.0"

    @pytest.mark.asyncio
    async def test_create_ip_instance(self, mock_engine):
        """测试便捷创建实例函数"""
        mock_engine.execute.return_value = MockTclResult(
            success=True,
            output="xilinx.com:ip:axi_gpio:2.0\n"
        )

        result = await create_ip_instance(
            mock_engine,
            "axi_gpio",
            "gpio_0",
            {"C_GPIO_WIDTH": 8}
        )

        assert result["vlnv"] == "xilinx.com:ip:axi_gpio:2.0"
        assert "commands" in result


class TestIPInfo:
    """测试 IPInfo 数据类"""

    def test_ip_info_creation(self):
        """测试 IPInfo 创建"""
        info = IPInfo(
            vlnv="xilinx.com:ip:axi_gpio:2.0",
            vendor="xilinx.com",
            library="ip",
            name="axi_gpio",
            version="2.0",
            description="AXI GPIO Interface",
        )

        assert info.vlnv == "xilinx.com:ip:axi_gpio:2.0"
        assert info.name == "axi_gpio"
        assert info.version == "2.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
