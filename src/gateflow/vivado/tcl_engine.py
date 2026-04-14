"""
Vivado Tcl 执行引擎

该模块提供与 AMD Vivado 工具的 Tcl 接口交互能力，
支持通过 subprocess 调用 Vivado 命令行模式执行 Tcl 命令。
"""

import asyncio
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from typing import Optional

from gateflow.config import TimeoutConfig, DEFAULT_TIMEOUT_CONFIG
from gateflow.errors import (
    ErrorCode,
    ErrorInfo,
    Result,
    make_success,
    make_error,
    generate_request_id,
    get_error_suggestion,
)

# 配置日志
logger = logging.getLogger(__name__)


class VivadoVersion(Enum):
    """Vivado 版本枚举"""
    V2019_1 = "2019.1"
    V2019_2 = "2019.2"
    V2020_1 = "2020.1"
    V2020_2 = "2020.2"
    V2021_1 = "2021.1"
    V2021_2 = "2021.2"
    V2022_1 = "2022.1"
    V2022_2 = "2022.2"
    V2023_1 = "2023.1"
    V2023_2 = "2023.2"
    V2024_1 = "2024.1"
    V2024_2 = "2024.2"


@dataclass
class TclResult:
    """Tcl 命令执行结果（兼容旧接口，内部使用统一错误模型）"""
    success: bool  # 执行是否成功
    output: str  # 完整输出内容
    errors: list[str] = field(default_factory=list)  # 错误信息列表
    warnings: list[str] = field(default_factory=list)  # 警告信息列表
    return_value: Optional[str] = None  # Tcl 命令返回值
    execution_time: float = 0.0  # 执行时间（秒）
    exit_code: int = 0  # 进程退出码
    
    def to_result(self, request_id: str | None = None) -> Result:
        """转换为统一的 Result 类型"""
        if self.success:
            return make_success(
                data=self.return_value or self.output,
                warnings=self.warnings if self.warnings else None,
                execution_time=self.execution_time,
                request_id=request_id,
            )
        else:
            # 根据错误类型选择错误码
            if self.exit_code == -1 and any("超时" in err for err in self.errors):
                code = ErrorCode.COMMAND_TIMEOUT
            elif self.exit_code != 0:
                code = ErrorCode.COMMAND_FAILED
            else:
                code = ErrorCode.TCL_RUNTIME_ERROR
            
            return make_error(
                code=code,
                message=self.errors[0] if self.errors else "命令执行失败",
                details={
                    "output": self.output,
                    "all_errors": self.errors,
                    "exit_code": self.exit_code,
                    "return_value": self.return_value,
                },
                suggestion=get_error_suggestion(code),
                request_id=request_id or generate_request_id(),
                execution_time=self.execution_time,
            )


@dataclass
class VivadoInfo:
    """Vivado 安装信息"""
    version: str  # 版本号
    install_path: Path  # 安装路径
    executable: Path  # 可执行文件路径
    tcl_shell: Path  # Tcl shell 路径


class VivadoDetector:
    """Vivado 安装检测器"""
    
    # Windows 默认安装路径
    WINDOWS_DEFAULT_PATHS = [
        Path("C:/Xilinx/Vivado"),
        Path("D:/Xilinx/Vivado"),
        Path("E:/Xilinx/Vivado"),
    ]
    
    @classmethod
    def detect_vivado(cls, config_path: Optional[Path] = None) -> Optional[VivadoInfo]:
        """
        自动检测系统中的 Vivado 安装
        
        检测顺序：
        1. 配置文件中的路径（如果提供）
        2. 环境变量 XILINX_VIVADO
        3. Windows 注册表（仅 Windows）
        4. 默认安装路径
        
        Args:
            config_path: 配置文件中的 Vivado 路径（可选）
        
        Returns:
            VivadoInfo 对象，如果未找到则返回 None
        """
        # 优先检查配置文件中的路径
        if config_path:
            info = cls._validate_vivado_path(config_path)
            if info:
                logger.debug(f"从配置文件检测到 Vivado: {config_path}")
                return info
            else:
                logger.warning(f"配置文件中的 Vivado 路径无效: {config_path}")
        
        # 尝试从环境变量获取
        vivado_path = os.environ.get("XILINX_VIVADO")
        if vivado_path:
            info = cls._validate_vivado_path(Path(vivado_path))
            if info:
                logger.debug(f"从环境变量检测到 Vivado: {vivado_path}")
                return info
        
        # 尝试从注册表获取（Windows）
        if os.name == 'nt':
            info = cls._detect_from_registry()
            if info:
                logger.debug("从注册表检测到 Vivado")
                return info
        
        # 搜索默认路径
        for base_path in cls.WINDOWS_DEFAULT_PATHS:
            if base_path.exists():
                # 查找版本目录
                for version_dir in sorted(base_path.iterdir(), reverse=True):
                    if version_dir.is_dir() and cls._is_version_dir(version_dir):
                        info = cls._validate_vivado_path(version_dir)
                        if info:
                            logger.debug(f"从默认路径检测到 Vivado: {version_dir}")
                            return info
        
        return None
    
    @classmethod
    def _detect_from_registry(cls) -> Optional[VivadoInfo]:
        """
        从 Windows 注册表检测 Vivado 安装
        
        Returns:
            VivadoInfo 对象，如果未找到则返回 None
        """
        try:
            import winreg
            
            # 尝试多个注册表位置
            reg_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Xilinx\Vivado"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Xilinx\Vivado"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Xilinx\Vivado"),
            ]
            
            for hkey, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        # 枚举版本子键
                        idx = 0
                        versions = []
                        while True:
                            try:
                                version_name = winreg.EnumKey(key, idx)
                                versions.append(version_name)
                                idx += 1
                            except OSError:
                                break
                        
                        # 选择最新版本
                        if versions:
                            latest_version = sorted(versions, reverse=True)[0]
                            with winreg.OpenKey(key, latest_version) as version_key:
                                try:
                                    install_path, _ = winreg.QueryValueEx(version_key, "InstallDir")
                                    if install_path:
                                        return cls._validate_vivado_path(Path(install_path))
                                except (FileNotFoundError, OSError):
                                    continue
                except (FileNotFoundError, OSError):
                    continue
                    
        except ImportError:
            logger.warning("无法导入 winreg 模块，跳过注册表检测")
        
        return None
    
    @classmethod
    def _is_version_dir(cls, path: Path) -> bool:
        """检查是否为版本目录"""
        # 版本目录名格式：YYYY.X
        pattern = r'^\d{4}\.\d{1,2}$'
        return bool(re.match(pattern, path.name))
    
    @classmethod
    def _validate_vivado_path(cls, path: Path) -> Optional[VivadoInfo]:
        """
        验证 Vivado 安装路径
        
        Args:
            path: Vivado 安装路径
            
        Returns:
            VivadoInfo 对象，如果无效则返回 None
        """
        # 检查可执行文件
        if os.name == 'nt':
            executable = path / "bin" / "vivado.bat"
            if not executable.exists():
                executable = path / "bin" / "vivado.exe"
        else:
            executable = path / "bin" / "vivado"
        
        if not executable.exists():
            logger.debug(f"Vivado 可执行文件不存在: {executable}")
            return None
        
        # 提取版本号
        version = path.name
        if not cls._is_version_dir(path):
            # 尝试从版本文件读取
            version_file = path / "version.txt"
            if version_file.exists():
                version = version_file.read_text().strip()
            else:
                version = "unknown"
        
        return VivadoInfo(
            version=version,
            install_path=path,
            executable=executable,
            tcl_shell=path / "bin" / ("vivado -mode tcl"),
        )


class TclEngine:
    """
    Vivado Tcl 执行引擎
    
    通过 subprocess 调用 Vivado 的批处理模式执行 Tcl 命令。
    支持同步和异步执行，提供超时控制和输出解析。
    支持会话管理，避免每次命令都启动新的 Vivado 进程。
    """
    
    def __init__(
        self,
        vivado_path: Optional[Path] = None,
        timeout: float = 3600.0,
        log_level: int = logging.INFO,
    ):
        """
        初始化 Tcl 执行引擎
        
        Args:
            vivado_path: Vivado 安装路径，如果为 None 则自动检测
            timeout: 默认超时时间（秒）
            log_level: 日志级别
        """
        self.timeout = timeout
        self.log_level = log_level
        
        # 检测或使用指定的 Vivado 安装
        if vivado_path:
            self.vivado_info = VivadoDetector._validate_vivado_path(vivado_path)
            if not self.vivado_info:
                raise ValueError(f"无效的 Vivado 路径: {vivado_path}")
        else:
            self.vivado_info = VivadoDetector.detect_vivado()
            if not self.vivado_info:
                raise RuntimeError(
                    "未找到 Vivado 安装。请设置 XILINX_VIVADO 环境变量 "
                    "或在初始化时指定 vivado_path 参数"
                )
        
        # 会话管理相关属性
        self._session_active = False
        self._process = None
        self._stdin = None
        self._stdout = None
        self._stderr = None
        self._output_queue: Queue = Queue()
        self._reader_thread: Optional[threading.Thread] = None
        self._session_lock = threading.Lock()
        
        logger.info(f"检测到 Vivado {self.vivado_info.version}: {self.vivado_info.install_path}")
    
    def execute(
        self,
        tcl_commands: str | list[str],
        timeout: Optional[float] = None,
        working_dir: Optional[Path] = None,
    ) -> TclResult:
        """
        同步执行 Tcl 命令
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认值
            working_dir: 工作目录
            
        Returns:
            TclResult 执行结果
        """
        # 标准化命令格式
        if isinstance(tcl_commands, list):
            tcl_script = "\n".join(tcl_commands)
        else:
            tcl_script = tcl_commands
        
        # 使用默认超时
        if timeout is None:
            timeout = self.timeout
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.tcl',
            delete=False,
            encoding='utf-8',
        ) as script_file:
            script_file.write(tcl_script)
            script_path = Path(script_file.name)
        
        try:
            # 执行命令
            start_time = time.time()
            
            cmd = [
                str(self.vivado_info.executable),
                "-mode", "batch",
                "-source", str(script_path),
                "-nojournal",  # 不生成 journal 文件
                "-nolog",  # 不生成 log 文件
            ]
            
            logger.debug(f"执行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                encoding='utf-8',
                errors='replace',
            )
            
            execution_time = time.time() - start_time
            
            # 解析输出
            return self._parse_output(
                output=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"Tcl 命令执行超时 ({timeout}秒)")
            return TclResult(
                success=False,
                output="",
                errors=[f"执行超时: 超过 {timeout} 秒"],
                execution_time=timeout,
                exit_code=-1,
            )
        except Exception as e:
            logger.exception("Tcl 命令执行失败")
            return TclResult(
                success=False,
                output="",
                errors=[f"执行异常: {str(e)}"],
                execution_time=0.0,
                exit_code=-1,
            )
        finally:
            # 清理临时文件
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass
    
    async def execute_async(
        self,
        tcl_commands: str | list[str],
        timeout: Optional[float] = None,
        working_dir: Optional[Path] = None,
    ) -> TclResult:
        """
        异步执行 Tcl 命令
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认值
            working_dir: 工作目录
            
        Returns:
            TclResult 执行结果
        """
        # 标准化命令格式
        if isinstance(tcl_commands, list):
            tcl_script = "\n".join(tcl_commands)
        else:
            tcl_script = tcl_commands
        
        # 使用默认超时
        if timeout is None:
            timeout = self.timeout
        
        # 创建临时脚本文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.tcl',
            delete=False,
            encoding='utf-8',
        ) as script_file:
            script_file.write(tcl_script)
            script_path = Path(script_file.name)
        
        try:
            start_time = time.time()
            
            cmd = [
                str(self.vivado_info.executable),
                "-mode", "batch",
                "-source", str(script_path),
                "-nojournal",
                "-nolog",
            ]
            
            logger.debug(f"异步执行命令: {' '.join(cmd)}")
            
            # 使用 asyncio 创建子进程
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
            )
            
            try:
                # 等待进程完成，带超时
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                execution_time = time.time() - start_time
                
                # 解码输出
                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')
                
                return self._parse_output(
                    output=stdout_str,
                    stderr=stderr_str,
                    exit_code=process.returncode or 0,
                    execution_time=execution_time,
                )
                
            except asyncio.TimeoutError:
                # 超时时终止进程
                try:
                    process.kill()
                    await process.wait()
                except ProcessLookupError:
                    pass
                
                logger.error(f"异步 Tcl 命令执行超时 ({timeout}秒)")
                return TclResult(
                    success=False,
                    output="",
                    errors=[f"执行超时: 超过 {timeout} 秒"],
                    execution_time=timeout,
                    exit_code=-1,
                )
                
        except Exception as e:
            logger.exception("异步 Tcl 命令执行失败")
            return TclResult(
                success=False,
                output="",
                errors=[f"执行异常: {str(e)}"],
                execution_time=0.0,
                exit_code=-1,
            )
        finally:
            # 清理临时文件
            try:
                script_path.unlink(missing_ok=True)
            except Exception:
                pass
    
    def execute_script(
        self,
        script_path: Path,
        timeout: Optional[float] = None,
        working_dir: Optional[Path] = None,
    ) -> TclResult:
        """
        执行 Tcl 脚本文件
        
        Args:
            script_path: Tcl 脚本文件路径
            timeout: 超时时间（秒）
            working_dir: 工作目录
            
        Returns:
            TclResult 执行结果
        """
        if not script_path.exists():
            return TclResult(
                success=False,
                output="",
                errors=[f"脚本文件不存在: {script_path}"],
                execution_time=0.0,
                exit_code=-1,
            )
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            start_time = time.time()
            
            cmd = [
                str(self.vivado_info.executable),
                "-mode", "batch",
                "-source", str(script_path),
                "-nojournal",
                "-nolog",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                encoding='utf-8',
                errors='replace',
            )
            
            execution_time = time.time() - start_time
            
            return self._parse_output(
                output=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=execution_time,
            )
            
        except subprocess.TimeoutExpired:
            return TclResult(
                success=False,
                output="",
                errors=[f"执行超时: 超过 {timeout} 秒"],
                execution_time=timeout,
                exit_code=-1,
            )
        except Exception as e:
            return TclResult(
                success=False,
                output="",
                errors=[f"执行异常: {str(e)}"],
                execution_time=0.0,
                exit_code=-1,
            )
    
    def _parse_output(
        self,
        output: str,
        stderr: str,
        exit_code: int,
        execution_time: float,
    ) -> TclResult:
        """
        解析 Vivado 输出
        
        Args:
            output: 标准输出
            stderr: 标准错误
            exit_code: 退出码
            execution_time: 执行时间
            
        Returns:
            TclResult 解析后的结果
        """
        # 合并输出
        full_output = output + "\n" + stderr if stderr else output
        
        # 提取错误信息
        errors = []
        error_patterns = [
            r'ERROR:\s*\[(.*?)\]\s*(.+?)(?=\n|$)',
            r'ERROR:\s*(.+?)(?=\n|$)',
        ]
        for pattern in error_patterns:
            matches = re.findall(pattern, full_output, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    errors.append(f"[{match[0]}] {match[1]}")
                else:
                    errors.append(match)
        
        # 提取警告信息
        warnings = []
        warning_patterns = [
            r'WARNING:\s*\[(.*?)\]\s*(.+?)(?=\n|$)',
            r'WARNING:\s*(.+?)(?=\n|$)',
        ]
        for pattern in warning_patterns:
            matches = re.findall(pattern, full_output, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    warnings.append(f"[{match[0]}] {match[1]}")
                else:
                    warnings.append(match)
        
        # 提取信息
        info_messages = re.findall(r'INFO:\s*(.+?)(?=\n|$)', full_output, re.MULTILINE)
        
        # 提取返回值（如果有的话）
        return_value = None
        return_match = re.search(r'# Return value:\s*(.+?)(?=\n|$)', full_output)
        if return_match:
            return_value = return_match.group(1).strip()
        
        # 判断是否成功
        # Vivado 退出码为 0 且没有 ERROR 级别的消息
        success = exit_code == 0 and len(errors) == 0
        
        return TclResult(
            success=success,
            output=full_output,
            errors=errors,
            warnings=warnings,
            return_value=return_value,
            execution_time=execution_time,
            exit_code=exit_code,
        )
    
    def get_version(self) -> str:
        """获取 Vivado 版本"""
        return self.vivado_info.version
    
    def get_install_path(self) -> Path:
        """获取 Vivado 安装路径"""
        return self.vivado_info.install_path
    
    @property
    def is_session_active(self) -> bool:
        """
        检查会话是否处于活动状态
        
        Returns:
            会话是否活动
        """
        return self._session_active and self._process is not None and self._process.poll() is None
    
    def execute_in_session(
        self,
        tcl_commands: str | list[str],
        timeout: Optional[float] = None,
        auto_start: bool = True,
    ) -> TclResult:
        """
        在会话中执行 Tcl 命令（同步版本）
        
        如果会话未启动，会自动启动会话（除非 auto_start=False）。
        这是推荐的使用方式，可以保持 Vivado 项目状态。
        
        超时语义说明：
        - timeout: 单个命令（或命令组）的执行超时时间
          - None 表示使用默认配置 (TimeoutConfig.single_command)
          - 如果传入命令列表，它们将作为一个整体执行，共享此超时时间
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认配置
            auto_start: 如果会话未启动，是否自动启动
        
        Returns:
            TclResult 执行结果
        
        Example:
            >>> engine = TclEngine()
            >>> # 第一次调用会自动启动会话
            >>> result = engine.execute_in_session("create_project my_project ./my_project")
            >>> # 后续调用复用同一个会话，项目状态保持
            >>> result = engine.execute_in_session("add_files {design.v}")
            >>> result = engine.execute_in_session("synth_design -top my_top")
            >>> # 完成后关闭会话
            >>> engine.stop_session()
        """
        if not self._session_active:
            if not auto_start:
                return TclResult(
                    success=False,
                    output="",
                    errors=["会话未启动且 auto_start=False"],
                    execution_time=0.0,
                    exit_code=-1,
                )
            if not self.start_session():
                return TclResult(
                    success=False,
                    output="",
                    errors=["无法启动 Vivado Tcl 会话"],
                    execution_time=0.0,
                    exit_code=-1,
                )
        
        return self.execute_batch(tcl_commands, timeout)
    
    async def execute_in_session_async(
        self,
        tcl_commands: str | list[str],
        timeout: Optional[float] = None,
        auto_start: bool = True,
    ) -> TclResult:
        """
        在会话中执行 Tcl 命令（异步版本）
        
        如果会话未启动，会自动启动会话（除非 auto_start=False）。
        这是推荐的使用方式，可以保持 Vivado 项目状态。
        
        超时语义说明：
        - timeout: 单个命令（或命令组）的执行超时时间
          - None 表示使用默认配置 (TimeoutConfig.single_command)
          - 如果传入命令列表，它们将作为一个整体执行，共享此超时时间
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认配置
            auto_start: 如果会话未启动，是否自动启动
        
        Returns:
            TclResult 执行结果
        """
        if not self._session_active:
            if not auto_start:
                return TclResult(
                    success=False,
                    output="",
                    errors=["会话未启动且 auto_start=False"],
                    execution_time=0.0,
                    exit_code=-1,
                )
            # 在异步环境中启动会话
            loop = asyncio.get_event_loop()
            if not await loop.run_in_executor(None, self.start_session):
                return TclResult(
                    success=False,
                    output="",
                    errors=["无法启动 Vivado Tcl 会话"],
                    execution_time=0.0,
                    exit_code=-1,
                )
        
        return await self.execute_batch_async(tcl_commands, timeout)
    
    def start_session(self, working_dir: Optional[Path] = None) -> bool:
        """
        启动 Vivado Tcl 会话
        
        Args:
            working_dir: 工作目录
        
        Returns:
            是否成功启动会话
        """
        with self._session_lock:
            if self._session_active:
                logger.debug("会话已处于活动状态")
                return True
            
            try:
                # 启动 Vivado Tcl 模式进程
                cmd = [
                    str(self.vivado_info.executable),
                    "-mode", "tcl",
                    "-nojournal",
                    "-nolog",
                ]
                
                logger.debug(f"启动 Vivado Tcl 会话: {' '.join(cmd)}")
                
                # 创建子进程，重定向标准输入输出
                self._process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=working_dir,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                )
                
                self._stdin = self._process.stdin
                self._stdout = self._process.stdout
                self._stderr = self._process.stderr
                
                # 启动后台线程读取输出
                self._output_queue = Queue()
                self._reader_thread = threading.Thread(
                    target=self._reader_thread_func,
                    daemon=True
                )
                self._reader_thread.start()
                
                # 读取初始输出，等待 Vivado 启动完成
                if not self._wait_for_prompt(timeout=60):
                    logger.error("等待 Vivado 启动超时")
                    self._cleanup_session()
                    return False
                
                self._session_active = True
                logger.info("Vivado Tcl 会话已启动")
                return True
                
            except Exception as e:
                logger.exception("启动 Vivado Tcl 会话失败")
                self._cleanup_session()
                return False
    
    def stop_session(self) -> bool:
        """
        停止 Vivado Tcl 会话
        
        Returns:
            是否成功停止会话
        """
        with self._session_lock:
            if not self._session_active:
                logger.debug("会话未活动")
                return True
            
            try:
                # 发送退出命令
                if self._stdin:
                    try:
                        self._stdin.write("exit\n")
                        self._stdin.flush()
                    except Exception:
                        pass
                
                # 等待进程结束
                if self._process:
                    try:
                        self._process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        pass
                
                self._cleanup_session()
                logger.info("Vivado Tcl 会话已停止")
                return True
                
            except Exception as e:
                logger.exception("停止 Vivado Tcl 会话失败")
                self._cleanup_session()
                return False
    
    def _cleanup_session(self):
        """
        清理会话资源
        """
        self._session_active = False
        
        # 等待读取线程结束
        if self._reader_thread and self._reader_thread.is_alive():
            # 给线程一些时间来结束
            self._reader_thread.join(timeout=2)
        
        self._reader_thread = None
        
        # 清空队列
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except Empty:
                break
        
        # 关闭文件描述符
        if self._stdin:
            try:
                self._stdin.close()
            except Exception:
                pass
        
        if self._stdout:
            try:
                self._stdout.close()
            except Exception:
                pass
        
        if self._stderr:
            try:
                self._stderr.close()
            except Exception:
                pass
        
        # 终止进程
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=5)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        
        self._process = None
        self._stdin = None
        self._stdout = None
        self._stderr = None
    
    def _reader_thread_func(self):
        """
        后台线程函数，持续读取 Vivado 输出并放入队列
        """
        while True:
            try:
                if not self._stdout:
                    break
                # 逐行读取输出
                line = self._stdout.readline()
                if not line:
                    # EOF
                    break
                self._output_queue.put(('stdout', line))
            except Exception as e:
                if self._session_active:
                    logger.debug(f"读取线程异常: {e}")
                break
        
        # 标记结束
        self._output_queue.put(('eof', ''))
    
    def _wait_for_prompt(self, timeout: float = 60.0) -> bool:
        """
        等待 Vivado 提示符出现
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否成功等到提示符
        """
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < timeout:
            try:
                source, line = self._output_queue.get(timeout=0.1)
                if source == 'eof':
                    logger.error("Vivado 进程意外结束")
                    return False
                output_lines.append(line)
                # 检查是否出现提示符 (Vivado% 或 Vivado>)
                if 'Vivado%' in line or 'Vivado>' in line:
                    startup_output = ''.join(output_lines)
                    logger.debug(f"Vivado 启动完成，输出: {startup_output[:500]}...")
                    return True
            except Empty:
                continue
        
        return False
    
    def execute_batch(self, tcl_commands: str | list[str], timeout: Optional[float] = None) -> TclResult:
        """
        在会话中执行批处理 Tcl 命令
        
        注意：此方法将多个命令作为一个整体执行，共享一个超时时间。
        如果需要逐个执行命令并分别控制超时，请使用 execute_in_session 逐个调用。
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认配置 (TimeoutConfig.single_command)
        
        Returns:
            TclResult 执行结果
        """
        if not self._session_active:
            # 如果会话未启动，启动会话
            if not self.start_session():
                return TclResult(
                    success=False,
                    output="",
                    errors=["无法启动 Vivado Tcl 会话"],
                    execution_time=0.0,
                    exit_code=-1,
                )
        
        # 标准化命令格式
        if isinstance(tcl_commands, list):
            tcl_script = "\n".join(tcl_commands)
        else:
            tcl_script = tcl_commands
        
        # 使用默认超时
        if timeout is None:
            timeout = DEFAULT_TIMEOUT_CONFIG.single_command
        
        start_time = time.time()
        
        try:
            # 发送命令到 Vivado
            if not self._stdin or not self._stdout:
                return TclResult(
                    success=False,
                    output="",
                    errors=["会话连接已断开"],
                    execution_time=0.0,
                    exit_code=-1,
                )
            
            # 发送命令，确保以换行符结束
            self._stdin.write(tcl_script + "\n")
            self._stdin.flush()
            
            # 读取输出直到提示符
            output = self._read_output_until_prompt(timeout)
            
            execution_time = time.time() - start_time
            
            # 记录命令完成日志
            cmd_preview = tcl_script[:50] + ('...' if len(tcl_script) > 50 else '')
            logger.info(f"批处理命令完成: {cmd_preview} 耗时 {execution_time:.2f}s")
            
            # 解析输出
            return self._parse_output(
                output=output,
                stderr="",  # 会话模式下 stderr 可能不会实时输出
                exit_code=0,  # 会话模式下无法直接获取退出码
                execution_time=execution_time,
            )
            
        except Exception as e:
            logger.exception("执行批处理命令失败")
            return TclResult(
                success=False,
                output="",
                errors=[f"执行异常: {str(e)}"],
                execution_time=0.0,
                exit_code=-1,
            )
    
    async def execute_batch_async(self, tcl_commands: str | list[str], timeout: Optional[float] = None) -> TclResult:
        """
        异步在会话中执行批处理 Tcl 命令
        
        注意：此方法将多个命令作为一个整体执行，共享一个超时时间。
        如果需要逐个执行命令并分别控制超时，请使用 execute_in_session_async 逐个调用。
        
        Args:
            tcl_commands: Tcl 命令字符串或命令列表
            timeout: 超时时间（秒），None 使用默认配置 (TimeoutConfig.single_command)
        
        Returns:
            TclResult 执行结果
        """
        # 确保会话已启动
        if not self._session_active:
            # 在异步环境中启动会话
            loop = asyncio.get_event_loop()
            if not await loop.run_in_executor(None, self.start_session):
                return TclResult(
                    success=False,
                    output="",
                    errors=["无法启动 Vivado Tcl 会话"],
                    execution_time=0.0,
                    exit_code=-1,
                )
        
        # 标准化命令格式
        if isinstance(tcl_commands, list):
            tcl_script = "\n".join(tcl_commands)
        else:
            tcl_script = tcl_commands
        
        # 使用默认超时
        if timeout is None:
            timeout = DEFAULT_TIMEOUT_CONFIG.single_command
        
        start_time = time.time()
        
        try:
            # 发送命令到 Vivado
            if not self._stdin or not self._stdout:
                return TclResult(
                    success=False,
                    output="",
                    errors=["会话连接已断开"],
                    execution_time=0.0,
                    exit_code=-1,
                )
            
            # 发送命令，确保以换行符结束
            self._stdin.write(tcl_script + "\n")
            self._stdin.flush()
            
            # 异步读取输出直到提示符
            loop = asyncio.get_event_loop()
            output = await loop.run_in_executor(None, self._read_output_until_prompt, timeout)
            
            execution_time = time.time() - start_time
            
            # 记录命令完成日志
            cmd_preview = tcl_script[:50] + ('...' if len(tcl_script) > 50 else '')
            logger.info(f"批处理命令完成: {cmd_preview} 耗时 {execution_time:.2f}s")
            
            # 解析输出
            return self._parse_output(
                output=output,
                stderr="",  # 会话模式下 stderr 可能不会实时输出
                exit_code=0,  # 会话模式下无法直接获取退出码
                execution_time=execution_time,
            )
            
        except Exception as e:
            logger.exception("异步执行批处理命令失败")
            return TclResult(
                success=False,
                output="",
                errors=[f"执行异常: {str(e)}"],
                execution_time=0.0,
                exit_code=-1,
            )
    
    def _read_output_until_prompt(self, timeout: float) -> str:
        """
        读取输出直到出现 Vivado 提示符
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            读取的输出
        """
        start_time = time.time()
        output_lines = []
        
        while time.time() - start_time < timeout:
            try:
                source, line = self._output_queue.get(timeout=0.1)
                if source == 'eof':
                    logger.warning("Vivado 进程在读取输出时意外结束")
                    break
                output_lines.append(line)
                # 检查是否出现提示符 (Vivado% 或 Vivado>)
                if 'Vivado%' in line or 'Vivado>' in line:
                    break
            except Empty:
                continue
        
        result = ''.join(output_lines)
        # 移除提示符
        result = re.sub(r'Vivado[%>]\s*$', '', result)
        
        return result
    
    def __del__(self):
        """
        析构函数，确保会话被关闭
        """
        try:
            # 检查会话管理属性是否存在
            if hasattr(self, '_session_active') and self._session_active:
                self.stop_session()
        except Exception:
            # 忽略析构函数中的异常
            pass
    
    def __repr__(self) -> str:
        session_status = "active" if hasattr(self, '_session_active') and self._session_active else "inactive"
        return f"TclEngine(vivado={self.vivado_info.version}, path={self.vivado_info.install_path}, session={session_status})"
