"""
术语检查工具测试
"""

import pytest
from pathlib import Path

from gateflow.utils.terminology import (
    TerminologyChecker,
    TerminologyIssue,
    check_terminology,
    check_file_terminology,
    check_directory_terminology,
    print_terminology_report,
)


class TestTerminologyChecker:
    """术语检查器测试"""
    
    def test_check_text_basic(self):
        """测试基本文本检查"""
        checker = TerminologyChecker()
        
        # 测试正确的术语
        issues = checker.check_text("创建一个项目")
        assert len(issues) == 0
        
        # 测试错误的术语
        issues = checker.check_text("创建一个工程")
        assert len(issues) > 0
        assert any("项目" in issue for issue in issues)
    
    def test_check_text_multiple_issues(self):
        """测试多个术语问题"""
        checker = TerminologyChecker()
        
        text = "创建工程文件并烧录FPGA，注意管脚约束"
        issues = checker.check_text(text)
        
        # 应该检测到多个问题
        assert len(issues) >= 3
    
    def test_check_terminology_function(self):
        """测试便捷函数"""
        issues = check_terminology("这是一个工程文件")
        assert len(issues) > 0
        assert any("项目" in issue for issue in issues)
    
    def test_check_file(self, tmp_path):
        """测试文件检查"""
        # 创建临时文件
        test_file = tmp_path / "test.md"
        test_file.write_text("这是一个工程文件示例", encoding='utf-8')
        
        checker = TerminologyChecker()
        issues = checker.check_file(test_file)
        
        assert len(issues) > 0
        assert all(isinstance(issue, TerminologyIssue) for issue in issues)
        assert all(issue.file_path == str(test_file) for issue in issues)
    
    def test_check_file_not_exists(self):
        """测试不存在的文件"""
        checker = TerminologyChecker()
        issues = checker.check_file("/nonexistent/file.md")
        assert len(issues) == 0
    
    def test_check_directory(self, tmp_path):
        """测试目录检查"""
        # 创建测试文件
        (tmp_path / "test1.md").write_text("工程文件", encoding='utf-8')
        (tmp_path / "test2.py").write_text("# 工程", encoding='utf-8')
        
        checker = TerminologyChecker()
        issues = checker.check_directory(tmp_path, extensions=['.md', '.py'])
        
        assert len(issues) >= 2
    
    def test_check_directory_with_exclude(self, tmp_path):
        """测试带排除模式的目录检查"""
        # 创建目录结构
        exclude_dir = tmp_path / "__pycache__"
        exclude_dir.mkdir()
        
        (exclude_dir / "test.md").write_text("工程文件", encoding='utf-8')
        (tmp_path / "main.md").write_text("项目文件", encoding='utf-8')
        
        checker = TerminologyChecker()
        issues = checker.check_directory(
            tmp_path,
            extensions=['.md'],
            exclude_patterns=['__pycache__']
        )
        
        # 应该只检查 main.md，不检查 __pycache__ 中的文件
        assert len(issues) == 0
    
    def test_get_statistics(self):
        """测试统计功能"""
        checker = TerminologyChecker()
        
        issues = [
            TerminologyIssue("file1.md", 1, "工程", "项目", "warning", "warning"),
            TerminologyIssue("file1.md", 2, "工程", "项目", "warning", "warning"),
            TerminologyIssue("file2.md", 1, "烧录", "编程", "warning", "warning"),
        ]
        
        stats = checker.get_statistics(issues)
        
        assert stats["total_issues"] == 3
        assert stats["by_severity"]["warning"] == 3
        assert stats["by_file"]["file1.md"] == 2
        assert stats["by_file"]["file2.md"] == 1
        assert stats["by_term"]["工程"] == 2
        assert stats["by_term"]["烧录"] == 1


class TestTerminologyRules:
    """术语规则测试"""
    
    def test_project_terminology(self):
        """测试项目相关术语"""
        checker = TerminologyChecker()
        
        # 错误用法
        assert len(checker.check_text("工程名称")) > 0
        assert len(checker.check_text("工程路径")) > 0
        assert len(checker.check_text("工程文件")) > 0
        
        # 正确用法
        assert len(checker.check_text("项目名称")) == 0
        assert len(checker.check_text("项目路径")) == 0
        assert len(checker.check_text("项目文件")) == 0
    
    def test_hardware_terminology(self):
        """测试硬件相关术语"""
        checker = TerminologyChecker()
        
        # 错误用法
        assert len(checker.check_text("烧录FPGA")) > 0
        assert len(checker.check_text("下载比特流")) > 0
        
        # 正确用法
        assert len(checker.check_text("编程 FPGA")) == 0
    
    def test_pin_terminology(self):
        """测试引脚相关术语"""
        checker = TerminologyChecker()
        
        # 错误用法
        assert len(checker.check_text("管脚约束")) > 0
        assert len(checker.check_text("针脚定义")) > 0
        
        # 正确用法
        assert len(checker.check_text("引脚约束")) == 0
    
    def test_constraint_terminology(self):
        """测试约束相关术语"""
        checker = TerminologyChecker()
        
        # 错误用法
        assert len(checker.check_text("时序限制")) > 0
        assert len(checker.check_text("限制条件")) > 0
        
        # 正确用法
        assert len(checker.check_text("时序约束")) == 0


class TestTerminologyIssue:
    """术语问题测试"""
    
    def test_issue_str(self):
        """测试字符串表示"""
        issue = TerminologyIssue(
            file_path="test.md",
            line_number=10,
            original_term="工程",
            suggested_term="项目",
            message="应使用 '项目' 而非 '工程'",
            severity="warning"
        )
        
        result = str(issue)
        assert "test.md" in result
        assert "10" in result
        assert "warning" in result
        assert "项目" in result
        assert "工程" in result
    
    def test_issue_to_dict(self):
        """测试字典转换"""
        issue = TerminologyIssue(
            file_path="test.md",
            line_number=10,
            original_term="工程",
            suggested_term="项目",
            message="应使用 '项目' 而非 '工程'",
            severity="warning"
        )
        
        result = issue.to_dict()
        
        assert result["file_path"] == "test.md"
        assert result["line_number"] == 10
        assert result["original_term"] == "工程"
        assert result["suggested_term"] == "项目"
        assert result["severity"] == "warning"


class TestConvenienceFunctions:
    """便捷函数测试"""
    
    def test_check_terminology(self):
        """测试 check_terminology 函数"""
        issues = check_terminology("工程文件")
        assert isinstance(issues, list)
        assert len(issues) > 0
    
    def test_check_file_terminology(self, tmp_path):
        """测试 check_file_terminology 函数"""
        test_file = tmp_path / "test.md"
        test_file.write_text("工程文件", encoding='utf-8')
        
        issues = check_file_terminology(test_file)
        assert isinstance(issues, list)
        assert len(issues) > 0
    
    def test_check_directory_terminology(self, tmp_path):
        """测试 check_directory_terminology 函数"""
        (tmp_path / "test.md").write_text("工程文件", encoding='utf-8')
        
        issues = check_directory_terminology(tmp_path, extensions=['.md'])
        assert isinstance(issues, list)
        assert len(issues) > 0
    
    def test_print_terminology_report(self, capsys):
        """测试打印报告"""
        issues = [
            TerminologyIssue("test.md", 1, "工程", "项目", "warning", "应使用 '项目'")
        ]
        
        print_terminology_report(issues)
        captured = capsys.readouterr()
        
        assert "术语检查报告" in captured.out
        assert "test.md" in captured.out
    
    def test_print_terminology_report_empty(self, capsys):
        """测试空报告"""
        print_terminology_report([])
        captured = capsys.readouterr()
        
        assert "未发现术语问题" in captured.out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
