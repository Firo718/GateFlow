"""
构建 MCP 工具。

提供 Vivado 综合、实现和比特流生成相关的 MCP 工具接口。
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.engine import (
    EngineManager,
    EngineMode,
    get_engine_manager,
    ensure_engine_initialized,
)
from gateflow.vivado.implementation import ImplementationTclGenerator
from gateflow.vivado.synthesis import SynthesisTclGenerator
from gateflow.tools.context_utils import AsyncContextBlockedProxy, project_context_error_message

logger = logging.getLogger(__name__)

# 全局状态管理
_engine_manager: EngineManager | None = None
_synthesis_manager: 'SynthesisManagerAdapter | None' = None
_implementation_manager: 'ImplementationManagerAdapter | None' = None

_RUN_COMPLETE_MARKERS = ("complete", "completed")
_RUN_FAILED_MARKERS = ("fail", "error", "cancel")
_RUN_RUNNING_MARKERS = ("running", "route_design", "place_design", "opt_design", "synth_design", "write_bitstream")
_RUN_QUEUED_MARKERS = ("queued", "pending")
_RUN_STEP_PATTERNS = (
    "synth_design",
    "opt_design",
    "place_design",
    "route_design",
    "write_bitstream",
)


def _result_success(result: Any) -> bool:
    """Handle both dict-style and object-style result payloads."""
    if isinstance(result, dict):
        return bool(result.get("success", False))
    return bool(getattr(result, "success", False))


def _result_text(result: Any) -> str:
    """Return primary text payload for both dict and object results."""
    if isinstance(result, dict):
        for key in ("result", "data", "output", "message"):
            value = result.get(key)
            if value is not None:
                return str(value)
        return ""
    for attr in ("result", "data", "output", "message"):
        value = getattr(result, attr, None)
        if value is not None:
            return str(value)
    return ""


def _result_errors(result: Any) -> list[str]:
    """Extract normalized error strings."""
    errors: list[str] = []
    if isinstance(result, dict):
        raw_errors = result.get("errors")
        if isinstance(raw_errors, list):
            errors.extend(str(item) for item in raw_errors if item)
        elif raw_errors:
            errors.append(str(raw_errors))
        raw_error = result.get("error")
        if raw_error:
            errors.append(str(raw_error))
        return errors

    raw_errors = getattr(result, "errors", None)
    if isinstance(raw_errors, list):
        errors.extend(str(item) for item in raw_errors if item)
    raw_error = getattr(result, "error", None)
    if raw_error:
        errors.append(str(getattr(raw_error, "message", raw_error)))
    return errors


def _dedupe_strings(items: list[str]) -> list[str]:
    """Preserve order while removing duplicates and empty strings."""
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _extract_last_known_step(*texts: str) -> str:
    """Return the latest known implementation/synthesis step from status or logs."""
    combined = "\n".join(texts).lower()
    found: list[str] = []
    for step in _RUN_STEP_PATTERNS:
        if step in combined:
            found.append(step)
    return found[-1] if found else "unknown"


def _derive_progress_hint(status: str, last_known_step: str) -> str:
    """Map raw status to a small text enum."""
    normalized = status.lower().strip()
    if any(marker in normalized for marker in _RUN_FAILED_MARKERS):
        return "failed"
    if any(marker in normalized for marker in _RUN_COMPLETE_MARKERS):
        return "completed"
    if "write_bitstream" in normalized and "run" in normalized:
        return "finishing"
    if any(marker in normalized for marker in _RUN_QUEUED_MARKERS):
        return "queued"
    if any(marker in normalized for marker in _RUN_RUNNING_MARKERS) or last_known_step != "unknown":
        return "running"
    return "unknown"


def _parse_progress_value(progress: str) -> str:
    """Normalize Vivado PROGRESS text while preserving unknown values."""
    return progress.strip() if progress and progress.strip() else "unknown"


def _parse_message_lines(lines: list[str], severity: str | None = None) -> list[dict[str, str]]:
    """Parse log/message lines into a stable severity/text structure."""
    severity_filter = _normalize_severity(severity) if severity else None
    messages: list[dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        match = re.search(r"\b(ERROR|CRITICAL WARNING|WARNING|INFO)\b\s*:?\s*(.*)", stripped, re.IGNORECASE)
        if match:
            sev = _normalize_severity(match.group(1))
            text = match.group(2).strip() or stripped
        else:
            sev = "info"
            text = stripped
        if severity_filter and sev != severity_filter:
            continue
        messages.append({"severity": sev, "text": text})
    return messages


def _parse_direct_messages(output: str, severity: str | None = None) -> tuple[list[dict[str, str]], str | None]:
    """Parse direct Vivado message query output."""
    severity_filter = _normalize_severity(severity) if severity else None
    messages: list[dict[str, str]] = []
    unavailable: str | None = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("__GATEFLOW_MESSAGES_UNAVAILABLE__|"):
            unavailable = line.split("|", 1)[1]
            continue
        if not line.startswith("__GATEFLOW_MESSAGE__|"):
            continue
        _, raw_severity, raw_text = (line.split("|", 2) + ["", ""])[:3]
        normalized = _normalize_severity(raw_severity or "info")
        if severity_filter and normalized != severity_filter:
            continue
        messages.append({"severity": normalized, "text": raw_text.strip()})
    return messages, unavailable


def _messages_query_tcl(limit: int) -> str:
    """Build a best-effort direct messages query that safely falls back if unsupported."""
    safe_limit = max(1, int(limit))
    return (
        f'set __gf_limit {safe_limit}; '
        'if {[catch {set __gf_messages [get_messages -quiet]} __gf_err]} { '
        'puts "__GATEFLOW_MESSAGES_UNAVAILABLE__|$__gf_err" '
        '} else { '
        'set __gf_count 0; '
        'foreach __gf_msg $__gf_messages { '
        'if {$__gf_count >= $__gf_limit} { break }; '
        'set __gf_sev "info"; '
        'catch {set __gf_sev [get_property SEVERITY $__gf_msg]}; '
        'set __gf_text [string map {\n " " \r " " | "/"} $__gf_msg]; '
        'catch {set __gf_text [string map {\n " " \r " " | "/"} [get_property MESSAGE $__gf_msg]]}; '
        'puts "__GATEFLOW_MESSAGE__|$__gf_sev|$__gf_text"; '
        'incr __gf_count '
        '} '
        '}'
    )


def _tail_lines(path: Path, limit: int = 200) -> list[str]:
    """Read the tail lines of a text file without failing the query path."""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-limit:]
    except Exception:
        return []


def _extract_file_paths(output: str, project_name: str = "") -> dict[str, str]:
    """
    从 Tcl 输出中提取文件路径。
    
    Args:
        output: Tcl 命令输出
        project_name: 项目名称
    
    Returns:
        包含各种文件路径的字典
    """
    paths = {}
    
    # 提取比特流路径
    bitstream_pattern = r"Writing bitstream (.+\.bit)"
    match = re.search(bitstream_pattern, output)
    if match:
        paths["bitstream_path"] = match.group(1)
    
    # 提取 LTX 文件路径（调试探针）
    ltx_pattern = r"Writing debug probes (.+\.ltx)"
    match = re.search(ltx_pattern, output)
    if match:
        paths["ltx_path"] = match.group(1)
    
    # 提取 DCP 路径
    dcp_pattern = r"Writing checkpoint (.+\.dcp)"
    match = re.search(dcp_pattern, output)
    if match:
        paths["checkpoint_path"] = match.group(1)
    
    # 提取报告路径
    report_pattern = r"Generating report (.+\.rpt)"
    match = re.search(report_pattern, output)
    if match:
        paths["report_path"] = match.group(1)
    
    # 提取综合报告路径（另一种格式）
    synth_report_pattern = r"Report (.+\.rpt) generated"
    match = re.search(synth_report_pattern, output)
    if match and "report_path" not in paths:
        paths["report_path"] = match.group(1)
    
    return paths


def _extract_timing_summary(output: str) -> dict[str, Any]:
    """
    从输出中提取时序摘要。
    
    Args:
        output: Tcl 命令输出
    
    Returns:
        时序摘要字典
    """
    timing = {}
    
    # 解析 Setup 时序
    wns_pattern = r'WNS[^(]*\([^)]*\)\s*:\s*([\d.-]+)'
    tns_pattern = r'TNS[^(]*\([^)]*\)\s*:\s*([\d.-]+)'
    
    wns_match = re.search(wns_pattern, output)
    tns_match = re.search(tns_pattern, output)
    
    if wns_match:
        timing['wns'] = float(wns_match.group(1))
    if tns_match:
        timing['tns'] = float(tns_match.group(1))
    
    # 解析 Hold 时序
    whs_pattern = r'WHS[^(]*\([^)]*\)\s*:\s*([\d.-]+)'
    ths_pattern = r'THS[^(]*\([^)]*\)\s*:\s*([\d.-]+)'
    
    whs_match = re.search(whs_pattern, output)
    ths_match = re.search(ths_pattern, output)
    
    if whs_match:
        timing['whs'] = float(whs_match.group(1))
    if ths_match:
        timing['ths'] = float(ths_match.group(1))
    
    # 判断时序是否满足
    wns = timing.get('wns', 0)
    whs = timing.get('whs', 0)
    timing['timing_met'] = wns >= 0 and whs >= 0
    
    return timing


_SEVERITY_RANK = {
    "info": 0,
    "warning": 1,
    "critical_warning": 2,
    "error": 3,
}


def _normalize_severity(value: str) -> str:
    """Normalize severity string to internal key."""
    return value.strip().lower().replace(" ", "_")


def _validate_min_severity(value: str) -> str:
    """Validate and normalize min severity."""
    normalized = _normalize_severity(value)
    if normalized not in _SEVERITY_RANK:
        supported = ", ".join(_SEVERITY_RANK.keys())
        raise ValueError(f"不支持的严重级别: {value}，可选值: {supported}")
    return normalized


def _extract_lint_findings(report: str) -> list[dict[str, str]]:
    """
    Extract lint-like findings from report text.

    Supports common Vivado report lines:
    - ERROR: ...
    - CRITICAL WARNING: ...
    - WARNING: ...
    - ... VIOLATED ...
    """
    findings: list[dict[str, str]] = []
    for raw_line in report.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        severity_match = re.search(
            r"\b(ERROR|CRITICAL WARNING|WARNING)\b\s*:?\s*(.*)",
            line,
            re.IGNORECASE,
        )
        if severity_match:
            severity = _normalize_severity(severity_match.group(1))
            message = severity_match.group(2).strip() or line
            findings.append({"severity": severity, "message": message})
            continue

        if "VIOLATED" in line.upper():
            findings.append({"severity": "warning", "message": line})

    return findings


def _summarize_lint_findings(
    report: str,
    min_severity: str,
    max_findings: int,
) -> dict[str, Any]:
    """Build lint summary payload from raw report text."""
    normalized = _validate_min_severity(min_severity)
    threshold = _SEVERITY_RANK[normalized]

    all_findings = _extract_lint_findings(report)
    matched = [
        item for item in all_findings if _SEVERITY_RANK.get(item["severity"], 0) >= threshold
    ]

    severity_counts: dict[str, int] = {}
    for item in matched:
        sev = item["severity"]
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    trimmed = matched[: max(1, max_findings)]
    return {
        "total_findings": len(all_findings),
        "matched_findings": len(matched),
        "severity_counts": severity_counts,
        "findings": [f"[{item['severity']}] {item['message']}" for item in trimmed],
    }


class RunObservabilityMixin:
    """Shared run launch/status/progress helpers for build adapters."""

    _engine: EngineManager

    def _log_candidates(self, run_directory: str | None) -> list[Path]:
        if not run_directory:
            return []
        run_dir = Path(run_directory)
        candidates = [
            run_dir / "runme.log",
            run_dir / "vivado.log",
        ]
        if run_dir.exists():
            candidates.extend(sorted(run_dir.glob("*.log")))
        return [path for path in candidates if path.exists()]

    def _log_text_for_step(self, run_directory: str | None) -> tuple[str, str | None]:
        for path in self._log_candidates(run_directory):
            lines = _tail_lines(path, limit=400)
            if lines:
                return "\n".join(lines), str(path)
        return "", None

    async def get_run_status(self, run_name: str) -> dict[str, Any]:
        """Return a stable run status payload from Vivado state."""
        status_result = await self._engine.execute(f'get_property STATUS [get_runs {run_name}]')
        if not _result_success(status_result):
            errors = _result_errors(status_result)
            error_text = "; ".join(errors) if errors else "run status query failed"
            error_code = "run_not_found" if "get_runs" in error_text.lower() else "run_status_query_failed"
            return {
                "success": False,
                "run_name": run_name,
                "status": None,
                "status_source": "vivado",
                "progress": "unknown",
                "current_step": "unknown",
                "needs_refresh": None,
                "is_running": False,
                "is_complete": False,
                "is_failed": False,
                "last_known_step": "unknown",
                "progress_hint": "unknown",
                "artifacts": {},
                "message": f"获取运行状态失败: {run_name}",
                "error": error_code,
                "details": error_text,
            }

        status = _result_text(status_result).strip() or "unknown"
        progress_result = await self._engine.execute(f'get_property PROGRESS [get_runs {run_name}]')
        progress = _parse_progress_value(_result_text(progress_result)) if _result_success(progress_result) else "unknown"
        current_step_result = await self._engine.execute(f'get_property CURRENT_STEP [get_runs {run_name}]')
        current_step = _result_text(current_step_result).strip() if _result_success(current_step_result) else "unknown"
        needs_refresh_result = await self._engine.execute(f'get_property NEEDS_REFRESH [get_runs {run_name}]')
        needs_refresh_text = _result_text(needs_refresh_result).strip() if _result_success(needs_refresh_result) else ""
        needs_refresh = None
        if needs_refresh_text:
            needs_refresh = needs_refresh_text in {"1", "true", "True"}
        dir_result = await self._engine.execute(f'get_property DIRECTORY [get_runs {run_name}]')
        run_directory = _result_text(dir_result).strip() if _result_success(dir_result) else None
        log_text, log_path = self._log_text_for_step(run_directory)

        last_known_step = current_step if current_step and current_step != "unknown" else _extract_last_known_step(status, progress, log_text)
        normalized_status = status.lower()
        if any(marker in normalized_status for marker in (*_RUN_COMPLETE_MARKERS, *_RUN_FAILED_MARKERS)):
            progress_basis = status
        else:
            progress_basis = progress if progress != "unknown" else status
        progress_hint = _derive_progress_hint(progress_basis, last_known_step)
        is_failed = progress_hint == "failed"
        is_complete = progress_hint == "completed"
        is_running = progress_hint in {"running", "finishing"}

        artifacts: dict[str, Any] = {}
        if run_directory:
            artifacts["run_directory"] = run_directory
        if log_path:
            artifacts["log_path"] = log_path

        return {
            "success": True,
            "run_name": run_name,
            "status": status,
            "status_source": "vivado",
            "progress": progress,
            "current_step": current_step,
            "needs_refresh": needs_refresh,
            "is_running": is_running,
            "is_complete": is_complete,
            "is_failed": is_failed,
            "last_known_step": last_known_step,
            "progress_hint": progress_hint,
            "artifacts": artifacts,
            "message": f"获取运行状态成功: {run_name}",
            "error": None,
        }

    async def get_run_progress(self, run_name: str) -> dict[str, Any]:
        """Return progress fields; v1 uses status/log hints rather than percentages."""
        result = await self.get_run_status(run_name)
        if result.get("success"):
            result["message"] = f"获取运行进度成功: {run_name}"
        return result

    async def get_run_messages(
        self,
        run_name: str,
        limit: int = 50,
        severity: str | None = None,
    ) -> dict[str, Any]:
        """Return recent messages from the run log, with severity classification."""
        status = await self.get_run_status(run_name)
        if not status.get("success", False):
            return {
                "success": False,
                "run_name": run_name,
                "status": status.get("status"),
                "messages": [],
                "matched_count": 0,
                "message": f"获取运行消息失败: {run_name}",
                "error": status.get("error"),
            }

        direct_messages: list[dict[str, str]] = []
        direct_unavailable: str | None = None
        engine_mode = getattr(self._engine, "mode", None)
        if engine_mode != EngineMode.TCP:
            direct_result = await self._engine.execute(_messages_query_tcl(max(limit, 50)))
            if _result_success(direct_result):
                direct_messages, direct_unavailable = _parse_direct_messages(_result_text(direct_result), severity=severity)
        else:
            direct_unavailable = "direct_messages_unsupported_over_tcp"

        if direct_messages:
            messages = direct_messages[-limit:] if limit > 0 else direct_messages
            return {
                "success": True,
                "run_name": run_name,
                "status": status.get("status"),
                "messages": messages,
                "matched_count": len(messages),
                "message": f"获取运行消息成功: {run_name}",
                "error": None,
                "source": "vivado_messages",
            }

        log_path = status.get("artifacts", {}).get("log_path")
        lines = _tail_lines(Path(log_path), limit=max(100, limit * 10)) if log_path else []
        messages = _parse_message_lines(lines, severity=severity)
        if limit > 0:
            messages = messages[-limit:]
        return {
            "success": True,
            "run_name": run_name,
            "status": status.get("status"),
            "messages": messages,
            "matched_count": len(messages),
            "message": f"获取运行消息成功: {run_name}",
            "error": None,
            "source": "run_log_fallback",
            "details": direct_unavailable,
        }

    async def launch_run(
        self,
        run_name: str,
        *,
        to_step: str | None = None,
        jobs: int = 4,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Launch a Vivado run and immediately sample Vivado state."""
        command = f"launch_runs {run_name}"
        if to_step:
            command += f" -to_step {to_step}"
        if jobs:
            command += f" -jobs {jobs}"
        launch_result = await self._engine.execute(command, timeout=timeout)
        if not _result_success(launch_result):
            status = await self.get_run_status(run_name)
            errors = _dedupe_strings(_result_errors(launch_result))
            details = "; ".join(errors) if errors else None
            if details and ("超时" in details or "timeout" in details.lower()):
                if status.get("success", False):
                    return {
                        **status,
                        "success": True,
                        "message": f"run 已提交，但 launch 命令返回超时: {run_name}",
                        "error": None,
                        "details": details,
                    }
            return {
                **status,
                "success": False,
                "message": f"run 未成功提交: {run_name}",
                "error": "run_launch_failed",
                "details": details,
            }

        status = await self.get_run_status(run_name)
        if not status.get("success", False):
            return {
                **status,
                "success": False,
                "message": f"run 已提交，但状态查询失败: {run_name}",
                "error": "run_status_query_failed",
            }
        status["message"] = f"run 已提交: {run_name}"
        status["submitted"] = True
        return status

    async def wait_for_run(
        self,
        run_name: str,
        *,
        timeout: float | None = None,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """Poll Vivado state until the run completes, fails, or times out."""
        timeout = 3600.0 if timeout is None else float(timeout)
        poll_interval = max(0.1, float(poll_interval))
        start = asyncio.get_running_loop().time()
        last_status: dict[str, Any] | None = None

        while True:
            last_status = await self.get_run_status(run_name)
            if not last_status.get("success", False):
                return last_status
            if last_status.get("is_complete"):
                return {**last_status, "success": True, "message": f"run 已完成: {run_name}", "error": None}
            if last_status.get("is_failed"):
                return {**last_status, "success": False, "message": f"run 失败: {run_name}", "error": "run_failed"}

            elapsed = asyncio.get_running_loop().time() - start
            if elapsed >= timeout:
                final_status = await self.get_run_status(run_name)
                if final_status.get("success", False):
                    last_status = final_status
                return {
                    **(last_status or {}),
                    "success": False,
                    "run_name": run_name,
                    "message": f"run 已提交，但等待阶段超时: {run_name}",
                    "error": "run_wait_timeout",
                }
            await asyncio.sleep(poll_interval)

    async def launch_and_wait_run(
        self,
        run_name: str,
        *,
        jobs: int = 4,
        to_step: str | None = None,
        timeout: float | None = None,
        poll_interval: float = 2.0,
        pre_commands: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run pre-commands, launch a run, then poll for completion."""
        for command in pre_commands or []:
            pre_result = await self._engine.execute(command)
            if not _result_success(pre_result):
                errors = _dedupe_strings(_result_errors(pre_result))
                return {
                    "success": False,
                    "run_name": run_name,
                    "status": None,
                    "status_source": "vivado",
                    "is_running": False,
                    "is_complete": False,
                    "is_failed": False,
                    "last_known_step": "unknown",
                    "progress_hint": "unknown",
                    "artifacts": {},
                    "message": f"run 准备阶段失败: {run_name}",
                    "error": "run_launch_failed",
                    "details": "; ".join(errors) if errors else None,
                }

        launch = await self.launch_run(run_name, to_step=to_step, jobs=jobs)
        if not launch.get("success", False):
            return launch
        return await self.wait_for_run(run_name, timeout=timeout, poll_interval=poll_interval)


async def _ensure_engine() -> EngineManager:
    """
    确保引擎已初始化
    
    Returns:
        已初始化的 EngineManager 实例
    """
    global _engine_manager
    if _engine_manager is None:
        _engine_manager = await ensure_engine_initialized(EngineMode.AUTO)
    return _engine_manager


async def _get_synthesis_manager() -> 'SynthesisManagerAdapter':
    """
    获取或创建综合管理器实例。
    
    综合管理器使用统一的 EngineManager 执行 Tcl 命令。
    """
    global _synthesis_manager
    if project_context_error_message("build"):
        return AsyncContextBlockedProxy("build")  # type: ignore[return-value]
    if _synthesis_manager is None:
        manager = await _ensure_engine()
        _synthesis_manager = SynthesisManagerAdapter(manager)
    return _synthesis_manager


async def _get_implementation_manager() -> 'ImplementationManagerAdapter':
    """
    获取或创建实现管理器实例。
    
    实现管理器使用统一的 EngineManager 执行 Tcl 命令。
    """
    global _implementation_manager
    if project_context_error_message("build"):
        return AsyncContextBlockedProxy("build")  # type: ignore[return-value]
    if _implementation_manager is None:
        manager = await _ensure_engine()
        _implementation_manager = ImplementationManagerAdapter(manager)
    return _implementation_manager


class SynthesisManagerAdapter(RunObservabilityMixin):
    """
    综合管理器适配器
    
    将 EngineManager 适配为综合管理器所需的接口，
    使现有的综合功能可以无缝使用新的引擎系统。
    """
    
    def __init__(self, engine_manager: EngineManager):
        """
        初始化适配器
        
        Args:
            engine_manager: EngineManager 实例
        """
        self._engine = engine_manager
    
    async def run_synthesis(
        self,
        run_name: str = "synth_1",
        jobs: int = 4,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        运行综合
        
        Args:
            run_name: 综合运行名称
            jobs: 并行任务数
            timeout: 超时时间（秒）
        
        Returns:
            运行结果
        """
        run_result = await self.launch_and_wait_run(
            run_name,
            jobs=jobs,
            timeout=timeout or 3600.0,
            pre_commands=[SynthesisTclGenerator.reset_synthesis_tcl(run_name)],
        )

        if run_result.get("success", False):
            # 获取资源利用率摘要
            utilization = None
            try:
                util_result = await self.get_utilization_report()
                if util_result.get("success"):
                    utilization = util_result.get("utilization")
            except Exception:
                pass
            return {
                "success": True,
                "status": run_result.get("status"),
                "message": f"综合运行成功: {run_name}",
                "report_path": run_result.get("artifacts", {}).get("log_path"),
                "checkpoint_path": None,
                "utilization": utilization,
                "last_known_step": run_result.get("last_known_step"),
                "progress_hint": run_result.get("progress_hint"),
                "artifacts": run_result.get("artifacts", {}),
            }
        return {
            "success": False,
            "status": run_result.get("status"),
            "message": run_result.get("message", "综合运行失败"),
            "error": run_result.get("error"),
            "last_known_step": run_result.get("last_known_step"),
            "progress_hint": run_result.get("progress_hint"),
            "artifacts": run_result.get("artifacts", {}),
        }

    async def start_synthesis(
        self,
        run_name: str = "synth_1",
        jobs: int = 4,
    ) -> dict[str, Any]:
        """Launch synthesis without waiting for completion."""
        return await self.launch_run(run_name, jobs=jobs)
    
    async def get_utilization_report(
        self,
        output_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        获取资源利用率报告
        
        Args:
            output_path: 输出文件路径
        
        Returns:
            资源利用率字典
        """
        # 先打开综合设计
        open_result = await self._engine.execute(
            SynthesisTclGenerator.open_synthesized_design_tcl()
        )
        
        if not open_result["success"]:
            return {
                "success": False,
                "utilization": {},
                "message": "无法打开综合设计",
                "error": "; ".join(open_result.get("errors", [])),
            }
        
        # 获取利用率报告
        from pathlib import Path
        command = SynthesisTclGenerator.get_utilization_report_tcl(
            Path(output_path) if output_path else None
        )
        result = await self._engine.execute(command)
        
        utilization = {}
        if result["success"]:
            utilization = self._parse_utilization_report(result.get("output", ""))
        
        return {
            "success": result["success"],
            "utilization": utilization,
            "raw_report": result.get("output", ""),
            "message": "获取资源利用率报告成功" if result["success"] else "获取资源利用率报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }
    
    def _parse_utilization_report(self, report: str) -> dict:
        """解析资源利用率报告"""
        utilization = {}
        
        patterns = {
            'slice_lut': r'Slice LUTs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'slice_registers': r'Slice Registers\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'lut': r'LUT as Logic\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'bram': r'Block RAM Tile\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'dsp': r'DSPs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'iob': r'IO\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, report)
            if match:
                utilization[key] = {
                    'used': int(match.group(1)),
                    'available': int(match.group(2)),
                    'utilization': float(match.group(3)),
                }
        
        return utilization


class ImplementationManagerAdapter(RunObservabilityMixin):
    """
    实现管理器适配器
    
    将 EngineManager 适配为实现管理器所需的接口，
    使现有的实现功能可以无缝使用新的引擎系统。
    """
    
    def __init__(self, engine_manager: EngineManager):
        """
        初始化适配器
        
        Args:
            engine_manager: EngineManager 实例
        """
        self._engine = engine_manager
    
    async def run_implementation(
        self,
        run_name: str = "impl_1",
        jobs: int = 4,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        运行实现
        
        Args:
            run_name: 实现运行名称
            jobs: 并行任务数
            timeout: 超时时间（秒）
        
        Returns:
            运行结果
        """
        run_result = await self.launch_and_wait_run(
            run_name,
            jobs=jobs,
            timeout=timeout or 3600.0,
            pre_commands=[ImplementationTclGenerator.reset_implementation_tcl(run_name)],
        )

        if run_result.get("success", False):
            # 获取资源利用率摘要
            utilization = None
            try:
                util_result = await self.get_utilization_report()
                if util_result.get("success"):
                    utilization = util_result.get("utilization")
            except Exception:
                pass
            
            return {
                "success": True,
                "status": run_result.get("status"),
                "message": f"实现运行成功: {run_name}",
                "report_path": run_result.get("artifacts", {}).get("log_path"),
                "checkpoint_path": None,
                "utilization": utilization,
                "timing_summary": None,
                "last_known_step": run_result.get("last_known_step"),
                "progress_hint": run_result.get("progress_hint"),
                "artifacts": run_result.get("artifacts", {}),
            }
        return {
            "success": False,
            "status": run_result.get("status"),
            "message": run_result.get("message", "实现运行失败"),
            "error": run_result.get("error"),
            "last_known_step": run_result.get("last_known_step"),
            "progress_hint": run_result.get("progress_hint"),
            "artifacts": run_result.get("artifacts", {}),
        }

    async def start_implementation(
        self,
        run_name: str = "impl_1",
        jobs: int = 4,
    ) -> dict[str, Any]:
        """Launch implementation without waiting for completion."""
        return await self.launch_run(run_name, jobs=jobs)
    
    async def generate_bitstream(
        self,
        run_name: str = "impl_1",
        output_path: Optional[str] = None,
        jobs: int = 4,
        timeout: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        生成比特流
        
        Args:
            run_name: 实现运行名称
            output_path: 输出路径
            timeout: 超时时间（秒）
        
        Returns:
            生成结果
        """
        run_result = await self.launch_and_wait_run(
            run_name,
            jobs=jobs,
            to_step="write_bitstream",
            timeout=timeout or 3600.0,
        )

        if run_result.get("success", False):
            bitstream_path = None
            ltx_path = None
            path_result = await self._engine.execute(
                ImplementationTclGenerator.get_bitstream_path_tcl(run_name)
            )
            if _result_success(path_result):
                base_dir = _result_text(path_result).strip()
                top_result = await self._engine.execute("get_property top [current_fileset]")
                top_name = _result_text(top_result).strip() if _result_success(top_result) else run_name
                bitstream_path = f"{base_dir}/{top_name}.bit"
                possible_ltx = Path(base_dir) / f"{top_name}.ltx"
                if possible_ltx.exists():
                    ltx_path = str(possible_ltx)

            # 获取文件大小
            file_size = None
            if bitstream_path:
                try:
                    # 尝试获取文件大小
                    size_result = await self._engine.execute(f"file size {bitstream_path}")
                    if _result_success(size_result):
                        size_str = _result_text(size_result).strip()
                        try:
                            file_size = int(size_str)
                        except ValueError:
                            pass
                except Exception:
                    pass
            
            return {
                "success": True,
                "bitstream_path": bitstream_path,
                "ltx_path": ltx_path,
                "size": file_size,
                "message": f"比特流生成成功",
                "status": run_result.get("status"),
                "last_known_step": run_result.get("last_known_step"),
                "progress_hint": run_result.get("progress_hint"),
                "artifacts": run_result.get("artifacts", {}),
            }
        return {
            "success": False,
            "bitstream_path": None,
            "ltx_path": None,
            "size": None,
            "message": run_result.get("message", "比特流生成失败"),
            "error": run_result.get("error"),
            "status": run_result.get("status"),
            "last_known_step": run_result.get("last_known_step"),
            "progress_hint": run_result.get("progress_hint"),
            "artifacts": run_result.get("artifacts", {}),
        }
    
    async def get_utilization_report(
        self,
        output_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        获取资源利用率报告
        
        Args:
            output_path: 输出文件路径
        
        Returns:
            资源利用率字典
        """
        # 先打开实现设计
        open_result = await self._engine.execute(
            ImplementationTclGenerator.open_implemented_design_tcl()
        )
        
        if not open_result["success"]:
            return {
                "success": False,
                "utilization": {},
                "message": "无法打开实现设计",
                "error": "; ".join(open_result.get("errors", [])),
            }
        
        # 获取利用率报告
        from pathlib import Path
        command = ImplementationTclGenerator.get_utilization_report_tcl(
            Path(output_path) if output_path else None
        )
        result = await self._engine.execute(command)
        
        utilization = {}
        if result["success"]:
            utilization = self._parse_utilization_report(result.get("output", ""))
        
        return {
            "success": result["success"],
            "utilization": utilization,
            "raw_report": result.get("output", ""),
            "message": "获取资源利用率报告成功" if result["success"] else "获取资源利用率报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }
    
    async def get_timing_report(
        self,
        output_path: Optional[str] = None,
        max_paths: int = 10,
    ) -> dict[str, Any]:
        """
        获取时序报告
        
        Args:
            output_path: 输出文件路径
            max_paths: 最大路径数
        
        Returns:
            时序信息字典
        """
        # 先打开实现设计
        open_result = await self._engine.execute(
            ImplementationTclGenerator.open_implemented_design_tcl()
        )
        
        if not open_result["success"]:
            return {
                "success": False,
                "timing": {},
                "message": "无法打开实现设计",
                "error": "; ".join(open_result.get("errors", [])),
            }
        
        # 获取时序报告
        from pathlib import Path
        command = ImplementationTclGenerator.get_timing_report_tcl(
            Path(output_path) if output_path else None,
            max_paths
        )
        result = await self._engine.execute(command)
        
        timing = {}
        if result["success"]:
            timing = self._parse_timing_report(result.get("output", ""))
        
        return {
            "success": result["success"],
            "timing": timing,
            "raw_report": result.get("output", ""),
            "message": "获取时序报告成功" if result["success"] else "获取时序报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }

    async def get_drc_report(
        self,
        output_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取 DRC 报告。"""
        open_result = await self._engine.execute(
            ImplementationTclGenerator.open_implemented_design_tcl()
        )
        if not open_result["success"]:
            return {
                "success": False,
                "raw_report": "",
                "message": "无法打开实现设计",
                "error": "; ".join(open_result.get("errors", [])),
            }

        from pathlib import Path

        command = ImplementationTclGenerator.get_drc_report_tcl(
            Path(output_path) if output_path else None
        )
        result = await self._engine.execute(command)
        return {
            "success": result["success"],
            "raw_report": result.get("output", ""),
            "message": "获取 DRC 报告成功" if result["success"] else "获取 DRC 报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }

    async def get_methodology_report(
        self,
        output_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取 methodology 报告。"""
        open_result = await self._engine.execute(
            ImplementationTclGenerator.open_implemented_design_tcl()
        )
        if not open_result["success"]:
            return {
                "success": False,
                "raw_report": "",
                "message": "无法打开实现设计",
                "error": "; ".join(open_result.get("errors", [])),
            }

        from pathlib import Path

        command = ImplementationTclGenerator.get_methodology_report_tcl(
            Path(output_path) if output_path else None
        )
        result = await self._engine.execute(command)
        return {
            "success": result["success"],
            "raw_report": result.get("output", ""),
            "message": "获取 methodology 报告成功" if result["success"] else "获取 methodology 报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }

    async def get_power_report(
        self,
        output_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """获取功耗报告。"""
        open_result = await self._engine.execute(
            ImplementationTclGenerator.open_implemented_design_tcl()
        )
        if not open_result["success"]:
            return {
                "success": False,
                "raw_report": "",
                "message": "无法打开实现设计",
                "error": "; ".join(open_result.get("errors", [])),
            }

        from pathlib import Path

        command = ImplementationTclGenerator.get_power_report_tcl(
            Path(output_path) if output_path else None
        )
        result = await self._engine.execute(command)
        return {
            "success": result["success"],
            "raw_report": result.get("output", ""),
            "message": "获取功耗报告成功" if result["success"] else "获取功耗报告失败",
            "error": "; ".join(result.get("errors", [])) if not result["success"] else None,
        }

    async def get_run_status(self, run_name: str) -> dict[str, Any]:
        """获取任意 run 状态。"""
        return await RunObservabilityMixin.get_run_status(self, run_name)
    
    def _parse_utilization_report(self, report: str) -> dict:
        """解析资源利用率报告"""
        utilization = {}
        
        patterns = {
            'slice_lut': r'Slice LUTs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'slice_registers': r'Slice Registers\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'lut': r'LUT as Logic\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'bram': r'Block RAM Tile\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'dsp': r'DSPs\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
            'iob': r'IO\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, report)
            if match:
                utilization[key] = {
                    'used': int(match.group(1)),
                    'available': int(match.group(2)),
                    'utilization': float(match.group(3)),
                }
        
        return utilization
    
    def _parse_timing_report(self, report: str) -> dict:
        """解析时序报告"""
        timing = {}
        
        # 解析 Setup 时序
        wns_pattern = r'WNS\(ns\)\s*:\s*([\d.-]+)'
        tns_pattern = r'TNS\(ns\)\s*:\s*([\d.-]+)'
        
        wns_match = re.search(wns_pattern, report)
        tns_match = re.search(tns_pattern, report)
        
        if wns_match:
            timing['wns'] = float(wns_match.group(1))
        if tns_match:
            timing['tns'] = float(tns_match.group(1))
        
        # 解析 Hold 时序
        whs_pattern = r'WHS\(ns\)\s*:\s*([\d.-]+)'
        ths_pattern = r'THS\(ns\)\s*:\s*([\d.-]+)'
        
        whs_match = re.search(whs_pattern, report)
        ths_match = re.search(ths_pattern, report)
        
        if whs_match:
            timing['whs'] = float(whs_match.group(1))
        if ths_match:
            timing['ths'] = float(ths_match.group(1))
        
        # 判断时序是否满足
        wns = timing.get('wns', 0)
        whs = timing.get('whs', 0)
        timing['timing_met'] = wns >= 0 and whs >= 0
        
        return timing


class SynthesisResult(BaseModel):
    """综合结果模型。"""

    success: bool = Field(description="操作是否成功")
    status: str | None = Field(default=None, description="综合状态")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    report_path: str | None = Field(default=None, description="综合报告路径")
    checkpoint_path: str | None = Field(default=None, description="DCP 检查点路径")
    utilization: dict[str, Any] | None = Field(default=None, description="资源利用率摘要")
    timing_summary: dict[str, Any] | None = Field(default=None, description="时序摘要")
    last_known_step: str | None = Field(default=None, description="最近一次已知 step")
    progress_hint: str | None = Field(default=None, description="文本进度提示")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="相关产物与日志路径")


class ImplementationResult(BaseModel):
    """实现结果模型。"""

    success: bool = Field(description="操作是否成功")
    status: str | None = Field(default=None, description="实现状态")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    report_path: str | None = Field(default=None, description="实现报告路径")
    checkpoint_path: str | None = Field(default=None, description="DCP 检查点路径")
    utilization: dict[str, Any] | None = Field(default=None, description="资源利用率")
    timing_summary: dict[str, Any] | None = Field(default=None, description="时序摘要")
    last_known_step: str | None = Field(default=None, description="最近一次已知 step")
    progress_hint: str | None = Field(default=None, description="文本进度提示")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="相关产物与日志路径")


class BitstreamResult(BaseModel):
    """比特流生成结果模型。"""

    success: bool = Field(description="操作是否成功")
    bitstream_path: str | None = Field(default=None, description="比特流文件路径")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    ltx_path: str | None = Field(default=None, description="调试探针文件路径")
    size: int | None = Field(default=None, description="文件大小（字节）")
    status: str | None = Field(default=None, description="run 状态")
    last_known_step: str | None = Field(default=None, description="最近一次已知 step")
    progress_hint: str | None = Field(default=None, description="文本进度提示")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="相关产物与日志路径")


class UtilizationReportResult(BaseModel):
    """资源利用率报告结果模型。"""

    success: bool = Field(description="操作是否成功")
    utilization: dict[str, Any] = Field(default_factory=dict, description="资源利用率数据")
    raw_report: str | None = Field(default=None, description="原始报告文本")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class TimingReportResult(BaseModel):
    """时序报告结果模型。"""

    success: bool = Field(description="操作是否成功")
    timing: dict[str, Any] = Field(default_factory=dict, description="时序数据")
    raw_report: str | None = Field(default=None, description="原始报告文本")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class RunStatusResult(BaseModel):
    """运行状态结果模型。"""

    success: bool = Field(description="操作是否成功")
    run_name: str | None = Field(default=None, description="运行名称")
    status: str | None = Field(default=None, description="运行状态")
    status_source: str | None = Field(default=None, description="状态来源")
    progress: str | None = Field(default=None, description="Vivado PROGRESS 属性")
    current_step: str | None = Field(default=None, description="Vivado CURRENT_STEP 属性")
    needs_refresh: bool | None = Field(default=None, description="Vivado NEEDS_REFRESH 属性")
    is_running: bool = Field(default=False, description="是否正在运行")
    is_complete: bool = Field(default=False, description="是否已完成")
    is_failed: bool = Field(default=False, description="是否失败")
    last_known_step: str | None = Field(default=None, description="最近一次已知 step")
    progress_hint: str | None = Field(default=None, description="文本进度提示")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="相关产物与日志路径")
    details: str | None = Field(default=None, description="附加错误或状态细节")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class RunMessagesResult(BaseModel):
    """运行消息结果模型。"""

    success: bool = Field(description="操作是否成功")
    run_name: str | None = Field(default=None, description="运行名称")
    status: str | None = Field(default=None, description="运行状态")
    messages: list[dict[str, str]] = Field(default_factory=list, description="消息列表")
    matched_count: int = Field(default=0, description="匹配消息数")
    source: str | None = Field(default=None, description="消息来源")
    details: str | None = Field(default=None, description="消息查询降级原因")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ReportTextResult(BaseModel):
    """文本型报告结果模型。"""

    success: bool = Field(description="操作是否成功")
    report_name: str = Field(description="报告名称")
    raw_report: str | None = Field(default=None, description="原始报告文本")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class LintReportResult(BaseModel):
    """Lint/检查类报告结果模型。"""

    success: bool = Field(description="操作是否成功")
    report_name: str = Field(description="报告名称")
    total_findings: int = Field(default=0, description="报告中识别到的问题总数")
    matched_findings: int = Field(default=0, description="按严重级别筛选后的问题数")
    severity_counts: dict[str, int] = Field(default_factory=dict, description="按严重级别统计")
    findings: list[str] = Field(default_factory=list, description="问题摘要列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


def register_build_tools(mcp: FastMCP) -> None:
    """
    注册构建相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def run_synthesis() -> SynthesisResult:
        """
        运行综合。

        此工具启动 Vivado 综合流程。综合将 RTL 代码转换为门级网表。
        运行前请确保已打开项目并设置了顶层模块。

        综合过程可能需要较长时间，取决于设计规模和复杂度。
        工具会等待综合完成后返回结果。

        Returns:
            SynthesisResult 包含综合状态和结果。

        Example:
            运行综合:
            ```
            result = run_synthesis()
            if result.success:
                print(f"综合完成，状态: {result.status}")
            ```
        """
        logger.info("运行综合")

        manager = await _get_synthesis_manager()
        result = await manager.run_synthesis()

        return SynthesisResult(
            success=result.get("success", False),
            status=result.get("status"),
            message=result.get("message", ""),
            error=result.get("error"),
            report_path=result.get("report_path"),
            checkpoint_path=result.get("checkpoint_path"),
            utilization=result.get("utilization"),
            timing_summary=result.get("timing_summary"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
        )

    @mcp.tool()
    async def run_synthesis_async() -> RunStatusResult:
        """启动综合但不等待完成。"""
        logger.info("异步启动综合")
        manager = await _get_synthesis_manager()
        result = await manager.start_synthesis()
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name") or "synth_1",
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def run_implementation() -> ImplementationResult:
        """
        运行实现。

        此工具启动 Vivado 实现流程。实现包括布局布线等步骤，
        将综合后的网表映射到目标器件的实际资源上。

        运行前请确保综合已完成。实现过程可能需要较长时间，
        工具会等待实现完成后返回结果。

        Returns:
            ImplementationResult 包含实现状态和结果。

        Example:
            运行实现:
            ```
            result = run_implementation()
            if result.success:
                print(f"实现完成，状态: {result.status}")
            ```
        """
        logger.info("运行实现")

        manager = await _get_implementation_manager()
        result = await manager.run_implementation()

        return ImplementationResult(
            success=result.get("success", False),
            status=result.get("status"),
            message=result.get("message", ""),
            error=result.get("error"),
            report_path=result.get("report_path"),
            checkpoint_path=result.get("checkpoint_path"),
            utilization=result.get("utilization"),
            timing_summary=result.get("timing_summary"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
        )

    @mcp.tool()
    async def run_implementation_async() -> RunStatusResult:
        """启动实现但不等待完成。"""
        logger.info("异步启动实现")
        manager = await _get_implementation_manager()
        result = await manager.start_implementation()
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name") or "impl_1",
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def generate_bitstream() -> BitstreamResult:
        """
        生成比特流。

        此工具生成用于 FPGA 编程的比特流文件 (.bit)。
        比特流生成是实现流程的最后一步。

        运行前请确保实现已完成。生成的比特流文件可用于
        通过 JTAG 或其他方式下载到 FPGA。

        Returns:
            BitstreamResult 包含比特流文件路径。

        Example:
            生成比特流:
            ```
            result = generate_bitstream()
            if result.success:
                print(f"比特流已生成: {result.bitstream_path}")
            ```
        """
        logger.info("生成比特流")

        manager = await _get_implementation_manager()
        result = await manager.generate_bitstream()

        return BitstreamResult(
            success=result.get("success", False),
            bitstream_path=result.get("bitstream_path"),
            message=result.get("message", ""),
            error=result.get("error"),
            ltx_path=result.get("ltx_path"),
            size=result.get("size"),
        )

    @mcp.tool()
    async def get_utilization_report() -> UtilizationReportResult:
        """
        获取资源利用率报告。

        此工具返回当前设计的资源利用率报告，包括:
        - LUT (查找表) 使用情况
        - FF (触发器) 使用情况
        - BRAM (块 RAM) 使用情况
        - DSP (数字信号处理单元) 使用情况
        - IO (输入输出) 使用情况

        报告显示每种资源的使用数量、可用数量和使用百分比。

        Returns:
            UtilizationReportResult 包含资源利用率数据。

        Example:
            获取资源利用率:
            ```
            report = get_utilization_report()
            if report.success:
                for resource, data in report.utilization.items():
                    print(f"{resource}: {data['used']}/{data['available']} ({data['percentage']}%)")
            ```
        """
        logger.info("获取资源利用率报告")

        # 优先使用实现后的报告，如果没有则使用综合后的报告
        impl_manager = await _get_implementation_manager()
        result = await impl_manager.get_utilization_report()

        if not result.get("success", False):
            # 尝试获取综合后的报告
            synth_manager = await _get_synthesis_manager()
            result = await synth_manager.get_utilization_report()

        return UtilizationReportResult(
            success=result.get("success", False),
            utilization=result.get("utilization", {}),
            raw_report=result.get("raw_report"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_timing_report() -> TimingReportResult:
        """
        获取时序报告。

        此工具返回当前设计的时序分析报告，包括:
        - Setup 时序裕量 (Setup Slack)
        - Hold 时序裕量 (Hold Slack)
        - 时序违例数量
        - 关键路径信息

        时序报告用于验证设计是否满足时序约束。
        正的裕量表示时序满足要求，负的裕量表示存在时序违例。

        Returns:
            TimingReportResult 包含时序数据。

        Example:
            获取时序报告:
            ```
            report = get_timing_report()
            if report.success:
                timing = report.timing
                if timing.get("timing_met"):
                    print("时序满足要求")
                else:
                    print(f"时序违例! Setup Slack: {timing['setup']['worst_slack']}")
            ```
        """
        logger.info("获取时序报告")

        manager = await _get_implementation_manager()
        result = await manager.get_timing_report()

        return TimingReportResult(
            success=result.get("success", False),
            timing=result.get("timing", {}),
            raw_report=result.get("raw_report"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_run_status(run_name: str = "synth_1") -> RunStatusResult:
        """获取综合或实现 run 的当前状态。"""
        logger.info(f"获取运行状态: {run_name}")
        manager = await _get_implementation_manager()
        result = await manager.get_run_status(run_name)
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name"),
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def launch_run(
        run_name: str = "synth_1",
        to_step: str | None = None,
        jobs: int = 4,
    ) -> RunStatusResult:
        """启动指定 run，但不等待完成。"""
        logger.info(f"启动 run: {run_name}, to_step={to_step}, jobs={jobs}")
        manager = await _get_implementation_manager()
        result = await manager.launch_run(run_name, to_step=to_step, jobs=jobs)
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name"),
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def wait_for_run(
        run_name: str = "synth_1",
        timeout: float | None = None,
        poll_interval: float = 2.0,
    ) -> RunStatusResult:
        """等待指定 run 完成，使用状态轮询而不是单次 wait_on_run。"""
        logger.info(f"等待 run: {run_name}, timeout={timeout}, poll_interval={poll_interval}")
        manager = await _get_implementation_manager()
        result = await manager.wait_for_run(run_name, timeout=timeout, poll_interval=poll_interval)
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name"),
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_run_progress(run_name: str = "synth_1") -> RunStatusResult:
        """获取 run 的文本进度提示和最近已知 step。"""
        logger.info(f"获取 run 进度: {run_name}")
        manager = await _get_implementation_manager()
        result = await manager.get_run_progress(run_name)
        return RunStatusResult(
            success=result.get("success", False),
            run_name=result.get("run_name"),
            status=result.get("status"),
            status_source=result.get("status_source"),
            is_running=result.get("is_running", False),
            is_complete=result.get("is_complete", False),
            is_failed=result.get("is_failed", False),
            progress=result.get("progress"),
            current_step=result.get("current_step"),
            needs_refresh=result.get("needs_refresh"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_run_messages(
        run_name: str = "synth_1",
        limit: int = 50,
        severity: str | None = None,
    ) -> RunMessagesResult:
        """从 run 日志中提取最近消息。"""
        logger.info(f"获取 run 消息: {run_name}, limit={limit}, severity={severity}")
        manager = await _get_implementation_manager()
        result = await manager.get_run_messages(run_name, limit=limit, severity=severity)
        return RunMessagesResult(
            success=result.get("success", False),
            run_name=result.get("run_name"),
            status=result.get("status"),
            messages=result.get("messages", []),
            matched_count=result.get("matched_count", 0),
            source=result.get("source"),
            details=result.get("details"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def run_full_flow() -> BitstreamResult:
        """执行综合、实现和 bitstream 生成的完整流程。"""
        logger.info("执行完整构建流程")
        synth_manager = await _get_synthesis_manager()
        synth_result = await synth_manager.run_synthesis()
        if not synth_result.get("success", False):
            return BitstreamResult(
                success=False,
                bitstream_path=None,
                message="完整流程失败：综合失败",
                error=synth_result.get("error"),
            )

        impl_manager = await _get_implementation_manager()
        impl_result = await impl_manager.run_implementation()
        if not impl_result.get("success", False):
            return BitstreamResult(
                success=False,
                bitstream_path=None,
                message="完整流程失败：实现失败",
                error=impl_result.get("error"),
            )

        result = await impl_manager.generate_bitstream()
        return BitstreamResult(
            success=result.get("success", False),
            bitstream_path=result.get("bitstream_path"),
            message=result.get("message", ""),
            error=result.get("error"),
            ltx_path=result.get("ltx_path"),
            size=result.get("size"),
            status=result.get("status"),
            last_known_step=result.get("last_known_step"),
            progress_hint=result.get("progress_hint"),
            artifacts=result.get("artifacts", {}),
        )

    @mcp.tool()
    async def get_drc_report() -> ReportTextResult:
        """获取实现后的 DRC 报告。"""
        logger.info("获取 DRC 报告")
        manager = await _get_implementation_manager()
        result = await manager.get_drc_report()
        return ReportTextResult(
            success=result.get("success", False),
            report_name="drc",
            raw_report=result.get("raw_report"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_methodology_report() -> ReportTextResult:
        """获取实现后的 methodology 报告。"""
        logger.info("获取 methodology 报告")
        manager = await _get_implementation_manager()
        result = await manager.get_methodology_report()
        return ReportTextResult(
            success=result.get("success", False),
            report_name="methodology",
            raw_report=result.get("raw_report"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def get_power_report() -> ReportTextResult:
        """获取实现后的功耗报告。"""
        logger.info("获取功耗报告")
        manager = await _get_implementation_manager()
        result = await manager.get_power_report()
        return ReportTextResult(
            success=result.get("success", False),
            report_name="power",
            raw_report=result.get("raw_report"),
            message=result.get("message", ""),
            error=result.get("error"),
        )

    @mcp.tool()
    async def check_methodology(
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> LintReportResult:
        """检查 methodology 报告并提取问题摘要。"""
        logger.info(
            f"检查 methodology 报告: min_severity={min_severity}, max_findings={max_findings}"
        )
        try:
            manager = await _get_implementation_manager()
            result = await manager.get_methodology_report()
            if not result.get("success", False):
                return LintReportResult(
                    success=False,
                    report_name="methodology",
                    message="methodology 检查失败",
                    error=result.get("error"),
                )

            summary = _summarize_lint_findings(
                report=result.get("raw_report", "") or "",
                min_severity=min_severity,
                max_findings=max_findings,
            )
            return LintReportResult(
                success=True,
                report_name="methodology",
                total_findings=summary["total_findings"],
                matched_findings=summary["matched_findings"],
                severity_counts=summary["severity_counts"],
                findings=summary["findings"],
                message=f"methodology 检查完成，匹配 {summary['matched_findings']} 条问题",
                error=None,
            )
        except Exception as e:
            logger.exception(f"检查 methodology 报告异常: {e}")
            return LintReportResult(
                success=False,
                report_name="methodology",
                message="methodology 检查失败",
                error=str(e),
            )

    @mcp.tool()
    async def check_drc(
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> LintReportResult:
        """检查 DRC 报告并提取问题摘要。"""
        logger.info(f"检查 DRC 报告: min_severity={min_severity}, max_findings={max_findings}")
        try:
            manager = await _get_implementation_manager()
            result = await manager.get_drc_report()
            if not result.get("success", False):
                return LintReportResult(
                    success=False,
                    report_name="drc",
                    message="DRC 检查失败",
                    error=result.get("error"),
                )

            summary = _summarize_lint_findings(
                report=result.get("raw_report", "") or "",
                min_severity=min_severity,
                max_findings=max_findings,
            )
            return LintReportResult(
                success=True,
                report_name="drc",
                total_findings=summary["total_findings"],
                matched_findings=summary["matched_findings"],
                severity_counts=summary["severity_counts"],
                findings=summary["findings"],
                message=f"DRC 检查完成，匹配 {summary['matched_findings']} 条问题",
                error=None,
            )
        except Exception as e:
            logger.exception(f"检查 DRC 报告异常: {e}")
            return LintReportResult(
                success=False,
                report_name="drc",
                message="DRC 检查失败",
                error=str(e),
            )

    @mcp.tool()
    async def lint_methodology(
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> LintReportResult:
        """methodology lint 别名（等价于 check_methodology）。"""
        return await check_methodology(min_severity=min_severity, max_findings=max_findings)

    @mcp.tool()
    async def lint_drc(
        min_severity: str = "warning",
        max_findings: int = 20,
    ) -> LintReportResult:
        """DRC lint 别名（等价于 check_drc）。"""
        return await check_drc(min_severity=min_severity, max_findings=max_findings)
