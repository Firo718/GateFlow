"""
协议一致性验证脚本

验证 TCP_PROTOCOL.md 规范与实现的一致性。
"""

import re
from pathlib import Path

from gateflow.vivado.tcp_client import VivadoTcpClient


def check_server_script_compliance():
    """检查服务器脚本是否符合协议规范"""
    print("=" * 60)
    print("检查服务器脚本合规性")
    print("=" * 60)
    
    # 读取服务器脚本模板（从 tcl_server.py）
    server_script_path = Path("src/gateflow/vivado/tcl_server.py")
    with open(server_script_path, encoding="utf-8") as f:
        content = f.read()
    
    checks = []
    
    # 检查 1: 协议版本标识
    if "::gateflow_protocol_version" in content:
        checks.append(("✓", "协议版本标识已定义"))
    else:
        checks.append(("✗", "缺少协议版本标识"))
    
    # 检查 2: UTF-8 编码
    if "encoding system utf-8" in content:
        checks.append(("✓", "UTF-8 编码已设置"))
    else:
        checks.append(("✗", "缺少 UTF-8 编码设置"))
    
    # 检查 3: OK 响应格式
    if 'set response "OK:' in content:
        checks.append(("✓", "OK 响应格式正确"))
    else:
        checks.append(("✗", "OK 响应格式不符合规范"))
    
    # 检查 4: ERROR 响应格式
    if 'set response "ERROR:' in content:
        checks.append(("✓", "ERROR 响应格式正确"))
    else:
        checks.append(("✗", "ERROR 响应格式不符合规范"))
    
    # 检查 5: 提示符格式
    if 'puts $channel "% "' in content:
        checks.append(("✓", "提示符格式正确 (% \\n)"))
    else:
        checks.append(("✗", "提示符格式不符合规范"))
    
    # 检查 6: 命令执行使用 uplevel
    if "uplevel #0" in content:
        checks.append(("✓", "使用 uplevel #0 执行命令"))
    else:
        checks.append(("✗", "未使用 uplevel #0 执行命令"))
    
    # 检查 7: 空命令处理
    if "string trim" in content and '$line eq ""' in content:
        checks.append(("✓", "正确处理空命令"))
    else:
        checks.append(("✗", "空命令处理不完善"))
    
    # 检查 8: UTF-8 编码配置
    if "-encoding utf-8" in content:
        checks.append(("✓", "通道编码设置为 UTF-8"))
    else:
        checks.append(("✗", "未设置通道编码"))
    
    # 输出结果
    for status, message in checks:
        print(f"  {status} {message}")
    
    # 统计
    passed = sum(1 for status, _ in checks if status == "✓")
    total = len(checks)
    print(f"\n合规性: {passed}/{total} 项通过")
    
    return passed == total


def check_client_compliance():
    """检查客户端解析是否符合协议规范"""
    print("\n" + "=" * 60)
    print("检查客户端解析合规性")
    print("=" * 60)
    
    client = VivadoTcpClient()
    checks = []
    
    # 检查 1: 提示符模式
    prompt_pattern = client.PROMPT_PATTERN.pattern
    if "[%#]" in prompt_pattern and r"\s*$" in prompt_pattern:
        checks.append(("✓", "提示符模式支持 % 和 #"))
    else:
        checks.append(("✗", "提示符模式不符合规范"))
    
    # 检查 2: OK 响应模式
    if hasattr(client, "OK_PATTERN"):
        ok_pattern = client.OK_PATTERN.pattern
        if r"^OK:" in ok_pattern:
            checks.append(("✓", "OK 响应模式已定义"))
        else:
            checks.append(("✗", "OK 响应模式不符合规范"))
    else:
        checks.append(("✗", "缺少 OK 响应模式"))
    
    # 检查 3: ERROR 响应模式
    if hasattr(client, "ERROR_PATTERNS") and len(client.ERROR_PATTERNS) > 0:
        error_pattern = client.ERROR_PATTERNS[0].pattern
        if r"^ERROR:" in error_pattern:
            checks.append(("✓", "ERROR 响应模式已定义"))
        else:
            checks.append(("✗", "ERROR 响应模式不符合规范"))
    else:
        checks.append(("✗", "缺少 ERROR 响应模式"))
    
    # 检查 4: WARNING 模式
    if hasattr(client, "WARNING_PATTERN"):
        warning_pattern = client.WARNING_PATTERN.pattern
        if r"^WARNING:" in warning_pattern:
            checks.append(("✓", "WARNING 模式已定义"))
        else:
            checks.append(("✗", "WARNING 模式不符合规范"))
    else:
        checks.append(("✗", "缺少 WARNING 模式"))
    
    # 检查 5: 响应解析函数
    if hasattr(client, "_parse_response"):
        checks.append(("✓", "响应解析函数已实现"))
    else:
        checks.append(("✗", "缺少响应解析函数"))
    
    # 输出结果
    for status, message in checks:
        print(f"  {status} {message}")
    
    # 统计
    passed = sum(1 for status, _ in checks if status == "✓")
    total = len(checks)
    print(f"\n合规性: {passed}/{total} 项通过")
    
    return passed == total


def check_protocol_examples():
    """检查协议文档中的示例是否能正确解析"""
    print("\n" + "=" * 60)
    print("检查协议示例解析")
    print("=" * 60)
    
    client = VivadoTcpClient()
    examples = [
        ("示例 1: 简单命令", "OK: Hello Vivado\n", True, "Hello Vivado"),
        ("示例 2: 获取项目信息", "OK: my_project\n", True, "my_project"),
        ("示例 3: 错误命令", "ERROR: invalid command name \"unknown_command\"\n", False, None),
        ("示例 4: 多行输出", "clk_wiz_0\naxi_gpio_0\naxi_uart_0\nOK: 3 IPs found\n", True, None),
        ("示例 5: 带警告的命令", "WARNING: Project directory already exists\nOK: my_project\n", True, "my_project"),
    ]
    
    checks = []
    for name, raw, expected_success, expected_result in examples:
        response = client._parse_response(raw)
        
        if response.success == expected_success:
            if expected_result is None or expected_result in response.result:
                checks.append(("✓", f"{name} - 解析正确"))
            else:
                checks.append(("✗", f"{name} - 结果不匹配: 期望 '{expected_result}', 实际 '{response.result}'"))
        else:
            checks.append(("✗", f"{name} - 成功状态不匹配: 期望 {expected_success}, 实际 {response.success}"))
    
    # 输出结果
    for status, message in checks:
        print(f"  {status} {message}")
    
    # 统计
    passed = sum(1 for status, _ in checks if status == "✓")
    total = len(checks)
    print(f"\n合规性: {passed}/{total} 项通过")
    
    return passed == total


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("TCP 协议一致性验证")
    print("=" * 60)
    print()
    
    # 检查服务器脚本
    server_ok = check_server_script_compliance()
    
    # 检查客户端解析
    client_ok = check_client_compliance()
    
    # 检查协议示例
    examples_ok = check_protocol_examples()
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    if server_ok and client_ok and examples_ok:
        print("✓ 所有检查通过，协议实现与文档一致")
        return 0
    else:
        print("✗ 存在不符合规范的项，请检查上述详细信息")
        return 1


if __name__ == "__main__":
    exit(main())
