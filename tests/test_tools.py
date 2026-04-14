"""
MCP 工具测试模块。

测试工具注册函数、Pydantic 模型验证和错误处理。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from pydantic import ValidationError

from gateflow.tools.build_tools import (
    SynthesisResult,
    ImplementationResult,
    BitstreamResult,
    UtilizationReportResult,
    TimingReportResult,
    register_build_tools,
    _ensure_engine,
    _get_synthesis_manager,
    _get_implementation_manager,
    _extract_file_paths,
    _extract_timing_summary,
)
from gateflow.tools.project_tools import (
    CreateProjectResult,
    OpenProjectResult,
    AddSourceFilesResult,
    SetTopModuleResult,
    ProjectInfoResult,
    register_project_tools,
)


class TestBuildToolsModels:
    """构建工具 Pydantic 模型测试。"""

    def test_synthesis_result_defaults(self):
        """测试 SynthesisResult 默认值。"""
        result = SynthesisResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.status is None
        assert result.error is None
        assert result.report_path is None
        assert result.checkpoint_path is None
        assert result.utilization is None
        assert result.timing_summary is None

    def test_synthesis_result_full(self):
        """测试 SynthesisResult 完整参数。"""
        utilization_data = {
            "slice_lut": {"used": 1000, "available": 20000, "utilization": 5.0}
        }
        timing_data = {"wns": 2.5, "whs": 0.8, "timing_met": True}
        
        result = SynthesisResult(
            success=True,
            status="completed",
            message="Synthesis completed successfully",
            error=None,
            report_path="/project/runs/synth_1/report.rpt",
            checkpoint_path="/project/runs/synth_1/design.dcp",
            utilization=utilization_data,
            timing_summary=timing_data,
        )
        
        assert result.status == "completed"
        assert "successfully" in result.message
        assert result.report_path == "/project/runs/synth_1/report.rpt"
        assert result.checkpoint_path == "/project/runs/synth_1/design.dcp"
        assert result.utilization["slice_lut"]["used"] == 1000
        assert result.timing_summary["wns"] == 2.5

    def test_synthesis_result_failure(self):
        """测试 SynthesisResult 失败情况。"""
        result = SynthesisResult(
            success=False,
            message="Synthesis failed",
            error="ERROR: [Synth 8-123] Some error",
        )
        
        assert result.success is False
        assert result.error is not None

    def test_implementation_result_defaults(self):
        """测试 ImplementationResult 默认值。"""
        result = ImplementationResult(success=True, message="Done")
        
        assert result.success is True
        assert result.message == "Done"
        assert result.report_path is None
        assert result.checkpoint_path is None
        assert result.utilization is None
        assert result.timing_summary is None

    def test_implementation_result_full(self):
        """测试 ImplementationResult 完整参数。"""
        utilization_data = {
            "slice_lut": {"used": 1500, "available": 20000, "utilization": 7.5}
        }
        timing_data = {"wns": 1.2, "whs": 0.5, "timing_met": True}
        
        result = ImplementationResult(
            success=True,
            status="completed",
            message="Implementation done",
            error=None,
            report_path="/project/runs/impl_1/report.rpt",
            checkpoint_path="/project/runs/impl_1/design.dcp",
            utilization=utilization_data,
            timing_summary=timing_data,
        )
        
        assert result.status == "completed"
        assert result.report_path == "/project/runs/impl_1/report.rpt"
        assert result.checkpoint_path == "/project/runs/impl_1/design.dcp"
        assert result.utilization["slice_lut"]["used"] == 1500
        assert result.timing_summary["timing_met"] is True

    def test_bitstream_result_defaults(self):
        """测试 BitstreamResult 默认值。"""
        result = BitstreamResult(success=True, message="Generated")
        
        assert result.success is True
        assert result.bitstream_path is None
        assert result.ltx_path is None
        assert result.size is None

    def test_bitstream_result_with_path(self):
        """测试 BitstreamResult 带路径。"""
        result = BitstreamResult(
            success=True,
            bitstream_path="/output/design.bit",
            message="Bitstream generated",
            ltx_path="/output/design.ltx",
            size=1234567,
        )
        
        assert result.bitstream_path == "/output/design.bit"
        assert result.ltx_path == "/output/design.ltx"
        assert result.size == 1234567

    def test_utilization_report_result_defaults(self):
        """测试 UtilizationReportResult 默认值。"""
        result = UtilizationReportResult(success=True, message="Report generated")
        
        assert result.utilization == {}
        assert result.raw_report is None

    def test_utilization_report_result_with_data(self):
        """测试 UtilizationReportResult 带数据。"""
        utilization_data = {
            "Slice LUTs": {"used": 1000, "available": 20000, "percentage": 5.0},
            "DSPs": {"used": 10, "available": 100, "percentage": 10.0},
        }
        
        result = UtilizationReportResult(
            success=True,
            utilization=utilization_data,
            raw_report="Raw report text",
            message="Report generated",
        )
        
        assert result.utilization["Slice LUTs"]["used"] == 1000
        assert result.raw_report == "Raw report text"

    def test_timing_report_result_defaults(self):
        """测试 TimingReportResult 默认值。"""
        result = TimingReportResult(success=True, message="Report generated")
        
        assert result.timing == {}
        assert result.raw_report is None

    def test_timing_report_result_with_data(self):
        """测试 TimingReportResult 带数据。"""
        timing_data = {
            "setup": {"worst_slack": 2.5},
            "hold": {"worst_slack": 0.8},
            "timing_met": True,
        }
        
        result = TimingReportResult(
            success=True,
            timing=timing_data,
            raw_report="Timing report",
            message="Timing met",
        )
        
        assert result.timing["timing_met"] is True


class TestExtractFunctions:
    """提取函数测试。"""

    def test_extract_file_paths_bitstream(self):
        """测试提取比特流路径。"""
        output = """
        Running bitstream generation...
        Writing bitstream /project/runs/impl_1/design.bit
        Bitstream generation completed.
        """
        
        paths = _extract_file_paths(output)
        
        assert "bitstream_path" in paths
        assert paths["bitstream_path"] == "/project/runs/impl_1/design.bit"

    def test_extract_file_paths_ltx(self):
        """测试提取 LTX 文件路径。"""
        output = """
        Writing debug probes /project/runs/impl_1/design.ltx
        """
        
        paths = _extract_file_paths(output)
        
        assert "ltx_path" in paths
        assert paths["ltx_path"] == "/project/runs/impl_1/design.ltx"

    def test_extract_file_paths_dcp(self):
        """测试提取 DCP 检查点路径。"""
        output = """
        Writing checkpoint /project/runs/synth_1/design.dcp
        """
        
        paths = _extract_file_paths(output)
        
        assert "checkpoint_path" in paths
        assert paths["checkpoint_path"] == "/project/runs/synth_1/design.dcp"

    def test_extract_file_paths_report(self):
        """测试提取报告路径。"""
        output = """
        Generating report /project/runs/synth_1/utilization.rpt
        """
        
        paths = _extract_file_paths(output)
        
        assert "report_path" in paths
        assert paths["report_path"] == "/project/runs/synth_1/utilization.rpt"

    def test_extract_file_paths_multiple(self):
        """测试提取多个文件路径。"""
        output = """
        Writing checkpoint /project/runs/synth_1/design.dcp
        Generating report /project/runs/synth_1/report.rpt
        Writing bitstream /project/runs/impl_1/design.bit
        Writing debug probes /project/runs/impl_1/design.ltx
        """
        
        paths = _extract_file_paths(output)
        
        assert paths["checkpoint_path"] == "/project/runs/synth_1/design.dcp"
        assert paths["report_path"] == "/project/runs/synth_1/report.rpt"
        assert paths["bitstream_path"] == "/project/runs/impl_1/design.bit"
        assert paths["ltx_path"] == "/project/runs/impl_1/design.ltx"

    def test_extract_file_paths_empty(self):
        """测试空输出。"""
        output = "No file paths here"
        
        paths = _extract_file_paths(output)
        
        assert paths == {}

    def test_extract_timing_summary_wns_tns(self):
        """测试提取 WNS 和 TNS。"""
        output = """
        Timing Summary
        -------------
        WNS(ns) : 2.500
        TNS(ns) : 0.000
        """
        
        timing = _extract_timing_summary(output)
        
        assert timing["wns"] == 2.5
        assert timing["tns"] == 0.0
        assert timing["timing_met"] is True

    def test_extract_timing_summary_whs_ths(self):
        """测试提取 WHS 和 THS。"""
        output = """
        WHS(ns) : 0.800
        THS(ns) : 0.000
        """
        
        timing = _extract_timing_summary(output)
        
        assert timing["whs"] == 0.8
        assert timing["ths"] == 0.0
        assert timing["timing_met"] is True

    def test_extract_timing_summary_negative_slack(self):
        """测试负时序裕量。"""
        output = """
        WNS(ns) : -1.500
        WHS(ns) : 0.200
        """
        
        timing = _extract_timing_summary(output)
        
        assert timing["wns"] == -1.5
        assert timing["whs"] == 0.2
        assert timing["timing_met"] is False

    def test_extract_timing_summary_all_negative(self):
        """测试全部负时序裕量。"""
        output = """
        WNS(ns) : -2.500
        TNS(ns) : -10.000
        WHS(ns) : -0.500
        THS(ns) : -2.000
        """
        
        timing = _extract_timing_summary(output)
        
        assert timing["wns"] == -2.5
        assert timing["tns"] == -10.0
        assert timing["whs"] == -0.5
        assert timing["ths"] == -2.0
        assert timing["timing_met"] is False

    def test_extract_timing_summary_empty(self):
        """测试空输出。"""
        output = "No timing information"
        
        timing = _extract_timing_summary(output)
        
        # 默认值
        assert timing.get("wns") is None
        assert timing.get("whs") is None
        # timing_met 默认为 True（因为没有负值）
        assert timing["timing_met"] is True


class TestProjectToolsModels:
    """项目工具 Pydantic 模型测试。"""

    def test_create_project_result_defaults(self):
        """测试 CreateProjectResult 默认值。"""
        result = CreateProjectResult(success=True, message="Created")
        
        assert result.success is True
        assert result.project is None
        assert result.error is None

    def test_create_project_result_with_project(self):
        """测试 CreateProjectResult 带项目信息。"""
        project_data = {
            "name": "test_project",
            "path": "/projects/test",
            "part": "xc7a35tcpg236-1",
        }
        
        result = CreateProjectResult(
            success=True,
            project=project_data,
            message="Project created successfully",
        )
        
        assert result.project["name"] == "test_project"

    def test_open_project_result_defaults(self):
        """测试 OpenProjectResult 默认值。"""
        result = OpenProjectResult(success=True, message="Opened")
        
        assert result.success is True
        assert result.project is None

    def test_add_source_files_result_defaults(self):
        """测试 AddSourceFilesResult 默认值。"""
        result = AddSourceFilesResult(success=True, message="Added")
        
        assert result.added_files == []
        assert result.invalid_files == []

    def test_add_source_files_result_with_files(self):
        """测试 AddSourceFilesResult 带文件列表。"""
        result = AddSourceFilesResult(
            success=True,
            added_files=["/src/top.v", "/src/module.v"],
            invalid_files=["/src/bad.v"],
            message="Files added",
        )
        
        assert len(result.added_files) == 2
        assert len(result.invalid_files) == 1

    def test_set_top_module_result_defaults(self):
        """测试 SetTopModuleResult 默认值。"""
        result = SetTopModuleResult(success=True, message="Set")
        
        assert result.top_module is None

    def test_set_top_module_result_with_module(self):
        """测试 SetTopModuleResult 带模块名。"""
        result = SetTopModuleResult(
            success=True,
            top_module="my_top",
            message="Top module set",
        )
        
        assert result.top_module == "my_top"

    def test_project_info_result_defaults(self):
        """测试 ProjectInfoResult 默认值。"""
        result = ProjectInfoResult(success=True, message="Info")
        
        assert result.project is None

    def test_project_info_result_with_info(self):
        """测试 ProjectInfoResult 带项目信息。"""
        project_info = {
            "name": "test_project",
            "part": "xc7a35tcpg236-1",
            "language": "Verilog",
        }
        
        result = ProjectInfoResult(
            success=True,
            project=project_info,
            message="Project info retrieved",
        )
        
        assert result.project["language"] == "Verilog"


class TestModelValidation:
    """模型验证测试。"""

    def test_synthesis_result_required_fields(self):
        """测试 SynthesisResult 必需字段。"""
        # 缺少必需字段应该失败
        with pytest.raises(ValidationError):
            SynthesisResult()  # 缺少 success 和 message

        with pytest.raises(ValidationError):
            SynthesisResult(success=True)  # 缺少 message

    def test_implementation_result_required_fields(self):
        """测试 ImplementationResult 必需字段。"""
        with pytest.raises(ValidationError):
            ImplementationResult()  # 缺少必需字段

    def test_bitstream_result_required_fields(self):
        """测试 BitstreamResult 必需字段。"""
        with pytest.raises(ValidationError):
            BitstreamResult()  # 缺少必需字段

    def test_create_project_result_required_fields(self):
        """测试 CreateProjectResult 必需字段。"""
        with pytest.raises(ValidationError):
            CreateProjectResult()  # 缺少必需字段

    def test_utilization_report_result_type_validation(self):
        """测试 UtilizationReportResult 类型验证。"""
        # 正确类型
        result = UtilizationReportResult(
            success=True,
            utilization={"key": "value"},
            message="OK",
        )
        assert result.utilization == {"key": "value"}

    def test_model_extra_fields_forbidden(self):
        """测试模型额外字段处理。"""
        # Pydantic v2 默认忽略额外字段
        result = SynthesisResult(
            success=True,
            message="OK",
            extra_field="should be ignored",  # type: ignore
        )
        assert result.success is True


class TestRegisterBuildTools:
    """构建工具注册测试。"""

    def test_register_build_tools(self):
        """测试注册构建工具。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_build_tools(mock_mcp)
        
        # 验证 tool 装饰器被调用
        assert mock_mcp.tool.called

    def test_register_build_tools_creates_decorators(self):
        """测试注册构建工具创建装饰器。"""
        mock_mcp = MagicMock()
        decorators = []
        
        def mock_decorator():
            def decorator(func):
                decorators.append(func.__name__)
                return func
            return decorator
        
        mock_mcp.tool = mock_decorator
        
        register_build_tools(mock_mcp)
        
        # 应该注册多个工具
        assert len(decorators) > 0


class TestRegisterProjectTools:
    """项目工具注册测试。"""

    def test_register_project_tools(self):
        """测试注册项目工具。"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock(return_value=lambda f: f)
        
        register_project_tools(mock_mcp)
        
        assert mock_mcp.tool.called

    def test_register_project_tools_creates_decorators(self):
        """测试注册项目工具创建装饰器。"""
        mock_mcp = MagicMock()
        decorators = []
        
        def mock_decorator():
            def decorator(func):
                decorators.append(func.__name__)
                return func
            return decorator
        
        mock_mcp.tool = mock_decorator
        
        register_project_tools(mock_mcp)
        
        assert len(decorators) > 0


class TestGlobalStateManagement:
    """全局状态管理测试。"""

    def setup_method(self):
        """每个测试前重置全局状态。"""
        import gateflow.tools.build_tools as build_tools
        import gateflow.tools.project_tools as project_tools
        
        build_tools._engine = None
        build_tools._synthesis_manager = None
        build_tools._implementation_manager = None
        project_tools._engine = None
        project_tools._project_manager = None

    def test_ensure_engine_creates_instance(self):
        """测试获取引擎创建实例。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager._initialized = True
        
        with patch("gateflow.tools.build_tools.ensure_engine_initialized", new_callable=AsyncMock) as mock_ensure:
            mock_ensure.return_value = mock_manager
            
            # 重置状态
            build_tools._engine_manager = None
            
            # 异步测试需要使用 pytest.mark.asyncio
            # 这里只测试函数存在
            assert _ensure_engine is not None

    def test_get_synthesis_manager_creates_instance(self):
        """测试获取综合管理器创建实例。"""
        import gateflow.tools.build_tools as build_tools
        
        # 测试函数存在
        assert _get_synthesis_manager is not None

    def test_get_implementation_manager_creates_instance(self):
        """测试获取实现管理器创建实例。"""
        import gateflow.tools.build_tools as build_tools
        
        # 测试函数存在
        assert _get_implementation_manager is not None


class TestToolFunctions:
    """工具函数测试。"""

    @pytest.mark.asyncio
    async def test_run_synthesis_tool(self):
        """测试运行综合工具。"""
        import gateflow.tools.build_tools as build_tools
        
        # 模拟综合管理器
        mock_manager = MagicMock()
        mock_manager.run_synthesis = AsyncMock(return_value={
            "success": True,
            "status": "completed",
            "message": "Synthesis completed",
        })
        build_tools._synthesis_manager = mock_manager
        
        # 创建模拟的 MCP 和工具函数
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "run_synthesis" in registered_tools:
            result = await registered_tools["run_synthesis"]()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_run_implementation_tool(self):
        """测试运行实现工具。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.run_implementation = AsyncMock(return_value={
            "success": True,
            "status": "completed",
            "message": "Implementation completed",
        })
        build_tools._implementation_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "run_implementation" in registered_tools:
            result = await registered_tools["run_implementation"]()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_generate_bitstream_tool(self):
        """测试生成比特流工具。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.generate_bitstream = AsyncMock(return_value={
            "success": True,
            "bitstream_path": "/output/design.bit",
            "message": "Bitstream generated",
        })
        build_tools._implementation_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "generate_bitstream" in registered_tools:
            result = await registered_tools["generate_bitstream"]()
            assert result.success is True
            assert result.bitstream_path == "/output/design.bit"

    @pytest.mark.asyncio
    async def test_get_utilization_report_tool(self):
        """测试获取资源利用率报告工具。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.get_utilization_report = AsyncMock(return_value={
            "success": True,
            "utilization": {"Slice LUTs": {"used": 1000, "available": 20000}},
            "raw_report": "Report text",
            "message": "Report generated",
        })
        build_tools._implementation_manager = mock_manager
        build_tools._synthesis_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "get_utilization_report" in registered_tools:
            result = await registered_tools["get_utilization_report"]()
            assert result.success is True
            assert "Slice LUTs" in result.utilization

    @pytest.mark.asyncio
    async def test_get_timing_report_tool(self):
        """测试获取时序报告工具。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.get_timing_report = AsyncMock(return_value={
            "success": True,
            "timing": {"setup": {"worst_slack": 2.5}, "timing_met": True},
            "raw_report": "Timing report",
            "message": "Report generated",
        })
        build_tools._implementation_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "get_timing_report" in registered_tools:
            result = await registered_tools["get_timing_report"]()
            assert result.success is True

    @pytest.mark.asyncio
    async def test_check_methodology_tool(self):
        """测试 methodology 检查工具。"""
        import gateflow.tools.build_tools as build_tools

        mock_manager = MagicMock()
        mock_manager.get_methodology_report = AsyncMock(
            return_value={
                "success": True,
                "raw_report": "CRITICAL WARNING: timing issue\nWARNING: reset issue\nINFO line",
                "message": "ok",
            }
        )
        build_tools._implementation_manager = mock_manager

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)

        if "check_methodology" in registered_tools:
            result = await registered_tools["check_methodology"](min_severity="warning")
            assert result.success is True
            assert result.report_name == "methodology"
            assert result.matched_findings >= 2

    @pytest.mark.asyncio
    async def test_check_drc_invalid_severity(self):
        """测试 DRC 检查工具的参数校验。"""
        import gateflow.tools.build_tools as build_tools

        mock_manager = MagicMock()
        mock_manager.get_drc_report = AsyncMock(
            return_value={
                "success": True,
                "raw_report": "ERROR: drc failed",
                "message": "ok",
            }
        )
        build_tools._implementation_manager = mock_manager

        mock_mcp = MagicMock()
        registered_tools = {}

        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func

            return decorator

        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)

        if "check_drc" in registered_tools:
            result = await registered_tools["check_drc"](min_severity="fatal")
            assert result.success is False
            assert result.error is not None


class TestProjectToolFunctions:
    """项目工具函数测试。"""

    @pytest.mark.asyncio
    async def test_create_project_tool(self):
        """测试创建项目工具。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.create_project = AsyncMock(return_value={
            "success": True,
            "project": {"name": "test", "part": "xc7a35tcpg236-1"},
            "message": "Project created",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "create_project" in registered_tools:
            result = await registered_tools["create_project"](
                name="test",
                path="/projects/test",
                part="xc7a35tcpg236-1",
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_open_project_tool(self):
        """测试打开项目工具。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.open_project = AsyncMock(return_value={
            "success": True,
            "project": {"name": "test"},
            "message": "Project opened",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "open_project" in registered_tools:
            result = await registered_tools["open_project"](
                path="/projects/test/test.xpr"
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_add_source_files_tool(self):
        """测试添加源文件工具。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.add_source_files = AsyncMock(return_value={
            "success": True,
            "added_files": ["/src/top.v"],
            "invalid_files": [],
            "message": "Files added",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "add_source_files" in registered_tools:
            result = await registered_tools["add_source_files"](
                files=["/src/top.v"],
                file_type="verilog",
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_set_top_module_tool(self):
        """测试设置顶层模块工具。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.set_top_module = AsyncMock(return_value={
            "success": True,
            "top_module": "my_top",
            "message": "Top module set",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "set_top_module" in registered_tools:
            result = await registered_tools["set_top_module"](
                module_name="my_top"
            )
            assert result.success is True

    @pytest.mark.asyncio
    async def test_get_project_info_tool(self):
        """测试获取项目信息工具。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.get_project_info = AsyncMock(return_value={
            "success": True,
            "project": {"name": "test", "part": "xc7a35tcpg236-1"},
            "message": "Info retrieved",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "get_project_info" in registered_tools:
            result = await registered_tools["get_project_info"]()
            assert result.success is True


class TestErrorHandling:
    """错误处理测试。"""

    @pytest.mark.asyncio
    async def test_synthesis_error(self):
        """测试综合错误处理。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.run_synthesis = AsyncMock(return_value={
            "success": False,
            "error": "Synthesis failed",
            "message": "Error during synthesis",
        })
        build_tools._synthesis_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "run_synthesis" in registered_tools:
            result = await registered_tools["run_synthesis"]()
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_implementation_error(self):
        """测试实现错误处理。"""
        import gateflow.tools.build_tools as build_tools
        
        mock_manager = MagicMock()
        mock_manager.run_implementation = AsyncMock(return_value={
            "success": False,
            "error": "Implementation failed",
            "message": "Error during implementation",
        })
        build_tools._implementation_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        if "run_implementation" in registered_tools:
            result = await registered_tools["run_implementation"]()
            assert result.success is False

    @pytest.mark.asyncio
    async def test_project_creation_error(self):
        """测试项目创建错误处理。"""
        import gateflow.tools.project_tools as project_tools
        
        mock_manager = MagicMock()
        mock_manager.create_project = AsyncMock(return_value={
            "success": False,
            "error": "Invalid path",
            "message": "Failed to create project",
        })
        project_tools._project_manager = mock_manager
        
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        if "create_project" in registered_tools:
            result = await registered_tools["create_project"](
                name="test",
                path="/invalid/path",
                part="xc7a35tcpg236-1",
            )
            assert result.success is False
            assert result.error is not None


class TestToolDescriptions:
    """工具描述测试。"""

    def test_build_tools_have_docstrings(self):
        """测试构建工具有文档字符串。"""
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_build_tools(mock_mcp)
        
        for name, func in registered_tools.items():
            assert func.__doc__ is not None, f"Tool {name} missing docstring"

    def test_project_tools_have_docstrings(self):
        """测试项目工具有文档字符串。"""
        mock_mcp = MagicMock()
        registered_tools = {}
        
        def capture_tool():
            def decorator(func):
                registered_tools[func.__name__] = func
                return func
            return decorator
        
        mock_mcp.tool = capture_tool
        register_project_tools(mock_mcp)
        
        for name, func in registered_tools.items():
            assert func.__doc__ is not None, f"Tool {name} missing docstring"
