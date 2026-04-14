"""
自定义 Tcl 执行 MCP 工具。

提供直接执行 Tcl 脚本的能力，支持高级用户自定义操作。
"""

import logging
import re
import time
from enum import Enum
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.settings import get_settings
from gateflow.vivado.tcp_client import TcpClientManager, TclResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Tcl 命令安全策略
# ============================================================================


class TclPolicy(str, Enum):
    """Tcl 命令执行策略"""

    SAFE = "safe"  # 只允许只读查询命令
    NORMAL = "normal"  # 允许常用工程命令
    UNSAFE = "unsafe"  # 允许所有命令（需要显式开启）


# SAFE 级别允许的命令前缀（只读查询）
SAFE_COMMANDS = {
    # 输出
    "puts",
    # 查询命令
    "get_",
    "list_",
    "report_",
    "check_",
    # 信息查询
    "version",
    "info",
    "current_",  # current_project, current_fileset 等
    # 属性查询
    "get_property",
    # 文件系统只读
    "file exists",
    "file readable",
    "file dirname",
    "file extension",
    "file rootname",
    "file tail",
    "file join",
    "file split",
    "file normalize",
    # 表达式计算
    "expr",
    # 变量操作（只读）
    "set",  # set 无参数时是查询
    # 字符串操作
    "string",
    "format",
    "scan",
    # 列表操作
    "llength",
    "lindex",
    "lrange",
    "lsearch",
    "lsort",
    "concat",
    "join",
    # 控制流（只读场景）
    "if",
    "switch",
    "foreach",
    "for",
    "while",
    # 辅助
    "catch",
    "try",
    "return",
    "error",
}

# NORMAL 级别额外允许的命令前缀（工程操作）
NORMAL_COMMANDS = {
    # 项目管理
    "create_",
    "open_",
    "close_",
    "add_",
    "remove_",
    "set_property",
    "reset_",
    # 设计流程
    "synth_design",
    "opt_design",
    "place_design",
    "route_design",
    "write_",
    "read_",
    # IP 管理
    "create_ip",
    "generate_target",
    "upgrade_ip",
    # 约束
    "add_files",
    "import_files",
    "set_",
    # 仿真
    "launch_simulation",
    "run",
    "close_sim",
    # 综合/实现
    "launch_runs",
    "wait_on_run",
    "reset_run",
    # 综合设置
    "set_part",
    "set_target",
}

# 危险命令模式
DANGEROUS_PATTERNS = [
    r"\bexec\s+",  # 执行系统命令
    r"\bfile\s+delete",  # 删除文件
    r"\bfile\s+mkdir\s+-p",  # 创建目录（可能覆盖）
    r"\bexit\b",  # 退出 Vivado
    r"\bshutdown\b",  # 关机命令
    r"\bsystem\b",  # 系统命令
    r"\bcatch\s+\{?\s*exec",  # 通过 catch 执行系统命令
    r"\bopen\s+\|",  # 管道命令
    r"\bsocket\b",  # 网络操作
    r"\bfconfigure\b.*-translation\s+binary",  # 二进制操作
    r"\bsource\s+http",  # 远程脚本
]


class PolicyCheckResult(BaseModel):
    """策略检查结果"""

    allowed: bool = Field(description="是否允许执行")
    policy: TclPolicy = Field(description="当前策略级别")
    violations: list[str] = Field(default_factory=list, description="违规项列表")
    message: str = Field(default="", description="检查消息")


def _extract_commands(script: str) -> list[str]:
    """
    从 Tcl 脚本中提取命令列表。

    Args:
        script: Tcl 脚本内容

    Returns:
        命令列表
    """
    # 移除注释
    lines = []
    for line in script.split("\n"):
        # 移除行内注释
        if "#" in line:
            # 简单处理：移除 # 后的内容（不考虑字符串中的 #）
            line = line.split("#")[0]
        lines.append(line)

    clean_script = "\n".join(lines)

    # 分割命令（按换行或分号）
    commands = []
    for cmd in re.split(r"[;\n]+", clean_script):
        cmd = cmd.strip()
        if cmd:
            commands.append(cmd)

    return commands


def _is_command_allowed(command: str, allowed_prefixes: set[str]) -> bool:
    """
    检查命令是否在允许的前缀列表中。

    Args:
        command: Tcl 命令
        allowed_prefixes: 允许的命令前缀集合

    Returns:
        是否允许
    """
    # 获取命令的第一个词（命令名）
    parts = command.split()
    if not parts:
        return False

    cmd_name = parts[0].lower()

    # 检查是否匹配任何允许的前缀
    for prefix in allowed_prefixes:
        if cmd_name.startswith(prefix.lower()) or cmd_name == prefix.lower():
            return True

    # 特殊处理 file 命令的子命令
    if cmd_name == "file" and len(parts) > 1:
        subcmd = parts[1].lower()
        # 检查 file 子命令是否在允许列表中
        file_prefix = f"file {subcmd}"
        for prefix in allowed_prefixes:
            if file_prefix.startswith(prefix.lower()):
                return True

    return False


def _check_dangerous_patterns(script: str) -> list[str]:
    """
    检查脚本中是否包含危险模式。

    Args:
        script: Tcl 脚本内容

    Returns:
        检测到的危险模式列表
    """
    violations = []
    script_lower = script.lower()

    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, script_lower, re.IGNORECASE):
            violations.append(f"检测到危险模式: {pattern}")

    return violations


def check_tcl_policy(script: str, policy: TclPolicy) -> PolicyCheckResult:
    """
    检查 Tcl 脚本是否符合指定的安全策略。

    Args:
        script: Tcl 脚本内容
        policy: 安全策略级别

    Returns:
        PolicyCheckResult 检查结果
    """
    violations = []

    # 首先检查危险模式（所有级别都需要检查）
    dangerous = _check_dangerous_patterns(script)
    if dangerous:
        violations.extend(dangerous)

    # 根据策略级别检查命令
    if policy == TclPolicy.SAFE:
        # SAFE 级别：只允许白名单中的命令
        commands = _extract_commands(script)
        for cmd in commands:
            if not _is_command_allowed(cmd, SAFE_COMMANDS):
                violations.append(f"SAFE 策略不允许命令: {cmd[:50]}...")

    elif policy == TclPolicy.NORMAL:
        # NORMAL 级别：允许 SAFE + NORMAL 命令
        allowed = SAFE_COMMANDS | NORMAL_COMMANDS
        commands = _extract_commands(script)
        for cmd in commands:
            if not _is_command_allowed(cmd, allowed):
                violations.append(f"NORMAL 策略不允许命令: {cmd[:50]}...")

    elif policy == TclPolicy.UNSAFE:
        # UNSAFE 级别：允许所有命令，但仍需检查危险模式
        pass

    # 生成消息
    if violations:
        message = f"策略检查失败 ({policy.value}): 发现 {len(violations)} 个违规项"
    else:
        message = f"策略检查通过 ({policy.value})"

    return PolicyCheckResult(
        allowed=len(violations) == 0,
        policy=policy,
        violations=violations,
        message=message,
    )


class TclExecutionResult(BaseModel):
    """Tcl 执行结果模型"""

    success: bool = Field(description="执行是否成功")
    result: str = Field(default="", description="执行结果")
    output: str = Field(default="", description="完整输出")
    errors: list[str] = Field(default_factory=list, description="错误列表")
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    message: str = Field(default="", description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class TclBatchResult(BaseModel):
    """批量 Tcl 执行结果模型"""

    success: bool = Field(description="整体是否成功")
    results: list[TclExecutionResult] = Field(default_factory=list, description="各命令结果")
    total_time: float = Field(default=0.0, description="总执行时间")
    message: str = Field(default="", description="结果消息")


def _convert_tcl_response(response: TclResponse) -> TclExecutionResult:
    """
    将 TclResponse 转换为 TclExecutionResult。

    Args:
        response: 原始 Tcl 响应

    Returns:
        TclExecutionResult 转换后的结果
    """
    return TclExecutionResult(
        success=response.success,
        result=response.result,
        output=response.raw_output,
        errors=[response.error] if response.error else [],
        warnings=response.warnings,
        execution_time=response.execution_time,
        message="执行成功" if response.success else "执行失败",
        error=response.error,
    )


def register_tcl_tools(mcp: FastMCP) -> None:
    """
    注册自定义 Tcl 执行工具。

    Args:
        mcp: FastMCP 服务器实例。
    """
    # 从全局配置读取默认 Tcl 策略
    settings = get_settings()
    security = settings.get_security_policy()
    default_tcl_policy = security.tcl_policy
    additional_dangerous_patterns = security.tcl_dangerous_patterns
    
    # 合并额外的危险模式
    if additional_dangerous_patterns:
        global DANGEROUS_PATTERNS
        DANGEROUS_PATTERNS = DANGEROUS_PATTERNS + additional_dangerous_patterns
        logger.info(f"添加额外的 Tcl 危险模式: {additional_dangerous_patterns}")
    
    logger.info(f"Tcl 工具使用默认策略: {default_tcl_policy}")

    @mcp.tool()
    async def execute_tcl(
        script: str,
        timeout: float = 3600.0,
        policy: str | None = None,
        allow_unsafe: bool = False,
    ) -> TclExecutionResult:
        """
        执行自定义 Tcl 脚本。

        此工具允许直接执行 Tcl 命令，提供最大的灵活性。
        适用于高级用户和特殊场景。

        Args:
            script: Tcl 脚本内容，支持多行脚本
            timeout: 超时时间（秒），默认 1 小时
            policy: 安全策略级别，可选值：
                - "safe": 只允许只读查询命令（如 get_*, list_*, puts 等）
                - "normal": 允许常用工程命令（如 create_*, synth_design 等）
                - "unsafe": 允许所有命令（需要 allow_unsafe=True）
                - None: 使用全局配置的默认策略
            allow_unsafe: 是否允许执行危险命令，默认 False。
                当 policy="unsafe" 或检测到危险命令时需要显式设置为 True。

        Returns:
            TclExecutionResult 执行结果

        Example:
            执行简单命令（safe 策略）:
            ```
            execute_tcl(script="puts Hello", policy="safe")
            ```

            执行工程命令（normal 策略）:
            ```
            execute_tcl(script="create_project my_proj ./my_proj", policy="normal")
            ```

            执行危险命令（unsafe 策略，需要显式确认）:
            ```
            execute_tcl(script="exec rm -rf temp", policy="unsafe", allow_unsafe=True)
            ```

        Warning:
            请谨慎使用此工具，错误的 Tcl 命令可能导致 Vivado 状态异常。
            使用 unsafe 策略时请确保了解命令的风险。
        """
        logger.info(f"执行 Tcl 脚本，长度: {len(script)} 字符，超时: {timeout} 秒，策略: {policy}")
        logger.debug(f"脚本内容: {script[:200]}{'...' if len(script) > 200 else ''}")

        # 使用默认策略（如果未指定）
        if policy is None:
            policy = default_tcl_policy
            logger.info(f"使用默认策略: {policy}")

        # 解析策略
        try:
            tcl_policy = TclPolicy(policy.lower())
        except ValueError:
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=[f"无效的策略级别: {policy}，可选值: safe, normal, unsafe"],
                warnings=[],
                execution_time=0.0,
                message="策略错误",
                error=f"无效的策略级别: {policy}",
            )

        # 检查策略
        policy_result = check_tcl_policy(script, tcl_policy)

        # 如果检测到危险命令，需要 allow_unsafe=True
        dangerous_violations = [v for v in policy_result.violations if "危险模式" in v]
        if dangerous_violations and not allow_unsafe:
            logger.warning(f"检测到危险命令，需要 allow_unsafe=True: {dangerous_violations}")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=dangerous_violations,
                warnings=[],
                execution_time=0.0,
                message="安全检查失败",
                error=f"检测到危险命令，需要设置 allow_unsafe=True 才能执行。违规项:\n" + "\n".join(dangerous_violations),
            )

        # 如果策略不允许且不是 unsafe 策略，拒绝执行
        if not policy_result.allowed and tcl_policy != TclPolicy.UNSAFE:
            logger.warning(f"策略检查失败: {policy_result.message}")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=policy_result.violations,
                warnings=[],
                execution_time=0.0,
                message="策略检查失败",
                error=f"命令不符合 {policy} 策略:\n" + "\n".join(policy_result.violations),
            )

        # unsafe 策略需要显式确认
        if tcl_policy == TclPolicy.UNSAFE and not allow_unsafe:
            logger.warning("unsafe 策略需要 allow_unsafe=True")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["unsafe 策略需要显式设置 allow_unsafe=True"],
                warnings=[],
                execution_time=0.0,
                message="需要确认",
                error="使用 unsafe 策略需要显式设置 allow_unsafe=True 以确认您了解风险",
            )

        # 获取客户端
        client = TcpClientManager.get_client()

        # 确保已连接
        if not await TcpClientManager.ensure_connected():
            logger.error("无法连接到 Vivado tcl_server")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["无法连接到 Vivado tcl_server"],
                warnings=[],
                execution_time=0.0,
                message="连接失败",
                error="无法连接到 Vivado tcl_server，请确认 Vivado 已启动且 tcl_server 正在运行",
            )

        # 执行脚本
        response = await client.execute_tcl(script, timeout=timeout)

        # 转换结果
        result = _convert_tcl_response(response)

        if result.success:
            logger.info(f"Tcl 脚本执行成功，耗时 {result.execution_time:.3f} 秒")
        else:
            logger.warning(f"Tcl 脚本执行失败: {result.error}")

        return result

    @mcp.tool()
    async def execute_tcl_batch(
        scripts: list[str],
        stop_on_error: bool = True,
        timeout: float = 3600.0,
        policy: str | None = None,
        allow_unsafe: bool = False,
    ) -> TclBatchResult:
        """
        批量执行 Tcl 脚本。

        按顺序执行多个 Tcl 脚本，可选择在遇到错误时停止。

        Args:
            scripts: Tcl 脚本列表
            stop_on_error: 遇到错误时是否停止，默认 True
            timeout: 总超时时间（秒）
            policy: 安全策略级别，可选值：safe, normal, unsafe，None 使用默认策略
            allow_unsafe: 是否允许执行危险命令

        Returns:
            TclBatchResult 批量执行结果

        Example:
            ```
            execute_tcl_batch(scripts=[
                "create_project my_proj ./my_proj",
                "add_files {top.v}",
                "set_property top top [current_fileset]"
            ], policy="normal")
            ```
        """
        # 使用默认策略（如果未指定）
        if policy is None:
            policy = default_tcl_policy
            logger.info(f"批量执行使用默认策略: {policy}")
        
        logger.info(f"批量执行 Tcl 脚本，数量: {len(scripts)}, 遇错停止: {stop_on_error}, 策略: {policy}")

        # 解析策略
        try:
            tcl_policy = TclPolicy(policy.lower())
        except ValueError:
            return TclBatchResult(
                success=False,
                results=[
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=[f"无效的策略级别: {policy}，可选值: safe, normal, unsafe"],
                        warnings=[],
                        execution_time=0.0,
                        message="策略错误",
                        error=f"无效的策略级别: {policy}",
                    )
                ],
                total_time=0.0,
                message="策略错误",
            )

        # unsafe 策略需要显式确认
        if tcl_policy == TclPolicy.UNSAFE and not allow_unsafe:
            return TclBatchResult(
                success=False,
                results=[
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=["unsafe 策略需要显式设置 allow_unsafe=True"],
                        warnings=[],
                        execution_time=0.0,
                        message="需要确认",
                        error="使用 unsafe 策略需要显式设置 allow_unsafe=True 以确认您了解风险",
                    )
                ],
                total_time=0.0,
                message="需要确认",
            )

        # 获取客户端
        client = TcpClientManager.get_client()

        # 确保已连接
        if not await TcpClientManager.ensure_connected():
            logger.error("无法连接到 Vivado tcl_server")
            return TclBatchResult(
                success=False,
                results=[
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=["无法连接到 Vivado tcl_server"],
                        warnings=[],
                        execution_time=0.0,
                        message="连接失败",
                        error="无法连接到 Vivado tcl_server",
                    )
                ],
                total_time=0.0,
                message="连接失败，无法执行批量脚本",
            )

        start_time = time.time()
        results: list[TclExecutionResult] = []
        all_success = True

        # 计算每个脚本的平均超时时间
        per_script_timeout = timeout / max(len(scripts), 1)

        for i, script in enumerate(scripts):
            logger.debug(f"执行第 {i + 1}/{len(scripts)} 个脚本")

            # 检查策略
            policy_result = check_tcl_policy(script, tcl_policy)

            # 如果检测到危险命令，需要 allow_unsafe=True
            dangerous_violations = [v for v in policy_result.violations if "危险模式" in v]
            if dangerous_violations and not allow_unsafe:
                results.append(
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=dangerous_violations,
                        warnings=[],
                        execution_time=0.0,
                        message="安全检查失败",
                        error=f"检测到危险命令，需要设置 allow_unsafe=True。违规项:\n" + "\n".join(dangerous_violations),
                    )
                )
                all_success = False
                if stop_on_error:
                    break
                continue

            # 如果策略不允许
            if not policy_result.allowed:
                results.append(
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=policy_result.violations,
                        warnings=[],
                        execution_time=0.0,
                        message="策略检查失败",
                        error=f"命令不符合 {policy} 策略:\n" + "\n".join(policy_result.violations),
                    )
                )
                all_success = False
                if stop_on_error:
                    break
                continue

            # 检查剩余时间
            elapsed = time.time() - start_time
            remaining_timeout = timeout - elapsed

            if remaining_timeout <= 0:
                # 超时，停止执行
                logger.warning(f"批量执行超时，已执行 {i}/{len(scripts)} 个脚本")
                results.append(
                    TclExecutionResult(
                        success=False,
                        result="",
                        output="",
                        errors=["批量执行超时"],
                        warnings=[],
                        execution_time=0.0,
                        message="执行超时",
                        error="批量执行超时，剩余脚本未执行",
                    )
                )
                all_success = False
                break

            # 执行单个脚本
            script_timeout = min(per_script_timeout, remaining_timeout)
            response = await client.execute_tcl(script, timeout=script_timeout)
            result = _convert_tcl_response(response)
            results.append(result)

            # 检查是否失败
            if not result.success:
                all_success = False
                if stop_on_error:
                    logger.warning(f"第 {i + 1} 个脚本执行失败，停止后续执行")
                    break

        total_time = time.time() - start_time

        # 生成消息
        success_count = sum(1 for r in results if r.success)
        message = f"批量执行完成: {success_count}/{len(results)} 成功，总耗时 {total_time:.3f} 秒"

        logger.info(message)

        return TclBatchResult(
            success=all_success and len(results) == len(scripts),
            results=results,
            total_time=total_time,
            message=message,
        )

    @mcp.tool()
    async def execute_tcl_file(
        file_path: str,
        timeout: float = 3600.0,
        policy: str | None = None,
        allow_unsafe: bool = False,
    ) -> TclExecutionResult:
        """
        执行 Tcl 脚本文件。

        读取并执行指定路径的 Tcl 脚本文件。

        Args:
            file_path: Tcl 脚本文件的绝对路径
            timeout: 超时时间（秒）
            policy: 安全策略级别，可选值：safe, normal, unsafe，None 使用默认策略
            allow_unsafe: 是否允许执行危险命令

        Returns:
            TclExecutionResult 执行结果

        Example:
            ```
            execute_tcl_file(file_path="C:/projects/build.tcl", policy="normal")
            ```
        """
        # 使用默认策略（如果未指定）
        if policy is None:
            policy = default_tcl_policy
            logger.info(f"执行文件使用默认策略: {policy}")
        
        logger.info(f"执行 Tcl 脚本文件: {file_path}")

        # 验证文件路径
        path = Path(file_path)
        if not path.is_absolute():
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["文件路径必须是绝对路径"],
                warnings=[],
                execution_time=0.0,
                message="路径错误",
                error=f"文件路径必须是绝对路径: {file_path}",
            )

        if not path.exists():
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["文件不存在"],
                warnings=[],
                execution_time=0.0,
                message="文件错误",
                error=f"Tcl 脚本文件不存在: {file_path}",
            )

        if not path.is_file():
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["路径不是文件"],
                warnings=[],
                execution_time=0.0,
                message="路径错误",
                error=f"路径不是文件: {file_path}",
            )

        # 读取文件内容
        try:
            script = path.read_text(encoding="utf-8")
            logger.debug(f"读取脚本文件成功，大小: {len(script)} 字节")
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                script = path.read_text(encoding="gbk")
                logger.debug(f"使用 GBK 编码读取脚本文件成功")
            except Exception as e:
                return TclExecutionResult(
                    success=False,
                    result="",
                    output="",
                    errors=["文件编码错误"],
                    warnings=[],
                    execution_time=0.0,
                    message="读取失败",
                    error=f"无法读取文件，编码错误: {e}",
                )
        except Exception as e:
            logger.exception(f"读取脚本文件失败: {e}")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["读取文件失败"],
                warnings=[],
                execution_time=0.0,
                message="读取失败",
                error=f"读取 Tcl 脚本文件失败: {e}",
            )

        # 使用 execute_tcl 执行脚本
        result = await execute_tcl(script, timeout=timeout, policy=policy, allow_unsafe=allow_unsafe)

        # 更新消息
        result.message = f"执行文件 {path.name}: {result.message}"

        return result

    @mcp.tool()
    async def get_tcl_variable(name: str) -> dict[str, Any]:
        """
        获取 Tcl 变量值。

        获取 Vivado 环境中 Tcl 变量的当前值。

        Args:
            name: 变量名（如 project_name, part_name 等）

        Returns:
            包含变量名和值的字典

        Example:
            ```
            get_tcl_variable(name="project_name")
            ```
        """
        logger.info(f"获取 Tcl 变量: {name}")

        # 获取客户端
        client = TcpClientManager.get_client()

        # 确保已连接
        if not await TcpClientManager.ensure_connected():
            logger.error("无法连接到 Vivado tcl_server")
            return {
                "success": False,
                "name": name,
                "value": None,
                "error": "无法连接到 Vivado tcl_server",
            }

        # 执行 Tcl 命令获取变量值
        # 使用 set 命令获取变量值
        command = f"set {name}"
        response = await client.execute_tcl(command, timeout=60.0)

        if response.success:
            value = response.result.strip()
            logger.info(f"获取变量成功: {name} = {value}")
            return {
                "success": True,
                "name": name,
                "value": value,
                "error": None,
            }
        else:
            # 变量可能不存在，尝试使用 catch 捕获
            catch_command = f'if {{[catch {{set {name}}} result]}} {{puts "ERROR: $result"}} else {{puts $result}}'
            catch_response = await client.execute_tcl(catch_command, timeout=60.0)

            if catch_response.success and not catch_response.error:
                value = catch_response.result.strip()
                logger.info(f"获取变量成功（使用 catch）: {name} = {value}")
                return {
                    "success": True,
                    "name": name,
                    "value": value,
                    "error": None,
                }
            else:
                error_msg = response.error or "变量不存在或无法访问"
                logger.warning(f"获取变量失败: {name}, 错误: {error_msg}")
                return {
                    "success": False,
                    "name": name,
                    "value": None,
                    "error": error_msg,
                }

    @mcp.tool()
    async def set_tcl_variable(
        name: str,
        value: str,
    ) -> TclExecutionResult:
        """
        设置 Tcl 变量值。

        在 Vivado 环境中设置 Tcl 变量。

        Args:
            name: 变量名
            value: 变量值（字符串形式）

        Returns:
            TclExecutionResult 执行结果

        Example:
            ```
            set_tcl_variable(name="my_param", value="100")
            ```
        """
        logger.info(f"设置 Tcl 变量: {name} = {value}")

        # 获取客户端
        client = TcpClientManager.get_client()

        # 确保已连接
        if not await TcpClientManager.ensure_connected():
            logger.error("无法连接到 Vivado tcl_server")
            return TclExecutionResult(
                success=False,
                result="",
                output="",
                errors=["无法连接到 Vivado tcl_server"],
                warnings=[],
                execution_time=0.0,
                message="连接失败",
                error="无法连接到 Vivado tcl_server",
            )

        # 转义值中的特殊字符
        # Tcl 中需要转义的字符: $ [ ] { } " \
        escaped_value = value.replace("\\", "\\\\").replace("$", "\\$")
        escaped_value = escaped_value.replace("[", "\\[").replace("]", "\\]")
        escaped_value = escaped_value.replace("{", "\\{").replace("}", "\\}")
        escaped_value = escaped_value.replace('"', '\\"')

        # 执行 Tcl 命令设置变量值
        command = f'set {name} "{escaped_value}"'
        response = await client.execute_tcl(command, timeout=60.0)

        result = _convert_tcl_response(response)

        if result.success:
            logger.info(f"设置变量成功: {name} = {value}")
            result.message = f"变量 {name} 已设置为: {value}"
        else:
            logger.warning(f"设置变量失败: {name}, 错误: {result.error}")

        return result

    @mcp.tool()
    async def evaluate_tcl_expression(expression: str) -> dict[str, Any]:
        """
        计算 Tcl 表达式。

        计算并返回 Tcl 表达式的结果。

        Args:
            expression: Tcl 表达式

        Returns:
            包含表达式结果的字典

        Example:
            ```
            evaluate_tcl_expression(expression="expr {10 + 20}")
            ```
        """
        logger.info(f"计算 Tcl 表达式: {expression}")

        # 获取客户端
        client = TcpClientManager.get_client()

        # 确保已连接
        if not await TcpClientManager.ensure_connected():
            logger.error("无法连接到 Vivado tcl_server")
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "error": "无法连接到 Vivado tcl_server",
            }

        # 执行表达式
        response = await client.execute_tcl(expression, timeout=60.0)

        if response.success:
            result_value = response.result.strip()
            logger.info(f"表达式计算成功: {expression} = {result_value}")
            return {
                "success": True,
                "expression": expression,
                "result": result_value,
                "execution_time": response.execution_time,
                "error": None,
            }
        else:
            error_msg = response.error or "表达式计算失败"
            logger.warning(f"表达式计算失败: {expression}, 错误: {error_msg}")
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "execution_time": response.execution_time,
                "error": error_msg,
            }
