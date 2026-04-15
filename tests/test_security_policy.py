"""
测试安全策略配置。

验证安全策略配置的功能：
1. SecurityPolicy 默认值和验证
2. 从环境变量加载配置
3. 配置验证和警告
4. GateFlowSettings 集成
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from gateflow.settings import (
    GateFlowSettings,
    SecurityPolicy,
    TimeoutConfig,
    get_settings,
    reset_settings,
    validate_security_policy,
)
from gateflow.utils.sandbox import SandboxConfig


class TestSecurityPolicy:
    """测试 SecurityPolicy 配置类"""

    def test_default_values(self):
        """测试默认值"""
        policy = SecurityPolicy()

        assert policy.sandbox_enabled is True
        assert len(policy.allowed_roots) == 1
        assert policy.allow_dangerous_operations is False
        assert policy.dangerous_operations_require_confirmation is True
        assert policy.tcl_policy == "normal"
        assert len(policy.tcl_dangerous_patterns) == 0
        assert policy.max_file_size == 100 * 1024 * 1024
        assert len(policy.allowed_file_extensions) == 0

    def test_custom_values(self):
        """测试自定义值"""
        policy = SecurityPolicy(
            sandbox_enabled=False,
            allowed_roots=["/custom/path"],
            allow_dangerous_operations=True,
            tcl_policy="safe",
            max_file_size=50 * 1024 * 1024,
        )

        assert policy.sandbox_enabled is False
        # 路径会被解析为绝对路径
        assert any("custom" in root and "path" in root for root in policy.allowed_roots)
        assert policy.allow_dangerous_operations is True
        assert policy.tcl_policy == "safe"
        assert policy.max_file_size == 50 * 1024 * 1024

    def test_path_expansion(self):
        """测试路径展开（~ 符号）"""
        policy = SecurityPolicy(allowed_roots=["~/projects"])

        # ~ 应该被展开为用户主目录
        assert "~" not in policy.allowed_roots[0]
        assert Path(policy.allowed_roots[0]).is_absolute()

    def test_tcl_policy_validation(self):
        """测试 Tcl 策略验证"""
        # 有效值
        for policy_level in ["safe", "normal", "unsafe"]:
            policy = SecurityPolicy(tcl_policy=policy_level)
            assert policy.tcl_policy == policy_level

        # 无效值
        with pytest.raises(ValueError, match="tcl_policy 必须是"):
            SecurityPolicy(tcl_policy="invalid")

    def test_from_env_sandbox_enabled(self):
        """测试从环境变量读取沙箱启用状态"""
        # 启用沙箱
        with patch.dict(os.environ, {"GATEFLOW_SANDBOX_ENABLED": "true"}):
            policy = SecurityPolicy.from_env()
            assert policy.sandbox_enabled is True

        # 禁用沙箱
        with patch.dict(os.environ, {"GATEFLOW_SANDBOX_ENABLED": "false"}):
            policy = SecurityPolicy.from_env()
            assert policy.sandbox_enabled is False

    def test_from_env_workspace_roots(self):
        """测试从环境变量读取工作空间根目录"""
        # Windows 风格
        with patch("gateflow.settings._get_env_separator", return_value=";"):
            with patch.dict(os.environ, {"GATEFLOW_WORKSPACE_ROOTS": "C:/path1;C:/path2"}):
                policy = SecurityPolicy.from_env()
                assert len(policy.allowed_roots) == 2
                assert policy.allowed_roots == ["C:/path1", "C:/path2"]

        # Unix 风格 - 跳过这个测试，因为在 Windows 上无法创建 PosixPath
        # with patch("gateflow.settings.os.name", "posix"):
        #     with patch.dict(os.environ, {"GATEFLOW_WORKSPACE_ROOTS": "/path1:/path2:/path3"}):
        #         policy = SecurityPolicy.from_env()
        #         assert len(policy.allowed_roots) == 3

    def test_sandbox_config_from_env_windows_roots(self):
        """SandboxConfig.from_env should keep Windows-style root lists intact."""
        with patch.dict(os.environ, {"GATEFLOW_WORKSPACE_ROOTS": "C:/path1;C:/path2"}):
            config = SandboxConfig.from_env()

        assert len(config.allowed_roots) == 2

    def test_from_env_allow_dangerous(self):
        """测试从环境变量读取危险操作配置"""
        # 允许危险操作
        with patch.dict(os.environ, {"GATEFLOW_ALLOW_DANGEROUS": "true"}):
            policy = SecurityPolicy.from_env()
            assert policy.allow_dangerous_operations is True

        # 不允许危险操作
        with patch.dict(os.environ, {"GATEFLOW_ALLOW_DANGEROUS": "false"}):
            policy = SecurityPolicy.from_env()
            assert policy.allow_dangerous_operations is False

    def test_from_env_tcl_policy(self):
        """测试从环境变量读取 Tcl 策略"""
        with patch.dict(os.environ, {"GATEFLOW_TCL_POLICY": "safe"}):
            policy = SecurityPolicy.from_env()
            assert policy.tcl_policy == "safe"

        with patch.dict(os.environ, {"GATEFLOW_TCL_POLICY": "unsafe"}):
            policy = SecurityPolicy.from_env()
            assert policy.tcl_policy == "unsafe"

    def test_from_env_max_file_size(self):
        """测试从环境变量读取最大文件大小"""
        with patch.dict(os.environ, {"GATEFLOW_MAX_FILE_SIZE": "200"}):
            policy = SecurityPolicy.from_env()
            assert policy.max_file_size == 200 * 1024 * 1024

    def test_to_dict(self):
        """测试转换为字典"""
        policy = SecurityPolicy(
            sandbox_enabled=False,
            allowed_roots=["/test"],
            tcl_policy="unsafe",
        )

        result = policy.to_dict()

        assert isinstance(result, dict)
        assert result["sandbox_enabled"] is False
        # 路径会被解析为绝对路径
        assert any("test" in root for root in result["allowed_roots"])
        assert result["tcl_policy"] == "unsafe"


class TestValidateSecurityPolicy:
    """测试安全策略验证"""

    def test_sandbox_disabled_warning(self):
        """测试沙箱禁用警告"""
        policy = SecurityPolicy(sandbox_enabled=False)
        warnings = validate_security_policy(policy)

        assert len(warnings) > 0
        assert any("沙箱已禁用" in w for w in warnings)

    def test_dangerous_operations_warning(self):
        """测试危险操作启用警告"""
        policy = SecurityPolicy(allow_dangerous_operations=True)
        warnings = validate_security_policy(policy)

        assert len(warnings) > 0
        assert any("危险操作已启用" in w for w in warnings)

    def test_unsafe_tcl_policy_warning(self):
        """测试 unsafe Tcl 策略警告"""
        policy = SecurityPolicy(tcl_policy="unsafe")
        warnings = validate_security_policy(policy)

        assert len(warnings) > 0
        assert any("unsafe" in w for w in warnings)

    def test_empty_allowed_roots_warning(self):
        """测试空根目录警告"""
        policy = SecurityPolicy(sandbox_enabled=True, allowed_roots=[])
        warnings = validate_security_policy(policy)

        assert len(warnings) > 0
        assert any("未配置允许的根目录" in w for w in warnings)

    def test_large_max_file_size_warning(self):
        """测试大文件大小警告"""
        policy = SecurityPolicy(max_file_size=2 * 1024 * 1024 * 1024)  # 2GB
        warnings = validate_security_policy(policy)

        assert len(warnings) > 0
        assert any("最大文件大小" in w for w in warnings)

    def test_no_warnings_for_safe_config(self):
        """测试安全配置无警告"""
        policy = SecurityPolicy(
            sandbox_enabled=True,
            allowed_roots=["/safe/path"],
            allow_dangerous_operations=False,
            tcl_policy="normal",
            max_file_size=100 * 1024 * 1024,
        )
        warnings = validate_security_policy(policy)

        assert len(warnings) == 0

    def test_multiple_warnings(self):
        """测试多个警告"""
        policy = SecurityPolicy(
            sandbox_enabled=False,
            allow_dangerous_operations=True,
            tcl_policy="unsafe",
        )
        warnings = validate_security_policy(policy)

        assert len(warnings) >= 3


class TestSecuritySettings:
    """测试 GateFlowSettings 中的安全策略集成"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_default_security_values(self):
        """测试默认安全策略值"""
        settings = GateFlowSettings()
        security = settings.get_security_policy()

        assert security.sandbox_enabled is True
        assert security.tcl_policy == "normal"
        assert security.allow_dangerous_operations is False

    def test_custom_security_values(self):
        """测试自定义安全策略值"""
        settings = GateFlowSettings(
            allow_dangerous_operations=True,
            tcl_policy="safe",
            workspace_roots=["/custom/path"],
        )
        security = settings.get_security_policy()

        assert security.allow_dangerous_operations is True
        assert security.tcl_policy == "safe"
        # 路径会被解析为绝对路径
        assert any("custom" in root and "path" in root for root in security.allowed_roots)

    def test_tcl_policy_validation(self):
        """测试 Tcl 策略验证"""
        # 有效值
        for policy in ["safe", "normal", "unsafe"]:
            settings = GateFlowSettings(tcl_policy=policy)
            assert settings.tcl_policy == policy

        # 无效值
        with pytest.raises(ValueError):
            GateFlowSettings(tcl_policy="invalid")

    def test_from_env_sandbox_enabled(self):
        """测试从环境变量读取沙箱启用状态"""
        with patch.dict(os.environ, {"GATEFLOW_SANDBOX_ENABLED": "false"}):
            policy = SecurityPolicy.from_env()
            assert policy.sandbox_enabled is False

    def test_from_env_workspace_roots(self):
        """测试从环境变量读取工作空间根目录"""
        # 在 Windows 上使用分号分隔
        with patch.dict(os.environ, {"GATEFLOW_WORKSPACE_ROOTS": "C:/path1;C:/path2"}):
            policy = SecurityPolicy.from_env()
            # 在 Windows 上，路径会被解析
            assert len(policy.allowed_roots) >= 1

    def test_from_env_allow_dangerous(self):
        """测试从环境变量读取危险操作配置"""
        with patch.dict(os.environ, {"GATEFLOW_ALLOW_DANGEROUS": "true"}):
            policy = SecurityPolicy.from_env()
            assert policy.allow_dangerous_operations is True

    def test_from_env_tcl_policy(self):
        """测试从环境变量读取 Tcl 策略"""
        with patch.dict(os.environ, {"GATEFLOW_TCL_POLICY": "safe"}):
            policy = SecurityPolicy.from_env()
            assert policy.tcl_policy == "safe"


class TestSandboxConfigIntegration:
    """测试 SandboxConfig 与 SecurityPolicy 的集成"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_from_settings(self):
        """测试从 GateFlowSettings 创建 SandboxConfig"""
        settings = GateFlowSettings(
            workspace_roots=["C:/test/path"],
            allow_dangerous_operations=True,
        )
        security = settings.get_security_policy()

        # 路径会被解析为绝对路径
        assert any("test" in root and "path" in root for root in security.allowed_roots)
        assert security.allow_dangerous_operations is True

    def test_default_from_settings(self):
        """测试默认配置"""
        settings = GateFlowSettings()
        security = settings.get_security_policy()

        # 默认沙箱启用
        assert security.sandbox_enabled is True
        # 默认危险操作禁用
        assert security.allow_dangerous_operations is False
        # 默认 Tcl 策略为 normal
        assert security.tcl_policy == "normal"

    def test_env_override(self):
        """测试环境变量覆盖"""
        # GateFlowSettings 使用 GATEFLOW_ALLOW_DANGEROUS_OPERATIONS
        # SecurityPolicy.from_env() 使用 GATEFLOW_ALLOW_DANGEROUS
        with patch.dict(os.environ, {
            "GATEFLOW_ALLOW_DANGEROUS_OPERATIONS": "true",
            "GATEFLOW_TCL_POLICY": "unsafe",
        }):
            # 需要重新创建 GateFlowSettings 实例才能读取环境变量
            settings = GateFlowSettings()
            security = settings.get_security_policy()

            assert security.allow_dangerous_operations is True
            assert security.tcl_policy == "unsafe"


class TestGlobalSettings:
    """测试全局配置管理"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_get_settings_singleton(self):
        """测试获取全局配置（单例）"""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_reload_settings(self):
        """测试重新加载配置"""
        settings1 = get_settings()

        # 重新加载
        settings2 = get_settings(reload=True)

        # 不是同一个实例
        assert settings1 is not settings2

        # 新实例应该是默认配置
        assert settings2.tcl_policy == "normal"

    def test_reload_from_env(self):
        """测试从环境变量重新加载"""
        # 第一次加载
        settings1 = get_settings()
        assert settings1.tcl_policy == "normal"

        # 修改环境变量
        with patch.dict(os.environ, {"GATEFLOW_TCL_POLICY": "unsafe"}):
            settings2 = get_settings(reload=True)
            assert settings2.tcl_policy == "unsafe"


class TestTimeoutConfig:
    """测试 TimeoutConfig 配置类"""

    def test_default_values(self):
        """测试默认值"""
        config = TimeoutConfig()

        assert config.single_command == 60.0
        assert config.batch_total == 3600.0
        assert config.connect == 10.0
        assert config.idle == 300.0

    def test_custom_values(self):
        """测试自定义值"""
        config = TimeoutConfig(
            single_command=60.0,
            batch_total=7200.0,
        )

        assert config.single_command == 60.0
        assert config.batch_total == 7200.0

    def test_validation_positive(self):
        """测试验证（必须为正数）"""
        with pytest.raises(ValueError):
            TimeoutConfig(single_command=0)

        with pytest.raises(ValueError):
            TimeoutConfig(single_command=-1)

    def test_from_settings(self):
        """测试从 GateFlowSettings 获取"""
        settings = GateFlowSettings(
            timeout_single_command=60.0,
            timeout_batch_total=7200.0,
        )
        config = settings.get_timeout_config()

        assert config.single_command == 60.0
        assert config.batch_total == 7200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
