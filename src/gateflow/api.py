"""
GateFlow 高级 API

提供简洁的 Python API，封装底层 MCP 工具。
"""

import logging
from pathlib import Path
from typing import Any

from gateflow.embedded import NonProjectProvider, VitisProvider, XSCTProvider
from gateflow.engine import (
    EngineManager,
    EngineMode,
    get_engine_manager,
    ensure_engine_initialized,
    ensure_engine_initialized_for_context,
)
from gateflow.tools.build_tools import ImplementationManagerAdapter, SynthesisManagerAdapter
from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.settings import get_settings
from gateflow.vivado.hardware import HardwareTclGenerator
from gateflow.vivado.ip_utils import IPRegistry, IPInstanceHelper
from gateflow.vivado.simulation import (
    SimulationConfig,
    SimulationManager,
    SimulationMode,
    SimulatorType,
)
from gateflow.utils.auto_config import ClockManager, InterruptManager

logger = logging.getLogger(__name__)

# 延迟导入平台模板，避免循环导入
_platform_registry = None


def _get_platform_registry():
    """获取平台注册表（延迟加载）"""
    global _platform_registry
    if _platform_registry is None:
        from gateflow.templates import PlatformRegistry
        _platform_registry = PlatformRegistry
    return _platform_registry


class GateFlow:
    """
    GateFlow 高级 API
    
    提供简洁的 Python 接口，让用户不需要直接写 Tcl 命令。
    
    Example:
        ```python
        import asyncio
        from gateflow import GateFlow
        
        async def main():
            gf = GateFlow()
            
            # 创建项目
            await gf.create_project("my_proj", "./projects", "xc7a35tcpg236-1")
            
            # 运行综合
            result = await gf.run_synthesis()
            print(f"状态: {result['status']}")
        
        asyncio.run(main())
        ```
    """
    
    def __init__(
        self,
        vivado_path: str | None = None,
        execution_context: ExecutionContext | None = None,
        gui_enabled: bool | None = None,
        gui_tcp_port: int | None = None,
    ):
        """
        初始化 GateFlow 实例。
        
        Args:
            vivado_path: Vivado 安装路径（可选，自动检测）
            execution_context: 执行上下文（为 Non-Project / Embedded 预留）
            gui_enabled: 是否默认通过 Vivado GUI 会话执行
            gui_tcp_port: GUI 会话 TCP 端口（可选）
        """
        self._engine: EngineManager | None = None
        self._vivado_path = vivado_path
        settings = get_settings()
        self._gui_enabled = settings.gui_enabled if gui_enabled is None else gui_enabled
        self._gui_tcp_port = gui_tcp_port or settings.gui_tcp_port
        self._execution_context = execution_context or ExecutionContext(
            kind=ExecutionContextKind.PROJECT
        )
        self._project_path: str | None = None
        self._ip_registry: IPRegistry | None = None
        self._synthesis_manager: SynthesisManagerAdapter | None = None
        self._implementation_manager: ImplementationManagerAdapter | None = None
        self._simulation_manager: SimulationManager | None = None
        # 自动配置管理器
        self._clock_manager: ClockManager | None = None
        self._interrupt_manager: InterruptManager | None = None
    
    async def _get_engine(self) -> EngineManager:
        """获取引擎实例"""
        if self._engine is None:
            # 如果提供了 vivado_path，设置环境变量
            if self._vivado_path:
                import os
                os.environ["XILINX_VIVADO"] = self._vivado_path
                logger.info(f"已设置 XILINX_VIVADO 环境变量: {self._vivado_path}")
            if self._gui_enabled:
                manager = get_engine_manager()
                manager._execution_context = self._execution_context
                if not manager.is_initialized:
                    await manager.initialize(EngineMode.GUI_SESSION)
                gui_result = await manager.ensure_gui_session(
                    project_path=self._project_path,
                    tcp_port=self._gui_tcp_port,
                )
                if not gui_result.get("success", False):
                    raise RuntimeError(gui_result.get("error") or gui_result.get("message") or "GUI session unavailable")
                self._engine = manager
            else:
                self._engine = await ensure_engine_initialized_for_context(self._execution_context)
        return self._engine

    @property
    def execution_context(self) -> ExecutionContext:
        """Return the active execution context."""
        return self._execution_context

    async def _get_ip_registry(self) -> IPRegistry:
        """Return a cached IP registry bound to the active engine."""
        if self._ip_registry is None:
            engine = await self._get_engine()
            self._ip_registry = IPRegistry(engine)
        return self._ip_registry

    async def _get_implementation_manager(self) -> ImplementationManagerAdapter:
        """Return a cached implementation manager adapter."""
        if self._implementation_manager is None:
            engine = await self._get_engine()
            self._implementation_manager = ImplementationManagerAdapter(engine)
        return self._implementation_manager

    async def _get_synthesis_manager(self) -> SynthesisManagerAdapter:
        """Return a cached synthesis manager adapter."""
        if self._synthesis_manager is None:
            engine = await self._get_engine()
            self._synthesis_manager = SynthesisManagerAdapter(engine)
        return self._synthesis_manager

    async def _get_simulation_manager(self) -> SimulationManager:
        """Return a cached simulation manager."""
        if self._simulation_manager is None:
            engine = await self._get_engine()
            self._simulation_manager = SimulationManager(engine)
        return self._simulation_manager

    @staticmethod
    def _result_success(result: Any) -> bool:
        """Handle both Result objects and dict-style payloads."""
        if isinstance(result, dict):
            return bool(result.get("success", False))
        return bool(getattr(result, "success", False))

    @staticmethod
    def _result_output(result: Any) -> str:
        """Extract text output from mixed result representations."""
        if isinstance(result, dict):
            for key in ("output", "result", "data", "message"):
                value = result.get(key)
                if value:
                    return str(value)
            return ""
        for attr in ("output", "data", "result", "message"):
            value = getattr(result, attr, None)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _result_error_message(result: Any) -> str | None:
        """Extract a normalized error string from mixed result representations."""
        if isinstance(result, dict):
            error = result.get("error")
            if error:
                return str(error)
            errors = result.get("errors") or []
            if errors:
                return "; ".join(str(item) for item in errors if item)
            return None

        error = getattr(result, "error", None)
        if error:
            return str(getattr(error, "message", error))
        errors = getattr(result, "errors", None) or []
        if errors:
            return "; ".join(str(item) for item in errors if item)
        return None

    @staticmethod
    def _normalize_simulation_mode(mode: str | SimulationMode) -> SimulationMode:
        """Accept enum values and common string aliases."""
        if isinstance(mode, SimulationMode):
            return mode
        mapping = {
            "behavioral": SimulationMode.BEHAVIORAL,
            "behavioural": SimulationMode.BEHAVIORAL,
            "post_synth": SimulationMode.POST_SYNTHESIS,
            "post_synthesis": SimulationMode.POST_SYNTHESIS,
            "post_impl": SimulationMode.POST_IMPLEMENTATION,
            "post_implementation": SimulationMode.POST_IMPLEMENTATION,
        }
        return mapping.get(str(mode).lower(), SimulationMode.BEHAVIORAL)

    @staticmethod
    def _normalize_simulator(simulator: str | SimulatorType) -> SimulatorType:
        """Accept enum values and common string aliases."""
        if isinstance(simulator, SimulatorType):
            return simulator
        mapping = {
            "vivado": SimulatorType.VIVADO,
            "modelsim": SimulatorType.MODELSIM,
            "questa": SimulatorType.QUESTASIM,
            "questasim": SimulatorType.QUESTASIM,
            "xcelium": SimulatorType.XCELIUM,
            "vcs": SimulatorType.VCS,
        }
        return mapping.get(str(simulator).lower(), SimulatorType.VIVADO)
    
    # ==================== 项目管理 ====================
    
    async def create_project(
        self,
        name: str,
        path: str,
        part: str,
    ) -> dict[str, Any]:
        """
        创建新项目
        
        Args:
            name: 项目名称
            path: 项目保存路径
            part: 目标器件型号
        
        Returns:
            创建结果字典
        """
        engine = await self._get_engine()
        
        # 生成 Tcl 命令
        commands = [
            f'create_project "{name}" "{path}" -part "{part}" -force',
            'set_property target_language Verilog [current_project]',
            'set_property simulator_language Verilog [current_project]',
            'set_property default_lib work [current_project]',
        ]
        
        # 批量执行命令
        results = await engine.execute_batch(commands)
        
        # 检查结果
        success = all(r.success for r in results)
        errors = []
        for r in results:
            if not r.success:
                # 从 error 对象中提取错误信息
                if r.error:
                    errors.append(r.error.message)
                # 也包含警告信息
                if r.warnings:
                    errors.extend(r.warnings)
        
        if success:
            self._project_path = path
            return {
                "success": True,
                "project": {
                    "name": name,
                    "path": path,
                    "part": part,
                },
                "message": f"项目 '{name}' 创建成功",
            }
        else:
            return {
                "success": False,
                "project": None,
                "message": "项目创建失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def create_project_from_template(
        self,
        platform: str,
        name: str,
        path: str,
        setup_ps: bool = False,
        add_peripherals: bool = False,
    ) -> dict[str, Any]:
        """
        从平台模板创建项目
        
        参考 ADI hdl-main 项目的设计模式，通过平台名称自动识别器件和板级支持包。
        
        Args:
            platform: 平台名称（如 "zcu102", "zed", "zc706"）
            name: 项目名称
            path: 项目保存路径
            setup_ps: 是否配置 PS（Processing System）
            add_peripherals: 是否添加默认外设
        
        Returns:
            创建结果字典，包含：
            - success: 是否成功
            - project: 项目信息
            - platform_info: 平台信息
            - message: 结果消息
        
        Example:
            ```python
            # 创建 ZCU102 项目
            result = await gf.create_project_from_template(
                platform="zcu102",
                name="my_project",
                path="./projects",
                setup_ps=True,
            )
            
            # 创建 Zedboard 项目
            result = await gf.create_project_from_template(
                platform="zed",
                name="zed_project",
                path="./projects",
            )
            ```
        """
        engine = await self._get_engine()
        
        # 获取平台注册表
        registry = _get_platform_registry()
        
        # 查找平台模板
        platform_class = registry.get(platform)
        if platform_class is None:
            available = registry.list_all()
            return {
                "success": False,
                "project": None,
                "platform_info": None,
                "message": f"未找到平台: {platform}",
                "error": f"可用平台: {', '.join(available)}",
            }
        
        # 获取平台信息
        platform_info = platform_class.get_info()
        
        # 生成 Tcl 命令
        if setup_ps:
            # 完整项目创建（包括 PS 配置）
            commands = platform_class.get_full_project_tcl(
                name=name,
                path=path,
            )
        else:
            # 仅创建项目
            commands = platform_class.get_tcl_create_project_commands(name, path)
        
        # 批量执行命令
        results = await engine.execute_batch(commands)
        
        # 检查结果
        success = all(r.success for r in results)
        errors = []
        for r in results:
            if not r.success:
                if r.error:
                    errors.append(r.error.message)
                if r.warnings:
                    errors.extend(r.warnings)
        
        if success:
            self._project_path = path
            return {
                "success": True,
                "project": {
                    "name": name,
                    "path": path,
                    "part": platform_info.device,
                    "board": platform_info.board_part,
                },
                "platform_info": platform_info.to_dict(),
                "message": f"项目 '{name}' 从模板 '{platform}' 创建成功",
            }
        else:
            return {
                "success": False,
                "project": None,
                "platform_info": platform_info.to_dict(),
                "message": "项目创建失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def list_platforms(self) -> dict[str, Any]:
        """
        列出所有可用的平台模板
        
        Returns:
            平台列表字典，包含：
            - success: 是否成功
            - platforms: 平台信息列表
            - count: 平台数量
            - message: 结果消息
        
        Example:
            ```python
            result = await gf.list_platforms()
            for name, info in result["platforms"].items():
                print(f"{name}: {info['display_name']}")
            ```
        """
        registry = _get_platform_registry()
        
        platforms = registry.get_all_info()
        
        return {
            "success": True,
            "platforms": {name: info.to_dict() for name, info in platforms.items()},
            "count": len(platforms),
            "message": f"找到 {len(platforms)} 个平台模板",
        }
    
    async def get_platform_info(self, platform: str) -> dict[str, Any]:
        """
        获取指定平台的详细信息
        
        Args:
            platform: 平台名称
        
        Returns:
            平台信息字典
        
        Example:
            ```python
            result = await gf.get_platform_info("zcu102")
            print(f"器件: {result['info']['device']}")
            print(f"PS 类型: {result['info']['ps_type']}")
            ```
        """
        registry = _get_platform_registry()
        
        info = registry.get_info(platform)
        
        if info:
            return {
                "success": True,
                "info": info.to_dict(),
                "message": f"获取平台 '{platform}' 信息成功",
            }
        else:
            return {
                "success": False,
                "info": None,
                "message": f"未找到平台: {platform}",
            }
    
    async def open_project(self, path: str) -> dict[str, Any]:
        """
        打开项目
        
        Args:
            path: 项目文件路径（.xpr 文件）
        
        Returns:
            打开结果字典
        """
        engine = await self._get_engine()
        result = await engine.execute(f'open_project "{path}"', timeout=120.0)
        
        if result.success:
            # 获取项目信息
            info_result = await engine.execute("current_project")
            project_name = (info_result.data or "").strip() if info_result.success else ""
            self._project_path = path
            
            return {
                "success": True,
                "project": {
                    "name": project_name,
                    "path": path,
                },
                "message": f"项目打开成功: {path}",
            }
        else:
            errors = [result.error.message] if result.error else []
            joined_errors = "; ".join(errors) if errors else "未知错误"
            if "超时" in joined_errors or "timeout" in joined_errors.lower():
                verify_result = await engine.execute("current_project")
                current_project = (verify_result.data or "").strip() if verify_result.success else ""
                if current_project and current_project == Path(path).stem:
                    self._project_path = path
                    return {
                        "success": True,
                        "project": {
                            "name": current_project,
                            "path": path,
                        },
                        "message": f"项目已在当前会话中打开: {path}",
                    }
            if "already open" in joined_errors.lower():
                self._project_path = path
                return {
                    "success": True,
                    "project": {
                        "name": Path(path).stem,
                        "path": path,
                    },
                    "message": f"项目已在当前会话中打开: {path}",
                }
            return {
                "success": False,
                "project": None,
                "message": "项目打开失败",
                "error": joined_errors,
            }
    
    async def add_source_files(
        self,
        files: list[str],
        file_type: str = "verilog",
    ) -> dict[str, Any]:
        """
        添加源文件
        
        Args:
            files: 文件路径列表
            file_type: 文件类型（verilog, vhdl, xdc 等）
        
        Returns:
            添加结果字典
        """
        from gateflow.utils.path_utils import normalize_path
        
        engine = await self._get_engine()
        
        # 根据文件类型选择文件集
        if file_type == "xdc":
            fileset = "constrs_1"
        else:
            fileset = "sources_1"
        
        # 转换所有文件路径为 Tcl 格式
        tcl_files = [normalize_path(f) for f in files]
        
        # 构建文件列表（使用 list 命令）
        if len(tcl_files) == 1:
            command = f'add_files -fileset {fileset} "{tcl_files[0]}"'
        else:
            file_list = " ".join(f'"{f}"' for f in tcl_files)
            command = f'add_files -fileset {fileset} [list {file_list}]'
        
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "added_files": files,
                "invalid_files": [],
                "message": f"成功添加 {len(files)} 个文件",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "added_files": [],
                "invalid_files": files,
                "message": "添加文件失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def set_top_module(self, module_name: str) -> dict[str, Any]:
        """
        设置顶层模块
        
        Args:
            module_name: 模块名称
        
        Returns:
            设置结果字典
        """
        engine = await self._get_engine()
        
        commands = [
            f'set_property top {module_name} [get_filesets sources_1]',
            'update_compile_order -fileset sources_1',
        ]
        
        results = await engine.execute_batch(commands)
        success = all(r.success for r in results)
        
        if success:
            return {
                "success": True,
                "top_module": module_name,
                "message": f"顶层模块设置为: {module_name}",
            }
        else:
            errors = []
            for r in results:
                if not r.success:
                    if r.error:
                        errors.append(r.error.message)
                    if r.warnings:
                        errors.extend(r.warnings)
            return {
                "success": False,
                "top_module": None,
                "message": "设置顶层模块失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def get_project_info(self) -> dict[str, Any]:
        """
        获取项目信息
        
        Returns:
            项目信息字典
        """
        engine = await self._get_engine()
        
        info = {}
        
        # 获取项目名称
        result = await engine.execute('get_property name [current_project]')
        if result.success:
            info["name"] = (result.data or "").strip()
        
        # 获取项目路径
        result = await engine.execute('get_property directory [current_project]')
        if result.success:
            info["directory"] = (result.data or "").strip()
        
        # 获取器件型号
        result = await engine.execute('get_property part [current_project]')
        if result.success:
            info["part"] = (result.data or "").strip()
        
        # 获取目标语言
        result = await engine.execute('get_property target_language [current_project]')
        if result.success:
            info["language"] = (result.data or "").strip()
        
        return {
            "success": True,
            "project": info,
            "message": "获取项目信息成功",
        }
    
    async def close_project(self) -> dict[str, Any]:
        """
        关闭项目
        
        Returns:
            关闭结果字典
        """
        engine = await self._get_engine()
        result = await engine.execute('close_project')
        
        if result.success:
            self._project_path = None
            return {
                "success": True,
                "message": "项目已关闭",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "message": "关闭项目失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    # ==================== 构建流程 ====================
    
    async def run_synthesis(
        self,
        run_name: str = "synth_1",
        jobs: int = 4,
    ) -> dict[str, Any]:
        """
        运行综合
        
        Args:
            run_name: 综合运行名称
            jobs: 并行任务数
        
        Returns:
            综合结果字典
        """
        manager = await self._get_synthesis_manager()
        return await manager.run_synthesis(run_name=run_name, jobs=jobs)
    
    async def run_implementation(
        self,
        run_name: str = "impl_1",
        jobs: int = 4,
    ) -> dict[str, Any]:
        """
        运行实现
        
        Args:
            run_name: 实现运行名称
            jobs: 并行任务数
        
        Returns:
            实现结果字典
        """
        manager = await self._get_implementation_manager()
        return await manager.run_implementation(run_name=run_name, jobs=jobs)
    
    async def generate_bitstream(
        self,
        run_name: str = "impl_1",
        jobs: int = 4,
    ) -> dict[str, Any]:
        """
        生成比特流
        
        Args:
            run_name: 实现运行名称
            jobs: 并行任务数
        
        Returns:
            比特流生成结果字典
        """
        manager = await self._get_implementation_manager()
        return await manager.generate_bitstream(run_name=run_name, jobs=jobs, timeout=3600.0)

    async def launch_run(
        self,
        run_name: str,
        to_step: str | None = None,
        jobs: int = 4,
    ) -> dict[str, Any]:
        """Launch a Vivado run without waiting for completion."""
        manager = await self._get_implementation_manager()
        return await manager.launch_run(run_name, to_step=to_step, jobs=jobs)

    async def wait_for_run(
        self,
        run_name: str,
        timeout: float | None = None,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """Poll Vivado run status until completion, failure, or timeout."""
        manager = await self._get_implementation_manager()
        return await manager.wait_for_run(
            run_name,
            timeout=timeout,
            poll_interval=poll_interval,
        )

    async def get_run_status(self, run_name: str) -> dict[str, Any]:
        """Get the current Vivado status for a run."""
        manager = await self._get_implementation_manager()
        return await manager.get_run_status(run_name)

    async def get_run_progress(self, run_name: str) -> dict[str, Any]:
        """Get a text progress hint and last known step for a run."""
        manager = await self._get_implementation_manager()
        return await manager.get_run_progress(run_name)

    async def get_run_messages(
        self,
        run_name: str,
        limit: int = 50,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Get recent run messages from the run log."""
        manager = await self._get_implementation_manager()
        return await manager.get_run_messages(run_name, limit=limit, severity=severity)
     
    async def get_utilization_report(self) -> dict[str, Any]:
        """
        获取资源利用率报告
        
        Returns:
            资源利用率字典
        """
        import re
        
        engine = await self._get_engine()
        
        # 打开综合或实现设计
        open_result = await engine.execute('open_run impl_1')
        if not open_result.success:
            open_result = await engine.execute('open_run synth_1')
        
        if not open_result.success:
            errors = [open_result.error.message] if open_result.error else []
            return {
                "success": False,
                "utilization": {},
                "message": "无法打开设计",
                "error": "; ".join(errors),
            }
        
        # 获取利用率报告
        result = await engine.execute('report_utilization -return_string')
        
        utilization = {}
        if result.success:
            # 解析报告
            report = result.data or ""
            
            patterns = {
                'slice_lut': r'Slice LUTs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
                'slice_registers': r'Slice Registers\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
                'lut': r'LUT as Logic\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
                'bram': r'Block RAM Tile\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
                'dsp': r'DSPs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, report)
                if match:
                    utilization[key] = {
                        'used': int(match.group(1)),
                        'available': int(match.group(2)),
                        'utilization': float(match.group(3)),
                    }
        
        errors = [result.error.message] if result.error else []
        return {
            "success": result.success,
            "utilization": utilization,
            "raw_report": result.data or "",
            "message": "获取资源利用率报告成功" if result.success else "获取资源利用率报告失败",
            "error": "; ".join(errors) if not result.success else None,
        }
    
    async def get_timing_report(self) -> dict[str, Any]:
        """
        获取时序报告
        
        Returns:
            时序信息字典
        """
        import re
        
        engine = await self._get_engine()
        
        # 打开实现设计
        open_result = await engine.execute('open_run impl_1')
        if not open_result.success:
            errors = [open_result.error.message] if open_result.error else []
            return {
                "success": False,
                "timing": {},
                "message": "无法打开实现设计",
                "error": "; ".join(errors),
            }
        
        # 获取时序报告
        result = await engine.execute('report_timing_summary -return_string')
        
        timing = {}
        if result.success:
            # 解析报告
            report = result.data or ""
            
            # 解析 Setup 时序
            wns_pattern = r'WNS\(ns\)\s*:\s*([\d.-]+)'
            tns_pattern = r'TNS\(ns\)\s*:\s*([\d.-]+)'
            
            wns_match = re.search(wns_pattern, report)
            tns_match = re.search(tns_pattern, report)
            
            if wns_match:
                timing['wns'] = float(wns_match.group(1))
            if tns_match:
                timing['tns'] = float(tns_match.group(1))
            
            # 解析 Hold 时序
            whs_pattern = r'WHS\(ns\)\s*:\s*([\d.-]+)'
            ths_pattern = r'THS\(ns\)\s*:\s*([\d.-]+)'
            
            whs_match = re.search(whs_pattern, report)
            ths_match = re.search(ths_pattern, report)
            
            if whs_match:
                timing['whs'] = float(whs_match.group(1))
            if ths_match:
                timing['ths'] = float(ths_match.group(1))
            
            # 判断时序是否满足
            wns = timing.get('wns', 0)
            whs = timing.get('whs', 0)
            timing['timing_met'] = wns >= 0 and whs >= 0
        
        errors = [result.error.message] if result.error else []
        return {
            "success": result.success,
            "timing": timing,
            "raw_report": result.data or "",
            "message": "获取时序报告成功" if result.success else "获取时序报告失败",
            "error": "; ".join(errors) if not result.success else None,
        }

    async def get_drc_report(self, output_path: str | None = None) -> dict[str, Any]:
        """Return the implementation DRC report through the high-level API."""
        manager = await self._get_implementation_manager()
        return await manager.get_drc_report(output_path=output_path)

    async def get_methodology_report(self, output_path: str | None = None) -> dict[str, Any]:
        """Return the implementation methodology report through the high-level API."""
        manager = await self._get_implementation_manager()
        return await manager.get_methodology_report(output_path=output_path)

    async def get_power_report(self, output_path: str | None = None) -> dict[str, Any]:
        """Return the implementation power report through the high-level API."""
        manager = await self._get_implementation_manager()
        return await manager.get_power_report(output_path=output_path)

    async def check_drc(
        self,
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> dict[str, Any]:
        """Summarize DRC findings using the same logic as the MCP tool layer."""
        from gateflow.tools.build_tools import _summarize_lint_findings

        report = await self.get_drc_report()
        if not report.get("success", False):
            return {
                "success": False,
                "report_name": "drc",
                "message": "DRC 检查失败",
                "error": report.get("error"),
            }

        summary = _summarize_lint_findings(
            report=report.get("raw_report", "") or "",
            min_severity=min_severity,
            max_findings=max_findings,
        )
        return {
            "success": True,
            "report_name": "drc",
            "total_findings": summary["total_findings"],
            "matched_findings": summary["matched_findings"],
            "severity_counts": summary["severity_counts"],
            "findings": summary["findings"],
            "message": f"DRC 检查完成，匹配 {summary['matched_findings']} 条问题",
            "error": None,
        }

    async def check_methodology(
        self,
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> dict[str, Any]:
        """Summarize methodology findings using the same logic as the MCP tool layer."""
        from gateflow.tools.build_tools import _summarize_lint_findings

        report = await self.get_methodology_report()
        if not report.get("success", False):
            return {
                "success": False,
                "report_name": "methodology",
                "message": "methodology 检查失败",
                "error": report.get("error"),
            }

        summary = _summarize_lint_findings(
            report=report.get("raw_report", "") or "",
            min_severity=min_severity,
            max_findings=max_findings,
        )
        return {
            "success": True,
            "report_name": "methodology",
            "total_findings": summary["total_findings"],
            "matched_findings": summary["matched_findings"],
            "severity_counts": summary["severity_counts"],
            "findings": summary["findings"],
            "message": f"methodology 检查完成，匹配 {summary['matched_findings']} 条问题",
            "error": None,
        }

    async def create_simulation_set(self, name: str, sources: list[str]) -> dict[str, Any]:
        """Create a simulation set through the high-level API."""
        manager = await self._get_simulation_manager()
        return await manager.create_simulation_set(name, sources)

    async def set_simulation_top(self, module: str, sim_set: str = "sim_1") -> dict[str, Any]:
        """Set the simulation top module through the high-level API."""
        manager = await self._get_simulation_manager()
        return await manager.set_simulation_top(module, sim_set)

    async def compile_simulation(self, sim_set: str = "sim_1") -> dict[str, Any]:
        """Compile a simulation fileset."""
        manager = await self._get_simulation_manager()
        return await manager.compile_simulation(sim_set)

    async def elaborate_simulation(self, sim_set: str = "sim_1") -> dict[str, Any]:
        """Elaborate a simulation fileset."""
        manager = await self._get_simulation_manager()
        return await manager.elaborate_simulation(sim_set)

    async def launch_simulation(
        self,
        sim_set: str = "sim_1",
        top_module: str | None = None,
        simulator: str | SimulatorType = SimulatorType.VIVADO,
        mode: str | SimulationMode = SimulationMode.BEHAVIORAL,
        simulation_time: str = "100us",
        run_mode: str = "default",
    ) -> dict[str, Any]:
        """Launch simulation using a normalized config object."""
        manager = await self._get_simulation_manager()
        config = SimulationConfig(
            name=sim_set,
            top_module=top_module,
            simulator=self._normalize_simulator(simulator),
            mode=self._normalize_simulation_mode(mode),
            simulation_time=simulation_time,
            run_mode=run_mode,
        )
        return await manager.launch_simulation(config)

    async def run_simulation(self, time: str = "all") -> dict[str, Any]:
        """Run the active simulation session."""
        manager = await self._get_simulation_manager()
        return await manager.run_simulation(time)

    async def probe_signal(self, signal: str, radix: str = "binary") -> dict[str, Any]:
        """Add a signal to the wave view for probing."""
        manager = await self._get_simulation_manager()
        return await manager.add_wave(signal, radix)

    async def add_force_signal(
        self,
        signal: str,
        value: str,
        repeat: str | None = None,
        after: str | None = None,
    ) -> dict[str, Any]:
        """Apply a simulation force to a signal."""
        manager = await self._get_simulation_manager()
        return await manager.add_force(signal, value, repeat, after)

    async def get_signal_value(self, signal: str) -> dict[str, Any]:
        """Read a simulation signal value."""
        manager = await self._get_simulation_manager()
        return await manager.get_signal_value(signal)

    async def remove_force_signal(self, signal: str) -> dict[str, Any]:
        """Remove a simulation force from a signal."""
        manager = await self._get_simulation_manager()
        return await manager.remove_force(signal)

    async def connect_hw_server(self, url: str = "localhost:3121") -> dict[str, Any]:
        """Connect to the Vivado hardware server."""
        engine = await self._get_engine()
        command = "\n".join(
            [
                HardwareTclGenerator.open_hw_manager_tcl(),
                HardwareTclGenerator.connect_hw_server_tcl(url),
            ]
        )
        result = await engine.execute(command)
        success = self._result_success(result)
        return {
            "success": success,
            "url": url,
            "message": f"硬件服务器连接成功: {url}" if success else "硬件服务器连接失败",
            "error": None if success else self._result_error_message(result),
        }

    async def list_hardware_targets(self) -> dict[str, Any]:
        """List visible hardware targets."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.get_hw_targets_tcl())
        success = self._result_success(result)
        output = self._result_output(result).strip() if success else ""
        targets = [line.strip() for line in output.splitlines() if line.strip()]
        return {
            "success": success,
            "targets": targets,
            "message": f"找到 {len(targets)} 个硬件目标" if success else "获取硬件目标失败",
            "error": None if success else self._result_error_message(result),
        }

    async def open_hardware_target(self, target: str | None = None) -> dict[str, Any]:
        """Open a hardware target."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.open_hw_target_tcl(target))
        success = self._result_success(result)
        return {
            "success": success,
            "target": target,
            "message": f"硬件目标已打开: {target or 'default'}" if success else "打开硬件目标失败",
            "error": None if success else self._result_error_message(result),
        }

    async def set_probe_file(self, device_name: str, probe_file_path: str) -> dict[str, Any]:
        """Bind an .ltx probe file to a hardware device."""
        engine = await self._get_engine()
        result = await engine.execute(
            HardwareTclGenerator.set_probe_file_tcl(device_name, probe_file_path)
        )
        success = self._result_success(result)
        return {
            "success": success,
            "device_name": device_name,
            "probe_file_path": probe_file_path,
            "message": "探针文件设置成功" if success else "探针文件设置失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_ila_list(self) -> dict[str, Any]:
        """List available ILA cores."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.get_hw_ila_tcl())
        success = self._result_success(result)
        output = self._result_output(result).strip() if success else ""
        ilas = [line.strip() for line in output.splitlines() if line.strip()]
        return {
            "success": success,
            "targets": ilas,
            "message": f"找到 {len(ilas)} 个 ILA 核" if success else "获取 ILA 列表失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_ila_run(self, ila: str) -> dict[str, Any]:
        """Trigger a hardware ILA capture."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.run_hw_ila_tcl(ila))
        success = self._result_success(result)
        return {
            "success": success,
            "name": ila,
            "message": f"ILA 已触发: {ila}" if success else "ILA 触发失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_ila_upload(self, ila: str) -> dict[str, Any]:
        """Upload an ILA capture."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.upload_hw_ila_tcl(ila))
        success = self._result_success(result)
        return {
            "success": success,
            "name": ila,
            "message": f"ILA 数据已上传: {ila}" if success else "ILA 数据上传失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_vio_list(self) -> dict[str, Any]:
        """List available VIO cores."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.get_hw_vio_tcl())
        success = self._result_success(result)
        output = self._result_output(result).strip() if success else ""
        vios = [line.strip() for line in output.splitlines() if line.strip()]
        return {
            "success": success,
            "targets": vios,
            "message": f"找到 {len(vios)} 个 VIO 核" if success else "获取 VIO 列表失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_vio_set_output(self, vio: str, probe: str, value: str) -> dict[str, Any]:
        """Set a VIO output probe."""
        engine = await self._get_engine()
        command = "\n".join(
            [
                HardwareTclGenerator.set_vio_output_tcl(vio, probe, value),
                f"commit_hw_vio [get_hw_vios {vio}]",
            ]
        )
        result = await engine.execute(command)
        success = self._result_success(result)
        return {
            "success": success,
            "name": f"{vio}:{probe}",
            "message": f"VIO 输出已设置: {probe}={value}" if success else "设置 VIO 输出失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_vio_get_input(self, vio: str, probe: str) -> dict[str, Any]:
        """Read a VIO input probe."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.get_vio_input_tcl(vio, probe))
        success = self._result_success(result)
        return {
            "success": success,
            "name": f"{vio}:{probe}",
            "value": self._result_output(result).strip() if success else None,
            "message": "读取 VIO 输入成功" if success else "读取 VIO 输入失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_vio_refresh(self, vio: str) -> dict[str, Any]:
        """Refresh a VIO core."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.refresh_hw_vio_tcl(vio))
        success = self._result_success(result)
        return {
            "success": success,
            "name": vio,
            "message": f"VIO 已刷新: {vio}" if success else "刷新 VIO 失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_axi_list(self) -> dict[str, Any]:
        """List available hardware AXI debug interfaces."""
        engine = await self._get_engine()
        result = await engine.execute(HardwareTclGenerator.get_hw_axis_tcl())
        success = self._result_success(result)
        output = self._result_output(result).strip() if success else ""
        axis = [line.strip() for line in output.splitlines() if line.strip()]
        return {
            "success": success,
            "targets": axis,
            "message": f"找到 {len(axis)} 个 HW AXI 接口" if success else "获取 HW AXI 列表失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_axi_read(self, axi_name: str, address: str, length: int = 1) -> dict[str, Any]:
        """Read through a hardware AXI debug interface."""
        engine = await self._get_engine()
        txn_name = f"axi_read_{abs(hash((axi_name, address))) & 0xffff:x}"
        command = "\n".join(
            [
                HardwareTclGenerator.create_hw_axi_txn_tcl(
                    txn_name=txn_name,
                    axi_name=axi_name,
                    address=address,
                    txn_type="read",
                    length=length,
                ),
                HardwareTclGenerator.run_hw_axi_txn_tcl(txn_name),
                HardwareTclGenerator.get_hw_axi_data_tcl(txn_name),
                HardwareTclGenerator.delete_hw_axi_txn_tcl(txn_name),
            ]
        )
        result = await engine.execute(command)
        success = self._result_success(result)
        return {
            "success": success,
            "axi_name": axi_name,
            "address": address,
            "transaction_name": txn_name,
            "value": self._result_output(result).strip() if success else None,
            "message": "HW AXI 读取成功" if success else "HW AXI 读取失败",
            "error": None if success else self._result_error_message(result),
        }

    async def hw_axi_write(
        self,
        axi_name: str,
        address: str,
        value: str,
        length: int = 1,
    ) -> dict[str, Any]:
        """Write through a hardware AXI debug interface."""
        engine = await self._get_engine()
        txn_name = f"axi_write_{abs(hash((axi_name, address))) & 0xffff:x}"
        command = "\n".join(
            [
                HardwareTclGenerator.create_hw_axi_txn_tcl(
                    txn_name=txn_name,
                    axi_name=axi_name,
                    address=address,
                    txn_type="write",
                    data=value,
                    length=length,
                ),
                HardwareTclGenerator.run_hw_axi_txn_tcl(txn_name),
                HardwareTclGenerator.delete_hw_axi_txn_tcl(txn_name),
            ]
        )
        result = await engine.execute(command)
        success = self._result_success(result)
        return {
            "success": success,
            "axi_name": axi_name,
            "address": address,
            "transaction_name": txn_name,
            "value": value,
            "message": "HW AXI 写入成功" if success else "HW AXI 写入失败",
            "error": None if success else self._result_error_message(result),
        }

    async def export_xsa(
        self,
        xpr_path: str,
        output_path: str | None = None,
        include_bit: bool = True,
    ) -> dict[str, Any]:
        """Export an XSA artifact from an existing Vivado project."""
        provider = NonProjectProvider(vivado_path=self._vivado_path)
        return provider.export_xsa(
            xpr_path=xpr_path,
            output_path=output_path,
            include_bit=include_bit,
        )

    async def build_standalone_elf(
        self,
        *,
        workspace_path: str,
        app_name: str,
        xpr_path: str | None = None,
        xsa_path: str | None = None,
        source_path: str | None = None,
        proc: str = "ps7_cortexa9_0",
        template: str = "Empty Application(C)",
        platform_name: str = "gateflow_hw",
        domain_name: str = "standalone_domain",
    ) -> dict[str, Any]:
        """Build a minimal standalone ELF using the embedded providers."""
        provider = NonProjectProvider(vivado_path=self._vivado_path)
        return provider.build_standalone_elf(
            workspace_path=workspace_path,
            app_name=app_name,
            xpr_path=xpr_path,
            xsa_path=xsa_path,
            source_path=source_path,
            proc=proc,
            template=template,
            platform_name=platform_name,
            domain_name=domain_name,
        )

    async def ensure_gui_session(
        self,
        project_path: str | None = None,
        tcp_port: int | None = None,
    ) -> dict[str, Any]:
        """Start or reuse a GUI-backed Vivado session."""
        manager = get_engine_manager()
        if not manager.is_initialized:
            await manager.initialize(EngineMode.GUI_SESSION)
        return await manager.ensure_gui_session(project_path=project_path, tcp_port=tcp_port)

    async def open_project_gui(
        self,
        path: str,
        tcp_port: int | None = None,
    ) -> dict[str, Any]:
        """Start a GUI session and bind it to the requested project path."""
        result = await self.ensure_gui_session(project_path=path, tcp_port=tcp_port)
        if not result.get("success", False):
            return result
        return {
            **result,
            "message": f"GUI 会话已启动并绑定工程: {path}",
            "project_path": path,
        }

    async def attach_gui_session(
        self,
        tcp_port: int,
        project_path: str | None = None,
    ) -> dict[str, Any]:
        """Attach to an already running GUI-backed Vivado session."""
        manager = get_engine_manager()
        if not manager.is_initialized:
            await manager.initialize(EngineMode.GUI_SESSION)
        return await manager.attach_gui_session(tcp_port=tcp_port, project_path=project_path)

    async def get_session_mode_info(self) -> dict[str, Any]:
        """Return current engine/session mode info."""
        manager = get_engine_manager()
        return manager.get_mode_info()
    
    # ==================== Block Design ====================
    
    async def create_bd_design(self, name: str) -> dict[str, Any]:
        """
        创建 Block Design
        
        Args:
            name: Block Design 名称
        
        Returns:
            创建结果字典
        """
        engine = await self._get_engine()
        
        command = f'create_bd_design "{name}"'
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "design_name": name,
                "message": f"Block Design '{name}' 创建成功",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "design_name": None,
                "message": "Block Design 创建失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def smart_connect(
        self,
        source: str,
        target: str,
        connect_type: str = "auto",
    ) -> dict[str, Any]:
        """
        智能连接 Block Design 中的对象
        
        自动判断连接类型并执行正确的连接命令：
        - 接口连接: connect_bd_intf_net
        - 信号连接: connect_bd_net
        - 常量连接: 自动创建常量源并连接
        
        Args:
            source: 源对象名称（可以是 pin、port、interface pin）
                   支持格式:
                   - "instance/pin": IP 实例的引脚
                   - "port": 外部端口
                   - "GND": 接地常量
                   - "VCC": 电源常量
            target: 目标对象名称
            connect_type: 连接类型
                - "auto": 自动判断（默认）
                - "interface": 强制接口连接
                - "signal": 强制信号连接
                - "constant": 常量连接
        
        Returns:
            连接结果字典，包含:
            - success: 是否成功
            - connect_type: 实际使用的连接类型
            - source: 源对象
            - target: 目标对象
            - message: 结果消息
            - error: 错误信息（如果失败）
        
        Example:
            ```python
            # 自动连接接口
            result = await gf.smart_connect(
                "axi_interconnect_0/M00_AXI",
                "axi_gpio_0/S_AXI"
            )
            
            # 连接到 GND
            result = await gf.smart_connect("GND", "ip_0/input_pin")
            
            # 连接到 VCC
            result = await gf.smart_connect("VCC", "ip_0/enable_pin")
            ```
        """
        engine = await self._get_engine()
        
        # 处理常量连接
        if source.upper() in ["GND", "VCC", "0", "1"]:
            return await self._connect_constant(source, target, engine)
        
        # 处理常量目标（反向连接）
        if target.upper() in ["GND", "VCC", "0", "1"]:
            return await self._connect_constant(target, source, engine)
        
        # 自动检测连接类型
        if connect_type == "auto":
            detected_type = await self._detect_connection_type(source, target, engine)
            if detected_type is None:
                return {
                    "success": False,
                    "connect_type": None,
                    "source": source,
                    "target": target,
                    "message": "无法检测连接类型",
                    "error": "源对象或目标对象不存在",
                }
            connect_type = detected_type
        
        # 执行连接
        try:
            if connect_type == "interface":
                result = await self._connect_interface(source, target, engine)
            else:
                result = await self._connect_signal(source, target, engine)
            
            return result
        except Exception as e:
            logger.error(f"智能连接失败: {e}")
            return {
                "success": False,
                "connect_type": connect_type,
                "source": source,
                "target": target,
                "message": "连接失败",
                "error": str(e),
            }

    @staticmethod
    def _exec_success(result: Any) -> bool:
        """Return success flag for both EngineResult objects and dict mocks."""
        if isinstance(result, dict):
            return bool(result.get("success", False))
        return bool(getattr(result, "success", False))

    @staticmethod
    def _exec_text(result: Any) -> str:
        """Return main text payload for both EngineResult objects and dict mocks."""
        if isinstance(result, dict):
            for key in ("data", "result", "output", "message"):
                value = result.get(key)
                if value is None:
                    continue
                return str(value)
            return ""

        for attr in ("data", "result", "output", "message"):
            value = getattr(result, attr, None)
            if value is None:
                continue
            return str(value)
        return ""

    @staticmethod
    def _exec_errors(result: Any) -> list[str]:
        """Extract normalized error messages for both EngineResult objects and dict mocks."""
        errors: list[str] = []
        if isinstance(result, dict):
            raw_errors = result.get("errors")
            if isinstance(raw_errors, list):
                errors.extend(str(err) for err in raw_errors if err)
            elif raw_errors:
                errors.append(str(raw_errors))

            raw_error = result.get("error")
            if isinstance(raw_error, dict):
                message = raw_error.get("message")
                if message:
                    errors.append(str(message))
            elif raw_error:
                errors.append(str(raw_error))
        else:
            raw_error = getattr(result, "error", None)
            if raw_error:
                message = getattr(raw_error, "message", None)
                if message:
                    errors.append(str(message))
                else:
                    errors.append(str(raw_error))
            warnings = getattr(result, "warnings", None)
            if isinstance(warnings, list):
                errors.extend(str(warn) for warn in warnings if warn)

        # 去重并保持顺序
        deduped: list[str] = []
        for err in errors:
            if err not in deduped:
                deduped.append(err)
        return deduped
    
    async def _detect_connection_type(
        self,
        source: str,
        target: str,
        engine,
    ) -> str | None:
        """检测连接类型"""
        
        # 检查是否为接口引脚
        source_is_intf = await self._is_interface_pin(source, engine)
        target_is_intf = await self._is_interface_pin(target, engine)
        
        # 如果任一端是接口引脚，则使用接口连接
        if source_is_intf or target_is_intf:
            return "interface"
        
        # 检查是否为普通引脚或端口
        source_exists = await self._object_exists(source, engine)
        target_exists = await self._object_exists(target, engine)
        
        if source_exists and target_exists:
            return "signal"
        
        return None
    
    async def _is_interface_pin(self, name: str, engine) -> bool:
        """检查是否为接口引脚"""
        # 检查接口引脚
        result = await engine.execute(f'get_bd_intf_pins -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return True
        
        # 检查接口端口
        result = await engine.execute(f'get_bd_intf_ports -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return True
        
        return False
    
    async def _object_exists(self, name: str, engine) -> bool:
        """检查对象是否存在"""
        # 检查普通引脚
        result = await engine.execute(f'get_bd_pins -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return True
        
        # 检查端口
        result = await engine.execute(f'get_bd_ports -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return True
        
        return False
    
    async def _connect_constant(
        self,
        constant_type: str,
        target: str,
        engine,
    ) -> dict[str, Any]:
        """连接常量"""
        constant_type = constant_type.upper()
        
        # 确定常量值
        if constant_type in ["GND", "0"]:
            const_value = 0
            const_name = f"gnd_const_{target.replace('/', '_')}"
        else:  # VCC or 1
            const_value = 1
            const_name = f"vcc_const_{target.replace('/', '_')}"
        
        # 获取目标引脚宽度
        width = await self._get_pin_width(target, engine)
        if width is None:
            width = 1
        
        # 检查是否已存在同名常量
        existing_const = await engine.execute(f'get_bd_cells -quiet {const_name}')
        if not self._exec_success(existing_const) or not self._exec_text(existing_const).strip():
            # 创建常量 IP
            commands = [
                f'create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant:1.1 {const_name}',
                f'set_property -dict [list CONFIG.CONST_WIDTH {{{width}}} CONFIG.CONST_VAL {{{const_value}}}] [get_bd_cells {const_name}]',
            ]
            
            result = await engine.execute_batch(commands)
            if not all(self._exec_success(r) for r in result):
                errors = []
                for r in result:
                    if not self._exec_success(r):
                        errors.extend(self._exec_errors(r))
                return {
                    "success": False,
                    "connect_type": "constant",
                    "source": constant_type,
                    "target": target,
                    "message": "创建常量 IP 失败",
                    "error": "; ".join(errors) if errors else "未知错误",
                }
        
        # 连接常量到目标
        connect_result = await self._connect_signal(f"{const_name}/dout", target, engine)
        
        if connect_result["success"]:
            connect_result["source"] = constant_type
            connect_result["connect_type"] = "constant"
            connect_result["constant_ip"] = const_name
            connect_result["constant_width"] = width
            connect_result["message"] = f"常量 {constant_type} 连接成功: {constant_type} -> {target}"
        
        return connect_result
    
    async def _get_pin_width(self, pin_name: str, engine) -> int | None:
        """获取引脚宽度"""
        # 获取左侧索引
        result = await engine.execute(f'get_property LEFT [get_bd_pins {pin_name}]')
        left_text = self._exec_text(result).strip()
        if self._exec_success(result) and left_text:
            try:
                left = int(left_text)
                # 获取右侧索引
                right_result = await engine.execute(f'get_property RIGHT [get_bd_pins {pin_name}]')
                right = 0
                right_text = self._exec_text(right_result).strip()
                if self._exec_success(right_result) and right_text:
                    right = int(right_text)
                return left - right + 1
            except (ValueError, TypeError):
                pass
        
        return None
    
    async def _connect_interface(
        self,
        source: str,
        target: str,
        engine,
    ) -> dict[str, Any]:
        """连接接口"""
        # 确定使用 get_bd_intf_pins 还是 get_bd_intf_ports
        source_cmd = await self._get_interface_get_command(source, engine)
        target_cmd = await self._get_interface_get_command(target, engine)
        
        command = f'connect_bd_intf_net [{source_cmd}] [{target_cmd}]'
        result = await engine.execute(command)
        
        if self._exec_success(result):
            return {
                "success": True,
                "connect_type": "interface",
                "source": source,
                "target": target,
                "message": f"接口连接成功: {source} -> {target}",
            }
        else:
            errors = self._exec_errors(result)
            return {
                "success": False,
                "connect_type": "interface",
                "source": source,
                "target": target,
                "message": "接口连接失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def _get_interface_get_command(self, name: str, engine) -> str:
        """获取接口对象的 get 命令"""
        # 检查是否为接口端口
        result = await engine.execute(f'get_bd_intf_ports -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return f'get_bd_intf_ports {name}'
        
        # 默认使用接口引脚
        return f'get_bd_intf_pins {name}'
    
    async def _connect_signal(
        self,
        source: str,
        target: str,
        engine,
    ) -> dict[str, Any]:
        """连接信号"""
        # 确定使用 get_bd_pins 还是 get_bd_ports
        source_cmd = await self._get_signal_get_command(source, engine)
        target_cmd = await self._get_signal_get_command(target, engine)
        
        command = f'connect_bd_net [{source_cmd}] [{target_cmd}]'
        result = await engine.execute(command)
        
        if self._exec_success(result):
            return {
                "success": True,
                "connect_type": "signal",
                "source": source,
                "target": target,
                "message": f"信号连接成功: {source} -> {target}",
            }
        else:
            errors = self._exec_errors(result)
            return {
                "success": False,
                "connect_type": "signal",
                "source": source,
                "target": target,
                "message": "信号连接失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def _get_signal_get_command(self, name: str, engine) -> str:
        """获取信号对象的 get 命令"""
        # 检查是否为端口
        result = await engine.execute(f'get_bd_ports -quiet {name}')
        if self._exec_success(result) and self._exec_text(result).strip():
            return f'get_bd_ports {name}'
        
        # 默认使用引脚
        return f'get_bd_pins {name}'
    
    async def add_bd_ip(
        self,
        ip_type: str,
        instance_name: str,
        config: dict[str, Any] | None = None,
        auto_find: bool = True,
    ) -> dict[str, Any]:
        """
        添加 IP 到 Block Design

        支持两种方式：
        1. 简称: ip_type="axi_gpio" - 自动查找最新版本（推荐）
        2. 完整 VLNV: ip_type="xilinx.com:ip:axi_gpio:2.0"

        参考 ADI 的 ad_ip_instance 函数设计，用户只需提供 IP 简称，
        系统会自动查找匹配的完整 VLNV。

        Args:
            ip_type: IP 类型（简称如 "axi_gpio" 或完整 VLNV）
            instance_name: 实例名称
            config: IP 配置属性
            auto_find: 是否自动查找 VLNV（当 ip_type 为简称时）

        Returns:
            添加结果字典，包含：
            - success: 是否成功
            - instance_name: 实例名称
            - ip_type: 实际使用的 VLNV
            - resolved_vlnv: 解析后的完整 VLNV
            - message: 结果消息

        Example:
            ```python
            # 方式 1: 使用简称（推荐）
            result = await gf.add_bd_ip("axi_gpio", "gpio_0", {"C_GPIO_WIDTH": 8})

            # 方式 2: 使用完整 VLNV
            result = await gf.add_bd_ip("xilinx.com:ip:axi_gpio:2.0", "gpio_0")

            # 方式 3: 禁用自动查找
            result = await gf.add_bd_ip("axi_gpio", "gpio_0", auto_find=False)
            ```
        """
        engine = await self._get_engine()

        # 确定要使用的 VLNV
        actual_vlnv = ip_type

        if auto_find:
            # 检查是否为简称（不包含完整 VLNV 格式）
            if ':' not in ip_type or ip_type.count(':') < 3:
                # 使用 IPRegistry 查找完整 VLNV
                if self._ip_registry is None:
                    self._ip_registry = IPRegistry(engine)

                resolved_vlnv = await self._ip_registry.find_ip(ip_type)
                if resolved_vlnv:
                    actual_vlnv = resolved_vlnv
                    logger.info(f"IP '{ip_type}' 解析为: {actual_vlnv}")
                else:
                    return {
                        "success": False,
                        "instance_name": None,
                        "ip_type": ip_type,
                        "resolved_vlnv": None,
                        "message": f"未找到 IP: {ip_type}",
                        "error": f"无法找到匹配的 IP 定义: {ip_type}",
                    }

        # 创建 IP 实例
        commands = [f'create_bd_cell -type ip -vlnv {actual_vlnv} {instance_name}']

        # 添加配置命令（参考 ADI 的做法，添加 CONFIG. 前缀）
        if config:
            config_list = []
            for key, value in config.items():
                # 如果键还没有 CONFIG. 前缀，添加它
                if not key.startswith("CONFIG."):
                    key = f"CONFIG.{key}"
                config_list.append(f"{key} {{{value}}}")

            config_str = " ".join(config_list)
            commands.append(f'set_property -dict [list {config_str}] [get_bd_cells {instance_name}]')

        results = await engine.execute_batch(commands)
        success = all(r.success for r in results)

        if success:
            return {
                "success": True,
                "instance_name": instance_name,
                "ip_type": ip_type,
                "resolved_vlnv": actual_vlnv,
                "message": f"IP '{instance_name}' 添加成功 (VLNV: {actual_vlnv})",
            }
        else:
            errors = []
            for r in results:
                if not r.success:
                    if r.error:
                        errors.append(r.error.message)
                    if r.warnings:
                        errors.extend(r.warnings)
            return {
                "success": False,
                "instance_name": None,
                "ip_type": ip_type,
                "resolved_vlnv": actual_vlnv,
                "message": "IP 添加失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    # ==================== IP 管理 ====================
    
    async def find_ip(self, ip_name: str) -> dict[str, Any]:
        """
        查找 IP 的完整 VLNV

        Args:
            ip_name: IP 简称（如 "axi_gpio"）

        Returns:
            查找结果字典，包含：
            - success: 是否成功
            - ip_name: IP 简称
            - vlnv: 完整 VLNV
            - message: 结果消息

        Example:
            ```python
            result = await gf.find_ip("axi_gpio")
            # 返回: {"success": True, "vlnv": "xilinx.com:ip:axi_gpio:2.0", ...}
            ```
        """
        try:
            registry = await self._get_ip_registry()
            query = await registry.query_ip(ip_name)
        except Exception as exc:
            return {
                "success": False,
                "ip_name": ip_name,
                "vlnv": None,
                "message": f"查找 IP 失败: {ip_name}",
                "error": "tcp_protocol_error",
                "details": str(exc),
            }

        if query.success:
            return {
                "success": True,
                "ip_name": ip_name,
                "vlnv": query.selected_vlnv,
                "candidates": query.candidates,
                "message": query.message,
                "error": None,
            }
        if query.error == "multiple_candidates" and query.selected_vlnv:
            return {
                "success": True,
                "ip_name": ip_name,
                "vlnv": query.selected_vlnv,
                "candidates": query.candidates,
                "message": (
                    f"{query.message}；默认返回最新候选 {query.selected_vlnv}"
                ),
                "error": None,
                "warning": "multiple_candidates",
            }
        return {
            "success": False,
            "ip_name": ip_name,
            "vlnv": query.selected_vlnv,
            "candidates": query.candidates,
            "message": query.message,
            "error": query.error,
            "details": query.details,
        }

    async def list_available_ips(
        self,
        filter_pattern: str = "*",
    ) -> dict[str, Any]:
        """
        列出所有可用的 IP

        Args:
            filter_pattern: 过滤模式（支持通配符）

        Returns:
            IP 列表结果字典

        Example:
            ```python
            # 列出所有 AXI 相关 IP
            result = await gf.list_available_ips("axi*")
            ```
        """
        try:
            registry = await self._get_ip_registry()
            result = await registry.query_available_ips(filter_pattern)
        except Exception as exc:
            return {
                "success": False,
                "ips": [],
                "count": 0,
                "message": "获取 IP catalog 失败",
                "error": "catalog_unavailable",
                "details": str(exc),
            }

        return {
            "success": result.get("success", False),
            "ips": result.get("ips", []),
            "count": result.get("count", 0),
            "message": result.get("message", ""),
            "error": result.get("error"),
            "details": result.get("details"),
        }

    async def get_ip_versions(self, ip_name: str) -> dict[str, Any]:
        """
        获取指定 IP 的所有可用版本

        Args:
            ip_name: IP 简称

        Returns:
            版本列表结果字典

        Example:
            ```python
            result = await gf.get_ip_versions("axi_gpio")
            # 返回: {"success": True, "versions": ["2.0", "1.1"], ...}
            ```
        """
        engine = await self._get_engine()

        if self._ip_registry is None:
            self._ip_registry = IPRegistry(engine)

        versions = await self._ip_registry.get_ip_versions(ip_name)

        return {
            "success": True,
            "ip_name": ip_name,
            "versions": versions,
            "count": len(versions),
            "message": f"IP '{ip_name}' 有 {len(versions)} 个版本",
        }

    async def get_ip_info(self, ip_name: str) -> dict[str, Any]:
        """
        获取 IP 的详细信息

        Args:
            ip_name: IP 简称或完整 VLNV

        Returns:
            IP 信息字典

        Example:
            ```python
            result = await gf.get_ip_info("axi_gpio")
            # 返回: {"success": True, "info": {...}, ...}
            ```
        """
        engine = await self._get_engine()

        if self._ip_registry is None:
            self._ip_registry = IPRegistry(engine)

        info = await self._ip_registry.get_ip_info(ip_name)

        if info:
            return {
                "success": True,
                "info": {
                    "vlnv": info.vlnv,
                    "vendor": info.vendor,
                    "library": info.library,
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                },
                "message": f"获取 IP 信息成功: {info.vlnv}",
            }
        else:
            return {
                "success": False,
                "info": None,
                "message": f"未找到 IP: {ip_name}",
            }
    
    async def apply_bd_automation(self, rule: str = "all") -> dict[str, Any]:
        """
        应用 Block Design 自动连接
        
        Args:
            rule: 自动连接规则（all, axi, clock, reset）
        
        Returns:
            应用结果字典
        """
        engine = await self._get_engine()
        
        if rule == "all":
            # 应用所有自动连接
            command = 'apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config { Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} Master {Auto} Slave {Auto} ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}}  [get_bd_intf_pins -filter {MODE==Master && VLNV=="xilinx.com:interface:aximm_rtl:1.0"} ]'
        else:
            command = f'apply_bd_automation -rule xilinx.com:bd_rule:{rule}'
        
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "rule": rule,
                "message": f"自动连接 '{rule}' 应用成功",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "rule": None,
                "message": "自动连接应用失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def validate_bd_design(self) -> dict[str, Any]:
        """
        验证 Block Design
        
        Returns:
            验证结果字典
        """
        engine = await self._get_engine()
        
        command = 'validate_bd_design'
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "message": "Block Design 验证通过",
                "warnings": [],
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "message": "Block Design 验证失败",
                "error": "; ".join(errors) if errors else "未知错误",
                "warnings": [],
            }
    
    async def generate_bd_wrapper(self) -> dict[str, Any]:
        """
        生成 HDL Wrapper
        
        Returns:
            生成结果字典
        """
        engine = await self._get_engine()
        
        # 获取当前 Block Design 名称
        bd_result = await engine.execute('current_bd_design')
        if not bd_result.success:
            errors = [bd_result.error.message] if bd_result.error else []
            return {
                "success": False,
                "wrapper_name": None,
                "message": "无法获取当前 Block Design",
                "error": "; ".join(errors),
            }
        
        bd_name = (bd_result.data or "").strip()
        
        command = f'generate_target all [get_files [get_property FILE_NAME [get_bd_designs {bd_name}]]]'
        result = await engine.execute(command)
        
        if result.success:
            wrapper_name = f"{bd_name}_wrapper"
            return {
                "success": True,
                "wrapper_name": wrapper_name,
                "message": "HDL Wrapper 生成成功",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "wrapper_name": None,
                "message": "HDL Wrapper 生成失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def create_bd_port(
        self,
        name: str,
        direction: str,
        port_type: str = "wire",
        width: int = 1,
    ) -> dict[str, Any]:
        """
        创建 Block Design 端口
        
        Args:
            name: 端口名称
            direction: 端口方向（in, out, inout）
            port_type: 端口类型（wire, clock, reset 等）
            width: 端口宽度
        
        Returns:
            创建结果字典
        """
        engine = await self._get_engine()
        
        # 构建命令
        command = f'create_bd_port -dir {direction} -type {port_type} -from 0 -to {width-1} {name}'
        if width == 1:
            command = f'create_bd_port -dir {direction} -type {port_type} {name}'
        
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "port_name": name,
                "direction": direction,
                "port_type": port_type,
                "width": width,
                "message": f"端口 '{name}' 创建成功",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "port_name": None,
                "message": "端口创建失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def connect_bd_ports(
        self,
        source_port: str,
        target_port: str,
    ) -> dict[str, Any]:
        """
        连接 Block Design 端口
        
        Args:
            source_port: 源端口路径
            target_port: 目标端口路径
        
        Returns:
            连接结果字典
        """
        engine = await self._get_engine()
        
        # 构建命令
        command = f'connect_bd_net [get_bd_pins {source_port}] [get_bd_pins {target_port}]'
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "source_port": source_port,
                "target_port": target_port,
                "message": f"端口连接成功: {source_port} -> {target_port}",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "source_port": source_port,
                "target_port": target_port,
                "message": "端口连接失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    # ==================== 约束管理 ====================
    
    async def create_clock(
        self,
        name: str,
        period: float,
        target: str,
    ) -> dict[str, Any]:
        """
        创建时钟约束
        
        Args:
            name: 时钟名称
            period: 时钟周期（纳秒）
            target: 目标端口名称
        
        Returns:
            创建结果字典
        """
        engine = await self._get_engine()
        
        command = f'create_clock -name {name} -period {period} [get_ports {target}]'
        result = await engine.execute(command)
        
        if result.success:
            return {
                "success": True,
                "clock_name": name,
                "period": period,
                "target": target,
                "message": f"时钟约束 '{name}' 创建成功",
            }
        else:
            errors = [result.error.message] if result.error else []
            return {
                "success": False,
                "clock_name": None,
                "message": "时钟约束创建失败",
                "error": "; ".join(errors) if errors else "未知错误",
            }
    
    async def create_constraint_file(
        self,
        filename: str,
        content: str,
    ) -> dict[str, Any]:
        """
        创建约束文件
        
        Args:
            filename: 文件名
            content: 文件内容
        
        Returns:
            创建结果字典
        """
        import os
        from pathlib import Path
        
        engine = await self._get_engine()
        
        # 获取项目目录
        if not self._project_path:
            return {
                "success": False,
                "file_path": None,
                "message": "未打开项目",
            }
        
        # 创建约束文件
        constraint_dir = Path(self._project_path) / "srcs" / "constrs_1" / "new"
        constraint_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = constraint_dir / filename
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 添加到项目
            add_result = await engine.execute(f'add_files -fileset constrs_1 "{file_path}"')
            
            if add_result.success:
                return {
                    "success": True,
                    "file_path": str(file_path),
                    "message": f"约束文件 '{filename}' 创建成功",
                }
            else:
                errors = [add_result.error.message] if add_result.error else []
                return {
                    "success": False,
                    "file_path": None,
                    "message": "添加约束文件失败",
                    "error": "; ".join(errors) if errors else "未知错误",
                }
        except Exception as e:
            return {
                "success": False,
                "file_path": None,
                "message": f"创建约束文件失败: {e}",
            }
    
    # ==================== 属性 ====================
    
    @property
    def project_path(self) -> str | None:
        """获取当前项目路径"""
        return self._project_path
    
    # ==================== 自动配置 ====================
    
    async def get_clock_manager(self) -> ClockManager:
        """
        获取时钟管理器（异步）
        
        Returns:
            ClockManager 实例
        
        Example:
            ```python
            clock_mgr = await gf.get_clock_manager()
            await clock_mgr.create_clock("clk0", 10.0)
            ```
        """
        if self._clock_manager is None:
            engine = await self._get_engine()
            self._clock_manager = ClockManager(engine)
        return self._clock_manager
    
    async def get_interrupt_manager(self) -> InterruptManager:
        """
        获取中断管理器（异步）
        
        Returns:
            InterruptManager 实例
        
        Example:
            ```python
            irq_mgr = await gf.get_interrupt_manager()
            await irq_mgr.connect_interrupt("gpio_0/ip2intc_irpt")
            ```
        """
        if self._interrupt_manager is None:
            engine = await self._get_engine()
            self._interrupt_manager = InterruptManager(engine)
        return self._interrupt_manager
    
    async def create_clock_network(
        self,
        name: str,
        period: float,
        source: str | None = None,
    ) -> dict[str, Any]:
        """
        创建时钟网络
        
        Args:
            name: 时钟名称
            period: 时钟周期（纳秒）
            source: 时钟源引脚（可选）
        
        Returns:
            创建结果字典
        
        Example:
            ```python
            # 创建 100MHz 时钟
            result = await gf.create_clock_network("fclk0", period=10.0, source="ps7_0/FCLK_CLK0")
            ```
        """
        manager = await self.get_clock_manager()
        return await manager.create_clock(name, period, source)
    
    async def connect_clock_network(
        self,
        clock_name: str,
        target_pins: list[str],
    ) -> dict[str, Any]:
        """
        连接时钟网络到目标引脚
        
        Args:
            clock_name: 时钟名称
            target_pins: 目标引脚列表
        
        Returns:
            连接结果字典
        
        Example:
            ```python
            result = await gf.connect_clock_network("fclk0", ["gpio_0/s_axi_aclk", "timer_0/s_axi_aclk"])
            ```
        """
        manager = await self.get_clock_manager()
        return await manager.connect_clock(clock_name, target_pins)
    
    async def create_reset_network(
        self,
        name: str,
        clock_name: str,
        active_low: bool = True,
        source: str | None = None,
    ) -> dict[str, Any]:
        """
        创建复位网络
        
        Args:
            name: 复位名称
            clock_name: 关联的时钟名称
            active_low: 是否为低电平有效
            source: 复位源引脚（可选）
        
        Returns:
            创建结果字典
        
        Example:
            ```python
            result = await gf.create_reset_network("fclk0_reset", "fclk0", source="ps7_0/FCLK_RESET0_N")
            ```
        """
        manager = await self.get_clock_manager()
        return await manager.create_reset(name, clock_name, active_low, source)
    
    async def connect_reset_network(
        self,
        reset_name: str,
        target_pins: list[str],
    ) -> dict[str, Any]:
        """
        连接复位网络到目标引脚
        
        Args:
            reset_name: 复位名称
            target_pins: 目标引脚列表
        
        Returns:
            连接结果字典
        """
        manager = await self.get_clock_manager()
        return await manager.connect_reset(reset_name, target_pins)
    
    async def setup_ps7_clocks(
        self,
        ps7_name: str = "ps7_0",
        frequencies: dict[int, float] | None = None,
    ) -> dict[str, Any]:
        """
        设置 PS7 的 Fabric 时钟
        
        Args:
            ps7_name: PS7 实例名称
            frequencies: FCLK 频率配置，key 为 FCLK ID (0-3)，value 为频率 (MHz)
        
        Returns:
            设置结果字典
        
        Example:
            ```python
            # 创建 FCLK0 为 100MHz
            result = await gf.setup_ps7_clocks(frequencies={0: 100.0})
            
            # 创建多个时钟
            result = await gf.setup_ps7_clocks(frequencies={0: 100.0, 1: 200.0})
            ```
        """
        manager = await self.get_clock_manager()
        return await manager.create_ps7_clocks(ps7_name, frequencies)
    
    async def connect_interrupt(
        self,
        source_pin: str,
        irq_number: int | None = None,
    ) -> dict[str, Any]:
        """
        连接中断信号
        
        Args:
            source_pin: 中断源引脚
            irq_number: 指定中断号（可选，自动分配）
        
        Returns:
            连接结果字典
        
        Example:
            ```python
            # 自动分配中断号
            result = await gf.connect_interrupt("gpio_0/ip2intc_irpt")
            
            # 指定中断号
            result = await gf.connect_interrupt("timer_0/interrupt", irq_number=0)
            ```
        """
        manager = await self.get_interrupt_manager()
        return await manager.connect_interrupt(source_pin, irq_number)
    
    async def list_interrupts(self) -> list[dict]:
        """
        列出所有已连接的中断
        
        Returns:
            中断列表
        """
        manager = await self.get_interrupt_manager()
        return await manager.list_interrupts()
    
    async def auto_configure(
        self,
        instances: list[str],
        clock_name: str | None = None,
        reset_name: str | None = None,
        connect_interrupts: bool = True,
    ) -> dict[str, Any]:
        """
        自动配置时钟、复位和中断
        
        自动为指定的 IP 实例：
        1. 连接时钟和复位信号
        2. 连接中断信号（可选）
        3. 分配地址空间
        
        Args:
            instances: IP 实例名称列表
            clock_name: 时钟名称（可选，使用默认时钟）
            reset_name: 复位名称（可选，使用默认复位）
            connect_interrupts: 是否连接中断，默认 True
        
        Returns:
            配置结果字典
        
        Example:
            ```python
            # 先设置 PS7 时钟
            await gf.setup_ps7_clocks(frequencies={0: 100.0})
            
            # 自动配置多个 IP
            result = await gf.auto_configure(["gpio_0", "timer_0", "uart_0"])
            
            # 返回结果包含：
            # - clock_connections: 时钟连接结果
            # - reset_connections: 复位连接结果
            # - interrupt_connections: 中断连接结果
            ```
        """
        logger.info(f"自动配置 IP 实例: {instances}")
        
        clock_manager = await self.get_clock_manager()
        interrupt_manager = await self.get_interrupt_manager()
        
        results = {
            "success": True,
            "instances": instances,
            "clock_connections": {},
            "reset_connections": {},
            "interrupt_connections": {},
            "errors": [],
        }
        
        for instance in instances:
            # 自动连接时钟和复位
            cr_result = await clock_manager.auto_connect_clock_reset(
                instance, clock_name, reset_name
            )
            
            results["clock_connections"][instance] = cr_result.get("clock_connected", [])
            results["reset_connections"][instance] = cr_result.get("reset_connected", [])
            
            if not cr_result.get("success"):
                results["errors"].append(f"{instance}: 时钟/复位连接失败")
            
            # 自动连接中断
            if connect_interrupts:
                irq_result = await interrupt_manager.auto_connect_interrupts(instance)
                results["interrupt_connections"][instance] = irq_result.get("connected_interrupts", [])
        
        # 自动分配地址
        engine = await self._get_engine()
        addr_result = await engine.execute("assign_bd_address")
        
        if not addr_result.get("success"):
            results["errors"].append("地址分配失败")
        
        results["success"] = len(results["errors"]) == 0
        results["message"] = f"自动配置完成，{len(instances)} 个实例"
        
        return results
    
    async def list_clock_networks(self) -> list[dict[str, Any]]:
        """
        列出所有时钟网络
        
        Returns:
            时钟网络列表
        """
        manager = await self.get_clock_manager()
        return manager.list_clocks()
    
    async def list_reset_networks(self) -> list[dict[str, Any]]:
        """
        列出所有复位网络
        
        Returns:
            复位网络列表
        """
        manager = await self.get_clock_manager()
        return manager.list_resets()
    
    async def get_interrupt_summary(self) -> dict[str, Any]:
        """
        获取中断配置摘要
        
        Returns:
            中断配置摘要
        """
        manager = await self.get_interrupt_manager()
        return manager.get_interrupt_summary()
