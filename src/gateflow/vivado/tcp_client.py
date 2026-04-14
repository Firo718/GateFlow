"""
Vivado TCP 客户端模块

通过 TCP 连接 Vivado tcl_server，实现持久连接和实时交互。
架构: AI Tool <--MCP--> GateFlow <--TCP:9999--> Vivado (tcl_server)
"""

import asyncio
import logging
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from gateflow.settings import get_settings, TimeoutConfig
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


class ConnectionState(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class TcpConfig:
    """
    TCP 连接配置
    
    Attributes:
        host: 服务器主机名
        port: 服务器端口
        timeout: 单个命令的默认超时时间（秒）
        reconnect_attempts: 重连尝试次数
        reconnect_delay: 重连延迟（秒）
        buffer_size: 缓冲区大小
        keepalive_interval: 心跳间隔（秒）
    """
    host: str = "localhost"
    port: int = 9999
    timeout: float = 60.0  # 单命令默认超时
    reconnect_attempts: int = 5
    reconnect_delay: float = 2.0
    buffer_size: int = 65536
    keepalive_interval: float = 30.0  # 心跳间隔（秒）


@dataclass
class TclResponse:
    """Tcl 响应结果（兼容旧接口，内部使用统一错误模型）"""
    success: bool
    result: str
    error: str | None = None
    execution_time: float = 0.0
    raw_output: str = ""
    warnings: list[str] = field(default_factory=list)
    request_id: str = ""  # 请求追踪 ID
    timeout_occurred: bool = False  # 是否发生超时
    reconnect_attempted: bool = False  # 是否尝试过重连
    reconnect_success: bool = False  # 重连是否成功
    
    def to_result(self) -> Result:
        """转换为统一的 Result 类型"""
        if self.success:
            return make_success(
                data=self.result,
                warnings=self.warnings,
                execution_time=self.execution_time,
                request_id=self.request_id,
            )
        else:
            # 根据错误类型选择错误码
            if self.timeout_occurred:
                code = ErrorCode.COMMAND_TIMEOUT
            elif self.error and "连接" in self.error:
                code = ErrorCode.CONNECTION_FAILED
            else:
                code = ErrorCode.COMMAND_FAILED
            
            return make_error(
                code=code,
                message=self.error or "命令执行失败",
                details={
                    "raw_output": self.raw_output,
                    "timeout_occurred": self.timeout_occurred,
                    "reconnect_attempted": self.reconnect_attempted,
                    "reconnect_success": self.reconnect_success,
                },
                suggestion=get_error_suggestion(code),
                request_id=self.request_id,
                execution_time=self.execution_time,
            )


class VivadoTcpClient:
    """
    Vivado TCP 客户端
    
    通过 TCP 连接 Vivado 的 tcl_server，支持：
    - 持久连接
    - 自动重连
    - 异步执行
    - 状态监控
    
    协议说明（遵循 TCP_PROTOCOL.md）：
    - 命令以换行符 \\n 结尾
    - 响应格式: OK: <result>\\n 或 ERROR: <error>\\n
    - 提示符格式: % \\n（部分版本使用 # \\n）
    - 支持多行响应
    """
    
    # Tcl 提示符模式（遵循协议规范，支持 % 和 #）
    PROMPT_PATTERN = re.compile(r'^[%#]\s*$', re.MULTILINE)
    
    # OK 响应模式
    OK_PATTERN = re.compile(r'^OK:\s*(.*)$', re.MULTILINE)
    
    # ERROR 响应模式
    ERROR_PATTERNS = [
        re.compile(r'^ERROR:\s*(.+)$', re.MULTILINE),
        re.compile(r'^invalid command name\s+"([^"]+)"', re.MULTILINE),
        re.compile(r'^wrong # args:.*$', re.MULTILINE),
    ]
    
    # 警告模式
    WARNING_PATTERN = re.compile(r'^WARNING:\s*(.+)$', re.MULTILINE)
    
    def __init__(self, config: TcpConfig | None = None):
        """
        初始化 TCP 客户端
        
        Args:
            config: TCP 连接配置，如果为 None 则使用默认配置
        """
        self.config = config or TcpConfig()
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._state = ConnectionState.DISCONNECTED
        self._last_error: str | None = None
        self._reconnect_count = 0
        self._on_state_change: Callable[[ConnectionState], None] | None = None
        self._lock = asyncio.Lock()  # 命令执行锁，确保一次只执行一个命令
        self._receive_buffer = ""  # 接收缓冲区
        self._connection_time: float | None = None  # 连接建立时间
        self._pending_requests: dict[str, dict[str, Any]] = {}  # 待处理请求追踪
        self._timeout_history: list[dict[str, Any]] = []  # 超时历史记录
    
    @property
    def state(self) -> ConnectionState:
        """获取当前连接状态"""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._state == ConnectionState.CONNECTED
    
    @property
    def connection_time(self) -> float | None:
        """获取连接持续时间（秒）"""
        if self._connection_time is None:
            return None
        return time.time() - self._connection_time
    
    async def connect(self) -> bool:
        """
        连接到 Vivado tcl_server
        
        Returns:
            连接是否成功
        """
        if self._state == ConnectionState.CONNECTED:
            logger.debug("已经连接，无需重复连接")
            return True
        
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            logger.info(f"正在连接 Vivado tcl_server: {self.config.host}:{self.config.port}")
            
            # 使用 asyncio 打开 TCP 连接
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host=self.config.host,
                    port=self.config.port,
                ),
                timeout=self.config.timeout
            )
            
            # 清空接收缓冲区
            self._receive_buffer = ""
            
            # 连接成功
            self._connection_time = time.time()
            self._reconnect_count = 0
            self._last_error = None
            self._set_state(ConnectionState.CONNECTED)
            
            logger.info(f"成功连接到 Vivado tcl_server")
            return True
            
        except asyncio.TimeoutError:
            error_msg = f"连接超时: {self.config.host}:{self.config.port}"
            logger.error(error_msg)
            self._last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            await self._cleanup_connection()
            return False
            
        except ConnectionRefusedError:
            error_msg = f"连接被拒绝: {self.config.host}:{self.config.port}，请确认 Vivado tcl_server 已启动"
            logger.error(error_msg)
            self._last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            await self._cleanup_connection()
            return False
            
        except OSError as e:
            error_msg = f"连接失败: {e}"
            logger.error(error_msg)
            self._last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            await self._cleanup_connection()
            return False
            
        except Exception as e:
            error_msg = f"连接异常: {e}"
            logger.exception(error_msg)
            self._last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            await self._cleanup_connection()
            return False
    
    async def disconnect(self) -> None:
        """断开连接"""
        if self._state == ConnectionState.DISCONNECTED:
            return
        
        logger.info("正在断开与 Vivado tcl_server 的连接")
        await self._cleanup_connection()
        self._set_state(ConnectionState.DISCONNECTED)
        self._connection_time = None
        logger.info("已断开连接")
    
    async def reconnect(self) -> bool:
        """
        尝试重新连接
        
        Returns:
            重连是否成功
        """
        if self._reconnect_count >= self.config.reconnect_attempts:
            error_msg = f"已达到最大重连次数 ({self.config.reconnect_attempts})"
            logger.error(error_msg)
            self._last_error = error_msg
            return False
        
        self._reconnect_count += 1
        self._set_state(ConnectionState.RECONNECTING)
        
        logger.info(f"尝试重连 (第 {self._reconnect_count}/{self.config.reconnect_attempts} 次)")
        
        # 等待重连延迟
        await asyncio.sleep(self.config.reconnect_delay)
        
        # 先清理旧连接
        await self._cleanup_connection()
        
        # 尝试连接
        success = await self.connect()
        
        if success:
            self._reconnect_count = 0
            logger.info("重连成功")
        else:
            logger.warning(f"重连失败，将尝试再次重连")
        
        return success
    
    async def execute_tcl(
        self,
        command: str,
        timeout: float | None = None,
        auto_reconnect: bool = True,
    ) -> TclResponse:
        """
        执行 Tcl 命令
        
        Args:
            command: Tcl 命令字符串
            timeout: 超时时间（秒），None 使用默认值
            auto_reconnect: 超时/断线后是否自动重连
        
        Returns:
            TclResponse 执行结果
        """
        # 生成请求 ID
        request_id = generate_request_id()
        
        # 检查连接状态
        if not self.is_connected:
            # 尝试自动连接
            if auto_reconnect:
                logger.info(f"[{request_id}] 未连接，尝试自动连接...")
                if not await self.connect():
                    return TclResponse(
                        success=False,
                        result="",
                        error="无法连接到 Vivado tcl_server",
                        execution_time=0.0,
                        request_id=request_id,
                    )
            else:
                return TclResponse(
                    success=False,
                    result="",
                    error="未连接到 Vivado tcl_server",
                    execution_time=0.0,
                    request_id=request_id,
                )
        
        # 使用默认超时
        if timeout is None:
            timeout = self.config.timeout
        
        start_time = time.time()
        
        # 记录请求开始
        self._pending_requests[request_id] = {
            "command": command,
            "start_time": start_time,
            "timeout": timeout,
            "status": "pending",
        }
        
        # 使用锁确保一次只执行一个命令
        async with self._lock:
            try:
                # 发送命令
                await self._send_command(command)
                
                # 接收响应
                raw_output = await asyncio.wait_for(
                    self._receive_until_prompt(),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # 更新请求状态
                self._pending_requests[request_id]["status"] = "completed"
                self._pending_requests[request_id]["execution_time"] = execution_time
                
                # 解析响应
                response = self._parse_response(raw_output)
                response.execution_time = execution_time
                response.raw_output = raw_output
                response.request_id = request_id
                
                logger.debug(f"[{request_id}] 命令执行完成，耗时 {execution_time:.3f}秒")
                
                return response
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                error_msg = f"命令执行超时 ({timeout}秒)"
                logger.error(f"[{request_id}] {error_msg}")
                
                # 记录超时信息
                timeout_info = {
                    "request_id": request_id,
                    "command": command,
                    "timeout": timeout,
                    "execution_time": execution_time,
                    "timestamp": time.time(),
                }
                self._timeout_history.append(timeout_info)
                self._pending_requests[request_id]["status"] = "timeout"
                
                # 超时后尝试重连
                reconnect_success = False
                if auto_reconnect:
                    logger.info(f"[{request_id}] 超时后尝试自动重连...")
                    await self._cleanup_connection()
                    self._set_state(ConnectionState.ERROR)
                    reconnect_success = await self.reconnect()
                
                return TclResponse(
                    success=False,
                    result="",
                    error=error_msg,
                    execution_time=execution_time,
                    request_id=request_id,
                    timeout_occurred=True,
                    reconnect_attempted=auto_reconnect,
                    reconnect_success=reconnect_success,
                )
                
            except ConnectionResetError:
                execution_time = time.time() - start_time
                error_msg = "连接被重置，可能 Vivado 已关闭"
                logger.error(f"[{request_id}] {error_msg}")
                
                self._pending_requests[request_id]["status"] = "connection_reset"
                
                # 断线后尝试重连
                reconnect_success = False
                if auto_reconnect:
                    logger.info(f"[{request_id}] 断线后尝试自动重连...")
                    await self._cleanup_connection()
                    self._set_state(ConnectionState.DISCONNECTED)
                    reconnect_success = await self.reconnect()
                
                return TclResponse(
                    success=False,
                    result="",
                    error=error_msg,
                    execution_time=execution_time,
                    request_id=request_id,
                    reconnect_attempted=auto_reconnect,
                    reconnect_success=reconnect_success,
                )
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_msg = f"命令执行异常: {e}"
                logger.exception(f"[{request_id}] {error_msg}")
                
                self._pending_requests[request_id]["status"] = "error"
                
                return TclResponse(
                    success=False,
                    result="",
                    error=error_msg,
                    execution_time=execution_time,
                    request_id=request_id,
                )
    
    async def execute_tcl_batch(
        self,
        commands: list[str],
        timeout: float | None = None,
        per_command_timeout: float | None = None,
        stop_on_error: bool = True,
    ) -> list[TclResponse]:
        """
        批量执行 Tcl 命令
        
        超时语义说明：
        - timeout: 批量命令的总超时时间（秒），从第一个命令开始到最后一个命令完成
          - None 表示使用默认配置 (TimeoutConfig.batch_total)
          - 如果总时间超过此值，剩余命令将被取消并返回超时错误
        - per_command_timeout: 单个命令的超时时间（秒）
          - None 表示使用默认配置 (TcpConfig.timeout)
          - 每个命令的执行时间不能超过此值
        
        Args:
            commands: Tcl 命令列表
            timeout: 总超时时间（秒），None 表示使用默认值
            per_command_timeout: 单命令超时（秒），None 表示使用默认值
            stop_on_error: 遇到错误是否停止
        
        Returns:
            响应列表
        """
        # 使用默认超时配置
        if timeout is None:
            settings = get_settings()
            timeout = settings.timeout_batch_total
        if per_command_timeout is None:
            per_command_timeout = self.config.timeout
        
        results = []
        batch_start_time = time.time()
        
        for i, command in enumerate(commands):
            # 检查剩余时间
            elapsed = time.time() - batch_start_time
            remaining_timeout = timeout - elapsed
            
            if remaining_timeout <= 0:
                # 总超时，记录警告并停止执行
                logger.warning(
                    f"批量执行总超时 ({timeout}s)，已执行 {i}/{len(commands)} 个命令"
                )
                # 为剩余命令添加超时错误结果
                for j in range(i, len(commands)):
                    results.append(TclResponse(
                        success=False,
                        result="",
                        error=f"批量执行总超时: 超过 {timeout} 秒",
                        execution_time=0.0,
                    ))
                break
            
            # 执行单个命令，使用剩余时间和单命令超时的较小值
            cmd_timeout = min(per_command_timeout, remaining_timeout)
            cmd_start_time = time.time()
            
            result = await self.execute_tcl(command, timeout=cmd_timeout, auto_reconnect=False)
            cmd_elapsed = time.time() - cmd_start_time
            
            # 记录命令完成日志
            logger.info(
                f"命令完成 [{i+1}/{len(commands)}]: {command[:50]}{'...' if len(command) > 50 else ''} "
                f"耗时 {cmd_elapsed:.2f}s"
            )
            
            results.append(result)
            
            # 检查是否需要停止
            if not result.success and stop_on_error:
                logger.warning(
                    f"批量执行因错误停止，已执行 {i+1}/{len(commands)} 个命令: {result.error}"
                )
                break
        
        # 记录批量执行总耗时
        total_elapsed = time.time() - batch_start_time
        logger.info(
            f"批量执行完成: {len(results)}/{len(commands)} 个命令，总耗时 {total_elapsed:.2f}s"
        )
        
        return results
    
    async def check_connection(self) -> bool:
        """
        检查连接是否有效
        
        Returns:
            连接是否有效
        """
        if not self.is_connected:
            return False
        
        try:
            # 执行一个简单的 Tcl 命令来检查连接
            response = await self.execute_tcl("puts OK", timeout=5.0)
            return response.success and "OK" in response.result
        except Exception as e:
            logger.debug(f"连接检查失败: {e}")
            return False
    
    async def get_vivado_info(self) -> dict[str, Any]:
        """
        获取 Vivado 信息
        
        Returns:
            Vivado 版本和状态信息
        """
        info = {
            "connected": self.is_connected,
            "state": self._state.value,
            "host": self.config.host,
            "port": self.config.port,
            "connection_time": self.connection_time,
            "last_error": self._last_error,
            "timeout_count": len(self._timeout_history),
            "pending_requests": len(self._pending_requests),
        }
        
        if self.is_connected:
            try:
                # 获取版本信息
                version_response = await self.execute_tcl("version", timeout=10.0, auto_reconnect=False)
                if version_response.success:
                    info["version"] = version_response.result.strip()
                
                # 获取当前工程
                project_response = await self.execute_tcl("current_project", timeout=5.0, auto_reconnect=False)
                if project_response.success:
                    info["current_project"] = project_response.result.strip()
                
            except Exception as e:
                logger.warning(f"获取 Vivado 信息失败: {e}")
        
        return info
    
    def get_timeout_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取超时历史记录
        
        Args:
            limit: 返回的最大记录数
        
        Returns:
            超时历史记录列表
        """
        return self._timeout_history[-limit:]
    
    def get_pending_requests(self) -> dict[str, dict[str, Any]]:
        """
        获取待处理请求
        
        Returns:
            待处理请求字典
        """
        return self._pending_requests.copy()
    
    def clear_timeout_history(self) -> None:
        """清空超时历史记录"""
        self._timeout_history.clear()
        logger.debug("超时历史记录已清空")
    
    def clear_pending_requests(self) -> None:
        """清空待处理请求（仅清理已完成的）"""
        completed = [
            rid for rid, req in self._pending_requests.items()
            if req.get("status") in ("completed", "timeout", "error", "connection_reset")
        ]
        for rid in completed:
            del self._pending_requests[rid]
        logger.debug(f"已清理 {len(completed)} 个已完成的请求")
    
    def set_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """
        设置状态变化回调
        
        Args:
            callback: 状态变化回调函数
        """
        self._on_state_change = callback
    
    def _set_state(self, state: ConnectionState) -> None:
        """
        设置状态并触发回调
        
        Args:
            state: 新的连接状态
        """
        old_state = self._state
        self._state = state
        
        if old_state != state:
            logger.debug(f"连接状态变化: {old_state.value} -> {state.value}")
            if self._on_state_change:
                try:
                    self._on_state_change(state)
                except Exception as e:
                    logger.warning(f"状态回调执行失败: {e}")
    
    async def _send_command(self, command: str) -> None:
        """
        发送命令到服务器
        
        Args:
            command: Tcl 命令字符串
        """
        if self._writer is None:
            raise RuntimeError("未连接到服务器")
        
        # 确保命令以换行符结尾
        if not command.endswith('\n'):
            command = command + '\n'
        
        logger.debug(f"发送命令: {repr(command.strip())}")
        
        self._writer.write(command.encode('utf-8'))
        await self._writer.drain()
    
    async def _receive_until_prompt(self) -> str:
        """
        接收服务器响应直到收到提示符
        
        Returns:
            接收到的完整响应（不包含提示符）
        """
        if self._reader is None:
            raise RuntimeError("未连接到服务器")
        
        output_lines = []
        
        while True:
            try:
                # 读取一行数据
                line = await self._reader.readline()
                
                if not line:
                    # 连接关闭
                    raise ConnectionResetError("服务器关闭了连接")
                
                # 解码行
                line_str = line.decode('utf-8', errors='replace')
                
                # 检查是否为提示符
                if self.PROMPT_PATTERN.match(line_str.strip()):
                    # 收到提示符，结束接收
                    logger.debug(f"收到提示符: {repr(line_str.strip())}")
                    break
                
                # 添加到输出
                output_lines.append(line_str)
                
            except asyncio.IncompleteReadError:
                # 读取不完整，连接可能已关闭
                raise ConnectionResetError("读取数据不完整，连接可能已关闭")
        
        # 合并所有行
        return ''.join(output_lines)
    
    def _parse_response(self, raw: str) -> TclResponse:
        """
        解析 Tcl 响应（遵循 TCP_PROTOCOL.md 规范）
        
        响应格式：
        - 成功: OK: <result>\\n
        - 失败: ERROR: <error_message>\\n
        - 多行: <lines>\\nOK: <summary>\\n 或 <lines>\\nERROR: <error>\\n
        
        Args:
            raw: 原始响应字符串
        
        Returns:
            TclResponse 解析后的响应
        """
        # 提取警告信息
        warnings = []
        for match in self.WARNING_PATTERN.finditer(raw):
            warnings.append(match.group(1).strip())
        
        # 提取错误信息
        error = None
        for pattern in self.ERROR_PATTERNS:
            match = pattern.search(raw)
            if match:
                error = match.group(0).strip()
                break
        
        # 提取 OK 响应（如果存在）
        ok_match = self.OK_PATTERN.search(raw)
        
        # 清理结果（移除 OK/ERROR/WARNING 行）
        result = raw
        
        # 移除 OK 行
        if ok_match:
            result = self.OK_PATTERN.sub('', result)
        
        # 移除 ERROR 行
        if error:
            for pattern in self.ERROR_PATTERNS:
                result = pattern.sub('', result)
        
        # 移除 WARNING 行
        for warning in warnings:
            result = result.replace(f"WARNING: {warning}\n", "")
            result = result.replace(f"WARNING: {warning}", "")
        
        # 清理空白行和多余的空格
        result = result.strip()
        
        # 如果有 OK 响应但没有提取到结果，使用 OK 后的内容
        if ok_match and not result:
            result = ok_match.group(1).strip()
        
        # 判断是否成功（根据是否有 ERROR 判断）
        success = error is None
        
        return TclResponse(
            success=success,
            result=result,
            error=error,
            warnings=warnings,
        )
    
    async def _cleanup_connection(self) -> None:
        """清理连接资源"""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.debug(f"关闭 writer 时出错: {e}")
            finally:
                self._writer = None
        
        self._reader = None
        self._receive_buffer = ""
    
    async def __aenter__(self) -> 'VivadoTcpClient':
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        await self.disconnect()
    
    def __repr__(self) -> str:
        return f"VivadoTcpClient(state={self._state.value}, host={self.config.host}, port={self.config.port})"


class TcpClientManager:
    """
    TCP 客户端管理器
    
    单例模式，管理全局 TCP 连接。
    提供统一的客户端访问接口，支持连接池和自动重连。
    """
    
    _instance: 'TcpClientManager | None' = None
    _client: VivadoTcpClient | None = None
    _config: TcpConfig | None = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_client(cls, config: TcpConfig | None = None) -> VivadoTcpClient:
        """
        获取 TCP 客户端实例
        
        Args:
            config: TCP 连接配置，首次调用时使用，后续调用忽略
        
        Returns:
            VivadoTcpClient 实例
        """
        if cls._client is None:
            # 首次创建客户端
            if config is None:
                # 从 settings 读取配置
                settings = get_settings()
                config = TcpConfig(
                    host=settings.tcp_host,
                    port=settings.tcp_port,
                    timeout=settings.timeout_single_command,
                    reconnect_attempts=settings.reconnect_attempts,
                    reconnect_delay=settings.reconnect_delay,
                )
            cls._config = config
            cls._client = VivadoTcpClient(config)
            logger.debug("创建新的 TCP 客户端实例")
        
        return cls._client
    
    @classmethod
    async def ensure_connected(cls) -> bool:
        """
        确保已连接
        
        Returns:
            是否已连接
        """
        if cls._client is None:
            logger.warning("客户端未初始化，请先调用 get_client()")
            return False
        
        if cls._client.is_connected:
            return True
        
        # 尝试连接
        logger.info("客户端未连接，尝试建立连接...")
        return await cls._client.connect()
    
    @classmethod
    async def disconnect_all(cls) -> None:
        """断开所有连接"""
        if cls._client:
            await cls._client.disconnect()
            cls._client = None
            logger.info("已断开所有 TCP 连接")
    
    @classmethod
    async def reconnect(cls) -> bool:
        """
        重新连接
        
        Returns:
            重连是否成功
        """
        if cls._client is None:
            logger.warning("客户端未初始化，无法重连")
            return False
        
        return await cls._client.reconnect()
    
    @classmethod
    def get_state(cls) -> ConnectionState:
        """
        获取当前连接状态
        
        Returns:
            ConnectionState 枚举值
        """
        if cls._client is None:
            return ConnectionState.DISCONNECTED
        return cls._client.state
    
    @classmethod
    def is_connected(cls) -> bool:
        """
        检查是否已连接
        
        Returns:
            是否已连接
        """
        if cls._client is None:
            return False
        return cls._client.is_connected
    
    @classmethod
    def reset(cls) -> None:
        """重置管理器（主要用于测试）"""
        if cls._client:
            # 注意：这里不调用 disconnect，因为 reset 通常在测试环境使用
            cls._client = None
        cls._config = None
        logger.debug("TCP 客户端管理器已重置")
    
    @classmethod
    def get_timeout_history(cls, limit: int = 10) -> list[dict[str, Any]]:
        """
        获取超时历史记录
        
        Args:
            limit: 返回的最大记录数
        
        Returns:
            超时历史记录列表
        """
        if cls._client is None:
            return []
        return cls._client.get_timeout_history(limit)
    
    @classmethod
    def get_pending_requests(cls) -> dict[str, dict[str, Any]]:
        """
        获取待处理请求
        
        Returns:
            待处理请求字典
        """
        if cls._client is None:
            return {}
        return cls._client.get_pending_requests()
    
    @classmethod
    def clear_timeout_history(cls) -> None:
        """清空超时历史记录"""
        if cls._client:
            cls._client.clear_timeout_history()
    
    @classmethod
    def clear_pending_requests(cls) -> None:
        """清空待处理请求"""
        if cls._client:
            cls._client.clear_pending_requests()


# 便捷函数
async def execute_tcl_command(
    command: str,
    config: TcpConfig | None = None,
    timeout: float | None = None,
    auto_reconnect: bool = True,
) -> TclResponse:
    """
    执行单个 Tcl 命令的便捷函数
    
    Args:
        command: Tcl 命令字符串
        config: TCP 连接配置（可选）
        timeout: 超时时间（可选）
        auto_reconnect: 超时/断线后是否自动重连
    
    Returns:
        TclResponse 执行结果
    """
    client = TcpClientManager.get_client(config)
    
    # 确保已连接
    if not await TcpClientManager.ensure_connected():
        return TclResponse(
            success=False,
            result="",
            error="无法连接到 Vivado tcl_server",
            execution_time=0.0,
        )
    
    # 执行命令
    return await client.execute_tcl(command, timeout=timeout, auto_reconnect=auto_reconnect)


async def execute_tcl_commands(
    commands: list[str],
    config: TcpConfig | None = None,
    timeout: float | None = None,
    per_command_timeout: float | None = None,
    stop_on_error: bool = True,
) -> list[TclResponse]:
    """
    批量执行 Tcl 命令的便捷函数
    
    Args:
        commands: Tcl 命令列表
        config: TCP 连接配置（可选）
        timeout: 总超时时间（秒），None 表示使用默认值
        per_command_timeout: 单命令超时（秒），None 表示使用默认值
        stop_on_error: 遇到错误是否停止
    
    Returns:
        TclResponse 列表
    """
    client = TcpClientManager.get_client(config)
    
    # 确保已连接
    if not await TcpClientManager.ensure_connected():
        return [
            TclResponse(
                success=False,
                result="",
                error="无法连接到 Vivado tcl_server",
                execution_time=0.0,
            )
            for _ in commands
        ]
    
    # 批量执行
    return await client.execute_tcl_batch(
        commands,
        timeout=timeout,
        per_command_timeout=per_command_timeout,
        stop_on_error=stop_on_error,
    )
