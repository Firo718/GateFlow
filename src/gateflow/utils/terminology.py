"""
GateFlow 术语检查工具

提供术语规范性检查功能，确保代码和文档中的术语使用一致。
"""

import re
from pathlib import Path
from typing import Optional


# 术语规范映射表
TERMINOLOGY_RULES = {
    # 项目相关
    "工程": "项目",
    "工程名称": "项目名称",
    "工程路径": "项目路径",
    "工程文件": "项目文件",
    
    # Block Design 相关
    "块设计": "Block Design",
    "模块设计": "Block Design",
    "IP实例化": "IP 实例",
    "实例名": "实例名称",
    "实例化名称": "实例名称",
    
    # 端口和引脚相关
    "管脚": "引脚",
    "针脚": "引脚",
    
    # 硬件相关
    "烧录": "编程",
    "烧录FPGA": "编程 FPGA",
    "下载比特流": "编程 FPGA",
    "下载FPGA": "编程 FPGA",
    
    # 约束相关
    "限制": "约束",
    "限制条件": "约束",
    
    # 其他
    "模拟": "仿真",
}

# 参数命名规范
PARAMETER_RULES = {
    "projectName": "project_name",
    "instanceName": "instance_name",
    "designName": "design_name",
    "portName": "port_name",
    "clockName": "clock_name",
    "moduleName": "module_name",
    "fileName": "file_name",
    "filePath": "file_path",
}

# 需要避免的术语模式
FORBIDDEN_PATTERNS = [
    (r"工程(?!师|务|序)", "应使用 '项目' 而非 '工程'"),
    (r"烧录", "应使用 '编程' 而非 '烧录'"),
    (r"管脚", "应使用 '引脚' 而非 '管脚'"),
    (r"下载.*FPGA", "应使用 '编程 FPGA' 而非 '下载 FPGA'"),
]


class TerminologyIssue:
    """术语问题"""
    
    def __init__(
        self,
        file_path: str,
        line_number: int,
        original_term: str,
        suggested_term: str,
        message: str,
        severity: str = "warning"
    ):
        """
        初始化术语问题
        
        Args:
            file_path: 文件路径
            line_number: 行号
            original_term: 原始术语
            suggested_term: 建议术语
            message: 问题描述
            severity: 严重程度 (error, warning, info)
        """
        self.file_path = file_path
        self.line_number = line_number
        self.original_term = original_term
        self.suggested_term = suggested_term
        self.message = message
        self.severity = severity
    
    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"{self.file_path}:{self.line_number}: "
            f"{self.severity}: {self.message} "
            f"(建议使用 '{self.suggested_term}' 替代 '{self.original_term}')"
        )
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "original_term": self.original_term,
            "suggested_term": self.suggested_term,
            "message": self.message,
            "severity": self.severity,
        }


class TerminologyChecker:
    """术语检查器"""
    
    def __init__(self, custom_rules: Optional[dict] = None):
        """
        初始化术语检查器
        
        Args:
            custom_rules: 自定义术语规则
        """
        self.rules = TERMINOLOGY_RULES.copy()
        if custom_rules:
            self.rules.update(custom_rules)
        
        # 编译正则表达式模式
        self.patterns = []
        for pattern, message in FORBIDDEN_PATTERNS:
            self.patterns.append((re.compile(pattern), message))
    
    def check_text(self, text: str) -> list[str]:
        """
        检查文本中的术语是否规范
        
        Args:
            text: 要检查的文本
        
        Returns:
            问题列表
        """
        issues = []
        
        # 检查禁止的模式
        for pattern, message in self.patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                issues.append(f"{message} (发现: '{match}')")
        
        # 检查术语映射
        for wrong, correct in self.rules.items():
            if wrong in text:
                issues.append(f"应使用 '{correct}' 而非 '{wrong}'")
        
        return issues
    
    def check_file(self, file_path: str | Path) -> list[TerminologyIssue]:
        """
        检查文件中的术语
        
        Args:
            file_path: 文件路径
        
        Returns:
            术语问题列表
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return []
        
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_number, line in enumerate(lines, start=1):
                # 检查禁止的模式
                for pattern, message in self.patterns:
                    matches = pattern.finditer(line)
                    for match in matches:
                        issues.append(TerminologyIssue(
                            file_path=str(file_path),
                            line_number=line_number,
                            original_term=match.group(),
                            suggested_term=self._get_suggestion(match.group()),
                            message=message,
                            severity="warning"
                        ))
                
                # 检查术语映射
                for wrong, correct in self.rules.items():
                    if wrong in line:
                        issues.append(TerminologyIssue(
                            file_path=str(file_path),
                            line_number=line_number,
                            original_term=wrong,
                            suggested_term=correct,
                            message=f"应使用 '{correct}' 而非 '{wrong}'",
                            severity="warning"
                        ))
        
        except Exception as e:
            issues.append(TerminologyIssue(
                file_path=str(file_path),
                line_number=0,
                original_term="",
                suggested_term="",
                message=f"读取文件失败: {e}",
                severity="error"
            ))
        
        return issues
    
    def check_directory(
        self,
        directory: str | Path,
        extensions: Optional[list[str]] = None,
        exclude_patterns: Optional[list[str]] = None
    ) -> list[TerminologyIssue]:
        """
        检查目录中的所有文件
        
        Args:
            directory: 目录路径
            extensions: 要检查的文件扩展名列表
            exclude_patterns: 要排除的文件模式列表
        
        Returns:
            术语问题列表
        """
        directory = Path(directory)
        
        if extensions is None:
            extensions = ['.py', '.md', '.rst', '.txt']
        
        if exclude_patterns is None:
            exclude_patterns = ['__pycache__', '.git', 'node_modules', 'venv']
        
        issues = []
        
        for ext in extensions:
            for file_path in directory.rglob(f'*{ext}'):
                # 检查是否应该排除
                should_exclude = False
                for pattern in exclude_patterns:
                    if pattern in str(file_path):
                        should_exclude = True
                        break
                
                if not should_exclude:
                    issues.extend(self.check_file(file_path))
        
        return issues
    
    def _get_suggestion(self, wrong_term: str) -> str:
        """获取建议的正确术语"""
        return self.rules.get(wrong_term, wrong_term)
    
    def get_statistics(self, issues: list[TerminologyIssue]) -> dict:
        """
        获取问题统计信息
        
        Args:
            issues: 问题列表
        
        Returns:
            统计信息字典
        """
        stats = {
            "total_issues": len(issues),
            "by_severity": {},
            "by_file": {},
            "by_term": {},
        }
        
        for issue in issues:
            # 按严重程度统计
            severity = issue.severity
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
            
            # 按文件统计
            file_path = issue.file_path
            stats["by_file"][file_path] = stats["by_file"].get(file_path, 0) + 1
            
            # 按术语统计
            term = issue.original_term
            stats["by_term"][term] = stats["by_term"].get(term, 0) + 1
        
        return stats


def check_terminology(text: str) -> list[str]:
    """
    检查文本中的术语是否规范（便捷函数）
    
    Args:
        text: 要检查的文本
    
    Returns:
        问题列表
    
    Example:
        ```python
        from gateflow.utils.terminology import check_terminology
        
        issues = check_terminology("创建一个工程文件")
        # 返回: ["应使用 '项目' 而非 '工程'"]
        ```
    """
    checker = TerminologyChecker()
    return checker.check_text(text)


def check_file_terminology(file_path: str | Path) -> list[TerminologyIssue]:
    """
    检查文件中的术语（便捷函数）
    
    Args:
        file_path: 文件路径
    
    Returns:
        术语问题列表
    
    Example:
        ```python
        from gateflow.utils.terminology import check_file_terminology
        
        issues = check_file_terminology("docs/README.md")
        for issue in issues:
            print(issue)
        ```
    """
    checker = TerminologyChecker()
    return checker.check_file(file_path)


def check_directory_terminology(
    directory: str | Path,
    extensions: Optional[list[str]] = None
) -> list[TerminologyIssue]:
    """
    检查目录中的术语（便捷函数）
    
    Args:
        directory: 目录路径
        extensions: 要检查的文件扩展名列表
    
    Returns:
        术语问题列表
    
    Example:
        ```python
        from gateflow.utils.terminology import check_directory_terminology
        
        issues = check_directory_terminology("docs", extensions=[".md"])
        print(f"发现 {len(issues)} 个术语问题")
        ```
    """
    checker = TerminologyChecker()
    return checker.check_directory(directory, extensions)


def print_terminology_report(issues: list[TerminologyIssue]) -> None:
    """
    打印术语检查报告
    
    Args:
        issues: 问题列表
    """
    if not issues:
        print("✓ 未发现术语问题")
        return
    
    checker = TerminologyChecker()
    stats = checker.get_statistics(issues)
    
    print("\n" + "="*60)
    print("术语检查报告")
    print("="*60)
    
    print(f"\n总计发现 {stats['total_issues']} 个问题")
    
    print("\n按严重程度:")
    for severity, count in stats["by_severity"].items():
        print(f"  {severity}: {count}")
    
    print("\n按文件:")
    for file_path, count in sorted(stats["by_file"].items(), key=lambda x: -x[1]):
        print(f"  {file_path}: {count}")
    
    print("\n按术语:")
    for term, count in sorted(stats["by_term"].items(), key=lambda x: -x[1]):
        print(f"  '{term}': {count}")
    
    print("\n详细问题:")
    for issue in issues:
        print(f"  {issue}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # 示例：检查当前目录
    import sys
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = "."
    
    path = Path(target)
    
    if path.is_file():
        issues = check_file_terminology(path)
    elif path.is_dir():
        issues = check_directory_terminology(path)
    else:
        print(f"错误: 路径不存在: {path}")
        sys.exit(1)
    
    print_terminology_report(issues)
    
    # 返回非零退出码如果有问题
    sys.exit(1 if issues else 0)
