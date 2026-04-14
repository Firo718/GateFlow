"""
文件操作 MCP 工具。

提供文件和目录操作功能，方便 AI 直接管理项目文件。

安全特性：
- 沙箱机制：所有文件操作限制在允许的根目录范围内
- 危险操作保护：删除和覆盖操作需要显式开关
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from gateflow.settings import get_settings
from gateflow.utils.sandbox import (
    SandboxConfig,
    validate_path_for_delete,
    validate_path_for_read,
    validate_path_for_write,
)

logger = logging.getLogger(__name__)


class CreateFileResult(BaseModel):
    """创建文件结果模型"""

    success: bool = Field(description="操作是否成功")
    path: str = Field(description="文件路径")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ReadFileResult(BaseModel):
    """读取文件结果模型"""

    success: bool = Field(description="操作是否成功")
    path: str = Field(description="文件路径")
    content: str = Field(default="", description="文件内容")
    lines: int = Field(default=0, description="行数")
    size: int = Field(default=0, description="文件大小（字节）")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class ListFilesResult(BaseModel):
    """列出文件结果模型"""

    success: bool = Field(description="操作是否成功")
    directory: str = Field(description="目录路径")
    files: list[dict[str, Any]] = Field(default_factory=list, description="文件列表")
    total_count: int = Field(default=0, description="文件总数")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class AppendFileResult(BaseModel):
    """追加文件结果模型"""

    success: bool = Field(description="操作是否成功")
    path: str = Field(description="文件路径")
    appended_lines: int = Field(default=0, description="追加行数")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class DeleteFileResult(BaseModel):
    """删除文件结果模型"""

    success: bool = Field(description="操作是否成功")
    path: str = Field(description="文件路径")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


class CopyFileResult(BaseModel):
    """复制文件结果模型"""

    success: bool = Field(description="操作是否成功")
    source: str = Field(description="源文件路径")
    destination: str = Field(description="目标文件路径")
    message: str = Field(description="结果消息")
    error: str | None = Field(default=None, description="错误信息")


def register_file_tools(mcp: FastMCP, sandbox_config: SandboxConfig | None = None) -> None:
    """
    注册文件操作工具。

    Args:
        mcp: FastMCP 实例
        sandbox_config: 沙箱配置，None 则从全局配置读取
    """
    # 从全局配置读取沙箱配置
    if sandbox_config is None:
        settings = get_settings()
        security = settings.get_security_policy()
        
        # 根据安全策略创建沙箱配置
        if security.sandbox_enabled:
            sandbox_config = SandboxConfig(
                allowed_roots=security.allowed_roots,
                allow_dangerous_operations=security.allow_dangerous_operations,
            )
        else:
            # 沙箱禁用时，允许访问所有路径
            # 但仍需要创建一个空的 SandboxConfig 以保持接口一致
            sandbox_config = SandboxConfig(
                allowed_roots=[],  # 空列表表示不限制
                allow_dangerous_operations=security.allow_dangerous_operations,
            )
            # 标记沙箱已禁用
            sandbox_config._sandbox_disabled = True
    
    logger.info(f"文件工具使用沙箱配置: {sandbox_config.to_dict()}")
    
    # 为方便内部使用，创建一个别名
    config = sandbox_config
    
    # 检查沙箱是否禁用
    sandbox_disabled = getattr(config, "_sandbox_disabled", False)
    
    def _validate_path_for_write(path: str) -> tuple[bool, str]:
        """包装路径验证，支持沙箱禁用"""
        if sandbox_disabled:
            return True, ""
        return validate_path_for_write(path, config.allowed_roots)
    
    def _validate_path_for_read(path: str) -> tuple[bool, str]:
        """包装路径验证，支持沙箱禁用"""
        if sandbox_disabled:
            return True, ""
        return validate_path_for_read(path, config.allowed_roots)
    
    def _validate_path_for_delete(path: str, allow_dangerous: bool) -> tuple[bool, str]:
        """包装路径验证，支持沙箱禁用"""
        if sandbox_disabled:
            # 即使沙箱禁用，删除操作仍需要危险操作开关
            if not (allow_dangerous or config.allow_dangerous_operations):
                return False, (
                    "删除操作需要显式启用危险操作开关。\n\n"
                    "解决方法:\n"
                    "1. 设置 allow_dangerous=True 参数\n"
                    "2. 或通过环境变量启用: export GATEFLOW_ALLOW_DANGEROUS=true\n\n"
                    "警告: 删除操作不可恢复，请谨慎使用！"
                )
            return True, ""
        return validate_path_for_delete(
            path, config.allowed_roots, allow_dangerous or config.allow_dangerous_operations
        )

    @mcp.tool()
    async def create_file(
        path: str,
        content: str = "",
        overwrite: bool = False,
        allow_dangerous: bool = False,
    ) -> CreateFileResult:
        """
        创建新文件。

        创建指定路径的文件，可选择是否覆盖已存在的文件。

        Args:
            path: 文件绝对路径
            content: 文件初始内容（可选）
            overwrite: 是否覆盖已存在的文件，默认 False
            allow_dangerous: 是否允许危险操作（覆盖文件），默认 False

        Returns:
            CreateFileResult 创建结果

        Example:
            创建 Verilog 文件:
            ```
            create_file(
                path="C:/projects/top.v",
                content="module top();\\nendmodule"
            )
            ```
        """
        logger.info(f"创建文件: path={path}, overwrite={overwrite}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_write(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return CreateFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            file_path = Path(path)

            # 检查文件是否存在
            if file_path.exists() and not overwrite:
                return CreateFileResult(
                    success=False,
                    path=path,
                    message="文件已存在",
                    error=f"文件 '{path}' 已存在，如需覆盖请设置 overwrite=True 和 allow_dangerous=True",
                )

            # 覆盖操作需要危险操作开关
            if file_path.exists() and overwrite:
                if not (allow_dangerous or config.allow_dangerous_operations):
                    return CreateFileResult(
                        success=False,
                        path=path,
                        message="覆盖操作需要危险操作开关",
                        error=(
                            f"覆盖已存在的文件 '{path}' 需要启用危险操作开关。\n\n"
                            f"解决方法:\n"
                            f"1. 设置 allow_dangerous=True 参数\n"
                            f"2. 或通过环境变量启用: export GATEFLOW_ALLOW_DANGEROUS=true\n\n"
                            f"警告: 覆盖操作不可恢复，请谨慎使用！"
                        ),
                    )

            # 创建父目录
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            file_path.write_text(content, encoding="utf-8")

            logger.info(f"文件创建成功: {path}")
            return CreateFileResult(
                success=True,
                path=path,
                message=f"文件创建成功: {path}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限创建文件 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"创建文件失败: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="创建文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def read_file(
        path: str,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> ReadFileResult:
        """
        读取文件内容。

        读取指定路径的文件内容，支持读取部分行。

        Args:
            path: 文件绝对路径
            start_line: 起始行号（从 1 开始），默认 1
            end_line: 结束行号（可选，默认到文件末尾）

        Returns:
            ReadFileResult 文件内容

        Example:
            读取完整文件:
            ```
            read_file(path="C:/projects/top.v")
            ```

            读取前 10 行:
            ```
            read_file(path="C:/projects/top.v", end_line=10)
            ```
        """
        logger.info(f"读取文件: path={path}, start_line={start_line}, end_line={end_line}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_read(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return ReadFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            file_path = Path(path)

            # 检查文件是否存在
            if not file_path.exists():
                return ReadFileResult(
                    success=False,
                    path=path,
                    message="文件不存在",
                    error=f"文件 '{path}' 不存在",
                )

            # 检查是否为文件
            if not file_path.is_file():
                return ReadFileResult(
                    success=False,
                    path=path,
                    message="路径不是文件",
                    error=f"'{path}' 不是文件",
                )

            # 读取文件内容
            content_full = file_path.read_text(encoding="utf-8")
            lines = content_full.splitlines(keepends=True)
            total_lines = len(lines)

            # 处理行号范围
            if start_line < 1:
                start_line = 1

            start_idx = start_line - 1
            end_idx = end_line if end_line is not None else total_lines

            # 边界检查
            if start_idx >= total_lines:
                return ReadFileResult(
                    success=False,
                    path=path,
                    message="起始行号超出范围",
                    error=f"起始行号 {start_line} 超出文件总行数 {total_lines}",
                )

            if end_idx > total_lines:
                end_idx = total_lines

            # 提取指定范围的内容
            selected_lines = lines[start_idx:end_idx]
            content = "".join(selected_lines)

            logger.info(f"文件读取成功: {path}, 读取行数: {len(selected_lines)}")
            return ReadFileResult(
                success=True,
                path=path,
                content=content,
                lines=len(selected_lines),
                size=len(content.encode("utf-8")),
                message=f"成功读取文件 {path}，共 {len(selected_lines)} 行",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return ReadFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限读取文件 '{path}': {str(e)}",
            )
        except UnicodeDecodeError as e:
            logger.error(f"编码错误: {e}")
            return ReadFileResult(
                success=False,
                path=path,
                message="文件编码错误",
                error=f"无法解码文件 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return ReadFileResult(
                success=False,
                path=path,
                message="读取文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def list_files(
        directory: str,
        pattern: str = "*",
        recursive: bool = False,
    ) -> ListFilesResult:
        """
        列出目录中的文件。

        列出指定目录中匹配模式的文件和子目录。

        Args:
            directory: 目录绝对路径
            pattern: 文件匹配模式（如 "*.v", "*.xdc"），默认 "*"
            recursive: 是否递归搜索子目录，默认 False

        Returns:
            ListFilesResult 文件列表

        Example:
            列出所有 Verilog 文件:
            ```
            list_files(directory="C:/projects/src", pattern="*.v")
            ```

            递归搜索所有源文件:
            ```
            list_files(directory="C:/projects", pattern="*.v", recursive=True)
            ```
        """
        logger.info(f"列出文件: directory={directory}, pattern={pattern}, recursive={recursive}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_read(directory)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return ListFilesResult(
                    success=False,
                    directory=directory,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            dir_path = Path(directory)

            # 检查目录是否存在
            if not dir_path.exists():
                return ListFilesResult(
                    success=False,
                    directory=directory,
                    message="目录不存在",
                    error=f"目录 '{directory}' 不存在",
                )

            # 检查是否为目录
            if not dir_path.is_dir():
                return ListFilesResult(
                    success=False,
                    directory=directory,
                    message="路径不是目录",
                    error=f"'{directory}' 不是目录",
                )

            # 获取文件列表
            files = []
            if recursive:
                items = dir_path.rglob(pattern)
            else:
                items = dir_path.glob(pattern)

            for item in items:
                try:
                    stat = item.stat()
                    files.append(
                        {
                            "name": item.name,
                            "path": str(item),
                            "relative_path": str(item.relative_to(dir_path)),
                            "is_file": item.is_file(),
                            "is_dir": item.is_dir(),
                            "size": stat.st_size if item.is_file() else 0,
                            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )
                except Exception as e:
                    logger.warning(f"无法获取文件信息 {item}: {e}")
                    continue

            # 排序：目录在前，然后按名称排序
            files.sort(key=lambda x: (not x["is_dir"], x["name"]))

            logger.info(f"列出文件成功: {directory}, 共 {len(files)} 个项目")
            return ListFilesResult(
                success=True,
                directory=directory,
                files=files,
                total_count=len(files),
                message=f"找到 {len(files)} 个项目",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return ListFilesResult(
                success=False,
                directory=directory,
                message="权限不足",
                error=f"没有权限访问目录 '{directory}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return ListFilesResult(
                success=False,
                directory=directory,
                message="列出文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def append_file(
        path: str,
        content: str,
    ) -> AppendFileResult:
        """
        追加内容到文件。

        在文件末尾追加内容，如果文件不存在则创建。

        Args:
            path: 文件绝对路径
            content: 要追加的内容

        Returns:
            AppendFileResult 追加结果

        Example:
            ```
            append_file(
                path="C:/projects/top.v",
                content="\\n// New comment"
            )
            ```
        """
        logger.info(f"追加文件: path={path}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_write(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return AppendFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            file_path = Path(path)

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 计算追加的行数
            appended_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

            # 追加内容
            with file_path.open("a", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"文件追加成功: {path}, 追加 {appended_lines} 行")
            return AppendFileResult(
                success=True,
                path=path,
                appended_lines=appended_lines,
                message=f"成功追加 {appended_lines} 行到文件 {path}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return AppendFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限写入文件 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"追加文件失败: {e}")
            return AppendFileResult(
                success=False,
                path=path,
                message="追加文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def write_file(
        path: str,
        content: str,
        allow_dangerous: bool = False,
    ) -> CreateFileResult:
        """
        写入文件（覆盖）。

        写入内容到文件，覆盖已存在的内容。

        Args:
            path: 文件绝对路径
            content: 文件内容
            allow_dangerous: 是否允许危险操作（覆盖已存在的文件），默认 False

        Returns:
            CreateFileResult 写入结果

        Example:
            ```
            write_file(
                path="C:/projects/top.v",
                content="module top();\\nendmodule"
            )
            ```
        """
        logger.info(f"写入文件: path={path}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_write(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return CreateFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            file_path = Path(path)

            # 检查文件是否存在，如果存在则需要危险操作开关
            if file_path.exists():
                if not (allow_dangerous or config.allow_dangerous_operations):
                    return CreateFileResult(
                        success=False,
                        path=path,
                        message="覆盖操作需要危险操作开关",
                        error=(
                            f"文件 '{path}' 已存在，覆盖需要启用危险操作开关。\n\n"
                            f"解决方法:\n"
                            f"1. 设置 allow_dangerous=True 参数\n"
                            f"2. 或通过环境变量启用: export GATEFLOW_ALLOW_DANGEROUS=true\n\n"
                            f"警告: 覆盖操作不可恢复，请谨慎使用！"
                        ),
                    )

            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            file_path.write_text(content, encoding="utf-8")

            logger.info(f"文件写入成功: {path}")
            return CreateFileResult(
                success=True,
                path=path,
                message=f"文件写入成功: {path}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限写入文件 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="写入文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def delete_file(
        path: str,
        allow_dangerous: bool = False,
    ) -> DeleteFileResult:
        """
        删除文件。

        删除指定路径的文件。

        Args:
            path: 文件绝对路径
            allow_dangerous: 是否允许危险操作（删除文件），默认 False

        Returns:
            DeleteFileResult 删除结果

        Warning:
            删除操作不可恢复，请谨慎使用。
        """
        logger.info(f"删除文件: path={path}")

        try:
            # 沙箱路径校验（删除需要危险操作开关）
            is_valid, error_msg = _validate_path_for_delete(path, allow_dangerous)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return DeleteFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内或未启用危险操作",
                    error=error_msg,
                )

            file_path = Path(path)

            # 检查文件是否存在
            if not file_path.exists():
                return DeleteFileResult(
                    success=False,
                    path=path,
                    message="文件不存在",
                    error=f"文件 '{path}' 不存在",
                )

            # 检查是否为文件
            if file_path.is_dir():
                return DeleteFileResult(
                    success=False,
                    path=path,
                    message="路径是目录",
                    error=f"'{path}' 是目录，请使用删除目录功能",
                )

            # 删除文件
            file_path.unlink()

            logger.info(f"文件删除成功: {path}")
            return DeleteFileResult(
                success=True,
                path=path,
                message=f"文件删除成功: {path}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return DeleteFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限删除文件 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return DeleteFileResult(
                success=False,
                path=path,
                message="删除文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def copy_file(
        source: str,
        destination: str,
        overwrite: bool = False,
        allow_dangerous: bool = False,
    ) -> CopyFileResult:
        """
        复制文件。

        复制文件到新位置。

        Args:
            source: 源文件绝对路径
            destination: 目标文件绝对路径
            overwrite: 是否覆盖已存在的目标文件，默认 False
            allow_dangerous: 是否允许危险操作（覆盖文件），默认 False

        Returns:
            CopyFileResult 复制结果

        Example:
            ```
            copy_file(
                source="C:/templates/top.v",
                destination="C:/projects/top.v"
            )
            ```
        """
        logger.info(f"复制文件: source={source}, destination={destination}")

        try:
            # 沙箱路径校验 - 源路径
            is_valid, error_msg = _validate_path_for_read(source)
            if not is_valid:
                logger.warning(f"源路径校验失败: {error_msg}")
                return CopyFileResult(
                    success=False,
                    source=source,
                    destination=destination,
                    message="源路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            # 沙箱路径校验 - 目标路径
            is_valid, error_msg = _validate_path_for_write(destination)
            if not is_valid:
                logger.warning(f"目标路径校验失败: {error_msg}")
                return CopyFileResult(
                    success=False,
                    source=source,
                    destination=destination,
                    message="目标路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            src_path = Path(source)
            dst_path = Path(destination)

            # 检查源文件是否存在
            if not src_path.exists():
                return CopyFileResult(
                    success=False,
                    source=source,
                    destination=destination,
                    message="源文件不存在",
                    error=f"源文件 '{source}' 不存在",
                )

            # 检查源文件是否为文件
            if not src_path.is_file():
                return CopyFileResult(
                    success=False,
                    source=source,
                    destination=destination,
                    message="源路径不是文件",
                    error=f"'{source}' 不是文件",
                )

            # 检查目标文件是否存在
            if dst_path.exists() and not overwrite:
                return CopyFileResult(
                    success=False,
                    source=source,
                    destination=destination,
                    message="目标文件已存在",
                    error=f"目标文件 '{destination}' 已存在，如需覆盖请设置 overwrite=True 和 allow_dangerous=True",
                )

            # 覆盖操作需要危险操作开关
            if dst_path.exists() and overwrite:
                if not (allow_dangerous or config.allow_dangerous_operations):
                    return CopyFileResult(
                        success=False,
                        source=source,
                        destination=destination,
                        message="覆盖操作需要危险操作开关",
                        error=(
                            f"覆盖目标文件 '{destination}' 需要启用危险操作开关。\n\n"
                            f"解决方法:\n"
                            f"1. 设置 allow_dangerous=True 参数\n"
                            f"2. 或通过环境变量启用: export GATEFLOW_ALLOW_DANGEROUS=true\n\n"
                            f"警告: 覆盖操作不可恢复，请谨慎使用！"
                        ),
                    )

            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # 复制文件
            shutil.copy2(src_path, dst_path)

            logger.info(f"文件复制成功: {source} -> {destination}")
            return CopyFileResult(
                success=True,
                source=source,
                destination=destination,
                message=f"文件复制成功: {source} -> {destination}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return CopyFileResult(
                success=False,
                source=source,
                destination=destination,
                message="权限不足",
                error=f"没有权限复制文件: {str(e)}",
            )
        except Exception as e:
            logger.error(f"复制文件失败: {e}")
            return CopyFileResult(
                success=False,
                source=source,
                destination=destination,
                message="复制文件失败",
                error=str(e),
            )

    @mcp.tool()
    async def create_directory(path: str) -> CreateFileResult:
        """
        创建目录。

        创建指定路径的目录，包括所有必要的父目录。

        Args:
            path: 目录绝对路径

        Returns:
            CreateFileResult 创建结果

        Example:
            ```
            create_directory(path="C:/projects/src/modules")
            ```
        """
        logger.info(f"创建目录: path={path}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_write(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return CreateFileResult(
                    success=False,
                    path=path,
                    message="路径不在允许的沙箱范围内",
                    error=error_msg,
                )

            dir_path = Path(path)

            # 检查目录是否已存在
            if dir_path.exists():
                return CreateFileResult(
                    success=False,
                    path=path,
                    message="目录已存在",
                    error=f"目录 '{path}' 已存在",
                )

            # 创建目录
            dir_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"目录创建成功: {path}")
            return CreateFileResult(
                success=True,
                path=path,
                message=f"目录创建成功: {path}",
            )

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="权限不足",
                error=f"没有权限创建目录 '{path}': {str(e)}",
            )
        except Exception as e:
            logger.error(f"创建目录失败: {e}")
            return CreateFileResult(
                success=False,
                path=path,
                message="创建目录失败",
                error=str(e),
            )

    @mcp.tool()
    async def file_exists(path: str) -> dict[str, Any]:
        """
        检查文件是否存在。

        Args:
            path: 文件或目录绝对路径

        Returns:
            包含存在状态和类型的字典

        Example:
            ```
            file_exists(path="C:/projects/top.v")
            ```
        """
        logger.info(f"检查文件存在: path={path}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_read(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return {
                    "exists": False,
                    "type": None,
                    "path": path,
                    "error": error_msg,
                    "message": "路径不在允许的沙箱范围内",
                }

            file_path = Path(path)

            if not file_path.exists():
                return {
                    "exists": False,
                    "type": None,
                    "path": path,
                    "message": f"路径 '{path}' 不存在",
                }

            # 确定类型
            if file_path.is_file():
                file_type = "file"
            elif file_path.is_dir():
                file_type = "directory"
            else:
                file_type = "other"

            logger.info(f"文件存在: {path}, 类型: {file_type}")
            return {
                "exists": True,
                "type": file_type,
                "path": path,
                "message": f"路径 '{path}' 存在，类型: {file_type}",
            }

        except Exception as e:
            logger.error(f"检查文件存在失败: {e}")
            return {
                "exists": False,
                "type": None,
                "path": path,
                "error": str(e),
                "message": "检查文件存在失败",
            }

    @mcp.tool()
    async def get_file_info(path: str) -> dict[str, Any]:
        """
        获取文件信息。

        获取文件的大小、修改时间等详细信息。

        Args:
            path: 文件绝对路径

        Returns:
            包含文件信息的字典

        Example:
            ```
            get_file_info(path="C:/projects/top.v")
            ```
        """
        logger.info(f"获取文件信息: path={path}")

        try:
            # 沙箱路径校验
            is_valid, error_msg = _validate_path_for_read(path)
            if not is_valid:
                logger.warning(f"路径校验失败: {error_msg}")
                return {
                    "success": False,
                    "path": path,
                    "error": error_msg,
                    "message": "路径不在允许的沙箱范围内",
                }

            file_path = Path(path)

            # 检查文件是否存在
            if not file_path.exists():
                return {
                    "success": False,
                    "path": path,
                    "error": f"路径 '{path}' 不存在",
                    "message": "文件不存在",
                }

            # 获取文件状态
            stat = file_path.stat()

            # 构建文件信息
            info = {
                "success": True,
                "path": path,
                "name": file_path.name,
                "parent": str(file_path.parent),
                "suffix": file_path.suffix,
                "stem": file_path.stem,
                "is_file": file_path.is_file(),
                "is_dir": file_path.is_dir(),
                "size": stat.st_size,
                "size_human": _format_size(stat.st_size),
                "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "message": f"获取文件信息成功",
            }

            # 如果是文件，尝试获取行数
            if file_path.is_file():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    info["lines"] = len(content.splitlines())
                except:
                    info["lines"] = None

            logger.info(f"获取文件信息成功: {path}")
            return info

        except PermissionError as e:
            logger.error(f"权限错误: {e}")
            return {
                "success": False,
                "path": path,
                "error": f"没有权限访问文件 '{path}': {str(e)}",
                "message": "权限不足",
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return {
                "success": False,
                "path": path,
                "error": str(e),
                "message": "获取文件信息失败",
            }


def _format_size(size: int) -> str:
    """
    格式化文件大小为人类可读格式。

    Args:
        size: 文件大小（字节）

    Returns:
        格式化后的大小字符串
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"
