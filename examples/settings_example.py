"""
GateFlow 统一配置系统使用示例

演示如何使用 pydantic-settings 管理配置，支持多种配置来源：
1. CLI 参数（构造函数参数，最高优先级）
2. 环境变量（前缀 GATEFLOW_）
3. .env 文件
4. 配置文件 ~/.gateflow/config.json
5. 默认值
"""

from gateflow.settings import GateFlowSettings, get_settings


def example_default_config():
    """示例 1: 使用默认配置"""
    print("=" * 60)
    print("示例 1: 使用默认配置")
    print("=" * 60)
    
    settings = GateFlowSettings()
    
    print(f"TCP 主机: {settings.tcp_host}")
    print(f"TCP 端口: {settings.tcp_port}")
    print(f"日志级别: {settings.log_level}")
    print(f"Tcl 策略: {settings.tcl_policy}")
    print(f"单命令超时: {settings.timeout_single_command}秒")
    print(f"批量总超时: {settings.timeout_batch_total}秒")
    print()


def example_cli_override():
    """示例 2: 使用 CLI 参数覆盖配置"""
    print("=" * 60)
    print("示例 2: 使用 CLI 参数覆盖配置")
    print("=" * 60)
    
    # 模拟 CLI 参数覆盖
    settings = GateFlowSettings(
        tcp_port=8888,
        log_level="DEBUG",
        timeout_single_command=60.0,
    )
    
    print(f"TCP 端口: {settings.tcp_port} (覆盖为 8888)")
    print(f"日志级别: {settings.log_level} (覆盖为 DEBUG)")
    print(f"单命令超时: {settings.timeout_single_command}秒 (覆盖为 60)")
    print()


def example_env_override():
    """示例 3: 使用环境变量覆盖配置"""
    import os
    
    print("=" * 60)
    print("示例 3: 使用环境变量覆盖配置")
    print("=" * 60)
    
    # 设置环境变量
    os.environ["GATEFLOW_TCP_PORT"] = "7777"
    os.environ["GATEFLOW_LOG_LEVEL"] = "WARNING"
    
    # 创建新的配置实例（会读取环境变量）
    settings = GateFlowSettings()
    
    print(f"TCP 端口: {settings.tcp_port} (环境变量覆盖为 7777)")
    print(f"日志级别: {settings.log_level} (环境变量覆盖为 WARNING)")
    print()
    
    # 清理环境变量
    del os.environ["GATEFLOW_TCP_PORT"]
    del os.environ["GATEFLOW_LOG_LEVEL"]


def example_global_settings():
    """示例 4: 使用全局配置实例"""
    print("=" * 60)
    print("示例 4: 使用全局配置实例")
    print("=" * 60)
    
    # 获取全局配置实例
    settings1 = get_settings()
    settings2 = get_settings()
    
    print(f"settings1 is settings2: {settings1 is settings2}")
    print(f"全局配置 TCP 端口: {settings1.tcp_port}")
    print()
    
    # 使用参数覆盖全局配置
    settings3 = get_settings(tcp_port=9999, log_level="ERROR")
    print(f"覆盖后的 TCP 端口: {settings3.tcp_port}")
    print(f"覆盖后的日志级别: {settings3.log_level}")
    print()


def example_compatible_apis():
    """示例 5: 使用兼容 API"""
    print("=" * 60)
    print("示例 5: 使用兼容 API（向后兼容旧代码）")
    print("=" * 60)
    
    settings = GateFlowSettings(
        timeout_single_command=60.0,
        timeout_batch_total=7200.0,
        tcp_host="192.168.1.100",
        tcp_port=8888,
    )
    
    # 获取超时配置（兼容旧代码）
    timeout_config = settings.get_timeout_config()
    print(f"TimeoutConfig.single_command: {timeout_config.single_command}")
    print(f"TimeoutConfig.batch_total: {timeout_config.batch_total}")
    
    # 获取 TCP 配置（兼容旧代码）
    tcp_config = settings.get_tcp_config()
    print(f"TcpConfig.host: {tcp_config.host}")
    print(f"TcpConfig.port: {tcp_config.port}")
    print()


def example_save_config():
    """示例 6: 保存配置到文件"""
    print("=" * 60)
    print("示例 6: 保存配置到文件")
    print("=" * 60)
    
    settings = GateFlowSettings(
        tcp_port=8888,
        log_level="DEBUG",
    )
    
    # 保存到 ~/.gateflow/config.json
    # settings.to_config_file()
    print("配置可以保存到 ~/.gateflow/config.json")
    print("使用 settings.to_config_file() 方法")
    print()


if __name__ == "__main__":
    example_default_config()
    example_cli_override()
    example_env_override()
    example_global_settings()
    example_compatible_apis()
    example_save_config()
    
    print("=" * 60)
    print("所有示例完成！")
    print("=" * 60)
