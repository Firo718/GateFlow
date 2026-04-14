"""
TCP 协议解析测试

测试 TCP_PROTOCOL.md 规范中定义的协议解析逻辑。
"""

import pytest
from gateflow.vivado.tcp_client import VivadoTcpClient, TclResponse


class TestPromptPattern:
    """测试提示符识别"""

    def test_prompt_percent(self):
        """测试 % 提示符"""
        client = VivadoTcpClient()
        # 提示符应该在行首
        assert client.PROMPT_PATTERN.match("% ")
        assert client.PROMPT_PATTERN.match("%")
        # 不应该匹配非提示符文本
        assert not client.PROMPT_PATTERN.match("OK: result")
        # 带前导空格的不是有效提示符（因为 ^ 锚点）
        assert not client.PROMPT_PATTERN.match(" % ")

    def test_prompt_hash(self):
        """测试 # 提示符（兼容性）"""
        client = VivadoTcpClient()
        # 提示符应该在行首
        assert client.PROMPT_PATTERN.match("# ")
        assert client.PROMPT_PATTERN.match("#")
        # 带前导空格的不是有效提示符（因为 ^ 锚点）
        assert not client.PROMPT_PATTERN.match(" # ")

    def test_prompt_in_multiline(self):
        """测试多行文本中的提示符识别"""
        client = VivadoTcpClient()
        text = "OK: result\n% \n"
        matches = list(client.PROMPT_PATTERN.finditer(text))
        assert len(matches) == 1
        assert matches[0].group(0).strip() == "%"


class TestResponseParsing:
    """测试响应解析"""

    def test_simple_ok_response(self):
        """测试简单的 OK 响应"""
        client = VivadoTcpClient()
        raw = "OK: my_project\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == "my_project"
        assert response.error is None
        assert len(response.warnings) == 0

    def test_simple_error_response(self):
        """测试简单的 ERROR 响应"""
        client = VivadoTcpClient()
        raw = "ERROR: invalid command name \"unknown_cmd\"\n"
        response = client._parse_response(raw)

        assert response.success is False
        assert response.error is not None
        assert "invalid command name" in response.error

    def test_empty_ok_response(self):
        """测试空的 OK 响应"""
        client = VivadoTcpClient()
        raw = "OK:\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == ""

    def test_multiline_response(self):
        """测试多行响应"""
        client = VivadoTcpClient()
        raw = "clk_wiz_0\naxi_gpio_0\naxi_uart_0\nOK: 3 IPs found\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert "clk_wiz_0" in response.result
        assert "axi_gpio_0" in response.result
        assert "axi_uart_0" in response.result

    def test_response_with_warning(self):
        """测试带警告的响应"""
        client = VivadoTcpClient()
        raw = "WARNING: Project directory already exists\nOK: my_project\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == "my_project"
        assert len(response.warnings) == 1
        assert "Project directory already exists" in response.warnings[0]

    def test_response_with_multiple_warnings(self):
        """测试带多个警告的响应"""
        client = VivadoTcpClient()
        raw = "WARNING: Warning 1\nWARNING: Warning 2\nOK: result\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert len(response.warnings) == 2
        assert "Warning 1" in response.warnings[0]
        assert "Warning 2" in response.warnings[1]

    def test_error_with_invalid_command(self):
        """测试无效命令错误"""
        client = VivadoTcpClient()
        raw = "ERROR: invalid command name \"unknown_cmd\"\n"
        response = client._parse_response(raw)

        assert response.success is False
        assert "invalid command name" in response.error

    def test_error_with_wrong_args(self):
        """测试参数错误"""
        client = VivadoTcpClient()
        raw = "ERROR: wrong # args: should be \"create_project name path\"\n"
        response = client._parse_response(raw)

        assert response.success is False
        assert "wrong # args" in response.error

    def test_chinese_characters(self):
        """测试中文字符"""
        client = VivadoTcpClient()
        raw = "OK: 项目创建成功\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert "项目创建成功" in response.result

    def test_multiline_with_error(self):
        """测试多行输出后跟错误"""
        client = VivadoTcpClient()
        raw = "Processing IP 1\nProcessing IP 2\nERROR: Failed to process IP 3\n"
        response = client._parse_response(raw)

        assert response.success is False
        assert "Failed to process IP 3" in response.error
        assert "Processing IP 1" in response.result
        assert "Processing IP 2" in response.result


class TestOkPattern:
    """测试 OK 响应模式"""

    def test_ok_with_result(self):
        """测试带结果的 OK"""
        client = VivadoTcpClient()
        match = client.OK_PATTERN.search("OK: my_result\n")
        assert match is not None
        assert match.group(1) == "my_result"

    def test_ok_empty(self):
        """测试空 OK"""
        client = VivadoTcpClient()
        match = client.OK_PATTERN.search("OK:\n")
        assert match is not None
        assert match.group(1) == ""

    def test_ok_with_spaces(self):
        """测试带空格的 OK"""
        client = VivadoTcpClient()
        match = client.OK_PATTERN.search("OK:   result with spaces  \n")
        assert match is not None
        assert "result with spaces" in match.group(1)


class TestErrorPatterns:
    """测试错误模式"""

    def test_error_pattern_1(self):
        """测试标准 ERROR 模式"""
        client = VivadoTcpClient()
        match = client.ERROR_PATTERNS[0].search("ERROR: some error\n")
        assert match is not None
        assert "some error" in match.group(1)

    def test_error_pattern_invalid_command(self):
        """测试无效命令模式"""
        client = VivadoTcpClient()
        match = client.ERROR_PATTERNS[1].search('invalid command name "bad_cmd"\n')
        assert match is not None
        assert match.group(1) == "bad_cmd"

    def test_error_pattern_wrong_args(self):
        """测试参数错误模式"""
        client = VivadoTcpClient()
        match = client.ERROR_PATTERNS[2].search("wrong # args: should be something\n")
        assert match is not None


class TestWarningPattern:
    """测试警告模式"""

    def test_warning_extraction(self):
        """测试警告提取"""
        client = VivadoTcpClient()
        text = "WARNING: This is a warning\nOK: result\n"
        matches = list(client.WARNING_PATTERN.finditer(text))

        assert len(matches) == 1
        assert matches[0].group(1) == "This is a warning"

    def test_multiple_warnings(self):
        """测试多个警告"""
        client = VivadoTcpClient()
        text = "WARNING: Warning 1\nWARNING: Warning 2\nOK: result\n"
        matches = list(client.WARNING_PATTERN.finditer(text))

        assert len(matches) == 2
        assert matches[0].group(1) == "Warning 1"
        assert matches[1].group(1) == "Warning 2"


class TestProtocolCompliance:
    """测试协议合规性"""

    def test_protocol_example_1(self):
        """测试协议文档示例 1: 简单命令"""
        client = VivadoTcpClient()
        # 服务器响应: OK: Hello Vivado\n% \n
        raw = "OK: Hello Vivado\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == "Hello Vivado"

    def test_protocol_example_2(self):
        """测试协议文档示例 2: 获取项目信息"""
        client = VivadoTcpClient()
        raw = "OK: my_project\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == "my_project"

    def test_protocol_example_3(self):
        """测试协议文档示例 3: 错误命令"""
        client = VivadoTcpClient()
        raw = "ERROR: invalid command name \"unknown_command\"\n"
        response = client._parse_response(raw)

        assert response.success is False
        assert "invalid command name" in response.error

    def test_protocol_example_4(self):
        """测试协议文档示例 4: 多行输出"""
        client = VivadoTcpClient()
        raw = "clk_wiz_0\naxi_gpio_0\naxi_uart_0\nOK: 3 IPs found\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert "clk_wiz_0" in response.result
        assert "axi_gpio_0" in response.result
        assert "axi_uart_0" in response.result

    def test_protocol_example_5(self):
        """测试协议文档示例 5: 带警告的命令"""
        client = VivadoTcpClient()
        raw = "WARNING: Project directory already exists\nOK: my_project\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == "my_project"
        assert len(response.warnings) == 1
        assert "Project directory already exists" in response.warnings[0]


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_response(self):
        """测试空响应"""
        client = VivadoTcpClient()
        raw = ""
        response = client._parse_response(raw)

        assert response.success is True
        assert response.result == ""

    def test_only_newlines(self):
        """测试仅包含换行符"""
        client = VivadoTcpClient()
        raw = "\n\n\n"
        response = client._parse_response(raw)

        assert response.success is True

    def test_result_with_newlines(self):
        """测试结果中包含换行符"""
        client = VivadoTcpClient()
        raw = "line1\nline2\nline3\nOK: success\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert "line1" in response.result
        assert "line2" in response.result
        assert "line3" in response.result

    def test_special_characters(self):
        """测试特殊字符"""
        client = VivadoTcpClient()
        raw = "OK: result with $pecial ch@r@cters! #%^&*\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert "$pecial ch@r@cters!" in response.result

    def test_very_long_response(self):
        """测试超长响应"""
        client = VivadoTcpClient()
        long_text = "x" * 10000
        raw = f"OK: {long_text}\n"
        response = client._parse_response(raw)

        assert response.success is True
        assert len(response.result) == 10000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
