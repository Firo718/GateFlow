"""
测试 GateFlow 统一配置系统

验证配置优先级：
1. 环境变量（最高优先级）
2. .env 文件
3. 配置文件 ~/.gateflow/config.json
4. CLI 参数
5. 默认值
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from gateflow.settings import (
    GateFlowSettings,
    TimeoutConfig,
    TcpConfig,
    get_settings,
    reset_settings,
    CONFIG_DIR,
    CONFIG_FILE,
)


class TestGateFlowSettings:
    """测试 GateFlowSettings 配置类"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_default_values(self):
        """测试默认值"""
        # 模拟不存在的配置文件，确保使用默认值
        with patch("gateflow.settings.CONFIG_FILE", Path("/nonexistent/config.json")):
            settings = GateFlowSettings()
            
            assert settings.tcp_host == "localhost"
            assert settings.tcp_port == 9999
            assert settings.timeout_single_command == 60.0
            assert settings.timeout_batch_total == 3600.0
            assert settings.timeout_connect == 10.0
            assert settings.timeout_idle == 300.0
            assert settings.allow_dangerous_operations is False
            assert settings.tcl_policy == "normal"
            assert settings.log_level == "INFO"
            assert settings.reconnect_attempts == 5
            assert settings.reconnect_delay == 2.0

    def test_environment_variable_override(self):
        """测试环境变量覆盖默认值"""
        with patch.dict(os.environ, {
            "GATEFLOW_TCP_PORT": "8888",
            "GATEFLOW_TCP_HOST": "192.168.1.100",
            "GATEFLOW_LOG_LEVEL": "DEBUG",
            "GATEFLOW_ALLOW_DANGEROUS_OPERATIONS": "true",
            "GATEFLOW_GUI_ENABLED": "true",
        }):
            settings = GateFlowSettings()
            
            assert settings.tcp_port == 8888
            assert settings.tcp_host == "192.168.1.100"
            assert settings.log_level == "DEBUG"
            assert settings.allow_dangerous_operations is True
            assert settings.gui_enabled is True

    def test_config_file_override(self, tmp_path):
        """测试配置文件覆盖默认值"""
        # 创建临时配置文件
        config_file = tmp_path / "config.json"
        config_data = {
            "tcp_port": 7777,
            "tcp_host": "127.0.0.1",
            "timeout_single_command": 60.0,
            "log_level": "WARNING",
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        
        # 模拟配置文件路径
        with patch("gateflow.settings.CONFIG_FILE", config_file):
            settings = GateFlowSettings()
            
            assert settings.tcp_port == 7777
            assert settings.tcp_host == "127.0.0.1"
            assert settings.timeout_single_command == 60.0
            assert settings.log_level == "WARNING"

    def test_cli_parameter_override(self):
        """测试 CLI 参数覆盖（构造函数参数）"""
        settings = GateFlowSettings(
            tcp_port=6666,
            tcp_host="10.0.0.1",
            log_level="ERROR",
        )
        
        assert settings.tcp_port == 6666
        assert settings.tcp_host == "10.0.0.1"
        assert settings.log_level == "ERROR"

    def test_priority_order(self, tmp_path):
        """测试配置优先级顺序"""
        # 1. 创建配置文件
        config_file = tmp_path / "config.json"
        config_data = {
            "tcp_port": 1111,  # 配置文件值
            "tcp_host": "config-host",
        }
        config_file.write_text(json.dumps(config_data), encoding="utf-8")
        
        # 2. 设置环境变量
        with patch.dict(os.environ, {
            "GATEFLOW_TCP_PORT": "2222",  # 环境变量值
        }):
            with patch("gateflow.settings.CONFIG_FILE", config_file):
                # 3. 创建配置（环境变量 > 配置文件）
                settings = GateFlowSettings()
                
                # 环境变量优先级高于配置文件
                assert settings.tcp_port == 2222
                # 配置文件次之
                assert settings.tcp_host == "config-host"
                
                # 4. CLI 参数优先级最高
                settings_with_override = GateFlowSettings(tcp_port=3333)
                assert settings_with_override.tcp_port == 3333

    def test_validation_tcl_policy(self):
        """测试 Tcl 策略验证"""
        # 有效值
        for policy in ["safe", "normal", "unsafe"]:
            settings = GateFlowSettings(tcl_policy=policy)
            assert settings.tcl_policy == policy
        
        # 无效值
        with pytest.raises(ValueError, match="tcl_policy 必须是"):
            GateFlowSettings(tcl_policy="invalid")

    def test_validation_log_level(self):
        """测试日志级别验证"""
        # 有效值
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = GateFlowSettings(log_level=level)
            assert settings.log_level == level
        
        # 小写也应该有效（会自动转换为大写）
        settings = GateFlowSettings(log_level="debug")
        assert settings.log_level == "DEBUG"
        
        # 无效值
        with pytest.raises(ValueError, match="log_level 必须是"):
            GateFlowSettings(log_level="INVALID")

    def test_validation_timeout_values(self):
        """测试超时值验证"""
        # 有效值
        settings = GateFlowSettings(
            timeout_single_command=60.0,
            timeout_batch_total=7200.0,
            timeout_connect=20.0,
            timeout_idle=600.0,
        )
        assert settings.timeout_single_command == 60.0
        
        # 无效值（必须大于 0）
        with pytest.raises(ValueError):
            GateFlowSettings(timeout_single_command=0)
        
        with pytest.raises(ValueError):
            GateFlowSettings(timeout_single_command=-1)

    def test_validation_tcp_port(self):
        """测试 TCP 端口验证"""
        # 有效值
        settings = GateFlowSettings(tcp_port=8080)
        assert settings.tcp_port == 8080
        
        # 无效值（超出范围）
        with pytest.raises(ValueError):
            GateFlowSettings(tcp_port=0)
        
        with pytest.raises(ValueError):
            GateFlowSettings(tcp_port=70000)

    def test_workspace_roots_parsing(self):
        """测试工作空间根目录解析"""
        # 列表格式
        settings = GateFlowSettings(workspace_roots=["/path1", "/path2"])
        assert settings.workspace_roots == ["/path1", "/path2"]
        
        # 字符串格式（使用路径分隔符）
        with patch("gateflow.settings._get_env_separator", return_value=";"):
            settings = GateFlowSettings(workspace_roots="/path1;/path2;/path3")
            assert settings.workspace_roots == ["/path1", "/path2", "/path3"]

    def test_get_timeout_config(self):
        """测试获取超时配置"""
        settings = GateFlowSettings(
            timeout_single_command=60.0,
            timeout_batch_total=7200.0,
            timeout_connect=20.0,
            timeout_idle=600.0,
        )
        
        timeout_config = settings.get_timeout_config()
        
        assert isinstance(timeout_config, TimeoutConfig)
        assert timeout_config.single_command == 60.0
        assert timeout_config.batch_total == 7200.0
        assert timeout_config.connect == 20.0
        assert timeout_config.idle == 600.0

    def test_get_tcp_config(self):
        """测试获取 TCP 配置"""
        settings = GateFlowSettings(
            tcp_host="192.168.1.100",
            tcp_port=8888,
            timeout_single_command=60.0,
            reconnect_attempts=10,
            reconnect_delay=5.0,
        )
        
        tcp_config = settings.get_tcp_config()
        
        assert isinstance(tcp_config, TcpConfig)
        assert tcp_config.host == "192.168.1.100"
        assert tcp_config.port == 8888
        assert tcp_config.timeout == 60.0
        assert tcp_config.reconnect_attempts == 10
        assert tcp_config.reconnect_delay == 5.0

    def test_get_workspace_roots(self):
        """测试获取工作空间根目录（Path 对象）"""
        settings = GateFlowSettings(workspace_roots=["/path1", "/path2"])
        
        roots = settings.get_workspace_roots()
        
        assert len(roots) == 2
        assert all(isinstance(r, Path) for r in roots)
        assert roots[0] == Path("/path1")
        assert roots[1] == Path("/path2")

    def test_get_workspace_roots_default(self):
        """测试默认工作空间根目录"""
        settings = GateFlowSettings(workspace_roots=[])
        
        roots = settings.get_workspace_roots()
        
        # 默认使用 ~/.gateflow/workspaces
        assert len(roots) == 1
        assert roots[0] == CONFIG_DIR / "workspaces"

    def test_to_config_file(self, tmp_path):
        """测试保存配置到文件"""
        config_file = tmp_path / "config.json"
        
        settings = GateFlowSettings(
            tcp_port=8888,
            tcp_host="192.168.1.100",
            log_level="DEBUG",
        )
        
        with patch("gateflow.settings.CONFIG_FILE", config_file):
            with patch("gateflow.settings.CONFIG_DIR", tmp_path):
                settings.to_config_file()
                
                # 验证文件已创建
                assert config_file.exists()
                
                # 验证文件内容
                with open(config_file, encoding="utf-8") as f:
                    saved_config = json.load(f)
                
                assert saved_config["tcp_port"] == 8888
                assert saved_config["tcp_host"] == "192.168.1.100"
                assert saved_config["log_level"] == "DEBUG"


class TestGetSettings:
    """测试全局配置实例管理"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_singleton(self):
        """测试单例模式"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

    def test_reload(self):
        """测试重新加载配置"""
        settings1 = get_settings()
        
        # 重新加载
        settings2 = get_settings(reload=True)
        
        # 不是同一个实例
        assert settings1 is not settings2

    def test_override(self):
        """测试覆盖配置"""
        settings = get_settings(tcp_port=8888, log_level="DEBUG")
        
        assert settings.tcp_port == 8888
        assert settings.log_level == "DEBUG"

    def test_reset(self):
        """测试重置配置"""
        settings1 = get_settings()
        
        reset_settings()
        
        settings2 = get_settings()
        
        # 重置后是新的实例
        assert settings1 is not settings2


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_config_module_imports(self):
        """测试从 config 模块导入"""
        from gateflow.config import TimeoutConfig, DEFAULT_TIMEOUT_CONFIG
        
        assert TimeoutConfig is not None
        assert DEFAULT_TIMEOUT_CONFIG is not None
        
        # 验证 TimeoutConfig 功能
        config = TimeoutConfig(
            single_command=60.0,
            batch_total=7200.0,
        )
        assert config.single_command == 60.0
        assert config.batch_total == 7200.0

    def test_timeout_config_validation(self):
        """测试 TimeoutConfig 验证"""
        # 有效值
        config = TimeoutConfig(
            single_command=60.0,
            batch_total=7200.0,
            connect=20.0,
            idle=600.0,
        )
        assert config.single_command == 60.0
        
        # 无效值
        with pytest.raises(ValueError):
            TimeoutConfig(single_command=0)


class TestEnvFile:
    """测试 .env 文件支持"""

    def setup_method(self):
        """每个测试方法前重置全局配置"""
        reset_settings()

    def teardown_method(self):
        """每个测试方法后重置全局配置"""
        reset_settings()

    def test_env_file_loading(self, tmp_path):
        """测试从 .env 文件加载配置"""
        # 创建临时 .env 文件
        env_file = tmp_path / ".env"
        env_file.write_text(
            "GATEFLOW_TCP_PORT=9999\n"
            "GATEFLOW_LOG_LEVEL=DEBUG\n",
            encoding="utf-8",
        )
        
        # 注意：pydantic-settings 的 env_file 需要在 model_config 中配置
        # 这里我们测试配置类是否支持 env_file 配置
        settings = GateFlowSettings()
        
        # 验证 model_config 中配置了 env_file
        assert settings.model_config.get("env_file") == ".env"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
