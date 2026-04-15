"""
GateFlow 执行引擎管理器

提供统一的 Tcl 执行接口，优先使用 TCP 连接，回退到 subprocess 模式。

架构说明：
- TCP 模式：连接到运行中的 Vivado tcl_server (localhost:9999)，支持持久连接和实时交互
- Subprocess 模式：每次执行启动新的 Vivado batch 进程，适用于无服务器场景
- Auto 模式：优先尝试 TCP，失败则回退到 subprocess
"""

import asyncio
import json
import logging
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from gateflow.execution_context import ExecutionContext, ExecutionContextKind
from gateflow.settings import CONFIG_DIR, TimeoutConfig, get_settings
from gateflow.vivado.tcp_client import (
    TcpClientManager,
    TcpConfig,
    VivadoTcpClient,
)
from gateflow.vivado.tcl_engine import TclEngine, TclResult, VivadoDetector
from gateflow.vivado.tcl_server import TclServerInstaller
from gateflow.utils.path_utils import PathConverter
from gateflow.errors import (
    ErrorCode,
    ErrorInfo,
    Result,
    make_success,
    make_error,
    generate_request_id,
    get_error_suggestion,
)

logger = logging.getLogger(__name__)

GUI_SESSION_STATE_FILE = CONFIG_DIR / "gui_session.json"


class EngineMode:
    """引擎模式枚举"""
    TCP = "tcp"
    SUBPROCESS = "subprocess"
    AUTO = "auto"
    GUI_SESSION = "gui_session"


class EngineManager:
    """
    执行引擎管理器
    
    统一管理 TCP 和 subprocess 两种执行模式：
    - 优先尝试 TCP 连接（如果 Vivado 已运行）
    - TCP 不可用时回退到 subprocess 模式
    - 支持会话管理，保持 Vivado 进程
    
    使用示例：
        # 获取单例实例
        manager = get_engine_manager()
        
        # 初始化（自动选择最佳模式）
        await manager.initialize()
        
        # 执行 Tcl 命令
        result = await manager.execute("puts Hello")
        
        # 或使用便捷函数
        result = await execute_tcl("current_project")
    """
    
    _instance: 'EngineManager | None' = None
    
    def __new__(cls):
        """单例模式：确保全局只有一个引擎管理器实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化引擎管理器"""
        if self._initialized:
            return
        
        self._initialized = True
        self._mode: str = EngineMode.AUTO
        self._tcp_client: VivadoTcpClient | None = None
        self._tcl_engine: TclEngine | None = None
        self._session_active = False
        self._last_project: str | None = None
        self._gui_process: subprocess.Popen[str] | None = None
        self._gui_project_path: str | None = None
        self._gui_tcp_port: int | None = None
        self._gui_server_script: str | None = None
        self._gui_owned_process: bool = False
        self._gui_pid: int | None = None
        self._gui_startup_pending: bool = False
        
        # 从 settings 读取超时配置
        settings = get_settings()
        self._execution_context: ExecutionContext = settings.get_execution_context()
        self._timeout_config: TimeoutConfig = settings.get_timeout_config()
        self._load_gui_session_state()
        
    @property
    def mode(self) -> str:
        """获取当前模式"""
        return self._mode
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接（TCP 模式）"""
        if self._tcp_client:
            return self._tcp_client.is_connected
        return False
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and (self._tcp_client is not None or self._tcl_engine is not None)

    @property
    def execution_context(self) -> ExecutionContext:
        """Return the configured execution context."""
        return self._execution_context
    
    async def initialize(self, mode: str = EngineMode.AUTO) -> bool:
        """
        初始化引擎
        
        Args:
            mode: 引擎模式 (tcp, subprocess, auto)
        
        Returns:
            初始化是否成功
        """
        if self._execution_context.kind in {
            ExecutionContextKind.NON_PROJECT,
            ExecutionContextKind.EMBEDDED,
        }:
            logger.info(
                f"执行上下文已切换为 {self._execution_context.kind}，当前仍复用 Vivado 主执行引擎"
            )

        if mode == EngineMode.AUTO:
            settings = get_settings()
            if settings.gui_enabled:
                logger.info("AUTO 模式检测到 gui_enabled=true，优先启动 GUI 会话模式")
                gui_result = await self.ensure_gui_session(
                    project_path=self._last_project,
                    tcp_port=settings.gui_tcp_port,
                )
                if gui_result.get("success", False):
                    self._mode = EngineMode.GUI_SESSION
                    return True
                logger.warning(f"GUI 会话模式初始化失败，回退到常规 AUTO 路径: {gui_result.get('error')}")

            # 尝试 TCP 连接
            try:
                self._tcp_client = TcpClientManager.get_client()
                if await TcpClientManager.ensure_connected():
                    self._mode = EngineMode.TCP
                    logger.info("使用 TCP 模式连接 Vivado")
                    return True
            except Exception as e:
                logger.debug(f"TCP 连接失败: {e}")
            
            # 回退到 subprocess 模式
            try:
                self._tcl_engine = TclEngine()
                self._mode = EngineMode.SUBPROCESS
                logger.info("使用 subprocess 模式")
                return True
            except Exception as e:
                logger.error(f"初始化失败: {e}")
                return False
        
        elif mode == EngineMode.TCP:
            self._tcp_client = TcpClientManager.get_client()
            if await TcpClientManager.ensure_connected():
                self._mode = EngineMode.TCP
                return True
            return False
        
        elif mode == EngineMode.GUI_SESSION:
            self._mode = EngineMode.GUI_SESSION
            return True
        
        else:  # subprocess
            self._tcl_engine = TclEngine()
            self._mode = EngineMode.SUBPROCESS
            return True
    
    async def execute(
        self,
        command: str,
        timeout: float | None = None,
        auto_reconnect: bool = True,
    ) -> Result:
        """
        执行 Tcl 命令
        
        Args:
            command: Tcl 命令
            timeout: 超时时间（秒），None 表示使用默认配置 (TimeoutConfig.single_command)
            auto_reconnect: 超时/断线后是否自动重连（仅 TCP 模式）
        
        Returns:
            Result 统一返回结构
        """
        # 使用默认超时配置
        if timeout is None:
            timeout = self._timeout_config.single_command
        
        # 自动转换命令中的 Windows 路径为 Tcl 格式
        command = PathConverter.convert_paths_in_command(command)
        logger.debug(f"执行命令（路径已转换）: {command}")
        
        start_time = time.time()
        
        if self._mode in {EngineMode.TCP, EngineMode.GUI_SESSION} and self._tcp_client:
            response = await self._tcp_client.execute_tcl(command, timeout, auto_reconnect)
            elapsed = time.time() - start_time
            
            # 记录超时警告
            if not response.success and "超时" in (response.error or ""):
                logger.warning(
                    f"[{response.request_id}] 命令超时 ({timeout}s): {command[:100]}{'...' if len(command) > 100 else ''}"
                )
            
            # 使用 TclResponse 的 to_result 方法转换
            result = response.to_result()
            result.execution_time = elapsed
            return result
            
        elif self._tcl_engine:
            # 使用会话模式执行，保持项目状态
            tcl_result = await self._tcl_engine.execute_in_session_async(command, timeout)
            elapsed = time.time() - start_time
            
            # 记录超时警告
            if not tcl_result.success and any("超时" in err for err in tcl_result.errors):
                logger.warning(
                    f"命令超时 ({timeout}s): {command[:100]}{'...' if len(command) > 100 else ''}"
                )
            
            # 使用 TclResult 的 to_result 方法转换
            result = tcl_result.to_result()
            result.execution_time = elapsed
            return result
        else:
            return make_error(
                code=ErrorCode.ENGINE_NOT_INITIALIZED,
                message="执行引擎未初始化",
                suggestion=get_error_suggestion(ErrorCode.ENGINE_NOT_INITIALIZED),
                request_id=generate_request_id(),
                execution_time=0.0,
            )
    
    async def execute_batch(
        self,
        commands: list[str],
        timeout: float | None = None,
        per_command_timeout: float | None = None,
        stop_on_error: bool = True,
    ) -> list[Result]:
        """
        批量执行 Tcl 命令
        
        超时语义说明：
        - timeout: 批量命令的总超时时间（秒），从第一个命令开始到最后一个命令完成
          - None 表示使用默认配置 (TimeoutConfig.batch_total)
          - 如果总时间超过此值，剩余命令将被取消并返回超时错误
        - per_command_timeout: 单个命令的超时时间（秒）
          - None 表示使用默认配置 (TimeoutConfig.single_command)
          - 每个命令的执行时间不能超过此值
        
        Args:
            commands: Tcl 命令列表
            timeout: 总超时时间（秒），None 表示使用默认值
            per_command_timeout: 单命令超时（秒），None 表示使用默认值
            stop_on_error: 遇到错误是否停止
        
        Returns:
            Result 列表
        """
        # 使用默认超时配置
        if timeout is None:
            timeout = self._timeout_config.batch_total
        if per_command_timeout is None:
            per_command_timeout = self._timeout_config.single_command
        
        results = []
        batch_start_time = time.time()
        
        for i, cmd in enumerate(commands):
            # 检查总超时
            elapsed = time.time() - batch_start_time
            remaining_time = timeout - elapsed
            
            if remaining_time <= 0:
                # 总超时，记录警告并停止执行
                logger.warning(
                    f"批量执行总超时 ({timeout}s)，已执行 {i}/{len(commands)} 个命令"
                )
                # 为剩余命令添加超时错误结果
                for j in range(i, len(commands)):
                    results.append(make_error(
                        code=ErrorCode.COMMAND_TIMEOUT,
                        message=f"批量执行总超时: 超过 {timeout} 秒",
                        suggestion=get_error_suggestion(ErrorCode.COMMAND_TIMEOUT),
                        request_id=generate_request_id(),
                        execution_time=0.0,
                    ))
                break
            
            # 执行单个命令，使用剩余时间和单命令超时的较小值
            cmd_timeout = min(per_command_timeout, remaining_time)
            cmd_start_time = time.time()
            
            result = await self.execute(cmd, cmd_timeout)
            cmd_elapsed = time.time() - cmd_start_time
            
            # 记录命令完成日志
            logger.info(
                f"命令完成 [{i+1}/{len(commands)}]: {cmd[:50]}{'...' if len(cmd) > 50 else ''} "
                f"耗时 {cmd_elapsed:.2f}s"
            )
            
            results.append(result)
            
            # 检查是否需要停止
            if not result.success and stop_on_error:
                logger.warning(
                    f"批量执行因错误停止，已执行 {i+1}/{len(commands)} 个命令"
                )
                break
        
        # 记录批量执行总耗时
        total_elapsed = time.time() - batch_start_time
        logger.info(
            f"批量执行完成: {len(results)}/{len(commands)} 个命令，总耗时 {total_elapsed:.2f}s"
        )
        
        return results
    
    async def execute_script(
        self,
        script_path: str,
        timeout: float | None = None,
    ) -> Result:
        """
        执行 Tcl 脚本文件
        
        Args:
            script_path: 脚本文件路径
            timeout: 超时时间（秒），None 表示使用默认配置
        
        Returns:
            Result 执行结果
        """
        # 使用默认超时配置
        if timeout is None:
            timeout = self._timeout_config.batch_total
        
        # 读取脚本内容
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
        except FileNotFoundError:
            return make_error(
                code=ErrorCode.FILE_NOT_FOUND,
                message=f"脚本文件不存在: {script_path}",
                suggestion=get_error_suggestion(ErrorCode.FILE_NOT_FOUND),
                request_id=generate_request_id(),
                execution_time=0.0,
            )
        except PermissionError:
            return make_error(
                code=ErrorCode.FILE_PERMISSION_DENIED,
                message=f"无权限读取脚本文件: {script_path}",
                suggestion=get_error_suggestion(ErrorCode.FILE_PERMISSION_DENIED),
                request_id=generate_request_id(),
                execution_time=0.0,
            )
        except Exception as e:
            return make_error(
                code=ErrorCode.FILE_READ_ERROR,
                message=f"读取脚本文件失败: {e}",
                request_id=generate_request_id(),
                execution_time=0.0,
            )
        
        return await self.execute(script_content, timeout)
    
    async def execute_async(
        self,
        command: str,
        timeout: float | None = None,
        auto_reconnect: bool = True,
    ) -> Result:
        """
        异步执行 Tcl 命令（execute 的别名）
        
        为了兼容使用 TclEngine 的代码，提供此方法作为 execute() 的别名。
        
        Args:
            command: Tcl 命令
            timeout: 超时时间（秒），None 表示使用默认配置
            auto_reconnect: 超时/断线后是否自动重连（仅 TCP 模式）
        
        Returns:
            Result 统一返回结构
        """
        return await self.execute(command, timeout, auto_reconnect)

    @staticmethod
    def _normalize_gui_pid(pid: Any) -> int | None:
        """Return an integer pid when available."""
        return pid if isinstance(pid, int) and pid > 0 else None

    @classmethod
    def _is_process_running(cls, pid: int | None) -> bool:
        """Best-effort process liveness check for persisted GUI sessions."""
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def _save_gui_session_state(self) -> None:
        """Persist GUI session metadata so status/attach can survive new CLI processes."""
        if self._gui_tcp_port is None:
            return

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "project_path": self._gui_project_path,
            "tcp_port": self._gui_tcp_port,
            "server_script": self._gui_server_script,
            "owned_process": self._gui_owned_process,
            "pid": self._gui_pid,
            "startup_pending": self._gui_startup_pending,
        }
        GUI_SESSION_STATE_FILE.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _clear_gui_session_state(self) -> None:
        """Remove persisted GUI session metadata."""
        try:
            GUI_SESSION_STATE_FILE.unlink(missing_ok=True)
        except Exception:
            logger.debug("failed to clear persisted GUI session state", exc_info=True)

    def _load_gui_session_state(self) -> None:
        """Load persisted GUI session metadata if it still looks valid."""
        if not GUI_SESSION_STATE_FILE.exists():
            return

        try:
            payload = json.loads(GUI_SESSION_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            logger.debug("failed to read persisted GUI session state", exc_info=True)
            self._clear_gui_session_state()
            return

        pid = self._normalize_gui_pid(payload.get("pid"))
        startup_pending = bool(payload.get("startup_pending", False))
        tcp_port = payload.get("tcp_port")
        if pid is not None and not self._is_process_running(pid):
            self._clear_gui_session_state()
            return
        if pid is None and startup_pending:
            self._clear_gui_session_state()
            return

        self._gui_pid = pid
        self._gui_project_path = payload.get("project_path")
        self._gui_tcp_port = tcp_port if isinstance(tcp_port, int) else None
        self._gui_server_script = payload.get("server_script")
        self._gui_owned_process = False
        self._gui_startup_pending = startup_pending

    def _persist_gui_launch(
        self,
        *,
        process: subprocess.Popen[str] | None,
        project_path: str | None,
        tcp_port: int,
        server_script: str | None,
        owned_process: bool,
        startup_pending: bool,
    ) -> None:
        """Update in-memory and persisted GUI session state."""
        self._gui_process = process
        normalized_pid = self._normalize_gui_pid(getattr(process, "pid", None))
        if normalized_pid is not None:
            self._gui_pid = normalized_pid
        self._gui_project_path = project_path
        self._gui_tcp_port = tcp_port
        self._gui_server_script = server_script
        self._gui_owned_process = owned_process
        self._gui_startup_pending = startup_pending
        self._save_gui_session_state()

    def _gui_session_is_active(self) -> bool:
        """Return whether the manager has a live or persisted GUI session."""
        if self._gui_process is not None and self._gui_process.poll() is None:
            return True
        if self._mode == EngineMode.GUI_SESSION and self._tcp_client is not None:
            return True
        if self._gui_startup_pending and self._is_process_running(self._gui_pid):
            return True
        if self._gui_tcp_port is not None and not self._gui_startup_pending:
            return True
        return False

    async def _connect_gui_tcp_client(self, tcp_port: int) -> bool:
        """Connect the shared TCP client to a GUI session port."""
        settings = get_settings()
        TcpClientManager.reset()
        tcp_config = TcpConfig(
            host=settings.tcp_host,
            port=tcp_port,
            timeout=settings.timeout_single_command,
            reconnect_attempts=settings.reconnect_attempts,
            reconnect_delay=settings.reconnect_delay,
        )
        self._tcp_client = TcpClientManager.get_client(config=tcp_config)
        return await TcpClientManager.ensure_connected()

    def _build_pending_gui_response(
        self,
        *,
        project_path: str | None,
        tcp_port: int,
        server_script: str | None,
    ) -> dict[str, Any]:
        """Return a response for a GUI session that is still starting."""
        return {
            "success": False,
            "message": "GUI 会话已启动，但 TCP server 仍在初始化",
            "error": "gui_tcp_not_ready",
            "project_path": project_path,
            "tcp_port": tcp_port,
            "gui_process_started": True,
            "shared_session": True,
            "server_script": server_script,
        }

    async def _attach_gui_session_impl(
        self,
        *,
        tcp_port: int,
        project_path: str | None = None,
    ) -> dict[str, Any]:
        """Attach to an already running Vivado GUI session via its GateFlow TCP port."""
        settings = get_settings()
        ready = await self._wait_for_tcp_ready(settings.tcp_host, tcp_port, timeout=10.0)
        if not ready:
            return {
                "success": False,
                "message": "无法附着到现有 GUI 会话",
                "error": "gui_attach_tcp_not_ready",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        connected = await self._connect_gui_tcp_client(tcp_port)
        if not connected:
            return {
                "success": False,
                "message": "无法附着到现有 GUI 会话",
                "error": "gui_attach_connect_failed",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        self._gui_process = None if self._gui_process is None else self._gui_process
        self._gui_owned_process = self._gui_process is not None and self._gui_owned_process
        self._gui_tcp_port = tcp_port
        self._gui_startup_pending = False
        self._mode = EngineMode.GUI_SESSION

        if project_path:
            open_result = await self.execute(f'open_project "{project_path}"', timeout=120.0)
            if not open_result.success:
                verify_result = await self.execute("current_project", timeout=30.0)
                verify_name = (
                    getattr(verify_result, "data", None)
                    or getattr(verify_result, "result", None)
                    or getattr(verify_result, "output", None)
                )
                if not (verify_result.success and str(verify_name).strip() == Path(project_path).stem):
                    return {
                        "success": False,
                        "message": "已附着到 GUI 会话，但工程打开失败",
                        "error": "gui_attach_open_project_failed",
                        "project_path": project_path,
                        "tcp_port": tcp_port,
                        "gui_process_started": False,
                        "shared_session": False,
                    }
            self._gui_project_path = project_path
        else:
            verify_result = await self.execute("current_project", timeout=30.0)
            if verify_result.success:
                current = (
                    getattr(verify_result, "data", None)
                    or getattr(verify_result, "result", None)
                    or getattr(verify_result, "output", None)
                )
                if current:
                    self._gui_project_path = str(current).strip()

        self._save_gui_session_state()
        return {
            "success": True,
            "message": "已附着到现有 GUI 会话",
            "error": None,
            "project_path": self._gui_project_path,
            "tcp_port": tcp_port,
            "gui_process_started": False,
            "shared_session": True,
            "attached": True,
        }

    async def _ensure_gui_session_impl(
        self,
        *,
        project_path: str | None = None,
        tcp_port: int | None = None,
    ) -> dict[str, Any]:
        """Internal implementation for GUI session startup and reuse."""
        settings = get_settings()
        selected_port = tcp_port or settings.gui_tcp_port
        vivado_info = VivadoDetector.detect_vivado(
            config_path=Path(settings.vivado_path) if settings.vivado_path else None
        )
        if not vivado_info:
            return {
                "success": False,
                "message": "无法启动 GUI 会话",
                "error": "vivado_not_found",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        if self._gui_process and self._gui_process.poll() is None:
            active_port = self._gui_tcp_port or selected_port
            if self._gui_startup_pending:
                ready = await self._wait_for_tcp_ready(settings.tcp_host, active_port, timeout=2.0)
                if not ready:
                    return self._build_pending_gui_response(
                        project_path=self._gui_project_path or project_path,
                        tcp_port=active_port,
                        server_script=self._gui_server_script,
                    )
            return await self._attach_gui_session_impl(
                tcp_port=active_port,
                project_path=project_path or self._gui_project_path,
            )

        if self._gui_tcp_port == selected_port:
            if self._gui_startup_pending:
                ready = await self._wait_for_tcp_ready(settings.tcp_host, selected_port, timeout=2.0)
                if not ready:
                    return self._build_pending_gui_response(
                        project_path=self._gui_project_path or project_path,
                        tcp_port=selected_port,
                        server_script=self._gui_server_script,
                    )
            elif await self._wait_for_tcp_ready(settings.tcp_host, selected_port, timeout=2.0):
                return await self._attach_gui_session_impl(
                    tcp_port=selected_port,
                    project_path=project_path or self._gui_project_path,
                )

        config_dir = Path.home() / ".gateflow"
        config_dir.mkdir(parents=True, exist_ok=True)
        script_path = config_dir / f"gui_session_{selected_port}.tcl"
        installer = TclServerInstaller(vivado_info)
        script_path.write_text(
            installer.generate_script(port=selected_port, blocking=False),
            encoding="utf-8",
        )

        cmd = [
            str(vivado_info.executable),
            "-mode",
            "gui",
            "-source",
            str(script_path),
            "-nolog",
            "-nojournal",
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._persist_gui_launch(
            process=process,
            project_path=project_path,
            tcp_port=selected_port,
            server_script=str(script_path),
            owned_process=True,
            startup_pending=True,
        )

        ready = await self._wait_for_tcp_ready(settings.tcp_host, selected_port)
        if not ready:
            return self._build_pending_gui_response(
                project_path=project_path,
                tcp_port=selected_port,
                server_script=str(script_path),
            )

        self._gui_startup_pending = False
        self._save_gui_session_state()
        return await self._attach_gui_session_impl(
            tcp_port=selected_port,
            project_path=project_path,
        )
    
    def get_mode_info(self) -> dict[str, Any]:
        """
        获取模式信息
        
        Returns:
            包含引擎状态信息的字典
        """
        info = {
            "mode": self._mode,
            "is_connected": self.is_connected,
            "is_initialized": self.is_initialized,
            "vivado_version": None,
            "tcp_state": None,
            "execution_context": self._execution_context.to_dict(),
            "gui_session": {
                "active": self._gui_session_is_active(),
                "project_path": self._gui_project_path,
                "tcp_port": self._gui_tcp_port,
                "server_script": self._gui_server_script,
                "owned_process": self._gui_owned_process,
                "pid": self._gui_pid,
                "startup_pending": self._gui_startup_pending,
            },
        }
        
        if self._tcl_engine:
            info["vivado_version"] = self._tcl_engine.get_version()
        
        if self._tcp_client:
            info["tcp_state"] = self._tcp_client.state.value
        
        return info
    
    async def switch_mode(self, mode: str) -> bool:
        """
        切换引擎模式
        
        Args:
            mode: 目标模式
        
        Returns:
            切换是否成功
        """
        if mode == self._mode:
            return True
        
        # 断开当前连接
        if self._tcp_client and self._tcp_client.is_connected:
            await self._tcp_client.disconnect()
        
        # 重新初始化
        return await self.initialize(mode)
    
    async def close(self) -> None:
        """关闭引擎，释放资源"""
        if self._tcp_client and self._tcp_client.is_connected:
            await self._tcp_client.disconnect()
        TcpClientManager.reset()
        if self._gui_owned_process and self._gui_process and self._gui_process.poll() is None:
            self._gui_process.terminate()
            try:
                self._gui_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._gui_process.kill()
        
        self._tcp_client = None
        self._tcl_engine = None
        self._gui_process = None
        self._gui_project_path = None
        self._gui_tcp_port = None
        self._gui_server_script = None
        self._gui_owned_process = False
        self._gui_pid = None
        self._gui_startup_pending = False
        self._clear_gui_session_state()
        self._initialized = False
        logger.info("引擎已关闭")

    async def _wait_for_tcp_ready(self, host: str, port: int, timeout: float = 30.0) -> bool:
        """Wait until the GUI-loaded TCP server responds to a simple probe."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with socket.create_connection((host, port), timeout=2.0) as sock:
                    sock.settimeout(2.0)
                    sock.sendall(b"expr 1+2\n")
                    data = sock.recv(4096).decode("utf-8", errors="replace")
                    if "OK: 3" in data:
                        return True
            except OSError:
                pass
            await asyncio.sleep(1.0)
        return False

    async def ensure_gui_session(
        self,
        *,
        project_path: str | None = None,
        tcp_port: int | None = None,
    ) -> dict[str, Any]:
        """Start a new Vivado GUI instance with a non-blocking GateFlow TCP server."""
        return await self._ensure_gui_session_impl(
            project_path=project_path,
            tcp_port=tcp_port,
        )
        settings = get_settings()
        vivado_info = VivadoDetector.detect_vivado(
            config_path=Path(settings.vivado_path) if settings.vivado_path else None
        )
        if not vivado_info:
            return {
                "success": False,
                "message": "无法启动 GUI 会话",
                "error": "vivado_not_found",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        if self._gui_process and self._gui_process.poll() is None:
            return {
                "success": True,
                "message": "GUI 会话已存在",
                "error": None,
                "project_path": self._gui_project_path,
                "tcp_port": self._gui_tcp_port,
                "gui_process_started": True,
                "shared_session": True,
                "server_script": self._gui_server_script,
            }

        selected_port = tcp_port or settings.gui_tcp_port
        config_dir = Path.home() / ".gateflow"
        config_dir.mkdir(parents=True, exist_ok=True)
        script_path = config_dir / f"gui_session_{selected_port}.tcl"
        installer = TclServerInstaller(vivado_info)
        script_path.write_text(installer.generate_script(port=selected_port, blocking=False), encoding="utf-8")

        cmd = [str(vivado_info.executable), "-mode", "gui", "-source", str(script_path), "-nolog", "-nojournal"]
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
        ready = await self._wait_for_tcp_ready(settings.tcp_host, selected_port)
        if not ready:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            return {
                "success": False,
                "message": "GUI 会话已启动但 TCP server 未就绪",
                "error": "gui_tcp_not_ready",
                "project_path": project_path,
                "tcp_port": selected_port,
                "gui_process_started": False,
                "shared_session": False,
                "server_script": str(script_path),
            }

        TcpClientManager.reset()
        tcp_config = TcpConfig(
            host=settings.tcp_host,
            port=selected_port,
            timeout=settings.timeout_single_command,
            reconnect_attempts=settings.reconnect_attempts,
            reconnect_delay=settings.reconnect_delay,
        )
        self._tcp_client = TcpClientManager.get_client(config=tcp_config)
        connected = await TcpClientManager.ensure_connected()
        if not connected:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            return {
                "success": False,
                "message": "GUI 会话 TCP 连接失败",
                "error": "gui_tcp_connect_failed",
                "project_path": project_path,
                "tcp_port": selected_port,
                "gui_process_started": False,
                "shared_session": False,
                "server_script": str(script_path),
            }

        self._gui_process = process
        self._gui_owned_process = True
        self._gui_tcp_port = selected_port
        self._gui_server_script = str(script_path)
        self._mode = EngineMode.GUI_SESSION
        if project_path:
            open_result = await self.execute(f'open_project "{project_path}"', timeout=120.0)
            if not open_result.success:
                verify_result = await self.execute("current_project", timeout=30.0)
                verify_name = getattr(verify_result, "data", None) or getattr(verify_result, "result", None) or getattr(verify_result, "output", None)
                if verify_result.success and str(verify_name).strip() == Path(project_path).stem:
                    self._gui_project_path = project_path
                    return {
                        "success": True,
                        "message": "GUI 会话已启动并绑定工程",
                        "error": None,
                        "project_path": project_path,
                        "tcp_port": selected_port,
                        "gui_process_started": True,
                        "shared_session": True,
                        "server_script": str(script_path),
                    }
                return {
                    "success": False,
                    "message": "GUI 会话已启动，但打开工程失败",
                    "error": "gui_open_project_failed",
                    "project_path": project_path,
                    "tcp_port": selected_port,
                    "gui_process_started": True,
                    "shared_session": False,
                    "server_script": str(script_path),
                }
            self._gui_project_path = project_path
        else:
            self._gui_project_path = None
        return {
            "success": True,
            "message": "GUI 会话已启动",
            "error": None,
            "project_path": project_path,
            "tcp_port": selected_port,
            "gui_process_started": True,
            "shared_session": True,
            "server_script": str(script_path),
        }

    async def attach_gui_session(
        self,
        *,
        tcp_port: int,
        project_path: str | None = None,
    ) -> dict[str, Any]:
        """Attach to an already running Vivado GUI session via its GateFlow TCP port."""
        return await self._attach_gui_session_impl(
            tcp_port=tcp_port,
            project_path=project_path,
        )
        settings = get_settings()
        ready = await self._wait_for_tcp_ready(settings.tcp_host, tcp_port, timeout=10.0)
        if not ready:
            return {
                "success": False,
                "message": "无法附着到现有 GUI 会话",
                "error": "gui_attach_tcp_not_ready",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        TcpClientManager.reset()
        tcp_config = TcpConfig(
            host=settings.tcp_host,
            port=tcp_port,
            timeout=settings.timeout_single_command,
            reconnect_attempts=settings.reconnect_attempts,
            reconnect_delay=settings.reconnect_delay,
        )
        self._tcp_client = TcpClientManager.get_client(config=tcp_config)
        connected = await TcpClientManager.ensure_connected()
        if not connected:
            return {
                "success": False,
                "message": "无法附着到现有 GUI 会话",
                "error": "gui_attach_connect_failed",
                "project_path": project_path,
                "tcp_port": tcp_port,
                "gui_process_started": False,
                "shared_session": False,
            }

        self._gui_process = None
        self._gui_owned_process = False
        self._gui_tcp_port = tcp_port
        self._gui_server_script = None
        self._mode = EngineMode.GUI_SESSION

        if project_path:
            open_result = await self.execute(f'open_project "{project_path}"', timeout=120.0)
            if not open_result.success:
                verify_result = await self.execute("current_project", timeout=30.0)
                verify_name = getattr(verify_result, "data", None) or getattr(verify_result, "result", None) or getattr(verify_result, "output", None)
                if not (verify_result.success and str(verify_name).strip() == Path(project_path).stem):
                    return {
                        "success": False,
                        "message": "已附着到 GUI 会话，但工程打开失败",
                        "error": "gui_attach_open_project_failed",
                        "project_path": project_path,
                        "tcp_port": tcp_port,
                        "gui_process_started": False,
                        "shared_session": False,
                    }
            self._gui_project_path = project_path
        else:
            verify_result = await self.execute("current_project", timeout=30.0)
            if verify_result.success:
                current = getattr(verify_result, "data", None) or getattr(verify_result, "result", None) or getattr(verify_result, "output", None)
                if current:
                    self._gui_project_path = str(current).strip()

        return {
            "success": True,
            "message": "已附着到现有 GUI 会话",
            "error": None,
            "project_path": self._gui_project_path,
            "tcp_port": tcp_port,
            "gui_process_started": False,
            "shared_session": True,
            "attached": True,
        }


# 全局便捷函数
_engine_manager: EngineManager | None = None


def get_engine_manager() -> EngineManager:
    """
    获取引擎管理器单例
    
    Returns:
        EngineManager 实例
    """
    global _engine_manager
    if _engine_manager is None:
        _engine_manager = EngineManager()
    return _engine_manager


async def execute_tcl(
    command: str,
    timeout: float | None = None,
    auto_reconnect: bool = True,
) -> Result:
    """
    执行 Tcl 命令的便捷函数
    
    Args:
        command: Tcl 命令
        timeout: 超时时间（秒），None 表示使用默认配置
        auto_reconnect: 超时/断线后是否自动重连（仅 TCP 模式）
    
    Returns:
        Result 统一返回结构
    """
    manager = get_engine_manager()
    if not manager.is_initialized:
        await manager.initialize()
    return await manager.execute(command, timeout, auto_reconnect)


async def execute_tcl_batch(
    commands: list[str],
    timeout: float | None = None,
    per_command_timeout: float | None = None,
    stop_on_error: bool = True,
) -> list[Result]:
    """
    批量执行 Tcl 命令的便捷函数
    
    Args:
        commands: Tcl 命令列表
        timeout: 总超时时间（秒），None 表示使用默认值
        per_command_timeout: 单命令超时（秒），None 表示使用默认值
        stop_on_error: 遇到错误是否停止
    
    Returns:
        Result 列表
    """
    manager = get_engine_manager()
    if not manager.is_initialized:
        await manager.initialize()
    return await manager.execute_batch(commands, timeout, per_command_timeout, stop_on_error)


async def ensure_engine_initialized(mode: str = EngineMode.AUTO) -> EngineManager:
    """
    确保引擎已初始化
    
    Args:
        mode: 引擎模式
    
    Returns:
        已初始化的 EngineManager 实例
    """
    manager = get_engine_manager()
    if not manager.is_initialized:
        await manager.initialize(mode)
    return manager


async def ensure_engine_initialized_for_context(
    context: ExecutionContext,
    mode: str = EngineMode.AUTO,
) -> EngineManager:
    """
    Ensure the shared engine is initialized for a specific execution context.

    This is a Phase 4 reservation hook for future non-project / embedded flows.
    """
    manager = get_engine_manager()
    manager._execution_context = context
    if not manager.is_initialized:
        await manager.initialize(mode)
    return manager
