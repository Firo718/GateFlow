"""
GateFlow 测试配置文件。

定义测试夹具、标记和共享配置。
"""

import os

import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ==================== 测试标记 ====================

def pytest_configure(config):
    """注册自定义测试标记。"""
    config.addinivalue_line(
        "markers", "vivado: marks tests as requiring Vivado (deselect with '-m \"not vivado\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "release_gate: marks tests as release-gate verification"
    )
    config.addinivalue_line(
        "markers", "hardware_smoke: marks tests as real hardware smoke verification"
    )
    config.addinivalue_line(
        "markers", "ai_real_usage: marks tests as AI-driven real FPGA usage verification"
    )


# ==================== 共享夹具 ====================

@pytest.fixture
def mock_vivado_info():
    """创建模拟的 VivadoInfo。"""
    from gateflow.vivado.tcl_engine import VivadoInfo
    
    return VivadoInfo(
        version="2024.1",
        install_path=Path("C:/Xilinx/Vivado/2024.1"),
        executable=Path("C:/Xilinx/Vivado/2024.1/bin/vivado.bat"),
        tcl_shell=Path("C:/Xilinx/Vivado/2024.1/bin/vivado -mode tcl"),
    )


@pytest.fixture
def mock_tcl_engine(mock_vivado_info):
    """创建模拟的 TclEngine。"""
    from gateflow.vivado.tcl_engine import TclEngine, VivadoDetector
    from unittest.mock import patch
    
    with patch.object(VivadoDetector, "detect_vivado", return_value=mock_vivado_info):
        engine = TclEngine()
        return engine


@pytest.fixture
def temp_project_dir(tmp_path):
    """创建临时项目目录。"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def sample_verilog_file(temp_project_dir):
    """创建示例 Verilog 文件。"""
    verilog_file = temp_project_dir / "top.v"
    verilog_file.write_text("""
module top(
    input clk,
    input rst,
    output led
);
    assign led = ~rst;
endmodule
""")
    return verilog_file


@pytest.fixture
def sample_constraint_file(temp_project_dir):
    """创建示例约束文件。"""
    constraint_file = temp_project_dir / "pins.xdc"
    constraint_file.write_text("""
set_property PACKAGE_PIN E3 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
""")
    return constraint_file


# ==================== 测试跳过条件 ====================

def pytest_collection_modifyitems(config, items):
    """根据条件修改测试项。"""
    # 如果指定了跳过 Vivado 测试，则跳过所有标记为 vivado 的测试
    skip_vivado = pytest.mark.skip(reason="需要 Vivado 环境")
    
    for item in items:
        if "vivado" in item.keywords:
            # 检查是否真的有 Vivado 环境
            # 这里可以添加实际的检查逻辑
            # 例如：检查环境变量或 Vivado 是否安装
            pass


def _truthy_env(name: str) -> bool:
    """Interpret a boolean-style environment variable."""
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


@pytest.fixture(scope="session")
def release_gate_tcp_config() -> dict[str, str]:
    """Return TCP release-gate config or skip with a clear reason."""
    port = os.getenv("GATEFLOW_TCP_PORT", "").strip()
    host = os.getenv("GATEFLOW_TCP_HOST", "localhost").strip()
    if not port:
        pytest.skip("TCP release-gate skipped: GATEFLOW_TCP_PORT not configured")
    return {"host": host, "port": port}


@pytest.fixture(scope="session")
def hardware_smoke_config() -> dict[str, str]:
    """Return hardware smoke config or skip with a clear reason."""
    if not _truthy_env("GATEFLOW_HW_SMOKE_ENABLE"):
        pytest.skip("hardware_smoke skipped: GATEFLOW_HW_SMOKE_ENABLE not enabled")

    required = {
        "server_url": os.getenv("GATEFLOW_HW_SERVER_URL", "").strip(),
        "bitstream": os.getenv("GATEFLOW_HW_BITSTREAM", "").strip(),
        "probe": os.getenv("GATEFLOW_HW_PROBE", "").strip(),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        pytest.skip(
            "hardware_smoke skipped: missing env "
            + ", ".join(f"GATEFLOW_HW_{name.upper()}" for name in missing)
        )

    target = os.getenv("GATEFLOW_HW_TARGET", "").strip()
    return {**required, "target": target}
