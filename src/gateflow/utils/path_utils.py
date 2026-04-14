"""
路径工具模块

提供路径格式转换功能，自动将 Windows 路径转换为 Tcl 格式。
"""

import os
import re
from pathlib import Path
from typing import Any


def to_tcl_path(path: str | Path) -> str:
    """
    将路径转换为 Tcl 格式。
    
    Windows 路径使用反斜杠，Tcl 使用正斜杠。
    此函数自动转换路径格式。
    
    Args:
        path: 原始路径（Windows 或 Unix 格式）
    
    Returns:
        Tcl 格式路径（正斜杠）
    
    Example:
        >>> to_tcl_path("C:\\Users\\project")
        'C:/Users/project'
        >>> to_tcl_path("D:/Xilinx/Vivado")
        'D:/Xilinx/Vivado'
        >>> to_tcl_path(r"D:\\project\\test")
        'D:/project/test'
    """
    # 转换为字符串
    if isinstance(path, Path):
        path_str = str(path)
    else:
        path_str = path
    
    # 统一使用正斜杠
    result = path_str.replace("\\", "/")
    
    return result


def to_windows_path(path: str) -> Path:
    """
    将 Tcl 路径转换为 Windows 路径。
    
    Args:
        path: Tcl 格式路径
    
    Returns:
        Windows Path 对象
    
    Example:
        >>> to_windows_path("C:/Users/project")
        WindowsPath('C:\\Users\\project')
    """
    # Tcl 路径使用正斜杠，转换为系统路径
    return Path(path.replace("/", os.sep))


def normalize_path(path: str | Path) -> str:
    """
    规范化路径，返回绝对路径的 Tcl 格式。
    
    Args:
        path: 原始路径
    
    Returns:
        规范化的 Tcl 格式路径
    
    Example:
        >>> normalize_path("./project")
        'F:/current/dir/project'  # 假设当前目录为 F:/current/dir
    """
    # 转换为 Path 对象
    if isinstance(path, str):
        p = Path(path)
    else:
        p = path
    
    # 获取绝对路径
    try:
        abs_path = p.resolve()
    except (OSError, RuntimeError):
        # 如果无法解析（如路径不存在），使用绝对路径
        abs_path = p.absolute()
    
    # 转换为 Tcl 格式
    return to_tcl_path(abs_path)


def convert_dict_paths(data: dict, keys: list[str] | None = None) -> dict:
    """
    递归转换字典中的路径值。
    
    Args:
        data: 原始字典
        keys: 需要转换的键名列表，如果为 None 则自动检测
    
    Returns:
        转换后的字典
    
    Example:
        >>> data = {"path": "C:\\Users\\project", "name": "test"}
        >>> convert_dict_paths(data)
        {'path': 'C:/Users/project', 'name': 'test'}
    """
    if keys is None:
        keys = PATH_KEYS
    
    result = {}
    
    for key, value in data.items():
        # 检查键名是否匹配路径键
        key_lower = key.lower()
        is_path_key = any(
            key_lower == path_key or key_lower.endswith(f"_{path_key}")
            for path_key in keys
        )
        
        if is_path_key and isinstance(value, str):
            # 转换路径值
            result[key] = to_tcl_path(value)
        elif is_path_key and isinstance(value, list):
            # 处理路径键对应的列表（如 files 列表）
            result[key] = [
                to_tcl_path(item) if isinstance(item, str)
                else convert_dict_paths(item, keys) if isinstance(item, dict)
                else item
                for item in value
            ]
        elif isinstance(value, dict):
            # 递归处理嵌套字典
            result[key] = convert_dict_paths(value, keys)
        elif isinstance(value, list):
            # 处理非路径键的列表
            result[key] = [
                convert_dict_paths(item, keys) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


# 常见路径键名
PATH_KEYS = [
    "path",
    "dir",
    "directory",
    "file",
    "files",
    "filename",
    "output",
    "output_dir",
    "output_path",
    "source",
    "source_dir",
    "source_path",
    "vivado_path",
    "project_path",
    "working_dir",
    "script_path",
    "constraint_file",
    "bitstream",
    "xdc",
    "tcl",
]


class PathConverter:
    """
    路径转换器
    
    提供路径转换的高级功能，包括命令中的路径检测和转换。
    """
    
    # Windows 路径正则模式
    # 匹配: C:\path, D:/path, \\server\share, etc.
    WINDOWS_PATH_PATTERN = re.compile(
        r'''
        (?:
            # 盘符路径: C:\, D:/, etc.
            [A-Za-z]:[\\/]
            |
            # UNC 路径: \\server\share
            \\\\[A-Za-z0-9_\-\.]+(?:\\[A-Za-z0-9_\-\.]+)+
            |
            # 相对路径（以 . 或 .. 开头）
            \.\.?[\\/]
        )
        # 路径部分（允许中文、空格等）
        [^\s"']*
        ''',
        re.VERBOSE
    )
    
    # Tcl 命令中的路径参数模式
    # 匹配引号或花括号包围的路径
    TCL_PATH_ARG_PATTERN = re.compile(
        r'''
        (?:
            # 双引号包围的路径
            "([^"]+)"
            |
            # 花括号包围的路径
            \{([^}]+)\}
        )
        ''',
        re.VERBOSE
    )
    
    @classmethod
    def convert_paths_in_command(cls, command: str) -> str:
        """
        转换 Tcl 命令中的 Windows 路径为 Tcl 格式。
        
        此方法会检测命令中的路径参数并自动转换。
        
        Args:
            command: 原始 Tcl 命令
        
        Returns:
            转换后的命令
        
        Example:
            >>> cmd = 'create_project "my_proj" "C:\\Users\\project"'
            >>> PathConverter.convert_paths_in_command(cmd)
            'create_project "my_proj" "C:/Users/project"'
        """
        def replace_path(match: re.Match) -> str:
            """替换匹配到的路径"""
            # 获取匹配的路径（引号或花括号中的内容）
            quoted_path = match.group(1) or match.group(2)
            
            if quoted_path:
                # 检查是否包含反斜杠（需要转换）
                if '\\' in quoted_path:
                    converted = to_tcl_path(quoted_path)
                    # 保持原来的引号格式
                    if match.group(1):
                        return f'"{converted}"'
                    else:
                        return f'{{{converted}}}'
            
            return match.group(0)
        
        # 替换所有路径参数
        result = cls.TCL_PATH_ARG_PATTERN.sub(replace_path, command)
        
        return result
    
    @classmethod
    def detect_and_convert(cls, text: str) -> str:
        """
        检测文本中的 Windows 路径并转换为 Tcl 格式。
        
        Args:
            text: 原始文本
        
        Returns:
            转换后的文本
        
        Example:
            >>> text = "Project path: C:\\Users\\project"
            >>> PathConverter.detect_and_convert(text)
            'Project path: C:/Users/project'
        """
        def replace_path(match: re.Match) -> str:
            """替换匹配到的路径"""
            path = match.group(0)
            if '\\' in path:
                return to_tcl_path(path)
            return path
        
        return cls.WINDOWS_PATH_PATTERN.sub(replace_path, text)
    
    @classmethod
    def is_tcl_path(cls, path: str) -> bool:
        """
        检查路径是否为 Tcl 格式（使用正斜杠）。
        
        Args:
            path: 路径字符串
        
        Returns:
            是否为 Tcl 格式
        """
        # Tcl 路径使用正斜杠，不包含反斜杠
        return '/' in path and '\\' not in path
    
    @classmethod
    def is_windows_path(cls, path: str) -> bool:
        """
        检查路径是否为 Windows 格式（使用反斜杠）。
        
        Args:
            path: 路径字符串
        
        Returns:
            是否为 Windows 格式
        """
        # Windows 路径包含反斜杠
        return '\\' in path


def convert_paths_in_dict_recursive(data: Any, keys: list[str] | None = None) -> Any:
    """
    递归转换任意数据结构中的路径。
    
    支持字典、列表、元组等嵌套结构。
    
    Args:
        data: 原始数据
        keys: 需要转换的键名列表
    
    Returns:
        转换后的数据
    """
    if keys is None:
        keys = PATH_KEYS
    
    if isinstance(data, dict):
        return convert_dict_paths(data, keys)
    elif isinstance(data, list):
        return [convert_paths_in_dict_recursive(item, keys) for item in data]
    elif isinstance(data, tuple):
        return tuple(convert_paths_in_dict_recursive(item, keys) for item in data)
    elif isinstance(data, str):
        # 对于字符串，检查是否看起来像路径
        if '\\' in data and (':' in data[:2] or data.startswith('\\\\')):
            return to_tcl_path(data)
        return data
    else:
        return data
