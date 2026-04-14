"""Real hardware smoke tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gateflow.tools.hardware_tools import register_hardware_tools


def _capture_tools():
    mock_mcp = MagicMock()
    registered_tools = {}

    def capture_tool():
        def decorator(func):
            registered_tools[func.__name__] = func
            return func

        return decorator

    mock_mcp.tool = capture_tool
    register_hardware_tools(mock_mcp)
    return registered_tools


@pytest.mark.hardware_smoke
@pytest.mark.vivado
@pytest.mark.integration
@pytest.mark.asyncio
async def test_hardware_release_smoke(hardware_smoke_config):
    """Run the real hardware smoke path when board resources are available."""
    tools = _capture_tools()

    connect = await tools["connect_hw_server"](url=hardware_smoke_config["server_url"])
    assert connect.success is True

    targets = await tools["list_hardware_targets"]()
    assert targets.success is True

    if hardware_smoke_config["target"]:
        opened = await tools["open_hardware_target"](hardware_smoke_config["target"])
        assert opened.success is True

    programmed = await tools["quick_program"](
        bitstream_path=hardware_smoke_config["bitstream"],
        probe_file_path=hardware_smoke_config["probe"],
        url=hardware_smoke_config["server_url"],
    )
    assert programmed.success is True

    probe = await tools["set_probe_file"](
        device_index=0,
        probe_file_path=hardware_smoke_config["probe"],
    )
    assert probe.success is True

    ilas = await tools["hw_ila_list"]()
    vios = await tools["hw_vio_list"]()
    axis = await tools["hw_axi_list"]()

    assert ilas.success is True
    assert vios.success is True
    assert axis.success is True
