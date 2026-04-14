"""
Tcl 执行工具安全策略测试。

测试 TclPolicy 策略分级和命令检测功能。
"""

import pytest

from gateflow.tools.tcl_tools import (
    TclPolicy,
    PolicyCheckResult,
    check_tcl_policy,
    _extract_commands,
    _is_command_allowed,
    _check_dangerous_patterns,
    SAFE_COMMANDS,
    NORMAL_COMMANDS,
    DANGEROUS_PATTERNS,
)


class TestTclPolicy:
    """测试 TclPolicy 枚举"""

    def test_policy_values(self):
        """测试策略值"""
        assert TclPolicy.SAFE.value == "safe"
        assert TclPolicy.NORMAL.value == "normal"
        assert TclPolicy.UNSAFE.value == "unsafe"

    def test_policy_count(self):
        """测试策略数量"""
        assert len(TclPolicy) == 3


class TestExtractCommands:
    """测试命令提取"""

    def test_single_command(self):
        """测试单行命令"""
        commands = _extract_commands("puts Hello")
        assert len(commands) == 1
        assert commands[0] == "puts Hello"

    def test_multiple_commands_newline(self):
        """测试多行命令（换行分隔）"""
        script = """
        puts Hello
        puts World
        """
        commands = _extract_commands(script)
        assert len(commands) == 2
        assert "puts Hello" in commands[0]
        assert "puts World" in commands[1]

    def test_multiple_commands_semicolon(self):
        """测试多命令（分号分隔）"""
        commands = _extract_commands("puts Hello; puts World")
        assert len(commands) == 2

    def test_remove_comments(self):
        """测试移除注释"""
        script = """
        # This is a comment
        puts Hello
        # Another comment
        """
        commands = _extract_commands(script)
        assert len(commands) == 1
        assert "puts Hello" in commands[0]

    def test_inline_comment(self):
        """测试行内注释"""
        commands = _extract_commands("puts Hello # inline comment")
        assert len(commands) == 1
        assert "#" not in commands[0]


class TestIsCommandAllowed:
    """测试命令白名单检查"""

    def test_safe_command_puts(self):
        """测试 SAFE 级别允许 puts"""
        assert _is_command_allowed("puts Hello", SAFE_COMMANDS) is True

    def test_safe_command_get(self):
        """测试 SAFE 级别允许 get_* 命令"""
        assert _is_command_allowed("get_projects", SAFE_COMMANDS) is True
        assert _is_command_allowed("get_property NAME", SAFE_COMMANDS) is True

    def test_safe_command_list(self):
        """测试 SAFE 级别允许 list_* 命令"""
        assert _is_command_allowed("list_ips", SAFE_COMMANDS) is True

    def test_safe_command_version(self):
        """测试 SAFE 级别允许 version"""
        assert _is_command_allowed("version", SAFE_COMMANDS) is True

    def test_safe_command_info(self):
        """测试 SAFE 级别允许 info"""
        assert _is_command_allowed("info vars", SAFE_COMMANDS) is True

    def test_safe_command_expr(self):
        """测试 SAFE 级别允许 expr"""
        assert _is_command_allowed("expr {1 + 2}", SAFE_COMMANDS) is True

    def test_safe_command_file_readonly(self):
        """测试 SAFE 级别允许只读 file 操作"""
        assert _is_command_allowed("file exists test.txt", SAFE_COMMANDS) is True
        assert _is_command_allowed("file readable test.txt", SAFE_COMMANDS) is True

    def test_safe_command_create_rejected(self):
        """测试 SAFE 级别拒绝 create_* 命令"""
        assert _is_command_allowed("create_project my_proj", SAFE_COMMANDS) is False

    def test_normal_command_create(self):
        """测试 NORMAL 级别允许 create_* 命令"""
        assert _is_command_allowed("create_project my_proj", NORMAL_COMMANDS) is True

    def test_normal_command_synth(self):
        """测试 NORMAL 级别允许 synth_design"""
        assert _is_command_allowed("synth_design", NORMAL_COMMANDS) is True

    def test_normal_command_add_files(self):
        """测试 NORMAL 级别允许 add_files"""
        assert _is_command_allowed("add_files top.v", NORMAL_COMMANDS) is True


class TestDangerousPatterns:
    """测试危险命令检测"""

    def test_exec_command(self):
        """测试检测 exec 命令"""
        violations = _check_dangerous_patterns("exec rm -rf /")
        assert len(violations) == 1
        assert "exec" in violations[0]

    def test_file_delete(self):
        """测试检测 file delete"""
        violations = _check_dangerous_patterns("file delete my_file")
        assert len(violations) == 1
        assert "file" in violations[0] and "delete" in violations[0]

    def test_exit_command(self):
        """测试检测 exit 命令"""
        violations = _check_dangerous_patterns("exit")
        assert len(violations) == 1
        assert "exit" in violations[0]

    def test_shutdown_command(self):
        """测试检测 shutdown 命令"""
        violations = _check_dangerous_patterns("shutdown")
        assert len(violations) == 1
        assert "shutdown" in violations[0]

    def test_system_command(self):
        """测试检测 system 命令"""
        violations = _check_dangerous_patterns("system ls")
        assert len(violations) == 1
        assert "system" in violations[0]

    def test_socket_command(self):
        """测试检测 socket 命令"""
        violations = _check_dangerous_patterns("socket -server handler 8080")
        assert len(violations) == 1
        assert "socket" in violations[0]

    def test_safe_command_no_violation(self):
        """测试安全命令无违规"""
        violations = _check_dangerous_patterns("puts Hello")
        assert len(violations) == 0

    def test_multiple_dangerous_commands(self):
        """测试多个危险命令"""
        script = """
        exec ls
        file delete test.txt
        exit
        """
        violations = _check_dangerous_patterns(script)
        assert len(violations) >= 2


class TestCheckTclPolicy:
    """测试策略检查"""

    def test_safe_policy_allows_puts(self):
        """测试 SAFE 策略允许 puts"""
        result = check_tcl_policy("puts Hello", TclPolicy.SAFE)
        assert result.allowed is True
        assert len(result.violations) == 0

    def test_safe_policy_allows_get_commands(self):
        """测试 SAFE 策略允许 get_* 命令"""
        result = check_tcl_policy("get_projects", TclPolicy.SAFE)
        assert result.allowed is True

    def test_safe_policy_rejects_create(self):
        """测试 SAFE 策略拒绝 create_* 命令"""
        result = check_tcl_policy("create_project my_proj", TclPolicy.SAFE)
        assert result.allowed is False
        assert len(result.violations) > 0

    def test_safe_policy_rejects_dangerous(self):
        """测试 SAFE 策略拒绝危险命令"""
        result = check_tcl_policy("exec rm -rf /", TclPolicy.SAFE)
        assert result.allowed is False
        # 应该有危险命令违规
        dangerous_violations = [v for v in result.violations if "危险模式" in v]
        assert len(dangerous_violations) > 0

    def test_normal_policy_allows_create(self):
        """测试 NORMAL 策略允许 create_* 命令"""
        result = check_tcl_policy("create_project my_proj", TclPolicy.NORMAL)
        assert result.allowed is True

    def test_normal_policy_allows_synth(self):
        """测试 NORMAL 策略允许 synth_design"""
        result = check_tcl_policy("synth_design", TclPolicy.NORMAL)
        assert result.allowed is True

    def test_normal_policy_rejects_dangerous(self):
        """测试 NORMAL 策略拒绝危险命令"""
        result = check_tcl_policy("exec rm -rf /", TclPolicy.NORMAL)
        assert result.allowed is False
        dangerous_violations = [v for v in result.violations if "危险模式" in v]
        assert len(dangerous_violations) > 0

    def test_unsafe_policy_allows_normal_commands(self):
        """测试 UNSAFE 策略允许普通命令"""
        result = check_tcl_policy("create_project my_proj", TclPolicy.UNSAFE)
        assert result.allowed is True

    def test_unsafe_policy_still_checks_dangerous(self):
        """测试 UNSAFE 策略仍检查危险命令"""
        result = check_tcl_policy("exec rm -rf /", TclPolicy.UNSAFE)
        # UNSAFE 策略下，危险命令会被检测但仍标记为违规
        # 只是在实际执行时需要 allow_unsafe=True
        dangerous_violations = [v for v in result.violations if "危险模式" in v]
        assert len(dangerous_violations) > 0

    def test_multiline_script(self):
        """测试多行脚本"""
        script = """
        puts "Starting"
        get_projects
        create_project my_proj ./my_proj
        """
        # SAFE 策略应该拒绝 create_project
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is False

        # NORMAL 策略应该允许
        result = check_tcl_policy(script, TclPolicy.NORMAL)
        assert result.allowed is True

    def test_script_with_comments(self):
        """测试带注释的脚本"""
        script = """
        # This is a safe script
        puts Hello
        # Get project info
        get_projects
        """
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is True


class TestPolicyCheckResult:
    """测试策略检查结果"""

    def test_result_model(self):
        """测试结果模型"""
        result = PolicyCheckResult(
            allowed=True,
            policy=TclPolicy.NORMAL,
            violations=[],
            message="策略检查通过 (normal)",
        )
        assert result.allowed is True
        assert result.policy == TclPolicy.NORMAL
        assert len(result.violations) == 0

    def test_result_with_violations(self):
        """测试带违规的结果"""
        result = PolicyCheckResult(
            allowed=False,
            policy=TclPolicy.SAFE,
            violations=["检测到危险模式: exec"],
            message="策略检查失败 (safe): 发现 1 个违规项",
        )
        assert result.allowed is False
        assert len(result.violations) == 1


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_script(self):
        """测试空脚本"""
        result = check_tcl_policy("", TclPolicy.SAFE)
        assert result.allowed is True

    def test_whitespace_only(self):
        """测试只有空白字符"""
        result = check_tcl_policy("   \n\t   ", TclPolicy.SAFE)
        assert result.allowed is True

    def test_case_insensitive_command(self):
        """测试命令大小写不敏感"""
        # 命令检查应该是大小写不敏感的
        result = check_tcl_policy("PUTS Hello", TclPolicy.SAFE)
        assert result.allowed is True

    def test_nested_commands(self):
        """测试嵌套命令"""
        script = "puts [get_projects]"
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is True

    def test_complex_expression(self):
        """测试复杂表达式"""
        script = """
        set a 10
        set b 20
        expr {$a + $b}
        """
        result = check_tcl_policy(script, TclPolicy.SAFE)
        # set 在 SAFE 级别是允许的
        assert result.allowed is True


class TestRealWorldScenarios:
    """测试真实场景"""

    def test_project_creation_script(self):
        """测试项目创建脚本"""
        script = """
        create_project my_proj ./my_proj -part xc7z020clg400-1
        add_files {top.v top.xdc}
        set_property top top [current_fileset]
        """
        # SAFE 策略应该拒绝
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is False

        # NORMAL 策略应该允许
        result = check_tcl_policy(script, TclPolicy.NORMAL)
        assert result.allowed is True

    def test_synthesis_script(self):
        """测试综合脚本"""
        script = """
        synth_design -top top
        opt_design
        place_design
        route_design
        """
        # SAFE 策略应该拒绝
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is False

        # NORMAL 策略应该允许
        result = check_tcl_policy(script, TclPolicy.NORMAL)
        assert result.allowed is True

    def test_query_script(self):
        """测试查询脚本"""
        script = """
        get_projects
        get_property NAME [current_project]
        list_ips
        report_timing_summary
        """
        # SAFE 策略应该允许
        result = check_tcl_policy(script, TclPolicy.SAFE)
        assert result.allowed is True

    def test_dangerous_script_with_exec(self):
        """测试包含 exec 的危险脚本"""
        script = """
        create_project my_proj ./my_proj
        exec rm -rf temp
        """
        # 即使 NORMAL 策略也应该检测到危险命令
        result = check_tcl_policy(script, TclPolicy.NORMAL)
        assert result.allowed is False
        dangerous_violations = [v for v in result.violations if "危险模式" in v]
        assert len(dangerous_violations) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
