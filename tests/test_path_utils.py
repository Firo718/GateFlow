"""
路径工具模块测试
"""

import pytest
from pathlib import Path
from gateflow.utils.path_utils import (
    to_tcl_path,
    to_windows_path,
    normalize_path,
    convert_dict_paths,
    PathConverter,
    PATH_KEYS,
)


class TestToTclPath:
    """测试 to_tcl_path 函数"""
    
    def test_windows_path_with_backslash(self):
        """测试 Windows 反斜杠路径转换"""
        assert to_tcl_path("C:\\Users\\project") == "C:/Users/project"
        assert to_tcl_path("D:\\Xilinx\\Vivado") == "D:/Xilinx/Vivado"
    
    def test_mixed_slashes(self):
        """测试混合斜杠路径"""
        assert to_tcl_path("C:/Users\\project") == "C:/Users/project"
        assert to_tcl_path("D:\\Xilinx/Vivado") == "D:/Xilinx/Vivado"
    
    def test_forward_slash_path(self):
        """测试已经是正斜杠的路径"""
        assert to_tcl_path("C:/Users/project") == "C:/Users/project"
        assert to_tcl_path("/home/user/project") == "/home/user/project"
    
    def test_path_object(self):
        """测试 Path 对象"""
        path = Path("C:\\Users\\project")
        assert to_tcl_path(path) == "C:/Users/project"
    
    def test_unc_path(self):
        """测试 UNC 路径"""
        # UNC 路径也会被转换
        assert to_tcl_path("\\\\server\\share\\folder") == "//server/share/folder"
    
    def test_relative_path(self):
        """测试相对路径"""
        assert to_tcl_path(".\\project\\src") == "./project/src"
        assert to_tcl_path("..\\project\\src") == "../project/src"
    
    def test_path_with_spaces(self):
        """测试带空格的路径"""
        assert to_tcl_path("C:\\Program Files\\Vivado") == "C:/Program Files/Vivado"
    
    def test_path_with_chinese(self):
        """测试带中文的路径"""
        assert to_tcl_path("C:\\用户\\项目") == "C:/用户/项目"


class TestToWindowsPath:
    """测试 to_windows_path 函数"""
    
    def test_tcl_path_conversion(self):
        """测试 Tcl 路径转换为 Windows 路径"""
        result = to_windows_path("C:/Users/project")
        # 结果应该是 Path 对象
        assert isinstance(result, Path)
        # 在 Windows 上，str(Path) 会使用反斜杠
        assert "Users" in str(result) and "project" in str(result)
    
    def test_forward_slash_path(self):
        """测试正斜杠路径"""
        result = to_windows_path("/home/user/project")
        assert isinstance(result, Path)


class TestNormalizePath:
    """测试 normalize_path 函数"""
    
    def test_relative_path_normalization(self):
        """测试相对路径规范化"""
        # 相对路径会被转换为绝对路径
        result = normalize_path("./project")
        # 结果应该是绝对路径（正斜杠格式）
        assert ":" in result or result.startswith("/")
        assert "/" in result
    
    def test_absolute_path_normalization(self):
        """测试绝对路径规范化"""
        result = normalize_path("C:\\Users\\project")
        # 应该转换为正斜杠
        assert "/" in result
        assert "\\" not in result
    
    def test_path_object_normalization(self):
        """测试 Path 对象规范化"""
        path = Path("C:\\Users\\project")
        result = normalize_path(path)
        assert "/" in result
        assert "\\" not in result


class TestConvertDictPaths:
    """测试 convert_dict_paths 函数"""
    
    def test_simple_dict_conversion(self):
        """测试简单字典转换"""
        data = {
            "path": "C:\\Users\\project",
            "name": "test",
        }
        result = convert_dict_paths(data)
        assert result["path"] == "C:/Users/project"
        assert result["name"] == "test"
    
    def test_nested_dict_conversion(self):
        """测试嵌套字典转换"""
        data = {
            "project": {
                "path": "C:\\Users\\project",
                "output_dir": "D:\\output",
            },
            "name": "test",
        }
        result = convert_dict_paths(data)
        assert result["project"]["path"] == "C:/Users/project"
        assert result["project"]["output_dir"] == "D:/output"
    
    def test_list_conversion(self):
        """测试列表转换"""
        data = {
            "files": [
                "C:\\src\\file1.v",
                "D:\\src\\file2.v",
            ],
        }
        result = convert_dict_paths(data)
        assert result["files"][0] == "C:/src/file1.v"
        assert result["files"][1] == "D:/src/file2.v"
    
    def test_custom_keys(self):
        """测试自定义键名"""
        data = {
            "custom_path": "C:\\Users\\project",
            "name": "test",
        }
        result = convert_dict_paths(data, keys=["custom_path"])
        assert result["custom_path"] == "C:/Users/project"
    
    def test_path_key_suffix(self):
        """测试路径键后缀匹配"""
        data = {
            "source_path": "C:\\src",
            "output_path": "D:\\output",
        }
        result = convert_dict_paths(data)
        assert result["source_path"] == "C:/src"
        assert result["output_path"] == "D:/output"


class TestPathConverter:
    """测试 PathConverter 类"""
    
    def test_convert_paths_in_command(self):
        """测试命令中的路径转换"""
        cmd = 'create_project "my_proj" "C:\\Users\\project"'
        result = PathConverter.convert_paths_in_command(cmd)
        assert result == 'create_project "my_proj" "C:/Users/project"'
    
    def test_convert_multiple_paths_in_command(self):
        """测试命令中的多个路径转换"""
        cmd = 'add_files "C:\\src\\file1.v" "D:\\src\\file2.v"'
        result = PathConverter.convert_paths_in_command(cmd)
        assert "C:/src/file1.v" in result
        assert "D:/src/file2.v" in result
    
    def test_convert_braced_paths(self):
        """测试花括号包围的路径"""
        cmd = 'open_project {C:\\Users\\project\\test.xpr}'
        result = PathConverter.convert_paths_in_command(cmd)
        assert result == 'open_project {C:/Users/project/test.xpr}'
    
    def test_no_conversion_needed(self):
        """测试不需要转换的命令"""
        cmd = 'create_project "my_proj" "/home/user/project"'
        result = PathConverter.convert_paths_in_command(cmd)
        assert result == cmd
    
    def test_detect_and_convert(self):
        """测试检测和转换"""
        text = "Project path: C:\\Users\\project"
        result = PathConverter.detect_and_convert(text)
        assert result == "Project path: C:/Users/project"
    
    def test_is_tcl_path(self):
        """测试 Tcl 路径检测"""
        assert PathConverter.is_tcl_path("C:/Users/project") is True
        assert PathConverter.is_tcl_path("C:\\Users\\project") is False
        assert PathConverter.is_tcl_path("/home/user/project") is True
    
    def test_is_windows_path(self):
        """测试 Windows 路径检测"""
        assert PathConverter.is_windows_path("C:\\Users\\project") is True
        assert PathConverter.is_windows_path("C:/Users/project") is False
        assert PathConverter.is_windows_path("/home/user/project") is False
    
    def test_complex_command(self):
        """测试复杂命令"""
        cmd = '''
        create_project "test" "C:\\Projects\\test" -part xc7a35t
        add_files -fileset sources_1 {"C:\\src\\top.v" "D:\\ip\\core.xci"}
        set_property top top [current_fileset]
        '''
        result = PathConverter.convert_paths_in_command(cmd)
        assert "C:/Projects/test" in result
        assert "C:/src/top.v" in result
        assert "D:/ip/core.xci" in result


class TestPathKeys:
    """测试路径键常量"""
    
    def test_path_keys_exist(self):
        """测试路径键列表存在"""
        assert "path" in PATH_KEYS
        assert "dir" in PATH_KEYS
        assert "file" in PATH_KEYS
        assert "vivado_path" in PATH_KEYS
        assert "project_path" in PATH_KEYS
    
    def test_path_keys_coverage(self):
        """测试路径键覆盖常见场景"""
        # 确保常见路径键都在列表中
        expected_keys = [
            "path", "dir", "directory", "file", "filename",
            "output", "output_dir", "source", "source_dir",
        ]
        for key in expected_keys:
            assert key in PATH_KEYS, f"缺少路径键: {key}"


class TestEdgeCases:
    """测试边界情况"""
    
    def test_empty_string(self):
        """测试空字符串"""
        assert to_tcl_path("") == ""
    
    def test_single_character(self):
        """测试单个字符"""
        assert to_tcl_path("C") == "C"
    
    def test_no_colon(self):
        """测试无盘符路径"""
        assert to_tcl_path("\\\\server\\share") == "//server/share"
    
    def test_network_path(self):
        """测试网络路径"""
        result = to_tcl_path("\\\\192.168.1.100\\share\\folder")
        assert result == "//192.168.1.100/share/folder"
    
    def test_path_with_special_chars(self):
        """测试特殊字符路径"""
        result = to_tcl_path("C:\\project (test)\\folder")
        assert result == "C:/project (test)/folder"
    
    def test_dict_with_none_values(self):
        """测试包含 None 值的字典"""
        data = {
            "path": None,
            "name": "test",
        }
        result = convert_dict_paths(data)
        assert result["path"] is None
        assert result["name"] == "test"
    
    def test_dict_with_numeric_values(self):
        """测试包含数值的字典"""
        data = {
            "path": "C:\\project",
            "count": 10,
            "ratio": 0.5,
        }
        result = convert_dict_paths(data)
        assert result["path"] == "C:/project"
        assert result["count"] == 10
        assert result["ratio"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
