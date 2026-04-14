"""
Minimal example: hardware debug runtime with targets, probes, ILA/VIO and AXI.
"""

import asyncio

from gateflow.vivado.hardware import HardwareManager, HardwareTclGenerator
from gateflow.vivado.tcl_engine import TclEngine


async def main() -> dict:
    engine = TclEngine()
    manager = HardwareManager(engine)

    connect_result = await manager.connect_server(url="localhost:3121")
    print("targets cmd:", HardwareTclGenerator.get_hw_targets_tcl())

    # Program and bind debug probes when matching files are available.
    program_result = await manager.program_fpga(device_index=0, bitstream_path="build/top.bit")
    probe_result = await manager.set_probe_file(device_index=0, probe_file_path="build/top.ltx")

    # ILA/VIO/HW AXI are currently exposed at tool level; here we show the exact Tcl commands.
    print(HardwareTclGenerator.get_hw_ila_tcl())
    print(HardwareTclGenerator.run_hw_ila_tcl("hw_ila_1"))
    print(HardwareTclGenerator.upload_hw_ila_tcl("hw_ila_1"))
    print(HardwareTclGenerator.get_hw_vio_tcl())
    print(HardwareTclGenerator.set_vio_output_tcl("hw_vio_1", "probe_out0", "1"))
    print(HardwareTclGenerator.get_vio_input_tcl("hw_vio_1", "probe_in0"))
    print(
        HardwareTclGenerator.create_hw_axi_txn_tcl(
            txn_name="axi_read_example",
            axi_name="hw_axi_1",
            address="0x40000000",
            txn_type="read",
        )
    )
    return {
        "connect_success": connect_result.get("success"),
        "program_success": program_result.success,
        "probe_success": probe_result.get("success"),
    }


if __name__ == "__main__":
    asyncio.run(main())
