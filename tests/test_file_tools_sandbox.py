"""
文件工具沙箱机制测试。

测试沙箱路径校验、危险操作保护等功能。
"""

import os
import tempfile
from pathlib import Path

import pytest

from gateflow.utils.sandbox import (
    SandboxConfig,
    get_default_config,
    set_default_config,
    validate_path,
    validate_path_for_delete,
    validate_path_for_read,
    validate_path_for_write,
)


class TestSandboxConfig:
    """测试沙箱配置"""

    def test_default_config(self):
        """测试默认配置"""
        config = SandboxConfig()

        # 应该包含默认工作空间目录
        assert len(config.allowed_roots) >= 1
        assert any(".gateflow" in str(root) for root in config.allowed_roots)

        # 默认不允许危险操作
        assert config.allow_dangerous_operations is False

    def test_custom_roots(self):
        """测试自定义根目录"""
        custom_root = "/tmp/test_workspace"
        config = SandboxConfig(allowed_roots=[custom_root])

        assert len(config.allowed_roots) == 1
        assert Path(custom_root).resolve() in config.allowed_roots

    def test_allow_dangerous_operations(self):
        """测试危险操作开关"""
        config = SandboxConfig(allow_dangerous_operations=True)
        assert config.allow_dangerous_operations is True

    def test_add_remove_root(self):
        """测试添加和移除根目录"""
        config = SandboxConfig()
        initial_count = len(config.allowed_roots)

        # 添加根目录
        new_root = "/tmp/new_workspace"
        config.add_root(new_root)
        assert len(config.allowed_roots) == initial_count + 1
        assert Path(new_root).resolve() in config.allowed_roots

        # 移除根目录
        config.remove_root(new_root)
        assert len(config.allowed_roots) == initial_count
        assert Path(new_root).resolve() not in config.allowed_roots

    def test_from_env(self, monkeypatch):
        """测试从环境变量创建配置"""
        # 设置环境变量 - Windows 使用分号分隔
        test_roots = "/tmp/test1;/tmp/test2" if os.name == "nt" else "/tmp/test1:/tmp/test2"
        monkeypatch.setenv("GATEFLOW_WORKSPACE_ROOTS", test_roots)
        monkeypatch.setenv("GATEFLOW_ALLOW_DANGEROUS", "true")

        config = SandboxConfig.from_env()

        assert len(config.allowed_roots) == 2
        assert config.allow_dangerous_operations is True

    def test_to_dict(self):
        """测试转换为字典"""
        config = SandboxConfig(allowed_roots=["/tmp/test"])
        config_dict = config.to_dict()

        assert "allowed_roots" in config_dict
        assert "allow_dangerous_operations" in config_dict
        assert isinstance(config_dict["allowed_roots"], list)


class TestValidatePath:
    """测试路径校验"""

    def test_validate_path_in_root(self, tmp_path):
        """测试在根目录内的路径"""
        root = tmp_path
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        is_valid, error = validate_path(test_file, [root], must_exist=True)

        assert is_valid is True
        assert error == ""

    def test_validate_path_outside_root(self, tmp_path):
        """测试在根目录外的路径"""
        root = tmp_path
        outside_path = "/etc/passwd"  # 系统文件，应该在沙箱外

        is_valid, error = validate_path(outside_path, [root])

        assert is_valid is False
        assert "不在允许的沙箱范围内" in error
        assert "GATEFLOW_WORKSPACE_ROOTS" in error

    def test_validate_path_nonexistent(self, tmp_path):
        """测试不存在的路径"""
        root = tmp_path
        nonexistent = tmp_path / "nonexistent.txt"

        # 不要求存在
        is_valid, error = validate_path(nonexistent, [root], must_exist=False)
        assert is_valid is True

        # 要求存在
        is_valid, error = validate_path(nonexistent, [root], must_exist=True)
        assert is_valid is False
        assert "不存在" in error

    def test_validate_path_subdirectory(self, tmp_path):
        """测试子目录路径"""
        root = tmp_path
        subdir = tmp_path / "subdir" / "deep" / "path"
        subdir.mkdir(parents=True, exist_ok=True)

        is_valid, error = validate_path(subdir, [root])

        assert is_valid is True

    def test_validate_path_symlink_outside(self, tmp_path):
        """测试符号链接指向沙箱外"""
        root = tmp_path
        link_path = tmp_path / "link_to_outside"

        # 注意：在某些系统上可能需要管理员权限创建符号链接
        try:
            # 创建指向沙箱外的符号链接
            link_path.symlink_to("/etc")
            is_valid, error = validate_path(link_path, [root])
            # 符号链接解析后应该在沙箱外
            assert is_valid is False
        except (OSError, NotImplementedError):
            # 跳过不支持符号链接的系统
            pytest.skip("系统不支持符号链接")


class TestValidatePathForOperations:
    """测试特定操作的路径校验"""

    def test_validate_for_read(self, tmp_path):
        """测试读取路径校验"""
        root = tmp_path
        test_file = tmp_path / "read_test.txt"
        test_file.write_text("content")

        # 在沙箱内且存在
        is_valid, error = validate_path_for_read(test_file, [root])
        assert is_valid is True

        # 在沙箱内但不存在
        nonexistent = tmp_path / "nonexistent.txt"
        is_valid, error = validate_path_for_read(nonexistent, [root])
        assert is_valid is False
        assert "不存在" in error

    def test_validate_for_write(self, tmp_path):
        """测试写入路径校验"""
        root = tmp_path
        new_file = tmp_path / "new_file.txt"

        # 在沙箱内，不需要存在
        is_valid, error = validate_path_for_write(new_file, [root])
        assert is_valid is True

        # 在沙箱外
        outside = "/tmp/outside_sandbox.txt"
        is_valid, error = validate_path_for_write(outside, [root])
        assert is_valid is False

    def test_validate_for_delete_without_permission(self, tmp_path):
        """测试删除路径校验 - 无权限"""
        root = tmp_path
        test_file = tmp_path / "delete_test.txt"
        test_file.write_text("content")

        # 不允许危险操作
        is_valid, error = validate_path_for_delete(
            test_file, [root], allow_dangerous=False
        )

        assert is_valid is False
        assert "危险操作开关" in error
        assert "GATEFLOW_ALLOW_DANGEROUS" in error

    def test_validate_for_delete_with_permission(self, tmp_path):
        """测试删除路径校验 - 有权限"""
        root = tmp_path
        test_file = tmp_path / "delete_test.txt"
        test_file.write_text("content")

        # 允许危险操作
        is_valid, error = validate_path_for_delete(
            test_file, [root], allow_dangerous=True
        )

        assert is_valid is True
        assert error == ""

    def test_validate_for_delete_outside_sandbox(self, tmp_path):
        """测试删除沙箱外的文件"""
        root = tmp_path
        # 创建一个在沙箱外的临时文件
        outside_dir = Path(tempfile.mkdtemp())
        outside_file = outside_dir / "test_outside.txt"
        outside_file.write_text("test content")

        try:
            # 即使允许危险操作，沙箱外的文件也不能删除
            is_valid, error = validate_path_for_delete(
                str(outside_file), [root], allow_dangerous=True
            )

            assert is_valid is False
            assert "不在允许的沙箱范围内" in error
        finally:
            # 清理临时文件
            if outside_file.exists():
                outside_file.unlink()
            if outside_dir.exists():
                outside_dir.rmdir()


class TestGlobalConfig:
    """测试全局配置管理"""

    def test_get_default_config(self):
        """测试获取默认配置"""
        config = get_default_config()
        assert isinstance(config, SandboxConfig)

        # 再次获取应该是同一个实例
        config2 = get_default_config()
        assert config is config2

    def test_set_default_config(self):
        """测试设置默认配置"""
        custom_config = SandboxConfig(allowed_roots=["/tmp/custom"])
        set_default_config(custom_config)

        # 获取的应该是自定义配置
        config = get_default_config()
        assert config is custom_config

        # 恢复默认配置
        set_default_config(SandboxConfig.from_env())


@pytest.mark.integration
class TestSandboxIntegration:
    """集成测试 - 测试沙箱与文件工具的集成"""

    @pytest.fixture
    def sandbox_setup(self, tmp_path):
        """设置测试环境"""
        # 创建测试文件
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # 创建子目录
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        return {
            "root": tmp_path,
            "test_file": test_file,
            "subdir": subdir,
        }

    def test_read_file_in_sandbox(self, sandbox_setup):
        """测试在沙箱内读取文件"""
        root = sandbox_setup["root"]
        test_file = sandbox_setup["test_file"]

        is_valid, error = validate_path_for_read(test_file, [root])
        assert is_valid is True

    def test_read_file_outside_sandbox(self, sandbox_setup):
        """测试读取沙箱外的文件"""
        root = sandbox_setup["root"]
        # 创建一个在沙箱外的临时文件
        outside_dir = Path(tempfile.mkdtemp())
        outside_file = outside_dir / "test_outside.txt"
        outside_file.write_text("test content")

        try:
            is_valid, error = validate_path_for_read(str(outside_file), [root])
            assert is_valid is False
            assert "不在允许的沙箱范围内" in error
        finally:
            # 清理临时文件
            if outside_file.exists():
                outside_file.unlink()
            if outside_dir.exists():
                outside_dir.rmdir()

    def test_write_file_in_sandbox(self, sandbox_setup):
        """测试在沙箱内写入文件"""
        root = sandbox_setup["root"]
        new_file = root / "new_file.txt"

        is_valid, error = validate_path_for_write(new_file, [root])
        assert is_valid is True

    def test_write_file_outside_sandbox(self, sandbox_setup):
        """测试写入沙箱外的文件"""
        root = sandbox_setup["root"]
        outside_file = "/tmp/outside.txt"

        is_valid, error = validate_path_for_write(outside_file, [root])
        assert is_valid is False

    def test_delete_file_requires_permission(self, sandbox_setup):
        """测试删除文件需要权限"""
        root = sandbox_setup["root"]
        test_file = sandbox_setup["test_file"]

        # 无权限
        is_valid, error = validate_path_for_delete(test_file, [root], allow_dangerous=False)
        assert is_valid is False
        assert "危险操作开关" in error

        # 有权限
        is_valid, error = validate_path_for_delete(test_file, [root], allow_dangerous=True)
        assert is_valid is True

    def test_copy_between_sandbox_paths(self, sandbox_setup):
        """测试在沙箱内复制文件"""
        root = sandbox_setup["root"]
        source = sandbox_setup["test_file"]
        dest = root / "copy.txt"

        # 源路径校验
        is_valid, error = validate_path_for_read(source, [root])
        assert is_valid is True

        # 目标路径校验
        is_valid, error = validate_path_for_write(dest, [root])
        assert is_valid is True

    def test_copy_from_outside_sandbox(self, sandbox_setup):
        """测试从沙箱外复制文件"""
        root = sandbox_setup["root"]
        source = "/etc/passwd"
        dest = root / "copy.txt"

        # 源路径校验应该失败
        is_valid, error = validate_path_for_read(source, [root])
        assert is_valid is False

    def test_copy_to_outside_sandbox(self, sandbox_setup):
        """测试复制文件到沙箱外"""
        root = sandbox_setup["root"]
        source = sandbox_setup["test_file"]
        dest = "/tmp/outside_copy.txt"

        # 目标路径校验应该失败
        is_valid, error = validate_path_for_write(dest, [root])
        assert is_valid is False


class TestErrorMessages:
    """测试错误信息的可操作性"""

    def test_error_message_contains_solution(self, tmp_path):
        """测试错误信息包含解决方法"""
        root = tmp_path
        outside_path = "/etc/passwd"

        is_valid, error = validate_path(outside_path, [root])

        assert is_valid is False
        # 错误信息应该包含解决方法
        assert "解决方法" in error
        assert "GATEFLOW_WORKSPACE_ROOTS" in error

    def test_delete_error_message(self, tmp_path):
        """测试删除操作的错误信息"""
        root = tmp_path
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        is_valid, error = validate_path_for_delete(test_file, [root], allow_dangerous=False)

        assert is_valid is False
        assert "解决方法" in error
        assert "GATEFLOW_ALLOW_DANGEROUS" in error
        assert "警告" in error


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_allowed_roots(self):
        """测试空的根目录列表"""
        config = SandboxConfig(allowed_roots=[])

        # 应该至少有一个默认根目录
        assert len(config.allowed_roots) >= 1

    def test_relative_path(self, tmp_path):
        """测试相对路径"""
        root = tmp_path
        relative_path = "test.txt"

        # 相对路径会被解析为绝对路径
        is_valid, error = validate_path(relative_path, [root])

        # 取决于当前工作目录，可能会失败
        # 这里主要测试不会抛出异常
        assert isinstance(is_valid, bool)
        assert isinstance(error, str)

    def test_path_with_parent_references(self, tmp_path):
        """测试包含父目录引用的路径"""
        root = tmp_path
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # 使用 .. 引用
        path_with_parent = subdir / ".." / "test.txt"

        is_valid, error = validate_path(path_with_parent, [root])

        # 解析后应该在沙箱内
        assert is_valid is True

    def test_multiple_roots(self, tmp_path_factory):
        """测试多个根目录"""
        root1 = tmp_path_factory.mktemp("root1")
        root2 = tmp_path_factory.mktemp("root2")

        file_in_root1 = root1 / "file1.txt"
        file_in_root2 = root2 / "file2.txt"

        file_in_root1.write_text("content1")
        file_in_root2.write_text("content2")

        # 使用两个根目录
        roots = [root1, root2]

        # 两个文件都应该有效
        is_valid1, _ = validate_path(file_in_root1, roots)
        is_valid2, _ = validate_path(file_in_root2, roots)

        assert is_valid1 is True
        assert is_valid2 is True

    def test_case_sensitivity(self, tmp_path):
        """测试路径大小写敏感性（取决于操作系统）"""
        root = tmp_path
        test_file = tmp_path / "Test.txt"
        test_file.write_text("content")

        # 在 Windows 上不区分大小写，在 Unix 上区分
        lower_path = tmp_path / "test.txt"

        is_valid, error = validate_path(lower_path, [root])

        # 主要测试不会抛出异常
        assert isinstance(is_valid, bool)
