"""
简单测试运行脚本。
"""

import sys
sys.path.insert(0, 'f:/GateFlow/src')

# 测试 ReportParser
from gateflow.utils.parser import ReportParser

print("=" * 60)
print("Testing ReportParser")
print("=" * 60)

# 测试资源利用率报告解析
util_report = """
| Slice LUTs | 1234 | 203800 | 0.61 |
| Slice Registers | 5678 | 407600 | 1.39 |
"""
result = ReportParser.parse_utilization_report(util_report)
print(f"Utilization Report Test: {'PASSED' if 'Slice LUTs' in result else 'FAILED'}")
print(f"  - Slice LUTs used: {result.get('Slice LUTs', {}).get('used', 'N/A')}")

# 测试时序报告解析
timing_report = """
Setup Slack: 2.5 ns
Hold Slack: 0.8 ns
"""
result = ReportParser.parse_timing_report(timing_report)
print(f"Timing Report Test: {'PASSED' if 'setup' in result else 'FAILED'}")
print(f"  - Setup worst_slack: {result.get('setup', {}).get('worst_slack', 'N/A')}")

# 测试功耗报告解析
power_report = """
Total On-Chip Power: 1.234 W
Dynamic Power: 0.856 W
Static Power: 0.378 W
"""
result = ReportParser.parse_power_report(power_report)
print(f"Power Report Test: {'PASSED' if result['total_power'] == 1.234 else 'FAILED'}")
print(f"  - Total Power: {result.get('total_power', 'N/A')} W")

# 测试 DRC 报告解析
drc_report = """
ERROR: Some error
WARNING: Some warning
"""
result = ReportParser.parse_drc_report(drc_report)
print(f"DRC Report Test: {'PASSED' if result['errors'] == 1 else 'FAILED'}")
print(f"  - Errors: {result.get('errors', 'N/A')}")
print(f"  - Warnings: {result.get('warnings', 'N/A')}")

print()
print("=" * 60)
print("Testing ProjectTclGenerator")
print("=" * 60)

from gateflow.vivado.project import ProjectTclGenerator, FileType
from pathlib import Path

# 测试创建项目命令
cmd = ProjectTclGenerator.create_project_tcl(
    name="test_project",
    path=Path("/projects/test"),
    part="xc7a35tcpg236-1",
)
print(f"Create Project Test: {'PASSED' if 'create_project' in cmd else 'FAILED'}")
print(f"  - Command: {cmd[:50]}...")

# 测试添加文件命令
files = [Path("/src/top.v"), Path("/src/module.v")]
commands = ProjectTclGenerator.add_files_tcl(files)
print(f"Add Files Test: {'PASSED' if 'add_files' in commands[0] else 'FAILED'}")

# 测试设置顶层模块命令
cmd = ProjectTclGenerator.set_top_module_tcl("my_top")
print(f"Set Top Module Test: {'PASSED' if 'my_top' in cmd else 'FAILED'}")

print()
print("=" * 60)
print("Testing Pydantic Models")
print("=" * 60)

from gateflow.tools.build_tools import SynthesisResult, BitstreamResult
from gateflow.tools.project_tools import CreateProjectResult

# 测试 SynthesisResult
result = SynthesisResult(success=True, message="Done")
print(f"SynthesisResult Test: {'PASSED' if result.success else 'FAILED'}")

# 测试 BitstreamResult
result = BitstreamResult(
    success=True,
    bitstream_path="/output/design.bit",
    message="Generated"
)
print(f"BitstreamResult Test: {'PASSED' if result.bitstream_path == '/output/design.bit' else 'FAILED'}")

# 测试 CreateProjectResult
result = CreateProjectResult(
    success=True,
    project={"name": "test"},
    message="Created"
)
print(f"CreateProjectResult Test: {'PASSED' if result.project['name'] == 'test' else 'FAILED'}")

print()
print("=" * 60)
print("All basic tests completed!")
print("=" * 60)
