"""
工具模块。

提供通用工具函数和解析器。
"""

from gateflow.utils.parser import ReportParser
from gateflow.utils.path_utils import (
    to_tcl_path,
    to_windows_path,
    normalize_path,
    convert_dict_paths,
    PathConverter,
    PATH_KEYS,
)
from gateflow.utils.auto_config import (
    ClockManager,
    InterruptManager,
    ClockSourceType,
    ResetSourceType,
    ClockInfo,
    ResetInfo,
    InterruptInfo,
)
from gateflow.utils.terminology import (
    TerminologyChecker,
    TerminologyIssue,
    check_terminology,
    check_file_terminology,
    check_directory_terminology,
    print_terminology_report,
)

__all__ = [
    "ReportParser",
    "to_tcl_path",
    "to_windows_path",
    "normalize_path",
    "convert_dict_paths",
    "PathConverter",
    "PATH_KEYS",
    # 自动配置
    "ClockManager",
    "InterruptManager",
    "ClockSourceType",
    "ResetSourceType",
    "ClockInfo",
    "ResetInfo",
    "InterruptInfo",
    # 术语检查
    "TerminologyChecker",
    "TerminologyIssue",
    "check_terminology",
    "check_file_terminology",
    "check_directory_terminology",
    "print_terminology_report",
]
