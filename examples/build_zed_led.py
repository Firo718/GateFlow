import argparse
import re
from pathlib import Path

from gateflow.utils.path_utils import normalize_path
from gateflow.vivado.implementation import ImplementationTclGenerator
from gateflow.vivado.project import ProjectTclGenerator
from gateflow.vivado.synthesis import SynthesisTclGenerator
from gateflow.vivado.tcl_engine import TclEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a zed LED blink project via GateFlow TclEngine (batch mode).")
    parser.add_argument("--vivado-path", default=None, help="Vivado root path, e.g. F:/Xilinx/Vivado/2023.1")
    parser.add_argument("--project-name", default="zed_led_blink", help="Vivado project name")
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    source_dir = here / "blink_led"
    src_file = source_dir / "blink_led.v"
    xdc_file = source_dir / "blink_led.xdc"

    if not src_file.exists() or not xdc_file.exists():
        print("BUILD_FAILED")
        print(f"Missing source files under: {source_dir.as_posix()}")
        return 1

    project_name = args.project_name
    project_dir = here / "build_output"
    log_file = here / "build_vivado.log"

    vivado_root = Path(args.vivado_path) if args.vivado_path else None
    engine = TclEngine(vivado_path=vivado_root, timeout=7200.0)

    project_dir_tcl = normalize_path(str(project_dir))
    src_file_tcl = normalize_path(str(src_file))
    xdc_file_tcl = normalize_path(str(xdc_file))

    commands: list[str] = []
    commands.append(f'create_project "{project_name}" "{project_dir_tcl}" -part "xc7z020clg484-1" -force')
    commands.append('set_property target_language Verilog [current_project]')
    commands.append('set_property simulator_language Verilog [current_project]')
    commands.append('set_property default_lib work [current_project]')

    commands.append(f'add_files -fileset sources_1 {{{src_file_tcl}}}')
    commands.append(f'add_files -fileset constrs_1 {{{xdc_file_tcl}}}')
    commands.append(ProjectTclGenerator.set_top_module_tcl("blink_led"))
    commands.append(ProjectTclGenerator.update_compile_order_tcl())

    commands.append(SynthesisTclGenerator.reset_synthesis_tcl("synth_1"))
    commands.extend(SynthesisTclGenerator.run_synthesis_complete_tcl("synth_1", jobs=4))
    commands.append(ImplementationTclGenerator.reset_implementation_tcl("impl_1"))
    commands.extend(ImplementationTclGenerator.run_implementation_complete_tcl("impl_1", jobs=4))
    commands.append(ImplementationTclGenerator.generate_bitstream_tcl("impl_1"))
    commands.append("wait_on_run impl_1")
    commands.append('set run_dir [get_property DIRECTORY [get_runs impl_1]]')
    commands.append('set top_name [get_property top [current_fileset]]')
    commands.append('puts "BIT_PATH:$run_dir/$top_name.bit"')

    result = engine.execute(commands, timeout=7200.0, working_dir=here)
    log_file.write_text(result.output, encoding="utf-8", errors="replace")

    if not result.success:
        print("BUILD_FAILED")
        print(f"LOG_FILE:{log_file.as_posix()}")
        return 1

    match = re.search(r"^BIT_PATH:(.+)$", result.output, re.MULTILINE)
    if match:
        print(f"BUILD_SUCCESS:{match.group(1).strip()}")
    else:
        print("BUILD_SUCCESS:BIT_PATH_NOT_FOUND")
    print(f"LOG_FILE:{log_file.as_posix()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
