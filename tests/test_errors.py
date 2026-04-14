"""
统一错误模型测试

测试 GateFlow 的统一错误模型，包括：
- ErrorCode 枚举
- ErrorInfo 数据类
- Result 数据类
- make_success 和 make_error 工具函数
"""

import pytest
from gateflow.errors import (
    ErrorCode,
    ErrorInfo,
    Result,
    make_success,
    make_error,
    make_error_from_exception,
    generate_request_id,
    get_error_message,
    get_error_suggestion,
)


class TestErrorCode:
    """测试 ErrorCode 枚举"""
    
    def test_error_code_values(self):
        """测试错误码值"""
        # 连接错误
        assert ErrorCode.CONNECTION_FAILED.value == 1001
        assert ErrorCode.CONNECTION_TIMEOUT.value == 1002
        assert ErrorCode.CONNECTION_LOST.value == 1003
        assert ErrorCode.CONNECTION_REFUSED.value == 1004
        
        # 执行错误
        assert ErrorCode.COMMAND_FAILED.value == 2001
        assert ErrorCode.COMMAND_TIMEOUT.value == 2002
        assert ErrorCode.COMMAND_SYNTAX_ERROR.value == 2003
        
        # 文件错误
        assert ErrorCode.FILE_NOT_FOUND.value == 3001
        assert ErrorCode.FILE_PERMISSION_DENIED.value == 3002
        assert ErrorCode.FILE_SANDBOX_VIOLATION.value == 3003
        
        # Tcl 错误
        assert ErrorCode.TCL_POLICY_VIOLATION.value == 4001
        assert ErrorCode.TCL_DANGEROUS_COMMAND.value == 4002
        
        # 项目错误
        assert ErrorCode.PROJECT_NOT_FOUND.value == 5001
        assert ErrorCode.PROJECT_CREATE_FAILED.value == 5003
        
        # 引擎错误
        assert ErrorCode.ENGINE_NOT_INITIALIZED.value == 7001
    
    def test_error_code_categories(self):
        """测试错误码分类"""
        # 连接错误 (1xxx)
        connection_codes = [e for e in ErrorCode if 1000 <= e.value < 2000]
        assert len(connection_codes) >= 4
        
        # 执行错误 (2xxx)
        execution_codes = [e for e in ErrorCode if 2000 <= e.value < 3000]
        assert len(execution_codes) >= 5
        
        # 文件错误 (3xxx)
        file_codes = [e for e in ErrorCode if 3000 <= e.value < 4000]
        assert len(file_codes) >= 6
        
        # Tcl 错误 (4xxx)
        tcl_codes = [e for e in ErrorCode if 4000 <= e.value < 5000]
        assert len(tcl_codes) >= 4


class TestErrorInfo:
    """测试 ErrorInfo 数据类"""
    
    def test_error_info_creation(self):
        """测试创建 ErrorInfo"""
        error = ErrorInfo(
            code=ErrorCode.CONNECTION_FAILED,
            message="无法连接到服务器",
        )
        
        assert error.code == ErrorCode.CONNECTION_FAILED
        assert error.message == "无法连接到服务器"
        assert error.details is None
        assert error.suggestion is None
        assert error.request_id is None
    
    def test_error_info_with_details(self):
        """测试带详细信息的 ErrorInfo"""
        error = ErrorInfo(
            code=ErrorCode.COMMAND_TIMEOUT,
            message="命令执行超时",
            details={"timeout": 30, "command": "synth_design"},
            suggestion="请增加超时时间",
            request_id="abc12345",
        )
        
        assert error.code == ErrorCode.COMMAND_TIMEOUT
        assert error.message == "命令执行超时"
        assert error.details == {"timeout": 30, "command": "synth_design"}
        assert error.suggestion == "请增加超时时间"
        assert error.request_id == "abc12345"
    
    def test_error_info_to_dict(self):
        """测试 ErrorInfo 转换为字典"""
        error = ErrorInfo(
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件不存在",
            details={"path": "/tmp/test.v"},
            suggestion="请确认文件路径正确",
            request_id="xyz98765",
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["code"] == 3001
        assert error_dict["code_name"] == "FILE_NOT_FOUND"
        assert error_dict["message"] == "文件不存在"
        assert error_dict["details"] == {"path": "/tmp/test.v"}
        assert error_dict["suggestion"] == "请确认文件路径正确"
        assert error_dict["request_id"] == "xyz98765"


class TestResult:
    """测试 Result 数据类"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = Result(
            success=True,
            data={"name": "test_project"},
            warnings=["这是一个警告"],
            execution_time=1.5,
            request_id="test1234",
        )
        
        assert result.success is True
        assert result.data == {"name": "test_project"}
        assert result.error is None
        assert result.warnings == ["这是一个警告"]
        assert result.execution_time == 1.5
        assert result.request_id == "test1234"
    
    def test_error_result(self):
        """测试错误结果"""
        error_info = ErrorInfo(
            code=ErrorCode.COMMAND_FAILED,
            message="命令执行失败",
        )
        result = Result(
            success=False,
            error=error_info,
            execution_time=0.5,
        )
        
        assert result.success is False
        assert result.data is None
        assert result.error.code == ErrorCode.COMMAND_FAILED
        assert result.error.message == "命令执行失败"
    
    def test_result_to_dict(self):
        """测试 Result 转换为字典"""
        result = Result(
            success=True,
            data={"value": 42},
            warnings=["warning1"],
            execution_time=2.0,
            request_id="req123",
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["data"] == {"value": 42}
        assert result_dict["error"] is None
        assert result_dict["warnings"] == ["warning1"]
        assert result_dict["execution_time"] == 2.0
        assert result_dict["request_id"] == "req123"
    
    def test_result_from_dict(self):
        """测试从字典创建 Result"""
        data = {
            "success": False,
            "data": None,
            "error": {
                "code": 2002,
                "code_name": "COMMAND_TIMEOUT",
                "message": "命令超时",
                "details": {"timeout": 30},
                "suggestion": "请增加超时时间",
                "request_id": "abc123",
            },
            "warnings": None,
            "execution_time": 30.0,
            "request_id": "abc123",
        }
        
        result = Result.from_dict(data)
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == ErrorCode.COMMAND_TIMEOUT
        assert result.error.message == "命令超时"
        assert result.error.details == {"timeout": 30}
        assert result.execution_time == 30.0


class TestMakeSuccess:
    """测试 make_success 函数"""
    
    def test_make_success_basic(self):
        """测试基本成功结果创建"""
        result = make_success(data="test_data")
        
        assert result.success is True
        assert result.data == "test_data"
        assert result.error is None
        assert result.warnings is None
        assert result.request_id is not None
    
    def test_make_success_with_warnings(self):
        """测试带警告的成功结果"""
        result = make_success(
            data={"key": "value"},
            warnings=["warning1", "warning2"],
            execution_time=1.5,
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.warnings == ["warning1", "warning2"]
        assert result.execution_time == 1.5
    
    def test_make_success_with_request_id(self):
        """测试带请求 ID 的成功结果"""
        result = make_success(
            data=None,
            request_id="custom_id",
        )
        
        assert result.request_id == "custom_id"


class TestMakeError:
    """测试 make_error 函数"""
    
    def test_make_error_basic(self):
        """测试基本错误结果创建"""
        result = make_error(
            code=ErrorCode.CONNECTION_FAILED,
            message="连接失败",
        )
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == ErrorCode.CONNECTION_FAILED
        assert result.error.message == "连接失败"
        assert result.request_id is not None
    
    def test_make_error_with_details(self):
        """测试带详细信息的错误结果"""
        result = make_error(
            code=ErrorCode.FILE_NOT_FOUND,
            message="文件不存在",
            details={"path": "/tmp/test.v"},
            suggestion="请确认文件路径正确",
        )
        
        assert result.error.details == {"path": "/tmp/test.v"}
        assert result.error.suggestion == "请确认文件路径正确"
    
    def test_make_error_with_execution_time(self):
        """测试带执行时间的错误结果"""
        result = make_error(
            code=ErrorCode.COMMAND_TIMEOUT,
            message="命令超时",
            execution_time=30.0,
        )
        
        assert result.execution_time == 30.0


class TestMakeErrorFromException:
    """测试 make_error_from_exception 函数"""
    
    def test_make_error_from_exception(self):
        """测试从异常创建错误结果"""
        try:
            raise ValueError("测试异常")
        except Exception as e:
            result = make_error_from_exception(e)
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == ErrorCode.COMMAND_EXECUTION_ERROR
        assert result.error.message == "测试异常"
        assert result.error.details is not None
        assert result.error.details["exception_type"] == "ValueError"
    
    def test_make_error_from_exception_with_custom_code(self):
        """测试从异常创建错误结果（自定义错误码）"""
        try:
            raise FileNotFoundError("文件未找到")
        except Exception as e:
            result = make_error_from_exception(
                e,
                code=ErrorCode.FILE_NOT_FOUND,
            )
        
        assert result.error.code == ErrorCode.FILE_NOT_FOUND


class TestGenerateRequestId:
    """测试 generate_request_id 函数"""
    
    def test_generate_request_id_length(self):
        """测试请求 ID 长度"""
        request_id = generate_request_id()
        assert len(request_id) == 8
    
    def test_generate_request_id_uniqueness(self):
        """测试请求 ID 唯一性"""
        ids = [generate_request_id() for _ in range(100)]
        assert len(set(ids)) == 100


class TestErrorMessages:
    """测试错误消息和建议"""
    
    def test_get_error_message(self):
        """测试获取错误消息"""
        message = get_error_message(ErrorCode.CONNECTION_FAILED)
        assert "无法连接" in message
        
        message = get_error_message(ErrorCode.COMMAND_TIMEOUT)
        assert "超时" in message
    
    def test_get_error_suggestion(self):
        """测试获取错误建议"""
        suggestion = get_error_suggestion(ErrorCode.CONNECTION_FAILED)
        assert suggestion is not None
        assert "tcl_server" in suggestion or "启动" in suggestion
        
        suggestion = get_error_suggestion(ErrorCode.COMMAND_TIMEOUT)
        assert suggestion is not None
        assert "超时" in suggestion
    
    def test_get_error_message_unknown(self):
        """测试获取未知错误的消息"""
        # 创建一个不存在的错误码（这里使用一个有效的错误码测试）
        message = get_error_message(ErrorCode.ENGINE_NOT_INITIALIZED)
        assert "未初始化" in message


class TestResultIntegration:
    """测试 Result 集成场景"""
    
    def test_success_to_dict_and_back(self):
        """测试成功结果的序列化和反序列化"""
        original = make_success(
            data={"project": "test", "files": ["a.v", "b.v"]},
            warnings=["warning1"],
            execution_time=5.0,
        )
        
        # 转换为字典
        data = original.to_dict()
        
        # 从字典重建
        restored = Result.from_dict(data)
        
        assert restored.success == original.success
        assert restored.data == original.data
        assert restored.warnings == original.warnings
        assert restored.execution_time == original.execution_time
    
    def test_error_to_dict_and_back(self):
        """测试错误结果的序列化和反序列化"""
        original = make_error(
            code=ErrorCode.PROJECT_CREATE_FAILED,
            message="项目创建失败",
            details={"reason": "权限不足"},
            suggestion="检查目录权限",
        )
        
        # 转换为字典
        data = original.to_dict()
        
        # 从字典重建
        restored = Result.from_dict(data)
        
        assert restored.success == original.success
        assert restored.error.code == original.error.code
        assert restored.error.message == original.error.message
        assert restored.error.details == original.error.details
        assert restored.error.suggestion == original.error.suggestion
