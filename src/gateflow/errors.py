"""
GateFlow 统一错误模型

提供统一的错误码、错误信息和返回结构，确保整个系统的错误处理一致。
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ErrorCode(Enum):
    """错误码枚举
    
    错误码分类：
    - 1xxx: 连接错误
    - 2xxx: 执行错误
    - 3xxx: 文件错误
    - 4xxx: Tcl 错误
    - 5xxx: 项目错误
    - 6xxx: 配置错误
    """
    
    # 连接错误 (1xxx)
    CONNECTION_FAILED = 1001
    CONNECTION_TIMEOUT = 1002
    CONNECTION_LOST = 1003
    CONNECTION_REFUSED = 1004
    
    # 执行错误 (2xxx)
    COMMAND_FAILED = 2001
    COMMAND_TIMEOUT = 2002
    COMMAND_SYNTAX_ERROR = 2003
    COMMAND_NOT_FOUND = 2004
    COMMAND_EXECUTION_ERROR = 2005
    
    # 文件错误 (3xxx)
    FILE_NOT_FOUND = 3001
    FILE_PERMISSION_DENIED = 3002
    FILE_SANDBOX_VIOLATION = 3003
    FILE_READ_ERROR = 3004
    FILE_WRITE_ERROR = 3005
    FILE_INVALID_PATH = 3006
    
    # Tcl 错误 (4xxx)
    TCL_POLICY_VIOLATION = 4001
    TCL_DANGEROUS_COMMAND = 4002
    TCL_SYNTAX_ERROR = 4003
    TCL_RUNTIME_ERROR = 4004
    
    # 项目错误 (5xxx)
    PROJECT_NOT_FOUND = 5001
    PROJECT_ALREADY_EXISTS = 5002
    PROJECT_CREATE_FAILED = 5003
    PROJECT_OPEN_FAILED = 5004
    PROJECT_INVALID_CONFIG = 5005
    
    # 配置错误 (6xxx)
    CONFIG_INVALID = 6001
    CONFIG_MISSING = 6002
    CONFIG_PARSE_ERROR = 6003
    
    # 引擎错误 (7xxx)
    ENGINE_NOT_INITIALIZED = 7001
    ENGINE_INIT_FAILED = 7002
    ENGINE_MODE_ERROR = 7003


@dataclass
class ErrorInfo:
    """统一错误信息结构
    
    Attributes:
        code: 错误码枚举值
        message: 错误消息
        details: 错误详细信息字典
        suggestion: 修复建议
        request_id: 请求追踪 ID
    """
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    suggestion: str | None = None
    request_id: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "code": self.code.value,
            "code_name": self.code.name,
            "message": self.message,
            "details": self.details,
            "suggestion": self.suggestion,
            "request_id": self.request_id,
        }


@dataclass
class Result:
    """统一返回结构
    
    所有工具和 API 的返回值都应使用此结构，确保一致性。
    
    Attributes:
        success: 操作是否成功
        data: 成功时返回的数据
        error: 失败时的错误信息
        warnings: 警告信息列表
        execution_time: 执行时间（秒）
        request_id: 请求追踪 ID
    """
    success: bool
    data: Any | None = None
    error: ErrorInfo | None = None
    warnings: list[str] | None = None
    execution_time: float = 0.0
    request_id: str | None = None
    
    @property
    def output(self) -> str:
        """兼容属性：返回 data 作为字符串"""
        if self.data is None:
            return ""
        return str(self.data)
    
    @property
    def errors(self) -> list[str]:
        """兼容属性：返回错误信息列表"""
        if self.error:
            return [self.error.message]
        return []
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        result = {
            "success": self.success,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "warnings": self.warnings,
            "execution_time": self.execution_time,
            "request_id": self.request_id,
        }
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Result":
        """从字典创建 Result 实例"""
        error_info = None
        if data.get("error"):
            error_data = data["error"]
            if isinstance(error_data, dict):
                # 从字典重建 ErrorInfo
                code_value = error_data.get("code")
                if code_value:
                    try:
                        error_code = ErrorCode(code_value)
                        error_info = ErrorInfo(
                            code=error_code,
                            message=error_data.get("message", ""),
                            details=error_data.get("details"),
                            suggestion=error_data.get("suggestion"),
                            request_id=error_data.get("request_id"),
                        )
                    except ValueError:
                        # 如果错误码无效，使用通用错误
                        pass
        
        return cls(
            success=data.get("success", False),
            data=data.get("data"),
            error=error_info,
            warnings=data.get("warnings"),
            execution_time=data.get("execution_time", 0.0),
            request_id=data.get("request_id"),
        )


def generate_request_id() -> str:
    """
    生成唯一的请求 ID
    
    Returns:
        8位短 ID，用于追踪请求
    """
    return str(uuid.uuid4())[:8]


def make_success(
    data: Any = None,
    warnings: list[str] | None = None,
    execution_time: float = 0.0,
    request_id: str | None = None,
) -> Result:
    """
    创建成功结果
    
    Args:
        data: 返回的数据
        warnings: 警告信息列表
        execution_time: 执行时间
        request_id: 请求 ID
    
    Returns:
        Result 实例
    """
    return Result(
        success=True,
        data=data,
        warnings=warnings,
        execution_time=execution_time,
        request_id=request_id or generate_request_id(),
    )


def make_error(
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
    suggestion: str | None = None,
    request_id: str | None = None,
    execution_time: float = 0.0,
) -> Result:
    """
    创建错误结果
    
    Args:
        code: 错误码
        message: 错误消息
        details: 错误详细信息
        suggestion: 修复建议
        request_id: 请求 ID
        execution_time: 执行时间
    
    Returns:
        Result 实例
    """
    return Result(
        success=False,
        error=ErrorInfo(
            code=code,
            message=message,
            details=details,
            suggestion=suggestion,
            request_id=request_id or generate_request_id(),
        ),
        execution_time=execution_time,
        request_id=request_id or generate_request_id(),
    )


def make_error_from_exception(
    exception: Exception,
    code: ErrorCode = ErrorCode.COMMAND_EXECUTION_ERROR,
    request_id: str | None = None,
    execution_time: float = 0.0,
) -> Result:
    """
    从异常创建错误结果
    
    Args:
        exception: 异常对象
        code: 错误码，默认为 COMMAND_EXECUTION_ERROR
        request_id: 请求 ID
        execution_time: 执行时间
    
    Returns:
        Result 实例
    """
    return make_error(
        code=code,
        message=str(exception),
        details={
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
        },
        request_id=request_id,
        execution_time=execution_time,
    )


# 错误消息模板
ERROR_MESSAGES = {
    ErrorCode.CONNECTION_FAILED: "无法连接到 Vivado tcl_server",
    ErrorCode.CONNECTION_TIMEOUT: "连接 Vivado tcl_server 超时",
    ErrorCode.CONNECTION_LOST: "与 Vivado tcl_server 的连接已断开",
    ErrorCode.CONNECTION_REFUSED: "连接被拒绝，请确认 Vivado tcl_server 已启动",
    
    ErrorCode.COMMAND_FAILED: "Tcl 命令执行失败",
    ErrorCode.COMMAND_TIMEOUT: "Tcl 命令执行超时",
    ErrorCode.COMMAND_SYNTAX_ERROR: "Tcl 命令语法错误",
    ErrorCode.COMMAND_NOT_FOUND: "Tcl 命令不存在",
    ErrorCode.COMMAND_EXECUTION_ERROR: "Tcl 命令执行异常",
    
    ErrorCode.FILE_NOT_FOUND: "文件不存在",
    ErrorCode.FILE_PERMISSION_DENIED: "文件权限不足",
    ErrorCode.FILE_SANDBOX_VIOLATION: "文件访问违反沙箱规则",
    ErrorCode.FILE_READ_ERROR: "文件读取失败",
    ErrorCode.FILE_WRITE_ERROR: "文件写入失败",
    ErrorCode.FILE_INVALID_PATH: "文件路径无效",
    
    ErrorCode.TCL_POLICY_VIOLATION: "Tcl 命令违反安全策略",
    ErrorCode.TCL_DANGEROUS_COMMAND: "检测到危险的 Tcl 命令",
    ErrorCode.TCL_SYNTAX_ERROR: "Tcl 语法错误",
    ErrorCode.TCL_RUNTIME_ERROR: "Tcl 运行时错误",
    
    ErrorCode.PROJECT_NOT_FOUND: "项目不存在",
    ErrorCode.PROJECT_ALREADY_EXISTS: "项目已存在",
    ErrorCode.PROJECT_CREATE_FAILED: "项目创建失败",
    ErrorCode.PROJECT_OPEN_FAILED: "项目打开失败",
    ErrorCode.PROJECT_INVALID_CONFIG: "项目配置无效",
    
    ErrorCode.CONFIG_INVALID: "配置无效",
    ErrorCode.CONFIG_MISSING: "缺少必要配置",
    ErrorCode.CONFIG_PARSE_ERROR: "配置解析失败",
    
    ErrorCode.ENGINE_NOT_INITIALIZED: "执行引擎未初始化",
    ErrorCode.ENGINE_INIT_FAILED: "执行引擎初始化失败",
    ErrorCode.ENGINE_MODE_ERROR: "执行引擎模式错误",
}

# 错误修复建议
ERROR_SUGGESTIONS = {
    ErrorCode.CONNECTION_FAILED: "请确认 Vivado tcl_server 已启动并监听正确的端口",
    ErrorCode.CONNECTION_TIMEOUT: "请检查网络连接或增加超时时间",
    ErrorCode.CONNECTION_LOST: "请检查 Vivado 是否正常运行",
    ErrorCode.CONNECTION_REFUSED: "请在 Vivado 中启动 tcl_server: start_gui 或使用 TCP 服务器",
    
    ErrorCode.COMMAND_TIMEOUT: "请增加超时时间或优化 Tcl 命令",
    ErrorCode.COMMAND_SYNTAX_ERROR: "请检查 Tcl 命令语法",
    
    ErrorCode.FILE_NOT_FOUND: "请确认文件路径正确",
    ErrorCode.FILE_PERMISSION_DENIED: "请检查文件权限或使用其他路径",
    ErrorCode.FILE_SANDBOX_VIOLATION: "请使用沙箱允许的路径",
    
    ErrorCode.TCL_DANGEROUS_COMMAND: "请避免使用危险的 Tcl 命令（如 exec, system 等）",
    
    ErrorCode.PROJECT_NOT_FOUND: "请确认项目路径正确",
    ErrorCode.PROJECT_ALREADY_EXISTS: "请使用不同的项目名称或删除现有项目",
    
    ErrorCode.ENGINE_NOT_INITIALIZED: "请先调用引擎初始化方法",
    ErrorCode.ENGINE_INIT_FAILED: "请检查 Vivado 安装和环境变量配置",
}


def get_error_message(code: ErrorCode) -> str:
    """获取错误码对应的默认消息"""
    return ERROR_MESSAGES.get(code, "未知错误")


def get_error_suggestion(code: ErrorCode) -> str | None:
    """获取错误码对应的修复建议"""
    return ERROR_SUGGESTIONS.get(code)
