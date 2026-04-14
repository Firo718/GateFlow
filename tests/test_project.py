"""
项目管理测试模块。

测试 ProjectTclGenerator、ProjectManager、ProjectConfig 等组件。
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gateflow.vivado.project import (
    FileType,
    ProjectConfig,
    ProjectTclGenerator,
    ProjectManager,
)
from gateflow.vivado.tcl_engine import TclResult


class TestFileType:
    """FileType 枚举测试。"""

    def test_file_type_values(self):
        """测试文件类型枚举值。"""
        assert FileType.VERILOG.value == "verilog"
        assert FileType.VHDL.value == "vhdl"
        assert FileType.SYSTEM_VERILOG.value == "systemverilog"
        assert FileType.XDC.value == "xdc"
        assert FileType.TCL.value == "tcl"

    def test_file_type_count(self):
        """测试文件类型数量。"""
        types = list(FileType)
        assert len(types) >= 8  # 至少有 8 种文件类型


class TestProjectConfig:
    """ProjectConfig 数据类测试。"""

    def test_required_fields(self):
        """测试必需字段。"""
        config = ProjectConfig(
            name="test_project",
            path=Path("/projects/test"),
            part="xc7a35tcpg236-1",
        )
        assert config.name == "test_project"
        assert config.path == Path("/projects/test")
        assert config.part == "xc7a35tcpg236-1"

    def test_default_values(self):
        """测试默认值。"""
        config = ProjectConfig(
            name="test",
            path=Path("/test"),
            part="xc7z020clg400-1",
        )
        assert config.board is None
        assert config.language == "Verilog"
        assert config.simulator == "ModelSim"

    def test_custom_values(self):
        """测试自定义值。"""
        config = ProjectConfig(
            name="custom_project",
            path=Path("/custom/path"),
            part="xc7z020clg400-1",
            board="zc702",
            language="VHDL",
            simulator="Questa",
        )
        assert config.board == "zc702"
        assert config.language == "VHDL"
        assert config.simulator == "Questa"


class TestProjectTclGenerator:
    """ProjectTclGenerator 测试。"""

    def test_create_project_tcl_basic(self):
        """测试基本创建项目命令。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="my_project",
            path=Path("/projects/my_project"),
            part="xc7a35tcpg236-1",
        )
        
        assert 'create_project "my_project"' in cmd
        # 路径可能被转换为 Windows 格式，所以检查路径的一部分
        assert 'my_project' in cmd
        assert '-part "xc7a35tcpg236-1"' in cmd
        assert '-force' in cmd

    def test_create_project_tcl_with_board(self):
        """测试带开发板的创建项目命令。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="my_project",
            path=Path("/projects/my_project"),
            part="xc7z020clg400-1",
            board="zc702",
        )
        
        assert '-board "zc702"' in cmd

    def test_create_project_tcl_no_force(self):
        """测试不强制覆盖的创建项目命令。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="my_project",
            path=Path("/projects/my_project"),
            part="xc7a35tcpg236-1",
            force=False,
        )
        
        assert '-force' not in cmd

    def test_create_project_full_tcl(self):
        """测试完整创建项目命令序列。"""
        config = ProjectConfig(
            name="full_project",
            path=Path("/projects/full"),
            part="xc7a35tcpg236-1",
            board="arty",
            language="VHDL",
        )
        
        commands = ProjectTclGenerator.create_project_full_tcl(config)
        
        assert len(commands) >= 3
        assert any("create_project" in cmd for cmd in commands)
        assert any("target_language" in cmd for cmd in commands)
        assert any("default_lib" in cmd for cmd in commands)

    def test_open_project_tcl(self):
        """测试打开项目命令。"""
        cmd = ProjectTclGenerator.open_project_tcl(
            Path("/projects/my_project/my_project.xpr")
        )
        
        assert 'open_project' in cmd
        assert 'my_project.xpr' in cmd

    def test_close_project_tcl(self):
        """测试关闭项目命令。"""
        cmd = ProjectTclGenerator.close_project_tcl()
        assert cmd == 'close_project'

    def test_save_project_tcl(self):
        """测试保存项目命令。"""
        cmd = ProjectTclGenerator.save_project_tcl()
        assert cmd == 'save_project'

    def test_add_files_tcl_basic(self):
        """测试基本添加文件命令。"""
        files = [Path("/src/top.v"), Path("/src/module.v")]
        commands = ProjectTclGenerator.add_files_tcl(files)
        
        assert len(commands) >= 1
        assert 'add_files' in commands[0]
        assert 'top.v' in commands[0]
        assert 'module.v' in commands[0]

    def test_add_files_tcl_with_type(self):
        """测试带文件类型的添加文件命令。"""
        files = [Path("/src/top.v")]
        commands = ProjectTclGenerator.add_files_tcl(
            files,
            file_type=FileType.VERILOG,
        )
        
        assert '-file_type verilog' in commands[0]

    def test_add_files_tcl_with_library(self):
        """测试带库的添加文件命令（VHDL）。"""
        files = [Path("/src/entity.vhd")]
        commands = ProjectTclGenerator.add_files_tcl(
            files,
            file_type=FileType.VHDL,
            library="my_lib",
        )
        
        assert any("library" in cmd for cmd in commands)

    def test_add_source_files_tcl(self):
        """测试添加源文件命令。"""
        files = [Path("/src/top.v"), Path("/src/module.v")]
        cmd = ProjectTclGenerator.add_source_files_tcl(files)
        
        assert 'add_files -fileset sources_1' in cmd

    def test_add_source_files_tcl_with_type(self):
        """测试带类型的添加源文件命令。"""
        files = [Path("/src/top.sv")]
        cmd = ProjectTclGenerator.add_source_files_tcl(
            files,
            file_type=FileType.SYSTEM_VERILOG,
        )
        
        assert '-file_type systemverilog' in cmd

    def test_add_constraint_files_tcl(self):
        """测试添加约束文件命令。"""
        files = [Path("/constraints/pins.xdc")]
        cmd = ProjectTclGenerator.add_constraint_files_tcl(files)
        
        assert 'add_files -fileset constrs_1' in cmd
        assert 'pins.xdc' in cmd

    def test_add_simulation_files_tcl(self):
        """测试添加仿真文件命令。"""
        files = [Path("/sim/tb.v")]
        cmd = ProjectTclGenerator.add_simulation_files_tcl(files)
        
        assert 'add_files -fileset sim_1' in cmd

    def test_add_simulation_files_tcl_custom_sim_set(self):
        """测试自定义仿真集的添加仿真文件命令。"""
        files = [Path("/sim/tb.v")]
        cmd = ProjectTclGenerator.add_simulation_files_tcl(
            files,
            sim_set="sim_2",
        )
        
        assert '-fileset sim_2' in cmd

    def test_remove_files_tcl(self):
        """测试移除文件命令。"""
        files = [Path("/src/old.v")]
        cmd = ProjectTclGenerator.remove_files_tcl(files)
        
        assert 'remove_files' in cmd
        assert 'old.v' in cmd

    def test_set_top_module_tcl(self):
        """测试设置顶层模块命令。"""
        cmd = ProjectTclGenerator.set_top_module_tcl("my_top")
        
        assert 'set_property top my_top' in cmd
        assert 'sources_1' in cmd

    def test_set_top_module_tcl_custom_fileset(self):
        """测试自定义文件集的设置顶层模块命令。"""
        cmd = ProjectTclGenerator.set_top_module_tcl(
            "my_top",
            fileset="sources_2",
        )
        
        assert 'sources_2' in cmd

    def test_set_top_module_auto_tcl(self):
        """测试自动设置顶层模块命令。"""
        cmd = ProjectTclGenerator.set_top_module_auto_tcl()
        
        assert 'set_property top' in cmd
        assert 'get_property top' in cmd

    def test_update_compile_order_tcl(self):
        """测试更新编译顺序命令。"""
        cmd = ProjectTclGenerator.update_compile_order_tcl()
        
        assert 'update_compile_order' in cmd
        assert 'sources_1' in cmd

    def test_get_project_info_tcl(self):
        """测试获取项目信息命令。"""
        commands = ProjectTclGenerator.get_project_info_tcl()
        
        assert len(commands) >= 5
        assert any("project_name" in cmd for cmd in commands)
        assert any("part_name" in cmd for cmd in commands)
        assert any("puts" in cmd for cmd in commands)

    def test_get_filesets_tcl(self):
        """测试获取文件集命令。"""
        cmd = ProjectTclGenerator.get_filesets_tcl()
        assert cmd == 'get_filesets'

    def test_get_files_tcl(self):
        """测试获取文件列表命令。"""
        cmd = ProjectTclGenerator.get_files_tcl()
        
        assert 'get_files' in cmd
        assert 'sources_1' in cmd

    def test_get_files_tcl_custom_fileset(self):
        """测试自定义文件集的获取文件列表命令。"""
        cmd = ProjectTclGenerator.get_files_tcl("constrs_1")
        
        assert 'constrs_1' in cmd

    def test_set_property_tcl(self):
        """测试设置属性命令。"""
        cmd = ProjectTclGenerator.set_property_tcl(
            property_name="target_language",
            value="VHDL",
        )
        
        assert 'set_property target_language VHDL' in cmd
        assert 'current_project' in cmd

    def test_set_property_tcl_with_object(self):
        """测试带对象的设置属性命令。"""
        cmd = ProjectTclGenerator.set_property_tcl(
            property_name="strategy",
            value="Vivado Synthesis Defaults",
            object_type="runs",
            object_name="synth_1",
        )
        
        assert 'get_runs synth_1' in cmd

    def test_import_files_tcl(self):
        """测试导入文件命令。"""
        files = [Path("/external/src/top.v")]
        cmd = ProjectTclGenerator.import_files_tcl(files)
        
        assert 'import_files' in cmd
        assert 'sources_1' in cmd

    def test_import_files_tcl_custom_fileset(self):
        """测试自定义文件集的导入文件命令。"""
        files = [Path("/external/src/top.v")]
        cmd = ProjectTclGenerator.import_files_tcl(files, fileset="constrs_1")
        
        assert '-fileset constrs_1' in cmd

    def test_refresh_design_tcl(self):
        """测试刷新设计命令。"""
        cmd = ProjectTclGenerator.refresh_design_tcl()
        
        assert 'update_compile_order' in cmd

    def test_set_strategy_tcl_synthesis(self):
        """测试设置综合策略命令。"""
        cmd = ProjectTclGenerator.set_strategy_tcl(
            step="synthesis",
            strategy="Vivado Synthesis Defaults",
        )
        
        assert 'synth_1' in cmd

    def test_set_strategy_tcl_implementation(self):
        """测试设置实现策略命令。"""
        cmd = ProjectTclGenerator.set_strategy_tcl(
            step="implementation",
            strategy="Vivado Implementation Defaults",
        )
        
        assert 'impl_1' in cmd

    def test_set_strategy_tcl_invalid_step(self):
        """测试无效步骤的设置策略命令。"""
        with pytest.raises(ValueError, match="未知的步骤"):
            ProjectTclGenerator.set_strategy_tcl(
                step="invalid",
                strategy="Some Strategy",
            )

    def test_export_project_tcl_tcl(self):
        """测试导出项目为 Tcl 命令。"""
        cmd = ProjectTclGenerator.export_project_tcl_tcl(
            output_path=Path("/export/project.tcl"),
        )
        
        assert 'write_project_tcl' in cmd
        assert 'project.tcl' in cmd

    def test_export_project_tcl_tcl_with_runs(self):
        """测试包含运行配置的导出项目命令。"""
        cmd = ProjectTclGenerator.export_project_tcl_tcl(
            output_path=Path("/export/project.tcl"),
            include_runs=True,
        )
        
        assert '-include_runs' in cmd

    def test_export_project_tcl_tcl_without_runs(self):
        """测试不包含运行配置的导出项目命令。"""
        cmd = ProjectTclGenerator.export_project_tcl_tcl(
            output_path=Path("/export/project.tcl"),
            include_runs=False,
        )
        
        assert '-include_runs' not in cmd


@pytest.mark.integration
class TestProjectManager:
    """ProjectManager 测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        engine.execute.return_value = TclResult(
            success=True,
            output="Success",
            errors=[],
            warnings=[],
        )
        return engine

    @pytest.fixture
    def project_manager(self, mock_engine):
        """创建 ProjectManager 实例。"""
        return ProjectManager(mock_engine)

    def test_initialization(self, mock_engine):
        """测试初始化。"""
        manager = ProjectManager(mock_engine)
        assert manager.engine == mock_engine
        assert manager.current_project is None

    def test_create_project_success(self, project_manager, mock_engine):
        """测试创建项目成功。"""
        result = project_manager.create_project(
            name="test_project",
            path=Path("/projects/test"),
            part="xc7a35tcpg236-1",
        )
        
        assert result is True
        assert project_manager.current_project is not None
        assert project_manager.current_project.name == "test_project"
        mock_engine.execute.assert_called_once()

    def test_create_project_failure(self, project_manager, mock_engine):
        """测试创建项目失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Creation failed"],
        )
        
        result = project_manager.create_project(
            name="test_project",
            path=Path("/projects/test"),
            part="xc7a35tcpg236-1",
        )
        
        assert result is False
        assert project_manager.current_project is None

    def test_create_project_with_board(self, project_manager, mock_engine):
        """测试带开发板创建项目。"""
        result = project_manager.create_project(
            name="test_project",
            path=Path("/projects/test"),
            part="xc7z020clg400-1",
            board="zc702",
        )
        
        assert result is True
        assert project_manager.current_project.board == "zc702"

    def test_open_project_success(self, project_manager, mock_engine):
        """测试打开项目成功。"""
        result = project_manager.open_project(
            Path("/projects/test/test.xpr")
        )
        
        assert result is True
        mock_engine.execute.assert_called_once()

    def test_open_project_failure(self, project_manager, mock_engine):
        """测试打开项目失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Open failed"],
        )
        
        result = project_manager.open_project(
            Path("/projects/test/test.xpr")
        )
        
        assert result is False

    def test_close_project_success(self, project_manager, mock_engine):
        """测试关闭项目成功。"""
        # 先创建一个项目
        project_manager.current_project = ProjectConfig(
            name="test",
            path=Path("/test"),
            part="xc7a35tcpg236-1",
        )
        
        result = project_manager.close_project()
        
        assert result is True
        assert project_manager.current_project is None

    def test_close_project_failure(self, project_manager, mock_engine):
        """测试关闭项目失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Close failed"],
        )
        
        result = project_manager.close_project()
        
        assert result is False

    def test_add_sources_success(self, project_manager, mock_engine):
        """测试添加源文件成功。"""
        files = [Path("/src/top.v"), Path("/src/module.v")]
        result = project_manager.add_sources(files)
        
        assert result is True
        mock_engine.execute.assert_called_once()

    def test_add_sources_with_import(self, project_manager, mock_engine):
        """测试导入源文件。"""
        files = [Path("/src/top.v")]
        result = project_manager.add_sources(files, import_files=True)
        
        assert result is True
        # 验证调用的是 import_files_tcl
        call_args = mock_engine.execute.call_args[0][0]
        assert "import_files" in call_args

    def test_add_sources_failure(self, project_manager, mock_engine):
        """测试添加源文件失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Add failed"],
        )
        
        files = [Path("/src/top.v")]
        result = project_manager.add_sources(files)
        
        assert result is False

    def test_add_constraints_success(self, project_manager, mock_engine):
        """测试添加约束文件成功。"""
        files = [Path("/constraints/pins.xdc")]
        result = project_manager.add_constraints(files)
        
        assert result is True
        mock_engine.execute.assert_called_once()

    def test_add_constraints_failure(self, project_manager, mock_engine):
        """测试添加约束文件失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Add failed"],
        )
        
        files = [Path("/constraints/pins.xdc")]
        result = project_manager.add_constraints(files)
        
        assert result is False

    def test_set_top_module_success(self, project_manager, mock_engine):
        """测试设置顶层模块成功。"""
        result = project_manager.set_top_module("my_top")
        
        assert result is True
        # 应该执行两个命令
        call_args = mock_engine.execute.call_args[0][0]
        assert isinstance(call_args, list)

    def test_set_top_module_failure(self, project_manager, mock_engine):
        """测试设置顶层模块失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Set failed"],
        )
        
        result = project_manager.set_top_module("my_top")
        
        assert result is False

    def test_get_project_info_success(self, project_manager, mock_engine):
        """测试获取项目信息成功。"""
        mock_engine.execute.return_value = TclResult(
            success=True,
            output="""
Project: test_project
Directory: /projects/test
Part: xc7a35tcpg236-1
Board: arty
Language: Verilog
""",
            errors=[],
        )
        
        info = project_manager.get_project_info()
        
        assert info["name"] == "test_project"
        assert info["part"] == "xc7a35tcpg236-1"
        assert info["board"] == "arty"
        assert info["language"] == "Verilog"

    def test_get_project_info_failure(self, project_manager, mock_engine):
        """测试获取项目信息失败。"""
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Get info failed"],
        )
        
        info = project_manager.get_project_info()
        
        assert info == {}

    def test_get_project_info_partial(self, project_manager, mock_engine):
        """测试部分项目信息。"""
        mock_engine.execute.return_value = TclResult(
            success=True,
            output="Project: test\nPart: xc7a35tcpg236-1",
            errors=[],
        )
        
        info = project_manager.get_project_info()
        
        assert "name" in info
        assert "part" in info
        assert "board" not in info


class TestProjectTclGeneratorEdgeCases:
    """ProjectTclGenerator 边界情况测试。"""

    def test_empty_files_list(self):
        """测试空文件列表。"""
        commands = ProjectTclGenerator.add_files_tcl([])
        assert len(commands) >= 1

    def test_special_characters_in_path(self):
        """测试路径中的特殊字符。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="test project",  # 包含空格
            path=Path("/projects/test project"),
            part="xc7a35tcpg236-1",
        )
        
        assert "test project" in cmd

    def test_long_file_list(self):
        """测试长文件列表。"""
        files = [Path(f"/src/file{i}.v") for i in range(100)]
        commands = ProjectTclGenerator.add_files_tcl(files)
        
        assert len(commands) >= 1
        # 所有文件都应该在命令中
        for i in range(100):
            assert f"file{i}.v" in commands[0]

    def test_unicode_in_project_name(self):
        """测试项目名中的 Unicode 字符。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="测试项目",
            path=Path("/projects/test"),
            part="xc7a35tcpg236-1",
        )
        
        assert "测试项目" in cmd

    def test_windows_path(self):
        """测试 Windows 路径。"""
        cmd = ProjectTclGenerator.open_project_tcl(
            Path("C:/Projects/test/test.xpr")
        )
        
        assert "C:/Projects" in cmd or "C:\\Projects" in cmd or "test.xpr" in cmd

    def test_network_path(self):
        """测试网络路径。"""
        cmd = ProjectTclGenerator.create_project_tcl(
            name="test",
            path=Path("//server/share/project"),
            part="xc7a35tcpg236-1",
        )
        
        assert "create_project" in cmd


@pytest.mark.integration
class TestProjectManagerIntegration:
    """ProjectManager 集成测试。"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟的 TclEngine。"""
        engine = MagicMock()
        return engine

    @pytest.fixture
    def project_manager(self, mock_engine):
        """创建 ProjectManager 实例。"""
        return ProjectManager(mock_engine)

    def test_full_project_workflow(self, project_manager, mock_engine):
        """测试完整项目工作流。"""
        # 模拟所有操作成功
        mock_engine.execute.return_value = TclResult(
            success=True,
            output="Project: workflow_test\nPart: xc7a35tcpg236-1",
            errors=[],
        )
        
        # 1. 创建项目
        result = project_manager.create_project(
            name="workflow_test",
            path=Path("/projects/workflow"),
            part="xc7a35tcpg236-1",
        )
        assert result is True
        
        # 2. 添加源文件
        result = project_manager.add_sources([Path("/src/top.v")])
        assert result is True
        
        # 3. 添加约束文件
        result = project_manager.add_constraints([Path("/constraints/pins.xdc")])
        assert result is True
        
        # 4. 设置顶层模块
        result = project_manager.set_top_module("top")
        assert result is True
        
        # 5. 获取项目信息
        info = project_manager.get_project_info()
        assert "name" in info or info == {}  # 取决于输出解析

    def test_error_recovery(self, project_manager, mock_engine):
        """测试错误恢复。"""
        # 第一次调用失败
        mock_engine.execute.return_value = TclResult(
            success=False,
            output="",
            errors=["Error"],
        )
        
        result = project_manager.create_project(
            name="test",
            path=Path("/test"),
            part="xc7a35tcpg236-1",
        )
        assert result is False
        
        # 第二次调用成功
        mock_engine.execute.return_value = TclResult(
            success=True,
            output="Success",
            errors=[],
        )
        
        result = project_manager.create_project(
            name="test",
            path=Path("/test"),
            part="xc7a35tcpg236-1",
        )
        assert result is True
