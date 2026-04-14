import argparse
import asyncio
import json
import os
from pathlib import Path

from gateflow import GateFlow
from gateflow.engine import EngineMode, ensure_engine_initialized


async def main() -> int:
    parser = argparse.ArgumentParser(description="Build zed LED blink via GateFlow TCP mode.")
    parser.add_argument("--vivado-path", default=None, help="Vivado root path. Optional.")
    parser.add_argument("--tcp-port", type=int, default=None, help="TCP port for GateFlow tcl_server (must match server).")
    parser.add_argument("--project-name", default="zed_led_blink_tcp", help="Vivado project name")
    args = parser.parse_args()

    if args.tcp_port is not None:
        os.environ["GATEFLOW_TCP_PORT"] = str(args.tcp_port)

    here = Path(__file__).resolve().parent
    source_dir = here / "blink_led"
    src_file = source_dir / "blink_led.v"
    xdc_file = source_dir / "blink_led.xdc"

    if not src_file.exists() or not xdc_file.exists():
        print(json.dumps({"success": False, "error": f"Missing source files under {source_dir.as_posix()}"}, ensure_ascii=False, indent=2))
        return 1

    # Force TCP mode. Ensure Vivado tcl_server is running on configured host/port.
    await ensure_engine_initialized(mode=EngineMode.TCP)

    gf = GateFlow(vivado_path=args.vivado_path)
    steps: list[tuple[str, dict]] = []

    result = await gf.create_project(
        name=args.project_name,
        path=str(here / "build_output_tcp"),
        part="xc7z020clg484-1",
    )
    steps.append(("create_project", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.add_source_files([str(src_file)], file_type="verilog")
    steps.append(("add_source_files_verilog", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.set_top_module("blink_led")
    steps.append(("set_top_module", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.add_source_files([str(xdc_file)], file_type="xdc")
    steps.append(("add_source_files_xdc", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.run_synthesis(jobs=4)
    steps.append(("run_synthesis", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.run_implementation(jobs=4)
    steps.append(("run_implementation", result))
    if not result.get("success"):
        print(json.dumps(steps, ensure_ascii=False, indent=2))
        return 1

    result = await gf.generate_bitstream(jobs=4)
    steps.append(("generate_bitstream", result))

    print(json.dumps(steps, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
