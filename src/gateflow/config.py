"""
GateFlow 配置模块

定义全局配置类，包括超时配置、连接配置等。

注意：此模块已重构，配置现在由 gateflow.settings 模块统一管理。
为了向后兼容，TimeoutConfig 和 DEFAULT_TIMEOUT_CONFIG 仍然从这里导出。

推荐使用方式：
    >>> from gateflow.settings import get_settings
    >>> settings = get_settings()
    >>> timeout_config = settings.get_timeout_config()

兼容旧代码：
    >>> from gateflow.config import TimeoutConfig, DEFAULT_TIMEOUT_CONFIG
"""

# 从 settings 模块导入，保持向后兼容
from gateflow.settings import DEFAULT_TIMEOUT_CONFIG, TimeoutConfig

__all__ = ["TimeoutConfig", "DEFAULT_TIMEOUT_CONFIG"]
