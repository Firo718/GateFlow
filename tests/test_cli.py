"""
GateFlow CLI 模块测试
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from gateflow.cli import (
    DiagnosticResult,
    EnvironmentDiagnostics,
    cmd_runs,
    cmd_status,
    create_parser,
    create_startup_script,
    main,
)


class TestCreateParser:
    """create_parser 函数测试"""

    def test_parser_creation(self):
        """测试解析器创建"""
        parser = create_parser()
        assert parser.prog == "gateflow"
        assert "MCP 服务器" in parser.description

    def test_version_argument(self, capsys):
        """测试版本参数"""
        with pytest.raises(SystemExit):
            create_parser().parse_args(["--version"])

    def test_verbose_argument(self):
        """测试详细日志参数"""
        parser = create_parser()
        args = parser.parse_args(["--verbose"])
        assert args.verbose is True

    def test_install_command(self):
        """测试 install 命令"""
        parser = create_parser()
        args = parser.parse_args(["install"])
        assert args.command == "install"
        assert args.path is None
        assert args.port is None

    def test_install_command_with_path(self):
        """测试带路径的 install 命令"""
        parser = create_parser()
        args = parser.parse_args(["install", "/path/to/vivado"])
        assert args.command == "install"
        assert args.path == "/path/to/vivado"

    def test_install_command_with_port(self):
        """测试带端口的 install 命令"""
        parser = create_parser()
        args = parser.parse_args(["install", "--port", "8888"])
        assert args.command == "install"
        assert args.port == 8888

    def test_uninstall_command(self):
        """测试 uninstall 命令"""
        parser = create_parser()
        args = parser.parse_args(["uninstall"])
        assert args.command == "uninstall"
        assert args.path is None

    def test_status_command(self):
        """测试 status 命令"""
        parser = create_parser()
        args = parser.parse_args(["status"])
        assert args.command == "status"
        assert args.port is None

    def test_status_command_with_port(self):
        """测试带端口的 status 命令"""
        parser = create_parser()
        args = parser.parse_args(["status", "--port", "8888"])
        assert args.command == "status"
        assert args.port == 8888

    def test_doctor_command(self):
        """测试 doctor 命令"""
        parser = create_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"
        assert args.port is None
        assert args.json is False

    def test_doctor_command_with_port(self):
        """测试带端口的 doctor 命令"""
        parser = create_parser()
        args = parser.parse_args(["doctor", "--port", "8888"])
        assert args.command == "doctor"
        assert args.port == 8888

    def test_doctor_command_with_json(self):
        """测试带 JSON 输出的 doctor 命令"""
        parser = create_parser()
        args = parser.parse_args(["doctor", "--json"])
        assert args.command == "doctor"
        assert args.json is True

    def test_activate_command(self):
        """测试 activate 命令"""
        parser = create_parser()
        args = parser.parse_args(["activate", "test-key"])
        assert args.command == "activate"
        assert args.key == "test-key"

    def test_capabilities_command(self):
        """测试 capabilities 命令"""
        parser = create_parser()
        args = parser.parse_args(["capabilities", "--json", "--write"])
        assert args.command == "capabilities"
        assert args.json is True
        assert args.write is True

    def test_runs_status_command(self):
        """测试 runs status 命令"""
        parser = create_parser()
        args = parser.parse_args(["runs", "status", "impl_1"])
        assert args.command == "runs"
        assert args.runs_command == "status"
        assert args.run_name == "impl_1"

    def test_runs_messages_command(self):
        """测试 runs messages 命令"""
        parser = create_parser()
        args = parser.parse_args(["runs", "messages", "impl_1", "--limit", "10", "--severity", "error"])
        assert args.command == "runs"
        assert args.runs_command == "messages"
        assert args.limit == 10
        assert args.severity == "error"

    def test_gui_open_command(self):
        """测试 gui open 命令"""
        parser = create_parser()
        args = parser.parse_args(["gui", "open", "F:/demo/demo.xpr", "--port", "10099"])
        assert args.command == "gui"
        assert args.gui_command == "open"
        assert args.xpr_path == "F:/demo/demo.xpr"
        assert args.port == 10099

    def test_gui_attach_command(self):
        """测试 gui attach 命令"""
        parser = create_parser()
        args = parser.parse_args(["gui", "attach", "--port", "10124", "F:/demo/demo.xpr"])
        assert args.command == "gui"
        assert args.gui_command == "attach"
        assert args.port == 10124
        assert args.xpr_path == "F:/demo/demo.xpr"


class TestCreateStartupScript:
    """create_startup_script 函数测试"""

    def test_script_content(self):
        """测试启动脚本内容"""
        vivado_path = Path("/path/to/vivado")
        script_path = Path("/path/to/script.tcl")
        script = create_startup_script(vivado_path, script_path, 9999)

        assert "GateFlow Tcl Server" in script
        assert str(vivado_path) in script
        assert str(script_path) in script
        assert "9999" in script
        assert "vivado -mode tcl" in script

    def test_script_port(self):
        """测试启动脚本端口"""
        vivado_path = Path("/path/to/vivado")
        script_path = Path("/path/to/script.tcl")
        script = create_startup_script(vivado_path, script_path, 8888)

        assert "8888" in script


class TestDiagnosticResult:
    """DiagnosticResult 数据类测试"""

    def test_passed_result(self):
        """测试通过的检测结果"""
        result = DiagnosticResult(
            name="测试项",
            passed=True,
            message="测试通过",
            details="详细信息",
        )
        assert result.name == "测试项"
        assert result.passed is True
        assert result.message == "测试通过"
        assert result.details == "详细信息"
        assert result.fix_suggestion is None

    def test_failed_result(self):
        """测试失败的检测结果"""
        result = DiagnosticResult(
            name="测试项",
            passed=False,
            message="测试失败",
            fix_suggestion="修复建议",
        )
        assert result.name == "测试项"
        assert result.passed is False
        assert result.message == "测试失败"
        assert result.fix_suggestion == "修复建议"


class TestEnvironmentDiagnostics:
    """EnvironmentDiagnostics 类测试"""

    def test_check_port_availability_free(self, tmp_path):
        """测试端口可用检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                diagnostics = EnvironmentDiagnostics()
                
                # 使用一个不太可能被占用的端口
                result = diagnostics.check_port_availability(port=59999)
                assert result.passed is True
                assert "可用" in result.message

    def test_check_config_file_exists(self, tmp_path):
        """测试配置文件存在检测"""
        config_file = tmp_path / "config.json"
        config_file.write_text("{}")
        
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                diagnostics = EnvironmentDiagnostics()
                
                result = diagnostics.check_config_file()
                assert result.passed is True
                assert "存在" in result.message

    def test_check_config_file_not_exists(self, tmp_path):
        """测试配置文件不存在检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                diagnostics = EnvironmentDiagnostics()
                
                result = diagnostics.check_config_file()
                assert result.passed is False
                assert "不存在" in result.message

    def test_check_permissions(self, tmp_path):
        """测试权限检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                diagnostics = EnvironmentDiagnostics()
                
                result = diagnostics.check_permissions()
                assert result.passed is True
                assert "正常" in result.message

    def test_run_all_diagnostics(self, tmp_path):
        """测试运行所有诊断"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None, tcp_port=59999)
                diagnostics = EnvironmentDiagnostics()
                
                results = diagnostics.run_all_diagnostics(port=59999)
                assert len(results) == 11
                assert all(isinstance(r, DiagnosticResult) for r in results)

    def test_check_vivado_installation_not_found(self, tmp_path):
        """测试 Vivado 未安装检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                with patch("gateflow.cli.VivadoDetector.detect_vivado", return_value=None):
                    diagnostics = EnvironmentDiagnostics()
                    
                    result = diagnostics.check_vivado_installation()
                    assert result.passed is False
                    assert "未检测到" in result.message

    def test_check_vivado_installation_found(self, tmp_path):
        """测试 Vivado 已安装检测"""
        from gateflow.vivado.tcl_engine import VivadoInfo
        
        mock_info = VivadoInfo(
            version="2023.1",
            install_path=Path("/path/to/vivado"),
            executable=Path("/path/to/vivado/bin/vivado.bat"),
            tcl_shell=Path("/path/to/vivado/bin/vivado -mode tcl"),
        )
        
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                with patch("gateflow.cli.VivadoDetector.detect_vivado", return_value=mock_info):
                    diagnostics = EnvironmentDiagnostics()
                    
                    result = diagnostics.check_vivado_installation()
                    assert result.passed is True
                    assert "2023.1" in result.message

    def test_check_environment_variable_set(self, tmp_path):
        """测试环境变量已设置检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                with patch.dict("os.environ", {"XILINX_VIVADO": "/path/to/vivado"}):
                    with patch("pathlib.Path.exists", return_value=True):
                        diagnostics = EnvironmentDiagnostics()
                        
                        result = diagnostics.check_environment_variable()
                        assert result.passed is True
                        assert "已设置" in result.message

    def test_check_environment_variable_not_set(self, tmp_path):
        """测试环境变量未设置检测"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None)
                # 确保环境变量不存在
                env = dict(os.environ)
                env.pop("XILINX_VIVADO", None)
                with patch.dict("os.environ", env, clear=True):
                    diagnostics = EnvironmentDiagnostics()
                    
                    result = diagnostics.check_environment_variable()
                    assert result.passed is False
                    assert "未设置" in result.message

    def test_check_port_availability_accepts_gateflow_listener(self, tmp_path):
        """端口被 GateFlow tcl_server 占用时不应报失败。"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None, tcp_port=10099)
                diagnostics = EnvironmentDiagnostics()

                with patch("socket.socket.bind", side_effect=OSError()):
                    with patch("gateflow.cli._probe_tcp_protocol", return_value=("gateflow", "OK: 3")):
                        result = diagnostics.check_port_availability(port=10099)

        assert result.passed is True
        assert "GateFlow" in result.message

    def test_check_tcl_server_installation_runtime_ok_without_injection(self, tmp_path):
        """运行态正常时不应误报未安装。"""
        fake_vivado = Mock(version="2024.1", install_path=Path("/vivado"), executable=Path("/vivado/bin/vivado"))

        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path="/vivado", tcp_port=10099)
                diagnostics = EnvironmentDiagnostics()
                with patch.object(diagnostics, "_detect_vivado_info", return_value=fake_vivado):
                    with patch.object(
                        diagnostics,
                        "get_tcl_server_status",
                        return_value={
                            "passed": True,
                            "summary": "tcl_server 可运行，但 Vivado_init.tcl 未自动注入 GateFlow",
                            "overall_state": "runtime_ok_manual_injection_missing",
                            "tcp_listener_ok": True,
                            "tcp_protocol_ok": True,
                            "vivado_init_present": True,
                            "vivado_init_contains_gateflow": False,
                            "vivado_init_path": str(tmp_path / "Vivado_init.tcl"),
                            "protocol_details": "OK: 3",
                            "fix_suggestion": "rerun install",
                        },
                    ):
                        result = diagnostics.check_tcl_server_installation(port=10099)

        assert result.passed is True
        assert "可运行" in result.message

    def test_check_tcl_server_installation_runtime_ok_without_vivado_detection(self, tmp_path):
        """即使本机未探测到 Vivado，只要 TCP 运行态健康也不应误报失败。"""
        with patch("gateflow.cli.CONFIG_DIR", tmp_path):
            with patch("gateflow.cli.get_settings") as mock_settings:
                mock_settings.return_value = Mock(vivado_path=None, tcp_port=10099)
                diagnostics = EnvironmentDiagnostics()
                with patch.object(diagnostics, "_detect_vivado_info", return_value=None):
                    with patch.object(
                        diagnostics,
                        "get_tcl_server_status",
                        return_value={
                            "passed": True,
                            "summary": "tcl_server 可运行，但 Vivado_init.tcl 未自动注入 GateFlow",
                            "overall_state": "runtime_ok_manual_injection_missing",
                            "tcp_listener_ok": True,
                            "tcp_protocol_ok": True,
                            "vivado_init_present": False,
                            "vivado_init_contains_gateflow": False,
                            "vivado_init_path": None,
                            "protocol_details": "OK: 3",
                            "fix_suggestion": None,
                        },
                    ):
                        result = diagnostics.check_tcl_server_installation(port=10099)

        assert result.passed is True
        assert "可运行" in result.message

    def test_get_tcl_server_status_uses_detected_init_tcl_path(self, tmp_path):
        """doctor/status should honor the init_tcl_path returned by Vivado detection."""
        init_tcl_path = tmp_path / "Vivado_init.tcl"
        init_tcl_path.write_text(
            "# ===== GateFlow Tcl Server BEGIN =====\n"
            "gateflow_start_server 10099\n"
            "# ===== GateFlow Tcl Server END =====\n",
            encoding="utf-8",
        )
        fake_vivado = type(
            "FakeVivadoInfo",
            (),
            {
                "version": "2024.1",
                "install_path": Path("/vivado"),
                "executable": Path("/vivado/bin/vivado"),
                "init_tcl_path": init_tcl_path,
            },
        )()

        with patch("gateflow.cli.get_settings", return_value=Mock(vivado_path="/vivado", tcp_port=10099)):
            diagnostics = EnvironmentDiagnostics()
            with patch.object(diagnostics, "_detect_vivado_info", return_value=fake_vivado):
                with patch.object(
                    diagnostics,
                    "check_port_listener",
                    return_value=DiagnosticResult("listener", True, "ok"),
                ):
                    with patch.object(
                        diagnostics,
                        "check_tcp_protocol",
                        return_value=DiagnosticResult("protocol", True, "ok"),
                    ):
                        status = diagnostics.get_tcl_server_status(port=10099)

        assert status["vivado_init_present"] is True
        assert status["vivado_init_contains_gateflow"] is True
        assert status["vivado_init_path"] == str(init_tcl_path)

    def test_cmd_status_ascii_output(self, tmp_path, capsys):
        """ASCII 模式下 status 应避免 emoji。"""
        (tmp_path / "config.json").write_text("{}", encoding="utf-8")
        fake_settings = Mock(tcp_port=10099, vivado_path=None, log_level="INFO")
        fake_tcl_status = {
            "config_present": True,
            "script_present": True,
            "startup_script_present": True,
            "vivado_init_present": False,
            "vivado_init_contains_gateflow": False,
            "tcp_listener_ok": True,
            "tcp_protocol_ok": True,
            "effective_runtime_ok": True,
            "passed": True,
            "summary": "runtime ok",
            "fix_suggestion": None,
            "vivado_init_path": None,
            "protocol_details": "OK: 3",
        }

        with patch.dict("os.environ", {"GATEFLOW_ASCII_OUTPUT": "1"}):
            with patch("gateflow.cli.CONFIG_DIR", tmp_path):
                with patch("gateflow.cli.get_settings", return_value=fake_settings):
                        with patch("gateflow.cli.build_capability_manifest", return_value={"tool_count": 160}):
                            with patch("gateflow.cli.EnvironmentDiagnostics._detect_vivado_info", return_value=None):
                                with patch("gateflow.cli.EnvironmentDiagnostics.get_tcl_server_status", return_value=fake_tcl_status):
                                    rc = cmd_status(Mock(port=None))

        output = capsys.readouterr().out
        assert rc == 0
        assert "[OK]" in output
        assert "runtime ok" in output

    def test_cmd_runs_status(self, capsys):
        """runs status 应调用高层 API 并打印 run 状态。"""
        fake_gf = Mock()
        fake_gf.get_run_status = AsyncMock(
            return_value={
                "success": True,
                "run_name": "impl_1",
                "status": "Running",
                "status_source": "vivado",
                "is_running": True,
                "is_complete": False,
                "is_failed": False,
                "last_known_step": "route_design",
                "progress_hint": "running",
                "artifacts": {"run_directory": "build/impl_1"},
                "message": "获取运行状态成功: impl_1",
                "error": None,
            }
        )

        with patch("gateflow.GateFlow", return_value=fake_gf):
            rc = cmd_runs(Mock(runs_command="status", run_name="impl_1"))

        output = capsys.readouterr().out
        assert rc == 0
        assert "impl_1" in output
        assert "route_design" in output

    def test_cmd_runs_messages_failure(self, capsys):
        """runs messages 失败时返回非 0。"""
        fake_gf = Mock()
        fake_gf.get_run_messages = AsyncMock(
            return_value={
                "success": False,
                "run_name": "missing",
                "status": None,
                "messages": [],
                "matched_count": 0,
                "message": "获取运行消息失败: missing",
                "error": "run_not_found",
            }
        )

        with patch("gateflow.GateFlow", return_value=fake_gf):
            rc = cmd_runs(Mock(runs_command="messages", run_name="missing", limit=50, severity=None))

        output = capsys.readouterr().out
        assert rc == 1
        assert "run_not_found" in output


class TestMain:
    """main 函数测试"""

    def test_main_no_command(self):
        """测试无子命令时的主函数"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = None
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.server.main") as mock_server_main:
                result = main()
                assert result == 0
                mock_server_main.assert_called_once()

    def test_main_install_command(self):
        """测试 install 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "install"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_install") as mock_cmd_install:
                mock_cmd_install.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_install.assert_called_once_with(mock_args)

    def test_main_uninstall_command(self):
        """测试 uninstall 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "uninstall"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_uninstall") as mock_cmd_uninstall:
                mock_cmd_uninstall.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_uninstall.assert_called_once_with(mock_args)

    def test_main_status_command(self):
        """测试 status 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "status"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_status") as mock_cmd_status:
                mock_cmd_status.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_status.assert_called_once_with(mock_args)

    def test_main_activate_command(self):
        """测试 activate 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "activate"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_activate") as mock_cmd_activate:
                mock_cmd_activate.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_activate.assert_called_once_with(mock_args)

    def test_main_doctor_command(self):
        """测试 doctor 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "doctor"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_doctor") as mock_cmd_doctor:
                mock_cmd_doctor.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_doctor.assert_called_once_with(mock_args)

    def test_main_capabilities_command(self):
        """测试 capabilities 命令"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = "capabilities"
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.cli.cmd_capabilities") as mock_cmd_capabilities:
                mock_cmd_capabilities.return_value = 0
                result = main()
                assert result == 0
                mock_cmd_capabilities.assert_called_once_with(mock_args)

    def test_main_keyboard_interrupt(self):
        """测试键盘中断"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = None
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.server.main") as mock_server_main:
                mock_server_main.side_effect = KeyboardInterrupt()
                result = main()
                assert result == 0

    def test_main_exception(self):
        """测试异常处理"""
        with patch("gateflow.cli.create_parser") as mock_parser:
            mock_args = Mock()
            mock_args.command = None
            mock_args.verbose = False
            mock_args.log_level = None
            mock_args.tcp_port = None
            mock_parser.return_value.parse_args.return_value = mock_args

            with patch("gateflow.server.main") as mock_server_main:
                mock_server_main.side_effect = Exception("Test error")
                result = main()
                assert result == 1
