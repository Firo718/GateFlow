"""
报告解析器。

提供 Vivado 报告文件的解析功能。
"""

import re
from typing import Any


class ReportParser:
    """
    Vivado 报告解析器。

    提供解析各种 Vivado 报告的静态方法。
    """

    @staticmethod
    def parse_utilization_report(report_text: str) -> dict[str, Any]:
        """
        解析资源利用率报告。

        Args:
            report_text: 报告文本内容。

        Returns:
            解析后的资源利用率字典，格式为:
            {
                "resource_name": {
                    "used": int,
                    "available": int,
                    "percentage": float
                },
                ...
            }
        """
        utilization = {}
        lines = report_text.split("\n")

        for line in lines:
            # 解析资源使用行
            # 格式示例: "Slice LUTs          |  1234 |  203800 |   0.61"
            if "|" in line:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    resource_name = parts[0]
                    try:
                        used = int(parts[1].replace(",", ""))
                        available = int(parts[2].replace(",", ""))
                        if available > 0:
                            percentage = (used / available) * 100
                        else:
                            percentage = 0

                        utilization[resource_name] = {
                            "used": used,
                            "available": available,
                            "percentage": round(percentage, 2),
                        }
                    except ValueError:
                        continue

        return utilization

    @staticmethod
    def parse_timing_report(report_text: str) -> dict[str, Any]:
        """
        解析时序报告。

        Args:
            report_text: 报告文本内容。

        Returns:
            解析后的时序字典，格式为:
            {
                "setup": {
                    "worst_slack": float,
                    "total_violations": int
                },
                "hold": {
                    "worst_slack": float,
                    "total_violations": int
                },
                "timing_met": bool
            }
        """
        timing = {
            "setup": {},
            "hold": {},
            "timing_met": True,
        }

        lines = report_text.split("\n")

        for line in lines:
            # 解析 Setup 时序裕量
            if "Setup" in line and "Slack" in line:
                match = re.search(r"[-+]?\d*\.?\d+", line.split(":")[-1])
                if match:
                    slack = float(match.group())
                    timing["setup"]["worst_slack"] = slack
                    if slack < 0:
                        timing["timing_met"] = False

            # 解析 Hold 时序裕量
            elif "Hold" in line and "Slack" in line:
                match = re.search(r"[-+]?\d*\.?\d+", line.split(":")[-1])
                if match:
                    slack = float(match.group())
                    timing["hold"]["worst_slack"] = slack
                    if slack < 0:
                        timing["timing_met"] = False

            # 解析时序违例数量
            elif "Timing Violations" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    try:
                        violations = int(parts[1].strip())
                        if violations > 0:
                            timing["timing_met"] = False
                            if "setup" not in timing:
                                timing["setup"]["total_violations"] = violations
                    except ValueError:
                        continue

        return timing

    @staticmethod
    def parse_power_report(report_text: str) -> dict[str, Any]:
        """
        解析功耗报告。

        Args:
            report_text: 报告文本内容。

        Returns:
            解析后的功耗字典，格式为:
            {
                "total_power": float,
                "dynamic_power": float,
                "static_power": float,
                "components": {
                    "component_name": {
                        "power": float,
                        "percentage": float
                    }
                }
            }
        """
        power = {
            "total_power": 0.0,
            "dynamic_power": 0.0,
            "static_power": 0.0,
            "components": {},
        }

        lines = report_text.split("\n")

        for line in lines:
            # 解析总功耗
            if "Total On-Chip Power" in line:
                match = re.search(r"(\d+\.?\d*)\s*W", line)
                if match:
                    power["total_power"] = float(match.group(1))

            # 解析动态功耗
            elif "Dynamic" in line and "Power" in line:
                match = re.search(r"(\d+\.?\d*)\s*W", line)
                if match:
                    power["dynamic_power"] = float(match.group(1))

            # 解析静态功耗
            elif "Static" in line and "Power" in line:
                match = re.search(r"(\d+\.?\d*)\s*W", line)
                if match:
                    power["static_power"] = float(match.group(1))

        return power

    @staticmethod
    def parse_clock_report(report_text: str) -> list[dict[str, Any]]:
        """
        解析时钟报告。

        Args:
            report_text: 报告文本内容。

        Returns:
            时钟列表，每个时钟包含:
            {
                "name": str,
                "period": float,
                "frequency": float,
                "waveform": list[float]
            }
        """
        clocks = []
        lines = report_text.split("\n")

        for line in lines:
            # 解析时钟定义行
            # 格式示例: "clk_100MHz    10.000    100.000    {0.000 5.000}"
            if "clk" in line.lower() or "clock" in line.lower():
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        clock = {
                            "name": parts[0],
                            "period": float(parts[1]),
                            "frequency": float(parts[2]),
                            "waveform": [],
                        }
                        # 解析波形
                        if len(parts) >= 4:
                            waveform_str = parts[3].strip("{}")
                            waveform = [float(x) for x in waveform_str.split()]
                            clock["waveform"] = waveform

                        clocks.append(clock)
                    except ValueError:
                        continue

        return clocks

    @staticmethod
    def parse_drc_report(report_text: str) -> dict[str, Any]:
        """
        解析设计规则检查 (DRC) 报告。

        Args:
            report_text: 报告文本内容。

        Returns:
            DRC 结果字典，格式为:
            {
                "passed": bool,
                "errors": int,
                "warnings": int,
                "violations": list[dict]
            }
        """
        drc = {
            "passed": True,
            "errors": 0,
            "warnings": 0,
            "violations": [],
        }

        lines = report_text.split("\n")

        for line in lines:
            # 解析错误数量
            if "ERROR" in line.upper():
                drc["errors"] += 1
                drc["passed"] = False
                drc["violations"].append({
                    "type": "error",
                    "message": line.strip(),
                })

            # 解析警告数量
            elif "WARNING" in line.upper():
                drc["warnings"] += 1
                drc["violations"].append({
                    "type": "warning",
                    "message": line.strip(),
                })

        return drc

    @staticmethod
    def extract_section(report_text: str, section_name: str) -> str | None:
        """
        从报告中提取指定章节内容。

        Args:
            report_text: 报告文本内容。
            section_name: 章节名称。

        Returns:
            章节内容，如果未找到则返回 None。
        """
        lines = report_text.split("\n")
        section_start = -1
        section_end = -1

        for i, line in enumerate(lines):
            # 查找章节开始
            if section_name.lower() in line.lower():
                section_start = i
            # 查找下一个章节开始（作为当前章节结束）
            elif section_start >= 0 and line.strip() and line.startswith(("+", "-", "=")):
                section_end = i
                break

        if section_start >= 0:
            if section_end < 0:
                section_end = len(lines)
            return "\n".join(lines[section_start:section_end])

        return None
