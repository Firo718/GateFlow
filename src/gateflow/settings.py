"""
GateFlow 统一配置模块

使用 pydantic-settings 管理所有配置，支持多种配置来源：
- 环境变量（最高优先级，前缀 GATEFLOW_）
- .env 文件
- 配置文件 ~/.gateflow/config.json
- CLI 参数
- 默认值

配置优先级（从高到低）：
1. CLI 参数（构造函数参数）
2. 环境变量
3. .env 文件
4. 配置文件 config.json
5. 默认值

使用示例：
    >>> from gateflow.settings import get_settings
    >>> settings = get_settings()
    >>> print(settings.tcp_port)
    9999
    
    # 通过环境变量覆盖
    # export GATEFLOW_TCP_PORT=8888
    >>> settings = get_settings(reload=True)  # 需要重新加载
    >>> print(settings.tcp_port)
    8888
"""

import json
import logging
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = Path.home() / ".gateflow"
CONFIG_FILE = CONFIG_DIR / "config.json"


# ============================================================================
# 安全策略配置
# ============================================================================


@dataclass
class SecurityPolicy:
    """
    安全策略配置。

    定义文件沙箱、危险操作、Tcl 执行等安全相关的配置。

    Attributes:
        sandbox_enabled: 是否启用沙箱机制
        allowed_roots: 允许访问的根目录列表
        allow_dangerous_operations: 是否允许危险操作（如删除文件）
        dangerous_operations_require_confirmation: 危险操作是否需要确认
        tcl_policy: Tcl 执行策略级别 (safe, normal, unsafe)
        tcl_dangerous_patterns: 额外的 Tcl 危险模式列表
        max_file_size: 最大文件大小限制（字节）
        allowed_file_extensions: 允许的文件扩展名列表（空列表表示不限制）

    Example:
        ```python
        # 使用默认安全策略
        policy = SecurityPolicy()

        # 自定义安全策略
        policy = SecurityPolicy(
            sandbox_enabled=True,
            allowed_roots=["/home/user/projects"],
            tcl_policy="normal",
        )
        ```
    """

    # 沙箱配置
    sandbox_enabled: bool = True
    allowed_roots: list[str] = field(default_factory=lambda: ["~/.gateflow/workspaces"])

    # 危险操作配置
    allow_dangerous_operations: bool = False
    dangerous_operations_require_confirmation: bool = True

    # Tcl 执行策略
    tcl_policy: str = "normal"  # safe, normal, unsafe
    tcl_dangerous_patterns: list[str] = field(default_factory=list)

    # 文件操作限制
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_extensions: list[str] = field(default_factory=list)

    def __post_init__(self):
        """初始化后处理"""
        # 展开路径中的 ~ 符号
        self.allowed_roots = [
            str(Path(root).expanduser().resolve())
            for root in self.allowed_roots
        ]

        # 验证 tcl_policy
        valid_policies = ("safe", "normal", "unsafe")
        if self.tcl_policy not in valid_policies:
            raise ValueError(
                f"tcl_policy 必须是 {valid_policies} 之一，当前值: {self.tcl_policy}"
            )

    @classmethod
    def from_env(cls) -> "SecurityPolicy":
        """
        从环境变量创建安全策略。

        环境变量:
            GATEFLOW_SANDBOX_ENABLED: 是否启用沙箱 (true/false)
            GATEFLOW_WORKSPACE_ROOTS: 允许的根目录列表（路径分隔符分隔）
            GATEFLOW_ALLOW_DANGEROUS: 是否允许危险操作 (true/false)
            GATEFLOW_TCL_POLICY: Tcl 执行策略 (safe/normal/unsafe)
            GATEFLOW_MAX_FILE_SIZE: 最大文件大小（MB）

        Returns:
            SecurityPolicy 实例
        """
        # 读取沙箱启用状态
        sandbox_enabled = os.getenv("GATEFLOW_SANDBOX_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        # 读取根目录配置
        env_roots = os.getenv("GATEFLOW_WORKSPACE_ROOTS", "")
        if env_roots:
            separator = ";" if os.name == "nt" else ":"
            allowed_roots = [r.strip() for r in env_roots.split(separator) if r.strip()]
        else:
            allowed_roots = ["~/.gateflow/workspaces"]

        # 读取危险操作配置
        allow_dangerous = os.getenv("GATEFLOW_ALLOW_DANGEROUS", "false").lower() in (
            "true",
            "1",
            "yes",
        )

        # 读取 Tcl 策略
        tcl_policy = os.getenv("GATEFLOW_TCL_POLICY", "normal").lower()

        # 读取最大文件大小
        max_file_size_mb = int(os.getenv("GATEFLOW_MAX_FILE_SIZE", "100"))
        max_file_size = max_file_size_mb * 1024 * 1024

        return cls(
            sandbox_enabled=sandbox_enabled,
            allowed_roots=allowed_roots,
            allow_dangerous_operations=allow_dangerous,
            tcl_policy=tcl_policy,
            max_file_size=max_file_size,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "sandbox_enabled": self.sandbox_enabled,
            "allowed_roots": self.allowed_roots,
            "allow_dangerous_operations": self.allow_dangerous_operations,
            "dangerous_operations_require_confirmation": self.dangerous_operations_require_confirmation,
            "tcl_policy": self.tcl_policy,
            "tcl_dangerous_patterns": self.tcl_dangerous_patterns,
            "max_file_size": self.max_file_size,
            "allowed_file_extensions": self.allowed_file_extensions,
        }


def validate_security_policy(policy: SecurityPolicy) -> list[str]:
    """
    验证安全策略配置，返回警告列表。

    检查安全策略配置是否存在潜在风险，并返回警告信息。

    Args:
        policy: 安全策略配置实例

    Returns:
        警告消息列表

    Example:
        ```python
        policy = SecurityPolicy(sandbox_enabled=False)
        warnings = validate_security_policy(policy)
        for warning in warnings:
            print(f"警告: {warning}")
        ```
    """
    warnings_list = []

    # 检查沙箱是否禁用
    if not policy.sandbox_enabled:
        warnings_list.append(
            "沙箱已禁用，文件操作无限制，存在安全风险。"
            "建议启用沙箱以限制文件访问范围。"
        )

    # 检查危险操作是否允许
    if policy.allow_dangerous_operations:
        warnings_list.append(
            "危险操作已启用，允许删除和覆盖文件等高风险操作。"
            "请确保在受信任的环境中使用。"
        )

    # 检查 Tcl 策略
    if policy.tcl_policy == "unsafe":
        warnings_list.append(
            "Tcl 策略设为 unsafe，可执行任意命令，存在安全风险。"
            "建议使用 normal 或 safe 策略。"
        )

    # 检查根目录是否为空
    if policy.sandbox_enabled and not policy.allowed_roots:
        warnings_list.append(
            "沙箱已启用但未配置允许的根目录，将无法进行任何文件操作。"
        )

    # 检查最大文件大小
    if policy.max_file_size > 1024 * 1024 * 1024:  # 1GB
        warnings_list.append(
            f"最大文件大小设置为 {policy.max_file_size / (1024 * 1024):.0f}MB，"
            "可能导致内存问题。建议不超过 1GB。"
        )

    # 记录警告
    for warning in warnings_list:
        logger.warning(f"安全策略警告: {warning}")

    return warnings_list


def _load_config_file() -> dict[str, Any]:
    """
    加载配置文件 ~/.gateflow/config.json
    
    Returns:
        配置字典
    """
    if not CONFIG_FILE.exists():
        return {}
    
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"加载配置文件失败: {e}")
        return {}


def _get_env_separator() -> str:
    """获取环境变量路径分隔符"""
    return ";" if os.name == "nt" else ":"


class ConfigFileSource(PydanticBaseSettingsSource):
    """配置文件数据源"""
    
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        self._config_data = _load_config_file()
    
    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:
        """获取字段值"""
        if field_name in self._config_data:
            return self._config_data[field_name], field_name, False
        return None, field_name, False
    
    def __call__(self) -> dict[str, Any]:
        """返回所有配置"""
        return self._config_data


class GateFlowSettings(BaseSettings):
    """
    GateFlow 统一配置类
    
    所有配置项都支持通过以下方式设置：
    1. CLI 参数（构造函数参数，最高优先级）
    2. 环境变量（前缀 GATEFLOW_）
    3. .env 文件
    4. 配置文件 ~/.gateflow/config.json
    5. 默认值
    
    Attributes:
        vivado_path: Vivado 安装路径
        tcp_host: TCP 服务器主机名
        tcp_port: TCP 服务器端口
        timeout_single_command: 单个命令执行的超时时间（秒）
        timeout_batch_total: 批量命令的总超时时间（秒）
        timeout_connect: 连接超时时间（秒）
        timeout_idle: 空闲超时时间（秒）
        workspace_roots: 允许访问的工作空间根目录列表
        allow_dangerous_operations: 是否允许危险操作（如删除文件）
        tcl_policy: Tcl 命令策略 (safe, normal, unsafe)
        log_level: 日志级别
    """
    
    model_config = SettingsConfigDict(
        env_prefix="GATEFLOW_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # 支持嵌套配置，如 GATEFLOW_TIMEOUT__SINGLE_COMMAND
        extra="ignore",  # 忽略额外的环境变量
    )
    
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """
        自定义配置源优先级
        
        优先级顺序（从高到低）：
        1. init_settings - 构造函数参数（CLI 参数）
        2. env_settings - 环境变量
        3. dotenv_settings - .env 文件
        4. ConfigFileSource - 配置文件 config.json
        5. file_secret_settings - 文件密钥（暂不使用）
        
        Returns:
            配置源元组
        """
        return (
            init_settings,        # 最高优先级：CLI 参数
            env_settings,         # 环境变量
            dotenv_settings,      # .env 文件
            ConfigFileSource(settings_cls),  # 配置文件
        )
    
    # Vivado 配置
    vivado_path: str | None = Field(
        default=None,
        description="Vivado 安装路径",
    )
    
    # TCP 配置
    tcp_host: str = Field(
        default="localhost",
        description="TCP 服务器主机名",
    )
    tcp_port: int = Field(
        default=9999,
        ge=1,
        le=65535,
        description="TCP 服务器端口",
    )
    
    # 超时配置
    timeout_single_command: float = Field(
        default=60.0,
        gt=0,
        description="单个命令执行的超时时间（秒）",
    )
    timeout_batch_total: float = Field(
        default=3600.0,
        gt=0,
        description="批量命令的总超时时间（秒）",
    )
    timeout_connect: float = Field(
        default=10.0,
        gt=0,
        description="连接超时时间（秒）",
    )
    timeout_idle: float = Field(
        default=300.0,
        gt=0,
        description="空闲超时时间（秒）",
    )
    
    # 安全配置
    workspace_roots: list[str] = Field(
        default_factory=list,
        description="允许访问的工作空间根目录列表",
    )
    allow_dangerous_operations: bool = Field(
        default=False,
        description="是否允许危险操作（如删除文件）",
    )
    tcl_policy: str = Field(
        default="normal",
        description="Tcl 命令策略 (safe, normal, unsafe)",
    )
    
    # 日志配置
    log_level: str = Field(
        default="INFO",
        description="日志级别",
    )

    # 执行上下文预留
    execution_context_kind: str = Field(
        default="project",
        description="执行上下文类型 (project, non_project, embedded)",
    )
    execution_workspace: str | None = Field(
        default=None,
        description="执行上下文工作目录（为后续 Non-Project / Embedded 预留）",
    )
    
    # TCP 重连配置
    reconnect_attempts: int = Field(
        default=5,
        ge=0,
        description="TCP 重连尝试次数",
    )
    reconnect_delay: float = Field(
        default=2.0,
        ge=0,
        description="TCP 重连延迟（秒）",
    )

    # GUI 会话配置
    gui_tcp_port: int = Field(
        default=10099,
        ge=1,
        le=65535,
        description="GUI 会话模式默认 TCP 端口",
    )
    gui_enabled: bool = Field(
        default=False,
        description="是否默认启用 GUI 会话模式",
    )

    # 工具开关配置
    enabled_tools: list[str] | None = Field(
        default=None,
        description="启用的工具列表（None 表示全部启用）",
    )
    disabled_tools: list[str] = Field(
        default_factory=list,
        description="禁用的工具列表",
    )
    disable_dangerous_tools: bool = Field(
        default=False,
        description="是否禁用所有危险工具",
    )
    
    @field_validator("tcl_policy")
    @classmethod
    def validate_tcl_policy(cls, v: str) -> str:
        """验证 Tcl 策略"""
        valid_policies = ("safe", "normal", "unsafe")
        if v not in valid_policies:
            raise ValueError(f"tcl_policy 必须是 {valid_policies} 之一，当前值: {v}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level 必须是 {valid_levels} 之一，当前值: {v}")
        return v_upper
    
    @field_validator("workspace_roots", mode="before")
    @classmethod
    def parse_workspace_roots(cls, v: Any) -> list[str]:
        """
        解析工作空间根目录
        
        支持多种格式：
        - 列表: ["/path1", "/path2"]
        - 字符串（路径分隔符分隔）: "/path1:/path2" (Unix) 或 "/path1;/path2" (Windows)
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # 使用路径分隔符分割
            separator = _get_env_separator()
            return [p.strip() for p in v.split(separator) if p.strip()]
        return []
    
    def to_config_file(self) -> None:
        """
        保存配置到文件 ~/.gateflow/config.json
        
        注意：只保存非敏感配置，环境变量优先级更高
        """
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 读取现有配置
        existing_config = _load_config_file()
        
        # 更新配置
        config_data = {
            "vivado_path": self.vivado_path,
            "tcp_host": self.tcp_host,
            "tcp_port": self.tcp_port,
            "timeout_single_command": self.timeout_single_command,
            "timeout_batch_total": self.timeout_batch_total,
            "timeout_connect": self.timeout_connect,
            "timeout_idle": self.timeout_idle,
            "workspace_roots": self.workspace_roots,
            "allow_dangerous_operations": self.allow_dangerous_operations,
            "tcl_policy": self.tcl_policy,
            "log_level": self.log_level,
            "reconnect_attempts": self.reconnect_attempts,
            "reconnect_delay": self.reconnect_delay,
            "enabled_tools": self.enabled_tools,
            "disabled_tools": self.disabled_tools,
            "disable_dangerous_tools": self.disable_dangerous_tools,
        }
        
        # 合并现有配置（保留其他字段）
        merged_config = {**existing_config, **config_data}
        
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(merged_config, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
    
    def get_timeout_config(self) -> "TimeoutConfig":
        """
        获取超时配置（兼容旧代码）
        
        Returns:
            TimeoutConfig 实例
        """
        return TimeoutConfig(
            single_command=self.timeout_single_command,
            batch_total=self.timeout_batch_total,
            connect=self.timeout_connect,
            idle=self.timeout_idle,
        )
    
    def get_tcp_config(self) -> "TcpConfig":
        """
        获取 TCP 配置（兼容旧代码）
        
        Returns:
            TcpConfig 实例
        """
        return TcpConfig(
            host=self.tcp_host,
            port=self.tcp_port,
            timeout=self.timeout_single_command,
            reconnect_attempts=self.reconnect_attempts,
            reconnect_delay=self.reconnect_delay,
        )
    
    def get_workspace_roots(self) -> list[Path]:
        """
        获取工作空间根目录列表（转换为 Path 对象）
        
        Returns:
            Path 对象列表
        """
        if not self.workspace_roots:
            # 默认使用 ~/.gateflow/workspaces
            return [CONFIG_DIR / "workspaces"]
        return [Path(root) for root in self.workspace_roots]
    
    def get_security_policy(self) -> SecurityPolicy:
        """
        获取安全策略配置
        
        Returns:
            SecurityPolicy 实例
        """
        return SecurityPolicy(
            sandbox_enabled=True,  # 沙箱默认启用
            allowed_roots=self.workspace_roots if self.workspace_roots else ["~/.gateflow/workspaces"],
            allow_dangerous_operations=self.allow_dangerous_operations,
            tcl_policy=self.tcl_policy,
        )

    def get_execution_context(self) -> "ExecutionContext":
        """
        获取执行上下文配置。

        为后续 Non-Project / Embedded / Vitis 执行路径预留统一入口。
        """
        from gateflow.execution_context import ExecutionContext

        workspace = Path(self.execution_workspace) if self.execution_workspace else None
        return ExecutionContext(
            kind=self.execution_context_kind,
            workspace=workspace,
        )
    
    def validate_security(self) -> list[str]:
        """
        验证安全策略配置
        
        Returns:
            警告消息列表
        """
        policy = self.get_security_policy()
        return validate_security_policy(policy)


class TimeoutConfig:
    """
    超时配置（兼容旧代码）
    
    Attributes:
        single_command: 单个命令执行的超时时间（秒），默认 60 秒
        batch_total: 批量命令的总超时时间（秒），默认 3600 秒
        connect: 连接超时时间（秒），默认 10 秒
        idle: 空闲超时时间（秒），默认 300 秒
    
    建议使用 GateFlowSettings.get_timeout_config() 获取实例
    """
    
    def __init__(
        self,
        single_command: float = 60.0,
        batch_total: float = 3600.0,
        connect: float = 10.0,
        idle: float = 300.0,
    ):
        self.single_command = single_command
        self.batch_total = batch_total
        self.connect = connect
        self.idle = idle
        
        # 验证
        if self.single_command <= 0:
            raise ValueError(f"single_command 必须大于 0，当前值: {self.single_command}")
        if self.batch_total <= 0:
            raise ValueError(f"batch_total 必须大于 0，当前值: {self.batch_total}")
        if self.connect <= 0:
            raise ValueError(f"connect 必须大于 0，当前值: {self.connect}")
        if self.idle <= 0:
            raise ValueError(f"idle 必须大于 0，当前值: {self.idle}")
        
        # 警告：批量超时小于单命令超时
        if self.batch_total < self.single_command:
            warnings.warn(
                f"batch_total ({self.batch_total}s) 小于 single_command ({self.single_command}s)，"
                "可能导致批量命令无法完成",
                UserWarning,
            )


class TcpConfig:
    """
    TCP 连接配置（兼容旧代码）
    
    建议使用 GateFlowSettings.get_tcp_config() 获取实例
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9999,
        timeout: float = 60.0,
        reconnect_attempts: int = 5,
        reconnect_delay: float = 2.0,
        buffer_size: int = 65536,
        keepalive_interval: float = 30.0,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.buffer_size = buffer_size
        self.keepalive_interval = keepalive_interval


# 全局配置实例
_settings: GateFlowSettings | None = None


def get_settings(reload: bool = False, **kwargs: Any) -> GateFlowSettings:
    """
    获取全局配置实例
    
    Args:
        reload: 是否重新加载配置
        **kwargs: 配置参数（用于覆盖）
    
    Returns:
        GateFlowSettings 实例
    
    Example:
        >>> settings = get_settings()
        >>> print(settings.tcp_port)
        9999
        
        # 强制重新加载
        >>> settings = get_settings(reload=True)
        
        # 覆盖配置（用于 CLI 参数）
        >>> settings = get_settings(tcp_port=8888)
    """
    global _settings
    
    if _settings is None or reload or kwargs:
        if kwargs:
            # 有覆盖参数，创建新实例
            _settings = GateFlowSettings(**kwargs)
        elif _settings is None or reload:
            _settings = GateFlowSettings()
    
    return _settings


def reset_settings() -> None:
    """
    重置全局配置实例（主要用于测试）
    """
    global _settings
    _settings = None


# 默认配置实例（兼容旧代码）
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig()
