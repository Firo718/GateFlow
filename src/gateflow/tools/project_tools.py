"""
项目管理 MCP 工具。

提供 Vivado 项目管理相关的 MCP 工具接口。
"""

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.engine import (
    EngineManager,
    EngineMode,
    get_engine_manager,
    ensure_engine_initialized,
    execute_tcl,
)
from gateflow.vivado.project import ProjectManager, ProjectTclGenerator
from gateflow.utils.path_utils import to_tcl_path, normalize_path
from gateflow.errors import (
    ErrorCode,
    ErrorInfo,
    Result,
    make_success,
    make_error,
    generate_request_id,
    get_error_suggestion,
)
from gateflow.tools.result_utils import clean_artifacts
from gateflow.tools.context_utils import AsyncContextBlockedProxy, project_context_error_message

logger = logging.getLogger(__name__)

# 全局状态管理
_engine_manager: EngineManager | None = None
_project_manager: ProjectManager | None = None


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


async def _get_project_manager() -> ProjectManager:
    """
    获取或创建项目管理器实例。
    
    项目管理器使用统一的 EngineManager 执行 Tcl 命令。
    """
    global _project_manager
    if project_context_error_message("project"):
        return AsyncContextBlockedProxy("project")  # type: ignore[return-value]
    if _project_manager is None:
        manager = await _ensure_engine()
        # 创建适配器，使 ProjectManager 可以使用 EngineManager
        _project_manager = ProjectManagerAdapter(manager)
    return _project_manager


class ProjectManagerAdapter:
    """
    项目管理器适配器
    
    将 EngineManager 适配为 ProjectManager 所需的接口，
    使现有的 ProjectManager 可以无缝使用新的引擎系统。
    """
    
    def __init__(self, engine_manager: EngineManager):
        """
        初始化适配器
        
        Args:
            engine_manager: EngineManager 实例
        """
        self._engine = engine_manager
    
    async def create_project(
        self,
        name: str,
        path: str,
        part: str,
        vivado_path: str | None = None,
    ) -> Result:
        """
        创建新项目
        
        Args:
            name: 项目名称
            path: 项目路径
            part: 目标器件
            vivado_path: Vivado 安装路径（可选）
        
        Returns:
            Result 统一返回结构
        """
        from pathlib import Path
        
        # 转换路径为 Tcl 格式
        tcl_path = normalize_path(path)
        logger.debug(f"路径转换: {path} -> {tcl_path}")
        
        # 生成 Tcl 命令
        commands = [
            f'create_project "{name}" "{tcl_path}" -part "{part}" -force',
            f'set_property target_language Verilog [current_project]',
            f'set_property simulator_language Verilog [current_project]',
            f'set_property default_lib work [current_project]',
        ]
        
        # 批量执行命令
        results = await self._engine.execute_batch(commands)
        
        # 检查结果
        success = all(r.success for r in results)
        errors = []
        for r in results:
            if not r.success and r.error:
                errors.append(r.error.message)
        
        if success:
            return make_success(
                data={
                    "name": name,
                    "path": path,
                    "part": part,
                },
                request_id=generate_request_id(),
            )
        else:
            return make_error(
                code=ErrorCode.PROJECT_CREATE_FAILED,
                message="项目创建失败",
                details={"errors": errors},
                suggestion=get_error_suggestion(ErrorCode.PROJECT_CREATE_FAILED),
                request_id=generate_request_id(),
            )
    
    async def open_project(self, path: str) -> Result:
        """
        打开项目
        
        Args:
            path: 项目文件路径
        
        Returns:
            Result 统一返回结构
        """
        # 转换路径为 Tcl 格式
        tcl_path = normalize_path(path)
        logger.debug(f"路径转换: {path} -> {tcl_path}")
        
        result = await self._engine.execute(f'open_project "{tcl_path}"')
        
        if result.success:
            # 获取项目信息
            info_result = await self._engine.execute("current_project")
            project_name = info_result.data.strip() if info_result.data else ""
            
            return make_success(
                data={
                    "name": project_name,
                    "path": path,
                },
                request_id=result.request_id,
            )
        else:
            # 转换错误码
            if result.error and "not found" in result.error.message.lower():
                code = ErrorCode.PROJECT_NOT_FOUND
            else:
                code = ErrorCode.PROJECT_OPEN_FAILED
            
            return make_error(
                code=code,
                message=result.error.message if result.error else "项目打开失败",
                suggestion=get_error_suggestion(code),
                request_id=result.request_id,
            )
    
    async def add_source_files(
        self,
        files: list[str],
        file_type: str = "verilog",
    ) -> Result:
        """
        添加源文件
        
        Args:
            files: 文件列表
            file_type: 文件类型
        
        Returns:
            Result 统一返回结构
        """
        # 根据文件类型选择文件集
        if file_type == "xdc":
            fileset = "constrs_1"
        else:
            fileset = "sources_1"
        
        # 转换所有文件路径为 Tcl 格式
        tcl_files = [normalize_path(f) for f in files]
        logger.debug(f"文件路径转换: {files} -> {tcl_files}")
        
        # 构建文件列表
        file_list = " ".join(f'"{f}"' for f in tcl_files)
        command = f'add_files -fileset {fileset} {{{file_list}}}'
        
        result = await self._engine.execute(command)
        
        if result.success:
            return make_success(
                data={
                    "added_files": files,
                    "invalid_files": [],
                },
                request_id=result.request_id,
            )
        else:
            return make_error(
                code=ErrorCode.FILE_NOT_FOUND,
                message=result.error.message if result.error else "添加文件失败",
                details={"files": files},
                suggestion=get_error_suggestion(ErrorCode.FILE_NOT_FOUND),
                request_id=result.request_id,
            )
    
    async def set_top_module(self, module_name: str) -> Result:
        """
        设置顶层模块
        
        Args:
            module_name: 模块名称
        
        Returns:
            Result 统一返回结构
        """
        commands = [
            f'set_property top {module_name} [get_filesets sources_1]',
            'update_compile_order -fileset sources_1',
        ]
        
        results = await self._engine.execute_batch(commands)
        success = all(r.success for r in results)
        
        if success:
            return make_success(
                data={"top_module": module_name},
                request_id=generate_request_id(),
            )
        else:
            errors = []
            for r in results:
                if not r.success and r.error:
                    errors.append(r.error.message)
            return make_error(
                code=ErrorCode.COMMAND_FAILED,
                message="设置顶层模块失败",
                details={"errors": errors},
                request_id=generate_request_id(),
            )
    
    async def get_project_info(self) -> Result:
        """
        获取项目信息
        
        Returns:
            Result 统一返回结构
        """
        info = {}
        
        # 获取项目名称
        result = await self._engine.execute('get_property name [current_project]')
        if result.success and result.data:
            info["name"] = result.data.strip()
        
        # 获取项目路径
        result = await self._engine.execute('get_property directory [current_project]')
        if result.success and result.data:
            info["directory"] = result.data.strip()
        
        # 获取器件型号
        result = await self._engine.execute('get_property part [current_project]')
        if result.success and result.data:
            info["part"] = result.data.strip()
        
        # 获取目标语言
        result = await self._engine.execute('get_property target_language [current_project]')
        if result.success and result.data:
            info["language"] = result.data.strip()
        
        return make_success(
            data=info,
            request_id=generate_request_id(),
        )


class CreateProjectResult(BaseModel):
    """创建项目结果模型。"""

    success: bool = Field(description="操作是否成功")
    project: dict[str, Any] | None = Field(default=None, description="项目信息")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class OpenProjectResult(BaseModel):
    """打开项目结果模型。"""

    success: bool = Field(description="操作是否成功")
    project: dict[str, Any] | None = Field(default=None, description="项目信息")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class AddSourceFilesResult(BaseModel):
    """添加源文件结果模型。"""

    success: bool = Field(description="操作是否成功")
    added_files: list[str] = Field(default_factory=list, description="成功添加的文件列表")
    invalid_files: list[str] = Field(default_factory=list, description="无效文件列表")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class SetTopModuleResult(BaseModel):
    """设置顶层模块结果模型。"""

    success: bool = Field(description="操作是否成功")
    top_module: str | None = Field(default=None, description="顶层模块名称")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


class ProjectInfoResult(BaseModel):
    """项目信息结果模型。"""

    success: bool = Field(description="操作是否成功")
    project: dict[str, Any] | None = Field(default=None, description="项目详细信息")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")
    artifacts: dict[str, Any] = Field(default_factory=dict, description="产物信息")


def _tool_result_success(result: Any) -> bool:
    """兼容 Result 对象与 dict 形式的 success 字段。"""
    if isinstance(result, dict):
        return bool(result.get("success", False))
    return bool(getattr(result, "success", False))


def _tool_result_payload(result: Any) -> dict[str, Any]:
    """兼容 Result 对象与 dict 形式的数据载荷。"""
    if isinstance(result, dict):
        payload = result.get("data")
        if isinstance(payload, dict):
            return payload
        return {
            key: value
            for key, value in result.items()
            if key not in {"success", "message", "error", "errors"}
        }

    payload = getattr(result, "data", None)
    if isinstance(payload, dict):
        return payload
    return {}


def _tool_result_error(result: Any) -> str | None:
    """兼容 Result 对象与 dict 形式的错误文本。"""
    if isinstance(result, dict):
        error = result.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        elif error:
            return str(error)

        errors = result.get("errors")
        if isinstance(errors, list) and errors:
            return "; ".join(str(err) for err in errors if err)
        if errors:
            return str(errors)
        return None

    error_obj = getattr(result, "error", None)
    if error_obj:
        message = getattr(error_obj, "message", None)
        if message:
            return str(message)
        return str(error_obj)
    return None


def register_project_tools(mcp: FastMCP) -> None:
    """
    注册项目管理相关工具。

    Args:
        mcp: FastMCP 服务器实例。
    """

    @mcp.tool()
    async def create_project(
        name: str,
        path: str,
        part: str,
        vivado_path: str | None = None,
    ) -> CreateProjectResult:
        """
        创建新的 Vivado 项目。

        此工具用于创建一个新的 Vivado FPGA 项目。项目将使用指定的名称、
        保存路径和目标器件创建。

        Args:
            name: 项目名称，将用于项目文件和目录命名。
            path: 项目保存路径，项目目录将在此路径下创建。
            part: 目标器件型号，如 xc7a35tcpg236-1 (Artix-7 35T)。
            
                FPGA 型号格式说明：
                - 正确格式：<器件型号><封装><速度等级>
                  例如：xc7z020clg484-2, xc7a35tcpg236-1, xczu7ev-ffvc1156-2-i
                
                - 错误格式示例：
                  × xc7z020-2clg484i (速度等级位置错误)
                  × xc7z020-2clg484 (缺少温度等级标识)
                  × xc7z020clg484 (缺少速度等级)
                
                - 常见器件系列：
                  Artix-7: xc7a35t, xc7a50t, xc7a75t, xc7a100t
                  Kintex-7: xc7k70t, xc7k160t, xc7k325t, xc7k410t
                  Virtex-7: xc7v585t, xc7v2000t
                  Zynq-7000: xc7z010, xc7z020, xc7z035, xc7z100
                  Zynq UltraScale+: xczu7ev, xczu9eg, xczu19eg
                  Kintex UltraScale+: xcku5p, xcku9p, xcku15p
                  Virtex UltraScale+: xcvu9p, xcvu13p
                
            vivado_path: Vivado 安装路径，可选。如未提供将自动检测。

        Returns:
            CreateProjectResult 包含创建结果和项目信息。

        Example:
            创建名为 "my_project" 的项目:
            ```
            create_project(
                name="my_project",
                path="/home/user/projects",
                part="xc7a35tcpg236-1"
            )
            ```
            
            创建 Zynq 项目:
            ```
            create_project(
                name="zynq_project",
                path="/home/user/projects",
                part="xc7z020clg484-2"
            )
            ```
        """
        logger.info(f"创建项目: name={name}, path={path}, part={part}")

        manager = await _get_project_manager()
        result = await manager.create_project(name, path, part, vivado_path)
        success = _tool_result_success(result)
        payload = _tool_result_payload(result)
        error = _tool_result_error(result)
        project = payload.get("project", payload) if success else None

        return CreateProjectResult(
            success=success,
            project=project,
            message="项目创建成功" if success else (error or "项目创建失败"),
            error=error,
            artifacts=clean_artifacts({"project_path": payload.get("path")}),
        )

    @mcp.tool()
    async def open_project(path: str) -> OpenProjectResult:
        """
        打开现有 Vivado 项目。

        此工具用于打开一个已存在的 Vivado 项目文件 (.xpr)。

        Args:
            path: 项目文件路径，必须是 .xpr 文件的完整路径。

        Returns:
            OpenProjectResult 包含打开结果和项目信息。

        Example:
            打开项目:
            ```
            open_project(path="/home/user/projects/my_project/my_project.xpr")
            ```
        """
        logger.info(f"打开项目: path={path}")

        manager = await _get_project_manager()
        result = await manager.open_project(path)
        success = _tool_result_success(result)
        payload = _tool_result_payload(result)
        error = _tool_result_error(result)
        project = payload.get("project", payload) if success else None

        return OpenProjectResult(
            success=success,
            project=project,
            message="项目打开成功" if success else (error or "项目打开失败"),
            error=error,
            artifacts=clean_artifacts({"project_path": payload.get("path")}),
        )

    @mcp.tool()
    async def add_source_files(
        files: list[str],
        file_type: str = "verilog",
    ) -> AddSourceFilesResult:
        """
        添加源文件到当前项目。

        此工具将指定的源文件添加到当前打开的 Vivado 项目中。
        支持多种文件类型，包括 Verilog、VHDL、SystemVerilog、约束文件等。

        Args:
            files: 源文件路径列表，支持绝对路径和相对路径。
            file_type: 文件类型，可选值:
                - "verilog": Verilog 源文件 (.v)
                - "vhdl": VHDL 源文件 (.vhd)
                - "systemverilog": SystemVerilog 源文件 (.sv)
                - "xdc": 约束文件 (.xdc)
                - "tcl": Tcl 脚本文件 (.tcl)
                默认为 "verilog"。

        Returns:
            AddSourceFilesResult 包含添加结果和文件列表。

        Example:
            添加 Verilog 文件:
            ```
            add_source_files(
                files=["/home/user/src/top.v", "/home/user/src/module.v"],
                file_type="verilog"
            )
            ```

            添加约束文件:
            ```
            add_source_files(
                files=["/home/user/constraints/pins.xdc"],
                file_type="xdc"
            )
            ```
        """
        logger.info(f"添加源文件: files={files}, file_type={file_type}")

        manager = await _get_project_manager()
        result = await manager.add_source_files(files, file_type)
        success = _tool_result_success(result)
        data = _tool_result_payload(result)
        error = _tool_result_error(result)
        return AddSourceFilesResult(
            success=success,
            added_files=data.get("added_files", []),
            invalid_files=data.get("invalid_files", []),
            message="文件添加成功" if success else (error or "添加文件失败"),
            error=error,
            artifacts=clean_artifacts({"files": data.get("added_files", [])}),
        )

    @mcp.tool()
    async def set_top_module(module_name: str) -> SetTopModuleResult:
        """
        设置顶层模块。

        此工具将指定的模块设置为 Vivado 项目的顶层模块。
        顶层模块是综合和实现的入口点。

        Args:
            module_name: 顶层模块名称，必须与源文件中定义的模块名一致。

        Returns:
            SetTopModuleResult 包含设置结果。

        Example:
            设置顶层模块:
            ```
            set_top_module(module_name="top")
            ```
        """
        logger.info(f"设置顶层模块: module_name={module_name}")

        manager = await _get_project_manager()
        result = await manager.set_top_module(module_name)
        success = _tool_result_success(result)
        data = _tool_result_payload(result)
        error = _tool_result_error(result)
        return SetTopModuleResult(
            success=success,
            top_module=data.get("top_module"),
            message="顶层模块设置成功" if success else (error or "设置顶层模块失败"),
            error=error,
            artifacts=clean_artifacts({"top_module": data.get("top_module")}),
        )

    @mcp.tool()
    async def get_project_info() -> ProjectInfoResult:
        """
        获取当前项目信息。

        此工具返回当前打开项目的详细信息，包括项目名称、路径、
        目标器件、顶层模块和源文件列表等。

        Returns:
            ProjectInfoResult 包含项目详细信息。

        Example:
            获取项目信息:
            ```
            project_info = get_project_info()
            print(project_info.project)
            ```
        """
        logger.info("获取项目信息")

        manager = await _get_project_manager()
        result = await manager.get_project_info()
        success = _tool_result_success(result)
        payload = _tool_result_payload(result)
        error = _tool_result_error(result)
        project = payload.get("project", payload) if success else None

        return ProjectInfoResult(
            success=success,
            project=project,
            message="获取项目信息成功" if success else (error or "获取项目信息失败"),
            error=error,
            artifacts=clean_artifacts({"project_name": (project or {}).get("name")}),
        )
