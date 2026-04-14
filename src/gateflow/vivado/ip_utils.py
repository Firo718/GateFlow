"""
Vivado IP 工具模块

提供 IP 核查找、版本管理等功能，参考 ADI hdl-main 项目的设计模式。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class IPInfo:
    """IP 核信息"""
    vlnv: str  # 完整 VLNV，如 "xilinx.com:ip:axi_gpio:2.0"
    vendor: str  # 供应商，如 "xilinx.com"
    library: str  # 库，如 "ip"
    name: str  # IP 名称，如 "axi_gpio"
    version: str  # 版本号，如 "2.0"
    description: str = ""  # IP 描述
    design_tool_contexts: str = ""  # 设计工具上下文


@dataclass
class IPDefinition:
    """IP 定义信息"""
    vlnv: str
    name: str
    version: str
    is_upgrade: bool = False  # 是否为升级版本
    is_locked: bool = False  # 是否锁定


@dataclass
class IPQueryResult:
    """Structured result for high-level IP lookup flows."""

    success: bool
    error: str | None
    message: str
    candidates: list[str] = field(default_factory=list)
    selected_vlnv: str | None = None
    catalog_available: bool = True
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a plain dictionary."""
        return {
            "success": self.success,
            "error": self.error,
            "message": self.message,
            "candidates": self.candidates,
            "selected_vlnv": self.selected_vlnv,
            "catalog_available": self.catalog_available,
            "details": self.details,
        }


class IPRegistry:
    """
    IP 核注册表，管理和查找 IP 定义

    参考 ADI 的 ad_ip_instance 函数设计，提供 IP 自动查找功能。
    用户只需要提供 IP 简称，函数会自动查找完整的 VLNV。

    Example:
        ```python
        registry = IPRegistry(engine)

        # 自动查找最新版本的 axi_gpio
        vlnv = await registry.find_ip("axi_gpio")
        # 返回: "xilinx.com:ip:axi_gpio:2.0"

        # 列出所有可用的 IP
        ips = await registry.list_available_ips("axi*")

        # 获取特定 IP 的所有版本
        versions = await registry.get_ip_versions("axi_gpio")
        ```
    """

    def __init__(self, engine):
        """
        初始化 IP 注册表

        Args:
            engine: TclEngine 实例，用于执行 Tcl 命令
        """
        self.engine = engine
        self._ip_cache: dict[str, list[IPInfo]] = {}

    async def _execute_ip_query(self, tcl_cmd: str) -> tuple[bool, str, str | None]:
        """Execute a Tcl query and normalize the output/error fields."""
        result = await self.engine.execute(tcl_cmd)
        if not result.success:
            error_msg = result.error.message if getattr(result, "error", None) else "未知错误"
            return False, "", error_msg
        return True, (result.data or result.output or ""), None

    async def _catalog_count(self) -> tuple[int | None, str | None]:
        """Return the size of the non-upgrade IPI-capable catalog."""
        tcl_cmd = r'''
            set ip_defs [get_ipdefs -all -filter "design_tool_contexts =~ *IPI* && UPGRADE_VERSIONS == \"\""]
            puts [llength $ip_defs]
        '''
        success, output, error = await self._execute_ip_query(tcl_cmd)
        if not success:
            return None, error
        try:
            return int(output.strip() or "0"), None
        except ValueError:
            return None, f"invalid_catalog_count: {output.strip()}"

    def _parse_vlnv_lines(self, output: str) -> list[str]:
        """Parse a Tcl output block into VLNV lines."""
        return [
            line.strip()
            for line in output.strip().split("\n")
            if line.strip() and ":" in line
        ]

    async def query_ip(
        self,
        ip_name: str,
        *,
        prefer_latest: bool = True,
    ) -> IPQueryResult:
        """Return a structured result for an IP lookup."""
        if self._is_full_vlnv(ip_name):
            return IPQueryResult(
                success=True,
                error=None,
                message=f"输入已是完整 VLNV: {ip_name}",
                candidates=[ip_name],
                selected_vlnv=ip_name,
            )

        tcl_cmd = f'''
            set ip_defs [get_ipdefs -all -filter "VLNV =~ *:{ip_name}:* && \
                design_tool_contexts =~ *IPI* && UPGRADE_VERSIONS == \\"\\"]]

            if {{[llength $ip_defs] > 0}} {{
                foreach ip_def $ip_defs {{
                    puts $ip_def
                }}
            }}
        '''

        success, output, error = await self._execute_ip_query(tcl_cmd)
        if not success:
            logger.error(f"查找 IP '{ip_name}' 失败: {error}")
            return IPQueryResult(
                success=False,
                error="tcp_protocol_error",
                message=f"查找 IP 失败: {ip_name}",
                catalog_available=False,
                details=error,
            )

        vlnvs = self._parse_vlnv_lines(output)
        if not vlnvs:
            catalog_count, catalog_error = await self._catalog_count()
            if catalog_count is None:
                return IPQueryResult(
                    success=False,
                    error="tcp_protocol_error",
                    message=f"查找 IP 失败: {ip_name}",
                    catalog_available=False,
                    details=catalog_error,
                )
            if catalog_count == 0:
                return IPQueryResult(
                    success=False,
                    error="catalog_unavailable",
                    message="Vivado IP catalog 不可用或为空",
                    catalog_available=False,
                )
            return IPQueryResult(
                success=False,
                error="ip_not_found",
                message=f"未找到 IP: {ip_name}",
                catalog_available=True,
            )

        sorted_vlnvs = self._sort_vlnvs_by_version(vlnvs)
        if len(sorted_vlnvs) > 1:
            return IPQueryResult(
                success=False,
                error="multiple_candidates",
                message=f"IP '{ip_name}' 匹配到多个候选项",
                candidates=sorted_vlnvs,
                selected_vlnv=sorted_vlnvs[0] if prefer_latest else None,
                catalog_available=True,
            )

        return IPQueryResult(
            success=True,
            error=None,
            message=f"找到 IP: {sorted_vlnvs[0]}",
            candidates=sorted_vlnvs,
            selected_vlnv=sorted_vlnvs[0],
            catalog_available=True,
        )

    async def query_available_ips(
        self,
        filter_pattern: str = "*",
        include_versions: bool = False,
    ) -> dict[str, Any]:
        """Return a structured result for catalog listing."""
        tcl_cmd = f'''
            set ip_defs [get_ipdefs -all -filter "VLNV =~ *:{filter_pattern}:* && \
                design_tool_contexts =~ *IPI* && UPGRADE_VERSIONS == \\"\\"]]

            foreach ip_def $ip_defs {{
                set name [get_property NAME $ip_def]
                set version [get_property VERSION $ip_def]
                set description [get_property DESCRIPTION $ip_def]
                puts "$ip_def|$name|$version|$description"
            }}
        '''

        success, output, error = await self._execute_ip_query(tcl_cmd)
        if not success:
            logger.error(f"列出 IP 失败: {error}")
            return {
                "success": False,
                "error": "tcp_protocol_error",
                "message": "获取 IP catalog 失败",
                "ips": [],
                "count": 0,
                "catalog_available": False,
                "details": error,
            }

        ip_list = []
        seen_ips = set()
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line or '|' not in line:
                continue

            parts = line.split('|')
            if len(parts) >= 3:
                vlnv = parts[0]
                name = parts[1]
                version = parts[2]
                description = parts[3] if len(parts) > 3 else ""

                if not include_versions:
                    if name in seen_ips:
                        continue
                    seen_ips.add(name)

                ip_list.append(
                    {
                        "name": name,
                        "vlnv": vlnv,
                        "version": version,
                        "description": description,
                    }
                )

        if not ip_list:
            catalog_count, catalog_error = await self._catalog_count()
            if catalog_count is None:
                return {
                    "success": False,
                    "error": "tcp_protocol_error",
                    "message": "获取 IP catalog 失败",
                    "ips": [],
                    "count": 0,
                    "catalog_available": False,
                    "details": catalog_error,
                }
            if catalog_count == 0:
                return {
                    "success": False,
                    "error": "catalog_unavailable",
                    "message": "Vivado IP catalog 不可用或为空",
                    "ips": [],
                    "count": 0,
                    "catalog_available": False,
                    "details": None,
                }

        logger.info(f"找到 {len(ip_list)} 个 IP")
        return {
            "success": True,
            "error": None,
            "message": f"找到 {len(ip_list)} 个 IP",
            "ips": ip_list,
            "count": len(ip_list),
            "catalog_available": True,
            "details": None,
        }

    async def find_ip(
        self,
        ip_name: str,
        prefer_latest: bool = True,
    ) -> str | None:
        """
        根据 IP 简称查找完整的 VLNV

        参考 ADI 的实现：
        ```tcl
        set ip_def [get_ipdefs -all -filter "VLNV =~ *:${i_ip}:* && \
            design_tool_contexts =~ *IPI* && UPGRADE_VERSIONS == \"\""]
        ```

        Args:
            ip_name: IP 简称（如 "axi_gpio", "processing_system7"）或完整 VLNV
            prefer_latest: 是否优先返回最新版本

        Returns:
            完整的 VLNV 字符串，如 "xilinx.com:ip:axi_gpio:2.0"
            如果未找到则返回 None

        Example:
            ```python
            # 简称查找
            vlnv = await registry.find_ip("axi_gpio")
            # 返回: "xilinx.com:ip:axi_gpio:2.0"

            # 如果已经是完整 VLNV，直接返回
            vlnv = await registry.find_ip("xilinx.com:ip:axi_gpio:2.0")
            # 返回: "xilinx.com:ip:axi_gpio:2.0"
            ```
        """
        query = await self.query_ip(ip_name, prefer_latest=prefer_latest)
        if query.success:
            return query.selected_vlnv
        if query.error == "multiple_candidates" and query.selected_vlnv and prefer_latest:
            logger.info(
                f"找到 IP '{ip_name}' 的 {len(query.candidates)} 个版本，选择最新版本: {query.selected_vlnv}"
            )
            return query.selected_vlnv
        logger.warning(f"未找到可直接解析的 IP: {ip_name}, error={query.error}")
        return None

    async def list_available_ips(
        self,
        filter_pattern: str = "*",
        include_versions: bool = False,
    ) -> list[dict[str, Any]]:
        """
        列出所有可用的 IP 核

        Args:
            filter_pattern: 过滤模式（支持通配符），如 "axi*", "*gpio*"
            include_versions: 是否包含所有版本信息

        Returns:
            IP 信息列表，每个元素包含：
            - name: IP 名称
            - vlnv: 完整 VLNV
            - version: 版本号
            - description: 描述（如果有）

        Example:
            ```python
            # 列出所有 AXI 相关的 IP
            ips = await registry.list_available_ips("axi*")

            # 列出所有 IP
            all_ips = await registry.list_available_ips()
            ```
        """
        result = await self.query_available_ips(filter_pattern, include_versions=include_versions)
        return result.get("ips", [])

    async def get_ip_versions(self, ip_name: str) -> list[str]:
        """
        获取指定 IP 的所有可用版本

        Args:
            ip_name: IP 简称

        Returns:
            版本号列表，按从新到旧排序，如 ["2.0", "1.1"]

        Example:
            ```python
            versions = await registry.get_ip_versions("axi_gpio")
            # 返回: ["2.0", "1.1"]
            ```
        """
        tcl_cmd = f'''
            set ip_defs [get_ipdefs -all -filter "VLNV =~ *:{ip_name}:* && \
                design_tool_contexts =~ *IPI*"]

            foreach ip_def $ip_defs {{
                set version [get_property VERSION $ip_def]
                puts $version
            }}
        '''

        result = await self.engine.execute(tcl_cmd)

        if not result.success:
            error_msg = result.error.message if result.error else "未知错误"
            logger.error(f"获取 IP '{ip_name}' 版本失败: {error_msg}")
            return []

        # 解析输出并去重
        versions = set()
        output = result.data or ""
        for line in output.strip().split('\n'):
            line = line.strip()
            if line:
                versions.add(line)

        # 按版本号排序
        sorted_versions = self._sort_versions(list(versions))
        logger.info(f"IP '{ip_name}' 有 {len(sorted_versions)} 个版本: {sorted_versions}")
        return sorted_versions

    async def get_ip_info(self, ip_name: str) -> IPInfo | None:
        """
        获取 IP 的详细信息

        Args:
            ip_name: IP 简称或完整 VLNV

        Returns:
            IPInfo 对象，如果未找到则返回 None
        """
        # 先查找 VLNV
        vlnv = await self.find_ip(ip_name)
        if not vlnv:
            return None

        # 解析 VLNV
        parts = vlnv.split(':')
        if len(parts) != 4:
            logger.error(f"无效的 VLNV 格式: {vlnv}")
            return None

        vendor, library, name, version = parts

        # 获取详细信息
        tcl_cmd = f'''
            set ip_def [get_ipdefs -filter "VLNV == {vlnv}"]
            if {{[llength $ip_def] > 0}} {{
                set description [get_property DESCRIPTION $ip_def]
                set contexts [get_property design_tool_contexts $ip_def]
                puts "$description|$contexts"
            }}
        '''

        result = await self.engine.execute(tcl_cmd)

        description = ""
        contexts = ""

        output = result.data or ""
        if result.success and output.strip():
            parts = output.strip().split('|')
            if len(parts) >= 1:
                description = parts[0]
            if len(parts) >= 2:
                contexts = parts[1]

        return IPInfo(
            vlnv=vlnv,
            vendor=vendor,
            library=library,
            name=name,
            version=version,
            description=description,
            design_tool_contexts=contexts,
        )

    async def ip_exists(self, ip_name: str) -> bool:
        """
        检查 IP 是否存在

        Args:
            ip_name: IP 简称或完整 VLNV

        Returns:
            IP 是否存在
        """
        vlnv = await self.find_ip(ip_name)
        return vlnv is not None

    def _is_full_vlnv(self, name: str) -> bool:
        """
        检查是否为完整的 VLNV

        VLNV 格式: vendor:library:name:version
        例如: xilinx.com:ip:axi_gpio:2.0

        Args:
            name: 要检查的名称

        Returns:
            是否为完整 VLNV
        """
        parts = name.split(':')
        return len(parts) == 4

    def _sort_vlnvs_by_version(self, vlnvs: list[str]) -> list[str]:
        """
        按 VLNV 中的版本号排序（从新到旧）

        Args:
            vlnvs: VLNV 列表

        Returns:
            排序后的 VLNV 列表
        """
        def extract_version(vlnv: str) -> tuple:
            """从 VLNV 中提取版本号用于排序"""
            parts = vlnv.split(':')
            if len(parts) == 4:
                version = parts[3]
                return self._parse_version(version)
            return (0, 0, 0)

        return sorted(vlnvs, key=extract_version, reverse=True)

    def _sort_versions(self, versions: list[str]) -> list[str]:
        """
        对版本号列表排序（从新到旧）

        Args:
            versions: 版本号列表

        Returns:
            排序后的版本号列表
        """
        return sorted(versions, key=self._parse_version, reverse=True)

    def _parse_version(self, version: str) -> tuple[int, ...]:
        """
        解析版本号为可比较的元组

        支持的版本格式：
        - "2.0" -> (2, 0)
        - "1.1.1" -> (1, 1, 1)
        - "2023.1" -> (2023, 1)

        Args:
            version: 版本字符串

        Returns:
            版本元组
        """
        try:
            # 移除可能的非数字字符
            clean_version = re.sub(r'[^\d.]', '', version)
            parts = [int(p) for p in clean_version.split('.') if p]
            return tuple(parts) if parts else (0,)
        except (ValueError, AttributeError):
            return (0,)

    def clear_cache(self) -> None:
        """清除 IP 缓存"""
        self._ip_cache.clear()
        logger.debug("IP 缓存已清除")


class IPInstanceHelper:
    """
    IP 实例化辅助类

    提供类似 ADI ad_ip_instance 的便捷接口。
    """

    def __init__(self, registry: IPRegistry):
        """
        初始化辅助类

        Args:
            registry: IPRegistry 实例
        """
        self.registry = registry

    async def create_bd_cell(
        self,
        ip_name: str,
        instance_name: str,
        config: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """
        创建 Block Design 单元（生成 Tcl 命令）

        参考 ADI 的 ad_ip_instance 函数：
        ```tcl
        proc ad_ip_instance {i_ip i_name {i_params {}}} {
          set ip_def [get_ipdefs -all -filter "VLNV =~ *:${i_ip}:* && \
            design_tool_contexts =~ *IPI* && UPGRADE_VERSIONS == \\"\\\"]
          set cell [create_bd_cell -type ip -vlnv ${ip_def} ${i_name}]
          if {$i_params != {}} {
            set config {}
            foreach {k v} $i_params {
              lappend config "CONFIG.$k" $v
            }
            set_property -dict $config $cell
          }
        }
        ```

        Args:
            ip_name: IP 简称或完整 VLNV
            instance_name: 实例名称
            config: 配置参数字典

        Returns:
            (vlnv, tcl_commands) 元组
            - vlnv: 完整的 VLNV
            - tcl_commands: Tcl 命令字典，包含 "create" 和 "config" 键

        Raises:
            ValueError: 如果 IP 未找到
        """
        # 查找 IP
        vlnv = await self.registry.find_ip(ip_name)
        if not vlnv:
            raise ValueError(f"未找到 IP: {ip_name}")

        # 生成创建命令
        commands = {
            "vlnv": vlnv,
            "create": f'create_bd_cell -type ip -vlnv {vlnv} {instance_name}',
            "config": [],
        }

        # 生成配置命令
        if config:
            # 参考 ADI 的做法，添加 CONFIG. 前缀
            config_list = []
            for key, value in config.items():
                # 如果键还没有 CONFIG. 前缀，添加它
                if not key.startswith("CONFIG."):
                    key = f"CONFIG.{key}"
                config_list.append(f"{key} {self._format_config_value(value)}")

            config_str = " ".join(config_list)
            commands["config"].append(
                f'set_property -dict [list {config_str}] [get_bd_cells {instance_name}]'
            )

        return vlnv, commands

    def _format_config_value(self, value: Any) -> str:
        """
        格式化配置值

        Args:
            value: 配置值

        Returns:
            格式化后的字符串
        """
        if isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, str):
            # 如果字符串包含空格或特殊字符，用花括号包围
            if ' ' in value or '{' in value or '}' in value:
                return f"{{{value}}}"
            return value
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            # 列表转换为 Tcl 列表格式
            return "{" + " ".join(str(v) for v in value) + "}"
        else:
            return str(value)


async def find_ip_vlnv(engine, ip_name: str) -> str | None:
    """
    便捷函数：查找 IP 的完整 VLNV

    Args:
        engine: TclEngine 实例
        ip_name: IP 简称

    Returns:
        完整 VLNV 或 None
    """
    registry = IPRegistry(engine)
    return await registry.find_ip(ip_name)


async def create_ip_instance(
    engine,
    ip_name: str,
    instance_name: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    便捷函数：创建 IP 实例

    类似于 ADI 的 ad_ip_instance 函数。

    Args:
        engine: TclEngine 实例
        ip_name: IP 简称或完整 VLNV
        instance_name: 实例名称
        config: 配置参数

    Returns:
        包含 vlnv 和 tcl_commands 的字典
    """
    registry = IPRegistry(engine)
    helper = IPInstanceHelper(registry)
    vlnv, commands = await helper.create_bd_cell(ip_name, instance_name, config)
    return {
        "vlnv": vlnv,
        "commands": commands,
    }
