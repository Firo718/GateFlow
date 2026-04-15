"""
GateFlow CLI 命令模块

提供命令行接口，包括：
- gateflow: 启动 MCP 服务器
- gateflow install: 安装 Tcl Server 到 Vivado
- gateflow uninstall: 卸载 Tcl Server
- gateflow status: 检查 Vivado 连接状态
- gateflow doctor: 诊断 GateFlow 环境
- gateflow --version: 显示版本
"""

import argparse
import asyncio
import json
import logging
import os
import socket
import shutil
import subprocess
import sys
from importlib import import_module
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from gateflow import __version__
from gateflow.capabilities import build_capability_manifest, write_capability_artifacts
from gateflow.settings import CONFIG_DIR, get_settings, reset_settings
from gateflow.vivado.tcl_engine import TclEngine, VivadoDetector
from gateflow.vivado.tcl_server import TclServerInstaller

logger = logging.getLogger(__name__)

# 支持的 Vivado 版本范围
MIN_SUPPORTED_VERSION = "2019.1"
MAX_SUPPORTED_VERSION = "2024.2"
ASCII_OUTPUT_ENV = "GATEFLOW_ASCII_OUTPUT"


@dataclass
class DiagnosticResult:
    """诊断检测结果"""
    name: str  # 检测项名称
    passed: bool  # 是否通过
    message: str  # 结果消息
    details: Optional[str] = None  # 详细信息
    fix_suggestion: Optional[str] = None  # 修复建议


def _ascii_output_enabled() -> bool:
    """Return whether the CLI should avoid non-ASCII output."""
    value = os.environ.get(ASCII_OUTPUT_ENV, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _icon(kind: str) -> str:
    """Return emoji icons by default and ASCII labels in fallback mode."""
    if _ascii_output_enabled():
        mapping = {
            "ok": "[OK]",
            "warn": "[WARN]",
            "fail": "[FAIL]",
            "info": "[INFO]",
        }
    else:
        mapping = {
            "ok": "\u2705",
            "warn": "\u26a0\ufe0f",
            "fail": "\u274c",
            "info": "\U0001f539",
        }
    return mapping[kind]


def _status_icon(passed: bool) -> str:
    return _icon("ok" if passed else "fail")


def _path_is_within(path: Path, root: Path) -> bool:
    """Compatibility helper for Path.is_relative_to."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _looks_like_repo_root(path: Path) -> bool:
    """Detect whether the current directory looks like a GateFlow checkout."""
    return (path / "pyproject.toml").exists() and (path / "src" / "gateflow").exists()


def _import_search_roots() -> list[Path]:
    """Return the likely import roots for the current interpreter."""
    roots: list[Path] = []
    try:
        import site

        user_site = site.getusersitepackages()
        if user_site:
            roots.append(Path(user_site))
        for entry in site.getsitepackages():
            roots.append(Path(entry))
    except Exception:
        pass

    roots.extend(
        [
            Path(sys.prefix),
            Path(sys.exec_prefix),
            Path(sys.executable).resolve().parent,
        ]
    )

    unique_roots: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        try:
            resolved = root.resolve()
        except Exception:
            continue
        if resolved not in seen:
            unique_roots.append(resolved)
            seen.add(resolved)
    return unique_roots


def _run_cli_version_probe() -> tuple[bool, str, str]:
    """Check whether `gateflow --version` works in the current environment."""
    scripts_dir = Path(sys.executable).resolve().parent
    candidate_names = ["gateflow"]
    if os.name == "nt":
        candidate_names.extend(["gateflow.exe", "gateflow.cmd"])

    cli_executable = None
    for name in candidate_names:
        candidate = scripts_dir / name
        if candidate.exists():
            cli_executable = str(candidate)
            break

    if cli_executable is None:
        for name in candidate_names:
            found = shutil.which(name)
            if found:
                cli_executable = found
                break

    if cli_executable is None:
        return False, "", "gateflow CLI 未出现在当前 Python 环境的 Scripts 路径或 PATH 中"

    try:
        completed = subprocess.run(
            [cli_executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except Exception as exc:
        return False, cli_executable, str(exc)

    combined_output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode == 0 and "GateFlow v" in combined_output:
        return True, cli_executable, combined_output.strip()

    detail = combined_output.strip() or f"exit code {completed.returncode}"
    return False, cli_executable, detail


def _run_install_self_check() -> list[DiagnosticResult]:
    """Run install-time validation for import health and CLI entrypoint usability."""
    results: list[DiagnosticResult] = []
    cwd = Path.cwd().resolve()
    repo_expected = cwd if _looks_like_repo_root(cwd) else None

    try:
        cli_module = import_module("gateflow.cli")
        module_path = Path(getattr(cli_module, "__file__", "")).resolve()
        results.append(
            DiagnosticResult(
                name="导入 gateflow.cli",
                passed=True,
                message="当前解释器可以导入 gateflow.cli",
                details=f"实际导入路径: {module_path}",
            )
        )
    except Exception as exc:
        module_path = None
        results.append(
            DiagnosticResult(
                name="导入 gateflow.cli",
                passed=False,
                message="当前解释器无法导入 gateflow.cli",
                details=str(exc),
                fix_suggestion="pip uninstall gateflow\npip install -e <repo-root>",
            )
        )

    cli_ok, cli_location, cli_detail = _run_cli_version_probe()
    cli_details = cli_detail
    if cli_location:
        cli_details = f"CLI 路径: {cli_location}\n{cli_detail}".strip()
    results.append(
        DiagnosticResult(
            name="gateflow --version",
            passed=cli_ok,
            message="gateflow --version 可运行" if cli_ok else "gateflow --version 不可运行",
            details=cli_details,
            fix_suggestion=None if cli_ok else "pip uninstall gateflow\npip install -e <repo-root>",
        )
    )

    if module_path is None:
        return results

    if repo_expected is not None:
        import_path_ok = _path_is_within(module_path, repo_expected)
        results.append(
            DiagnosticResult(
                name="导入路径校验",
                passed=import_path_ok,
                message=(
                    "editable install 导入路径与当前工作目录一致"
                    if import_path_ok
                    else "editable install 导入路径与当前工作目录不一致"
                ),
                details=f"当前实际导入路径: {module_path}\n预期工作目录: {repo_expected}",
                fix_suggestion=None if import_path_ok else f"pip uninstall gateflow\npip install -e {repo_expected}",
            )
        )
        return results

    import_root_ok = any(_path_is_within(module_path, root) for root in _import_search_roots())
    results.append(
        DiagnosticResult(
            name="导入路径校验",
            passed=import_root_ok,
            message=(
                "导入路径位于当前 Python 环境可接受的安装目录"
                if import_root_ok
                else "导入路径不在当前 Python 环境的常见安装目录中"
            ),
            details=f"当前实际导入路径: {module_path}",
            fix_suggestion=None if import_root_ok else "pip uninstall gateflow\npip install -e <repo-root>",
        )
    )
    return results


def _configure_console_output() -> None:
    """Use UTF-8 when possible and avoid hard failures on Windows consoles."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            try:
                reconfigure(errors="replace")
            except Exception:
                pass


def _probe_tcp_protocol(
    host: str,
    port: int,
    timeout: float = 1.5,
) -> tuple[str, str]:
    """
    Probe a TCP listener and classify whether it looks GateFlow-compatible.

    Returns:
        (status, raw_output)
        status in {"gateflow", "silent", "unknown", "unreachable"}
    """
    raw_output = ""
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(b"expr 1+2\n")

            chunks: list[str] = []
            while True:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data.decode("utf-8", errors="replace"))
                current = "".join(chunks)
                if "OK:" in current or "ERROR:" in current or "\n% " in current or "\n# " in current:
                    break

            raw_output = "".join(chunks).strip()
    except OSError:
        return "unreachable", raw_output

    if "OK: 3" in raw_output:
        return "gateflow", raw_output
    if not raw_output:
        return "silent", raw_output
    return "unknown", raw_output


class EnvironmentDiagnostics:
    """GateFlow 环境诊断工具"""
    
    def __init__(self):
        self.settings = get_settings()
        self.results: list[DiagnosticResult] = []
    
    def check_vivado_installation(self) -> DiagnosticResult:
        """
        检测 Vivado 安装
        
        Returns:
            DiagnosticResult 检测结果
        """
        config_vivado_path = Path(self.settings.vivado_path) if self.settings.vivado_path else None
        vivado_info = VivadoDetector.detect_vivado(config_path=config_vivado_path)
        
        if vivado_info:
            return DiagnosticResult(
                name="Vivado 安装",
                passed=True,
                message=f"已检测到 Vivado {vivado_info.version}",
                details=f"路径: {vivado_info.install_path}",
            )
        else:
            return DiagnosticResult(
                name="Vivado 安装",
                passed=False,
                message="未检测到 Vivado 安装",
                fix_suggestion="请从 AMD Xilinx 官网下载并安装 Vivado: https://www.xilinx.com/support/download.html",
            )
    
    def check_vivado_version(self) -> DiagnosticResult:
        """
        检测 Vivado 版本兼容性
        
        Returns:
            DiagnosticResult 检测结果
        """
        config_vivado_path = Path(self.settings.vivado_path) if self.settings.vivado_path else None
        vivado_info = VivadoDetector.detect_vivado(config_path=config_vivado_path)
        
        if not vivado_info:
            return DiagnosticResult(
                name="Vivado 版本",
                passed=False,
                message="无法检测版本（Vivado 未安装）",
                fix_suggestion="请先安装 Vivado",
            )
        
        version = vivado_info.version
        try:
            # 解析版本号
            year, minor = version.split(".")
            version_tuple = (int(year), int(minor))
            
            min_year, min_minor = MIN_SUPPORTED_VERSION.split(".")
            min_version = (int(min_year), int(min_minor))
            
            max_year, max_minor = MAX_SUPPORTED_VERSION.split(".")
            max_version = (int(max_year), int(max_minor))
            
            if min_version <= version_tuple <= max_version:
                return DiagnosticResult(
                    name="Vivado 版本",
                    passed=True,
                    message=f"版本 {version} 兼容",
                    details=f"支持版本范围: {MIN_SUPPORTED_VERSION} - {MAX_SUPPORTED_VERSION}",
                )
            elif version_tuple < min_version:
                return DiagnosticResult(
                    name="Vivado 版本",
                    passed=False,
                    message=f"版本 {version} 过低",
                    details=f"当前版本低于最低支持版本 {MIN_SUPPORTED_VERSION}",
                    fix_suggestion=f"建议升级到 Vivado {MIN_SUPPORTED_VERSION} 或更高版本",
                )
            else:
                return DiagnosticResult(
                    name="Vivado 版本",
                    passed=True,  # 高版本仍然标记为通过，但给出提示
                    message=f"版本 {version} 高于测试范围",
                    details=f"支持版本范围: {MIN_SUPPORTED_VERSION} - {MAX_SUPPORTED_VERSION}，高版本可能存在兼容性问题",
                )
        except (ValueError, AttributeError):
            return DiagnosticResult(
                name="Vivado 版本",
                passed=True,
                message=f"版本 {version}（无法验证兼容性）",
                details="版本号格式不标准，可能为开发版本",
            )
    
    def check_environment_variable(self) -> DiagnosticResult:
        """
        检测 XILINX_VIVADO 环境变量
        
        Returns:
            DiagnosticResult 检测结果
        """
        vivado_env = os.environ.get("XILINX_VIVADO")
        
        if vivado_env:
            vivado_path = Path(vivado_env)
            if vivado_path.exists():
                return DiagnosticResult(
                    name="环境变量",
                    passed=True,
                    message="XILINX_VIVADO 已设置",
                    details=f"值: {vivado_env}",
                )
            else:
                return DiagnosticResult(
                    name="环境变量",
                    passed=False,
                    message="XILINX_VIVADO 指向无效路径",
                    details=f"当前值: {vivado_env}",
                    fix_suggestion="请更新 XILINX_VIVADO 环境变量指向正确的 Vivado 安装路径",
                )
        else:
            # 检查配置文件中是否有路径
            if self.settings.vivado_path:
                return DiagnosticResult(
                    name="环境变量",
                    passed=True,
                    message="XILINX_VIVADO 未设置，但配置文件中有路径",
                    details=f"配置路径: {self.settings.vivado_path}",
                    fix_suggestion="可选：设置环境变量 XILINX_VIVADO 以便其他工具使用",
                )
            else:
                return DiagnosticResult(
                    name="环境变量",
                    passed=False,
                    message="XILINX_VIVADO 未设置",
                    fix_suggestion="请设置环境变量 XILINX_VIVADO 指向 Vivado 安装路径\n"
                                   "Windows: setx XILINX_VIVADO \"C:\\Xilinx\\Vivado\\2023.1\"\n"
                                   "Linux/macOS: export XILINX_VIVADO=/opt/Xilinx/Vivado/2023.1",
                )
    
    def check_port_availability(self, port: int = 9999) -> DiagnosticResult:
        """
        检测端口是否被占用
        
        Args:
            port: 要检测的端口号
        
        Returns:
            DiagnosticResult 检测结果
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return DiagnosticResult(
                    name="端口占用",
                    passed=True,
                    message=f"端口 {port} 可用",
                )
        except OSError:
            protocol_status, raw_output = _probe_tcp_protocol("127.0.0.1", port)
            if protocol_status == "gateflow":
                return DiagnosticResult(
                    name="端口占用",
                    passed=True,
                    message=f"端口 {port} 正被 GateFlow tcl_server 使用",
                    details=raw_output or None,
                )
            return DiagnosticResult(
                name="端口占用",
                passed=False,
                message=f"端口 {port} 已被占用",
                details=raw_output or None,
                fix_suggestion=f"运行以下命令查看占用进程:\n"
                               f"  Windows: netstat -ano | findstr {port}\n"
                               f"  Linux/macOS: lsof -i :{port}\n"
                               f"或使用其他端口: gateflow install --port <新端口>",
            )

    def check_tcl_server_script(self) -> DiagnosticResult:
        """检测 GateFlow 生成的 Tcl Server 脚本。"""
        script_path = CONFIG_DIR / "tcl_server.tcl"
        if script_path.exists():
            return DiagnosticResult(
                name="tcl_server 脚本",
                passed=True,
                message="脚本已生成",
                details=f"路径: {script_path}",
            )
        return DiagnosticResult(
            name="tcl_server 脚本",
            passed=False,
            message="脚本不存在",
            fix_suggestion="运行 `gateflow install` 生成 ~/.gateflow/tcl_server.tcl",
        )

    def check_startup_script(self) -> DiagnosticResult:
        """检测手动启动脚本。"""
        startup_path = CONFIG_DIR / "start_server.bat"
        if startup_path.exists():
            return DiagnosticResult(
                name="手动启动脚本",
                passed=True,
                message="启动脚本已生成",
                details=f"路径: {startup_path}",
            )
        return DiagnosticResult(
            name="手动启动脚本",
            passed=False,
            message="启动脚本不存在",
            fix_suggestion="运行 `gateflow install` 生成手动启动脚本",
        )

    def check_port_listener(self, port: int) -> DiagnosticResult:
        """检测指定端口是否已有 TCP 监听。"""
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                return DiagnosticResult(
                    name="TCP 监听",
                    passed=True,
                    message=f"127.0.0.1:{port} 正在监听",
                )
        except OSError:
            return DiagnosticResult(
                name="TCP 监听",
                passed=False,
                message=f"127.0.0.1:{port} 未监听",
                fix_suggestion="启动 Vivado 并加载 GateFlow tcl_server，或运行 start_server.bat",
            )

    def check_tcp_protocol(self, port: int) -> DiagnosticResult:
        """检测端口上的服务是否兼容 GateFlow TCP 协议。"""
        status, raw_output = _probe_tcp_protocol("127.0.0.1", port)
        if status == "gateflow":
            return DiagnosticResult(
                name="TCP 协议",
                passed=True,
                message=f"端口 {port} 返回 GateFlow 协议响应",
                details=raw_output,
            )
        if status == "silent":
            return DiagnosticResult(
                name="TCP 协议",
                passed=False,
                message=f"端口 {port} 已监听，但未返回 GateFlow 协议响应",
                fix_suggestion="该端口可能被其他 Tcl/MCP 服务占用，请改用独立端口并重新安装 GateFlow tcl_server",
            )
        if status == "unknown":
            return DiagnosticResult(
                name="TCP 协议",
                passed=False,
                message=f"端口 {port} 返回了非 GateFlow 响应",
                details=raw_output,
                fix_suggestion="检查该端口是否连接到了其他 MCP/Tcl 服务，建议为 GateFlow 使用独立端口",
            )
        return DiagnosticResult(
            name="TCP 协议",
            passed=False,
            message=f"无法连接到端口 {port} 进行协议探测",
            fix_suggestion="先启动 GateFlow tcl_server，再重试 status/doctor",
        )

    def _detect_vivado_info(self):
        """Return detected Vivado info using the configured path when available."""
        config_vivado_path = Path(self.settings.vivado_path) if self.settings.vivado_path else None
        return VivadoDetector.detect_vivado(config_path=config_vivado_path)

    def get_tcl_server_status(self, port: int | None = None) -> dict[str, Any]:
        """Collect a layered tcl_server status model for doctor/status output."""
        probe_port = port if port is not None else self.settings.tcp_port
        vivado_info = self._detect_vivado_info()

        config_present = (CONFIG_DIR / "config.json").exists()
        script_present = (CONFIG_DIR / "tcl_server.tcl").exists()
        startup_script_present = (CONFIG_DIR / "start_server.bat").exists()

        vivado_init_present = False
        vivado_init_contains_gateflow = False
        vivado_init_path: str | None = None

        if vivado_info:
            installer = TclServerInstaller(vivado_info)
            init_tcl_path = installer.get_init_tcl_path()
            if init_tcl_path:
                vivado_init_path = str(init_tcl_path)
                vivado_init_present = init_tcl_path.exists()
            vivado_init_contains_gateflow = installer.is_installed()

        listener_result = self.check_port_listener(probe_port)
        protocol_result = self.check_tcp_protocol(probe_port)

        tcp_listener_ok = listener_result.passed
        tcp_protocol_ok = protocol_result.passed
        effective_runtime_ok = tcp_listener_ok and tcp_protocol_ok

        if effective_runtime_ok and vivado_init_contains_gateflow:
            overall_state = "installed"
            summary = "tcl_server 已安装并可运行"
            passed = True
            fix_suggestion = None
        elif effective_runtime_ok:
            overall_state = "runtime_ok_manual_injection_missing"
            summary = "tcl_server 可运行，但 Vivado_init.tcl 未自动注入 GateFlow"
            passed = True
            fix_suggestion = "如需 Vivado 自动启动 GateFlow tcl_server，请重新运行 `gateflow install`"
        elif any([config_present, script_present, startup_script_present, vivado_init_present]):
            overall_state = "partial"
            summary = "tcl_server 安装不完整或运行态不可用"
            passed = False
            fix_suggestion = "重新运行 `gateflow install`，然后执行 `gateflow status --port <端口>` 验证"
        else:
            overall_state = "not_installed"
            summary = "未检测到 GateFlow tcl_server 安装"
            passed = False
            fix_suggestion = "运行 `gateflow install` 安装 Tcl Server"

        return {
            "config_present": config_present,
            "script_present": script_present,
            "startup_script_present": startup_script_present,
            "vivado_init_present": vivado_init_present,
            "vivado_init_contains_gateflow": vivado_init_contains_gateflow,
            "tcp_listener_ok": tcp_listener_ok,
            "tcp_protocol_ok": tcp_protocol_ok,
            "effective_runtime_ok": effective_runtime_ok,
            "overall_state": overall_state,
            "passed": passed,
            "summary": summary,
            "fix_suggestion": fix_suggestion,
            "port": probe_port,
            "listener_message": listener_result.message,
            "protocol_message": protocol_result.message,
            "protocol_details": protocol_result.details,
            "vivado_init_path": vivado_init_path,
        }

    def check_tcl_server_installation(self, port: int | None = None) -> DiagnosticResult:
        """
        检测 tcl_server 是否已安装到 Vivado
        
        Returns:
            DiagnosticResult 检测结果
        """
        status = self.get_tcl_server_status(port)
        vivado_info = self._detect_vivado_info()
        details = [
            f"状态: {status['overall_state']}",
            f"TCP 监听: {status['tcp_listener_ok']}",
            f"TCP 协议: {status['tcp_protocol_ok']}",
            f"Vivado_init.tcl 存在: {status['vivado_init_present']}",
            f"Vivado_init.tcl 含 GateFlow 注入: {status['vivado_init_contains_gateflow']}",
        ]
        if vivado_info:
            details.append(f"Vivado: {vivado_info.version} @ {vivado_info.install_path}")
        else:
            details.append("Vivado: 未探测到本机安装，仅依据运行态与本地配置判断")
        if status["vivado_init_path"]:
            details.append(f"Vivado_init.tcl 路径: {status['vivado_init_path']}")
        if status["protocol_details"]:
            details.append(f"协议响应: {status['protocol_details']}")

        return DiagnosticResult(
            name="tcl_server 安装",
            passed=status["passed"],
            message=status["summary"],
            details="\n".join(details),
            fix_suggestion=status["fix_suggestion"],
        )
    
    def check_config_file(self) -> DiagnosticResult:
        """
        检测配置文件
        
        Returns:
            DiagnosticResult 检测结果
        """
        config_file = CONFIG_DIR / "config.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    json.load(f)
                return DiagnosticResult(
                    name="配置文件",
                    passed=True,
                    message="配置文件存在",
                    details=f"路径: {config_file}",
                )
            except Exception as e:
                return DiagnosticResult(
                    name="配置文件",
                    passed=False,
                    message=f"配置文件读取失败: {e}",
                    fix_suggestion=f"删除配置文件并重新运行 `gateflow install`: {config_file}",
                )
        else:
            return DiagnosticResult(
                name="配置文件",
                passed=False,
                message="配置文件不存在",
                fix_suggestion="运行 `gateflow install` 创建配置文件",
            )
    
    def check_permissions(self) -> DiagnosticResult:
        """
        检测读写权限
        
        Returns:
            DiagnosticResult 检测结果
        """
        issues = []
        
        # 检查配置目录权限
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            test_file = CONFIG_DIR / ".permission_test"
            test_file.write_text("test", encoding='utf-8')
            test_file.unlink()
        except PermissionError:
            issues.append(f"配置目录 {CONFIG_DIR} 无写入权限")
        except Exception as e:
            issues.append(f"配置目录检测失败: {e}")
        
        # 检查 Vivado 安装目录权限（如果存在）
        if self.settings.vivado_path:
            try:
                # 检查 Vivado_init.tcl 所在目录
                if sys.platform == "win32":
                    appdata = os.environ.get('APPDATA')
                    if appdata:
                        init_tcl_dir = Path(appdata) / "Xilinx" / "Vivado"
                        if init_tcl_dir.exists():
                            test_file = init_tcl_dir / ".permission_test"
                            try:
                                test_file.write_text("test", encoding='utf-8')
                                test_file.unlink()
                            except PermissionError:
                                issues.append(f"Vivado 配置目录 {init_tcl_dir} 无写入权限")
            except Exception:
                pass
        
        if issues:
            return DiagnosticResult(
                name="权限检查",
                passed=False,
                message="存在权限问题",
                details="\n".join(f"  - {issue}" for issue in issues),
                fix_suggestion="请检查目录权限，或以管理员身份运行",
            )
        else:
            return DiagnosticResult(
                name="权限检查",
                passed=True,
                message="读写权限正常",
            )
    
    def run_all_diagnostics(self, port: int) -> list[DiagnosticResult]:
        """
        运行所有诊断检测
        
        Args:
            port: 要检测的端口号
        
        Returns:
            诊断结果列表
        """
        self.results = [
            self.check_vivado_installation(),
            self.check_vivado_version(),
            self.check_environment_variable(),
            self.check_port_availability(port),
            self.check_port_listener(port),
            self.check_tcp_protocol(port),
            self.check_tcl_server_installation(port),
            self.check_tcl_server_script(),
            self.check_startup_script(),
            self.check_config_file(),
            self.check_permissions(),
        ]
        return self.results


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        prog="gateflow",
        description="GateFlow - AI 辅助 Vivado FPGA 开发 MCP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  gateflow                    启动 MCP 服务器
  gateflow --version          显示版本信息
  gateflow install            自动检测并安装 Tcl Server
  gateflow install C:/Xilinx/Vivado/2024.1  指定 Vivado 路径安装
  gateflow status             检查 Vivado 连接状态
  gateflow doctor             诊断 GateFlow 环境
  gateflow doctor --json      以 JSON 格式输出诊断结果
  gateflow uninstall          卸载 Tcl Server

配置优先级（从高到低）:
  1. 环境变量 (GATEFLOW_*)
  2. .env 文件
  3. 配置文件 ~/.gateflow/config.json
  4. CLI 参数
  5. 默认值

环境变量示例:
  GATEFLOW_TCP_PORT=8888           设置 TCP 端口
  GATEFLOW_VIVADO_PATH=/path/to   设置 Vivado 路径
  GATEFLOW_LOG_LEVEL=DEBUG        设置日志级别

更多信息请访问: https://github.com/Firo718/GateFlow
        """,
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"GateFlow v{__version__}",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细日志",
    )

    # 全局配置参数（可覆盖配置文件）
    parser.add_argument(
        "--tcp-port",
        type=int,
        help="TCP 端口号（覆盖配置文件）",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别（覆盖配置文件）",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # install 子命令
    install_parser = subparsers.add_parser(
        "install",
        help="安装 Tcl Server 到 Vivado",
        description="安装 Tcl Server 到 Vivado，配置 GateFlow 与 Vivado 的集成",
    )
    install_parser.add_argument(
        "path",
        nargs="?",
        help="Vivado 安装路径（可选，自动检测）",
    )
    install_parser.add_argument(
        "--port", "-p",
        type=int,
        help="TCP 端口号（默认: 9999）",
    )

    # uninstall 子命令
    uninstall_parser = subparsers.add_parser(
        "uninstall",
        help="从 Vivado 卸载 Tcl Server",
        description="从 Vivado 卸载 Tcl Server，移除 GateFlow 配置",
    )
    uninstall_parser.add_argument(
        "path",
        nargs="?",
        help="Vivado 安装路径（可选，自动检测）",
    )

    # activate 子命令（预留）
    activate_parser = subparsers.add_parser(
        "activate",
        help="激活许可证（开源版本无需激活）",
        description="激活 GateFlow 许可证（开源版本无需激活）",
    )
    activate_parser.add_argument(
        "key",
        help="许可证密钥",
    )

    # status 子命令
    status_parser = subparsers.add_parser(
        "status",
        help="检查 Vivado 连接状态",
        description="检查 Vivado 安装和连接状态",
    )
    status_parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="TCP 端口号（默认: 使用配置的端口）",
    )

    # doctor 子命令
    doctor_parser = subparsers.add_parser(
        "doctor",
        help="诊断 GateFlow 环境",
        description="运行环境诊断，检测常见问题并提供修复建议",
    )
    doctor_parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="要检测的 TCP 端口号（默认: 使用配置中的端口）",
    )
    doctor_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果",
    )

    gui_parser = subparsers.add_parser(
        "gui",
        help="管理 Vivado GUI 会话",
        description="启动、查询和关闭 GateFlow 管理的 Vivado GUI 会话",
    )
    gui_subparsers = gui_parser.add_subparsers(dest="gui_command", required=True)

    gui_open_parser = gui_subparsers.add_parser("open", help="启动 GUI 会话并绑定工程")
    gui_open_parser.add_argument("xpr_path", help="Vivado 工程路径 (.xpr)")
    gui_open_parser.add_argument("--port", "-p", type=int, default=None, help="GUI 会话 TCP 端口")

    gui_attach_parser = gui_subparsers.add_parser("attach", help="附着到已有 GUI 会话")
    gui_attach_parser.add_argument("--port", "-p", type=int, required=True, help="已有 GUI 会话的 TCP 端口")
    gui_attach_parser.add_argument("xpr_path", nargs="?", help="可选工程路径；提供时会确认或切换到该工程")

    gui_subparsers.add_parser("status", help="查看 GUI 会话状态")
    gui_subparsers.add_parser("close", help="关闭 GUI 会话")

    gui_logs_parser = gui_subparsers.add_parser("logs", help="查看 GUI 会话日志入口信息")
    gui_logs_parser.add_argument("--tail", type=int, default=50, help="保留兼容参数，当前仅输出会话元信息")

    runs_parser = subparsers.add_parser(
        "runs",
        help="查询和控制 Vivado run",
        description="启动、等待和观察 Vivado synth/impl run 状态",
    )
    runs_subparsers = runs_parser.add_subparsers(dest="runs_command", required=True)

    runs_status_parser = runs_subparsers.add_parser("status", help="查询 run 状态")
    runs_status_parser.add_argument("run_name", help="run 名称，例如 synth_1 或 impl_1")

    runs_progress_parser = runs_subparsers.add_parser("progress", help="查询 run 进度提示")
    runs_progress_parser.add_argument("run_name", help="run 名称，例如 synth_1 或 impl_1")

    runs_messages_parser = runs_subparsers.add_parser("messages", help="查询 run 最近消息")
    runs_messages_parser.add_argument("run_name", help="run 名称，例如 synth_1 或 impl_1")
    runs_messages_parser.add_argument("--limit", type=int, default=50, help="最多返回消息数")
    runs_messages_parser.add_argument("--severity", default=None, help="过滤严重级别，例如 error/warning/info")

    runs_wait_parser = runs_subparsers.add_parser("wait", help="等待 run 完成")
    runs_wait_parser.add_argument("run_name", help="run 名称，例如 synth_1 或 impl_1")
    runs_wait_parser.add_argument("--timeout", type=float, default=None, help="最长等待秒数")
    runs_wait_parser.add_argument("--poll-interval", type=float, default=2.0, help="轮询间隔秒数")

    runs_launch_parser = runs_subparsers.add_parser("launch", help="启动 run 但不等待完成")
    runs_launch_parser.add_argument("run_name", help="run 名称，例如 synth_1 或 impl_1")
    runs_launch_parser.add_argument("--to-step", default=None, help="可选目标 step，例如 write_bitstream")
    runs_launch_parser.add_argument("--jobs", type=int, default=4, help="Vivado 并行 jobs 数")

    # capabilities 子命令
    capabilities_parser = subparsers.add_parser(
        "capabilities",
        help="输出/导出 MCP 能力清单",
        description="基于真实运行时工具注册，输出或导出 capability manifest",
    )
    capabilities_parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式打印能力清单",
    )
    capabilities_parser.add_argument(
        "--write",
        action="store_true",
        help="将能力清单写入 docs/CAPABILITIES.md 与 docs/CAPABILITIES.json",
    )
    capabilities_parser.add_argument(
        "--markdown-path",
        type=str,
        help="自定义 Markdown 输出路径（默认 docs/CAPABILITIES.md）",
    )
    capabilities_parser.add_argument(
        "--manifest-path",
        type=str,
        help="自定义 JSON 输出路径（默认 docs/CAPABILITIES.json）",
    )

    return parser


def cmd_install(args) -> int:
    """
    执行 install 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    print("=" * 60)
    print("GateFlow Tcl Server 安装")
    print("=" * 60)

    settings = get_settings()
    override_kwargs = {}
    if args.port is not None:
        override_kwargs["tcp_port"] = args.port
    if override_kwargs:
        settings = get_settings(**override_kwargs)

    vivado_path = None
    vivado_info = None
    if args.path:
        vivado_path = Path(args.path)
        if not vivado_path.exists():
            print(f"{_icon('fail')} 错误: 指定的路径不存在: {vivado_path}")
            return 1
        vivado_info = VivadoDetector._validate_vivado_path(vivado_path)
    else:
        config_vivado_path = settings.vivado_path
        config_path = Path(config_vivado_path) if config_vivado_path else None
        print(f"\n{_icon('info')} 正在检测 Vivado 安装...")
        vivado_info = VivadoDetector.detect_vivado(config_path=config_path)
        if vivado_info:
            vivado_path = vivado_info.install_path
            print(f"{_icon('ok')} 检测到 Vivado {vivado_info.version}")
            print(f"  路径: {vivado_path}")
        else:
            print(f"{_icon('fail')} 未检测到 Vivado 安装")
            print("\n请手动指定 Vivado 安装路径:")
            print("  gateflow install <vivado_path>")
            return 1

    if not vivado_info:
        print(f"{_icon('fail')} 错误: 无效的 Vivado 安装路径: {vivado_path}")
        return 1

    print(f"\n{_icon('info')} 保存配置...")
    settings = get_settings(
        vivado_path=str(vivado_info.install_path),
        tcp_port=args.port if args.port is not None else settings.tcp_port,
    )
    settings.to_config_file()

    print(f"\n{_icon('info')} 创建 Tcl Server 脚本...")
    installer = TclServerInstaller(vivado_info)
    script_content = installer.generate_script(port=settings.tcp_port, blocking=True)
    script_path = CONFIG_DIR / "tcl_server.tcl"
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        print(f"{_icon('ok')} Tcl Server 脚本已创建: {script_path}")
    except Exception as e:
        print(f"{_icon('fail')} 创建脚本失败: {e}")
        return 1

    print(f"\n{_icon('info')} 安装到 Vivado_init.tcl...")
    if installer.install_to_vivado(port=settings.tcp_port):
        init_tcl_path = installer.get_init_tcl_path()
        if init_tcl_path:
            print(f"{_icon('ok')} 已安装到: {init_tcl_path}")
    else:
        print(f"{_icon('warn')} 安装到 Vivado_init.tcl 失败（可继续使用手动启动方式）")

    print(f"\n{_icon('info')} 创建启动脚本...")
    startup_script = create_startup_script(vivado_info.install_path, script_path, settings.tcp_port)
    startup_path = CONFIG_DIR / "start_server.bat"
    try:
        with open(startup_path, "w", encoding="utf-8") as f:
            f.write(startup_script)
        print(f"{_icon('ok')} 启动脚本已创建: {startup_path}")
    except Exception as e:
        print(f"{_icon('fail')} 创建启动脚本失败: {e}")
        return 1

    print(f"\n{_icon('info')} 安装后自检:")
    self_check_results = _run_install_self_check()
    failed_checks = [result for result in self_check_results if not result.passed]
    for result in self_check_results:
        print(f"  {_status_icon(result.passed)} {result.name}: {result.message}")
        if result.details:
            for line in result.details.split("\n"):
                print(f"    {line}")
        if not result.passed and result.fix_suggestion:
            print("    修复建议:")
            for line in result.fix_suggestion.split("\n"):
                print(f"      {line}")

    print("\n" + "=" * 60)
    if failed_checks:
        print(f"{_icon('fail')} 安装完成，但安装后自检失败")
    else:
        print(f"{_icon('ok')} 安装完成")
    print("=" * 60)
    print("\n配置信息:")
    print(f"  Vivado 版本: {vivado_info.version}")
    print(f"  Vivado 路径: {vivado_info.install_path}")
    print(f"  TCP 端口: {settings.tcp_port}")
    print(f"  配置文件: {CONFIG_DIR / 'config.json'}")
    print(f"\n启动 Tcl Server:")
    print("  方式1: 启动 Vivado（自动加载 Tcl Server）")
    print(f"  方式2: {startup_path}")
    print("\n或手动启动:")
    print(f"  {vivado_info.executable} -mode tcl -source {script_path}")
    print("\nPATH 配置:")
    print("  如果 'gateflow' 命令不可用，请将当前 Python 环境的 Scripts 目录加入 PATH")
    print(r"  Windows: %APPDATA%\Python\PythonXX\Scripts")
    print("  Linux/macOS: ~/.local/bin")
    print(f"\n提示: 可通过设置 {ASCII_OUTPUT_ENV}=1 启用纯 ASCII CLI 输出。")

    return 0 if not failed_checks else 1


def cmd_uninstall(args) -> int:
    """
    执行 uninstall 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    print("=" * 60)
    print("GateFlow Tcl Server 卸载")
    print("=" * 60)

    settings = get_settings()

    # 确定 Vivado 路径（用于从 Vivado_init.tcl 移除）
    vivado_info = None
    if args.path:
        vivado_path = Path(args.path)
        if vivado_path.exists():
            vivado_info = VivadoDetector._validate_vivado_path(vivado_path)
    else:
        # 优先检查配置文件中的路径
        config_vivado_path = settings.vivado_path
        if config_vivado_path:
            vivado_info = VivadoDetector._validate_vivado_path(Path(config_vivado_path))
        else:
            # 自动检测
            vivado_info = VivadoDetector.detect_vivado()

    # 从 Vivado_init.tcl 移除
    if vivado_info:
        print("\n📦 从 Vivado_init.tcl 移除...")
        installer = TclServerInstaller(vivado_info)
        if installer.uninstall_from_vivado():
            print("✓ 已从 Vivado_init.tcl 移除")
        else:
            print("⚠ 从 Vivado_init.tcl 移除失败")

    # 删除配置文件
    config_file = CONFIG_DIR / "config.json"
    if config_file.exists():
        try:
            config_file.unlink()
            print(f"\n✓ 已删除配置文件: {config_file}")
        except Exception as e:
            print(f"❌ 删除配置文件失败: {e}")
            return 1

    # 删除 Tcl Server 脚本
    script_path = CONFIG_DIR / "tcl_server.tcl"
    if script_path.exists():
        try:
            script_path.unlink()
            print(f"✓ 已删除脚本文件: {script_path}")
        except Exception as e:
            print(f"❌ 删除脚本文件失败: {e}")
            return 1

    # 删除启动脚本
    startup_path = CONFIG_DIR / "start_server.bat"
    if startup_path.exists():
        try:
            startup_path.unlink()
            print(f"✓ 已删除启动脚本: {startup_path}")
        except Exception as e:
            print(f"❌ 删除启动脚本失败: {e}")
            return 1

    # 重置全局配置
    reset_settings()

    print("\n✓ 卸载完成!")
    return 0


def cmd_status(args) -> int:
    """
    执行 status 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    print("=" * 60)
    print("GateFlow 状态检查")
    print("=" * 60)

    override_kwargs = {}
    if args.port is not None:
        override_kwargs["tcp_port"] = args.port

    settings = get_settings(**override_kwargs)
    probe_port = args.port if args.port is not None else settings.tcp_port
    diagnostics = EnvironmentDiagnostics()
    manifest = build_capability_manifest()
    vivado_info = diagnostics._detect_vivado_info()
    tcl_server_status = diagnostics.get_tcl_server_status(probe_port)

    print(f"\n{_icon('info')} 配置信息:")
    config_file = CONFIG_DIR / "config.json"
    print(f"  {_status_icon(config_file.exists())} 配置文件: {config_file}")
    if settings.vivado_path:
        print(f"  {_icon('ok')} Vivado 路径: {settings.vivado_path}")
    else:
        print(f"  {_icon('warn')} Vivado 路径: 未配置")
    print(f"  {_icon('ok')} TCP 端口: {probe_port}")
    print(f"  {_icon('ok')} 日志级别: {settings.log_level}")
    print(f"  {_icon('ok')} MCP 工具数: {manifest['tool_count']}")

    print(f"\n{_icon('info')} Vivado 安装检测:")
    if vivado_info:
        print(f"  {_icon('ok')} 检测到 Vivado {vivado_info.version}")
        print(f"  {_icon('ok')} 安装路径: {vivado_info.install_path}")
        print(f"  {_icon('ok')} 可执行文件: {vivado_info.executable}")
    else:
        print(f"  {_icon('warn')} 未检测到 Vivado 安装")
        print("  请确保 Vivado 已正确安装")

    print(f"\n{_icon('info')} Tcl Server 分层状态:")
    fields = [
        ("config_present", "配置文件"),
        ("script_present", "tcl_server.tcl"),
        ("startup_script_present", "start_server.bat"),
        ("vivado_init_present", "Vivado_init.tcl"),
        ("vivado_init_contains_gateflow", "Vivado_init.tcl 包含 GateFlow 注入"),
        ("tcp_listener_ok", "TCP 监听"),
        ("tcp_protocol_ok", "TCP 协议"),
        ("effective_runtime_ok", "有效运行态"),
    ]
    for key, label in fields:
        print(f"  {_status_icon(bool(tcl_server_status[key]))} {label}: {tcl_server_status[key]}")
    print(f"  {_status_icon(bool(tcl_server_status['passed']))} 总结: {tcl_server_status['summary']}")
    listener_message = tcl_server_status.get("listener_message")
    protocol_message = tcl_server_status.get("protocol_message")
    if listener_message:
        print(f"    listener: {listener_message}")
    if protocol_message:
        print(f"    protocol: {protocol_message}")
    if tcl_server_status["vivado_init_path"]:
        print(f"    Vivado_init.tcl 路径: {tcl_server_status['vivado_init_path']}")
    if tcl_server_status["protocol_details"]:
        print(f"    协议响应: {tcl_server_status['protocol_details']}")
    if tcl_server_status["fix_suggestion"]:
        print(f"    建议: {tcl_server_status['fix_suggestion']}")

    if vivado_info:
        print(f"\n{_icon('info')} Vivado 批处理测试:")
        try:
            engine = TclEngine(vivado_path=vivado_info.install_path)
            result = engine.execute("puts \"GateFlow 连接测试成功\"")
            if result.success:
                print(f"  {_icon('ok')} Vivado 连接正常")
                print(f"  {_icon('ok')} 执行时间: {result.execution_time:.2f}秒")
            else:
                print(f"  {_icon('warn')} Vivado 连接测试失败")
                if result.errors:
                    for error in result.errors[:3]:
                        print(f"    - {error}")
        except Exception as e:
            print(f"  {_icon('warn')} Vivado 连接测试失败: {e}")

    print("\n" + "=" * 60)
    return 0


def cmd_activate(args) -> int:
    """
    执行 activate 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    print("=" * 60)
    print("GateFlow 许可证激活")
    print("=" * 60)
    print("\nℹ GateFlow 是开源软件，无需激活许可证")
    print("  您可以直接使用所有功能")
    print("\n如果您购买了商业支持，请联系 support@gateflow.dev")
    return 0


def cmd_doctor(args) -> int:
    """
    执行 doctor 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    diagnostics = EnvironmentDiagnostics()
    settings = get_settings()
    port = args.port if args.port is not None else settings.tcp_port
    results = diagnostics.run_all_diagnostics(port=port)
    tcl_server_status = diagnostics.get_tcl_server_status(port)

    if getattr(args, 'json', False):
        output = {
            "gateflow_version": __version__,
            "tcp_port": port,
            "ascii_output": _ascii_output_enabled(),
            "tcl_server": tcl_server_status,
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details,
                    "fix_suggestion": r.fix_suggestion,
                }
                for r in results
            ],
            "summary": {
                "total": len(results),
                "passed": sum(1 for r in results if r.passed),
                "failed": sum(1 for r in results if not r.passed),
            }
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0 if all(r.passed for r in results) else 1

    print("=" * 60)
    print("GateFlow 环境诊断")
    print("=" * 60)
    print()

    for result in results:
        status_symbol = "[OK]" if result.passed else "[FAIL]"
        print(f"{status_symbol} {result.name}: {result.message}")
        if result.details:
            for line in result.details.split("\n"):
                print(f"  {line}")
        if not result.passed and result.fix_suggestion:
            print("  修复建议:")
            for line in result.fix_suggestion.split("\n"):
                print(f"    {line}")
        print()

    print("[INFO] tcl_server 分层状态:")
    fields = [
        "config_present",
        "script_present",
        "startup_script_present",
        "vivado_init_present",
        "vivado_init_contains_gateflow",
        "tcp_listener_ok",
        "tcp_protocol_ok",
        "effective_runtime_ok",
    ]
    for field in fields:
        print(f"  {field}: {tcl_server_status[field]}")
    print(f"  overall_state: {tcl_server_status['overall_state']}")
    print(f"  summary: {tcl_server_status['summary']}")
    if tcl_server_status["fix_suggestion"]:
        print(f"  fix_suggestion: {tcl_server_status['fix_suggestion']}")
    if tcl_server_status["protocol_details"]:
        print(f"  protocol_details: {tcl_server_status['protocol_details']}")
    print()

    passed_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    print("=" * 60)
    print(f"诊断完成: {passed_count}/{total_count} 项通过")
    print("=" * 60)
    return 0 if passed_count == total_count else 1


def _print_run_result(result: dict[str, Any]) -> None:
    """Print a compact run status payload."""
    print("=" * 60)
    print("GateFlow Vivado Run")
    print("=" * 60)
    print(f"{_status_icon(bool(result.get('success')))} {result.get('message', '')}")
    print(f"  run_name: {result.get('run_name')}")
    print(f"  status: {result.get('status')}")
    print(f"  error: {result.get('error')}")
    if "status_source" in result:
        print(f"  status_source: {result.get('status_source')}")
    if "progress" in result:
        print(f"  progress: {result.get('progress')}")
    if "current_step" in result:
        print(f"  current_step: {result.get('current_step')}")
    if "needs_refresh" in result:
        print(f"  needs_refresh: {result.get('needs_refresh')}")
    if "is_running" in result:
        print(f"  is_running: {result.get('is_running')}")
        print(f"  is_complete: {result.get('is_complete')}")
        print(f"  is_failed: {result.get('is_failed')}")
    if "last_known_step" in result:
        print(f"  last_known_step: {result.get('last_known_step')}")
    if "progress_hint" in result:
        print(f"  progress_hint: {result.get('progress_hint')}")
    if result.get("artifacts"):
        print("  artifacts:")
        for key, value in result["artifacts"].items():
            print(f"    {key}: {value}")
    if result.get("messages") is not None:
        print(f"  matched_count: {result.get('matched_count', 0)}")
        if result.get("source"):
            print(f"  source: {result.get('source')}")
        for item in result.get("messages", []):
            print(f"  [{item.get('severity', 'info')}] {item.get('text', '')}")
    if result.get("details"):
        print(f"  details: {result.get('details')}")


def cmd_runs(args) -> int:
    """Execute `gateflow runs ...` commands."""
    from gateflow import GateFlow

    gf = GateFlow()
    if args.runs_command == "status":
        result = asyncio.run(gf.get_run_status(args.run_name))
    elif args.runs_command == "progress":
        result = asyncio.run(gf.get_run_progress(args.run_name))
    elif args.runs_command == "messages":
        result = asyncio.run(
            gf.get_run_messages(
                args.run_name,
                limit=args.limit,
                severity=args.severity,
            )
        )
    elif args.runs_command == "wait":
        result = asyncio.run(
            gf.wait_for_run(
                args.run_name,
                timeout=args.timeout,
                poll_interval=args.poll_interval,
            )
        )
    elif args.runs_command == "launch":
        result = asyncio.run(
            gf.launch_run(
                args.run_name,
                to_step=args.to_step,
                jobs=args.jobs,
            )
        )
    else:
        print(f"{_icon('fail')} 未知 runs 子命令: {args.runs_command}")
        return 1

    _print_run_result(result)
    return 0 if result.get("success", False) else 1


def cmd_gui(args) -> int:
    """Execute `gateflow gui ...` commands."""
    from gateflow import GateFlow
    from gateflow.engine import get_engine_manager

    gf = GateFlow()
    if args.gui_command == "open":
        result = asyncio.run(gf.open_project_gui(args.xpr_path, tcp_port=args.port))
    elif args.gui_command == "attach":
        result = asyncio.run(gf.attach_gui_session(tcp_port=args.port, project_path=args.xpr_path))
    elif args.gui_command == "status":
        result = asyncio.run(gf.get_session_mode_info())
    elif args.gui_command == "close":
        asyncio.run(get_engine_manager().close())
        result = {
            "success": True,
            "message": "GUI 会话已关闭",
            "error": None,
        }
    elif args.gui_command == "logs":
        result = asyncio.run(gf.get_session_mode_info())
    else:
        print(f"{_icon('fail')} 未知 gui 子命令: {args.gui_command}")
        return 1

    print("=" * 60)
    print("GateFlow Vivado GUI")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("success", True) else 1


def cmd_capabilities(args) -> int:
    """
    执行 capabilities 命令

    Args:
        args: 命令行参数

    Returns:
        退出码
    """
    manifest = build_capability_manifest()

    if getattr(args, "json", False):
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print("GateFlow Capability Manifest")
        print("=" * 60)
        print(f"工具总数: {manifest['tool_count']}")
        print("\n分类统计:")
        for category, count in sorted(manifest["categories"].items()):
            print(f"  - {category}: {count}")
        print("\n风险统计:")
        for risk, count in sorted(manifest["risk_levels"].items()):
            print(f"  - {risk}: {count}")

    if getattr(args, "write", False):
        output = write_capability_artifacts(
            markdown_path=getattr(args, "markdown_path", None),
            manifest_path=getattr(args, "manifest_path", None),
        )
        print(f"\n{_icon('ok')} 已写出能力清单文件:")
        print(f"  Markdown: {output['markdown_path']}")
        print(f"  JSON:     {output['manifest_path']}")
        if _ascii_output_enabled():
            print(f"  ASCII 模式: 由 {ASCII_OUTPUT_ENV}=1 启用")

    return 0


def create_startup_script(vivado_path: Path, script_path: Path, port: int) -> str:
    """
    创建启动脚本

    Args:
        vivado_path: Vivado 安装路径
        script_path: Tcl 脚本路径
        port: TCP 端口号

    Returns:
        启动脚本内容
    """
    return f"""@echo off
REM GateFlow Tcl Server 启动脚本

REM 设置 UTF-8 编码
chcp 65001 > nul

echo ========================================
echo GateFlow Tcl Server
echo ========================================
echo.
echo Vivado 路径: {vivado_path}
echo Tcl 脚本: {script_path}
echo TCP 端口: {port}
echo.
echo 启动中...
echo.

REM 设置 Vivado 环境
call "{vivado_path}\\settings64.bat"

REM 启动 Vivado Tcl 模式并加载脚本
vivado -mode tcl -source "{script_path}"

pause
"""


def setup_logging(verbose: bool = False, level: str | None = None) -> None:
    """配置日志"""
    if level:
        log_level = getattr(logging, level.upper(), logging.INFO)
    else:
        log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """
    CLI 主入口

    Returns:
        退出码
    """
    parser = create_parser()
    args = parser.parse_args()
    _configure_console_output()

    # 设置日志级别
    log_level = args.log_level if hasattr(args, 'log_level') else None
    setup_logging(verbose=getattr(args, "verbose", False), level=log_level)

    try:
        if args.command == "install":
            return cmd_install(args)
        elif args.command == "uninstall":
            return cmd_uninstall(args)
        elif args.command == "status":
            return cmd_status(args)
        elif args.command == "activate":
            return cmd_activate(args)
        elif args.command == "doctor":
            return cmd_doctor(args)
        elif args.command == "gui":
            return cmd_gui(args)
        elif args.command == "runs":
            return cmd_runs(args)
        elif args.command == "capabilities":
            return cmd_capabilities(args)
        else:
            # 无子命令时启动 MCP 服务器
            print("=" * 60)
            print("GateFlow MCP Server")
            print("=" * 60)
            
            # 获取配置（支持 CLI 参数覆盖）
            override_kwargs = {}
            if hasattr(args, 'tcp_port') and args.tcp_port is not None:
                override_kwargs["tcp_port"] = args.tcp_port
            if hasattr(args, 'log_level') and args.log_level is not None:
                override_kwargs["log_level"] = args.log_level
            
            settings = get_settings(**override_kwargs)
            
            print(f"\n版本: {__version__}")
            print(f"配置目录: {CONFIG_DIR}")
            print(f"TCP 端口: {settings.tcp_port}")
            print(f"日志级别: {settings.log_level}")
            print("\n正在启动 MCP 服务器...")
            print("提示: 按 Ctrl+C 停止服务器\n")

            from gateflow.server import main as server_main
            server_main()
            return 0
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
        return 0
    except Exception as e:
        logger.exception("命令执行失败")
        print(f"\n❌ 错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
