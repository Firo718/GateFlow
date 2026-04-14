"""Minimal example: compile, elaborate, run, probe and force via GateFlow."""

import asyncio

from gateflow import GateFlow


async def main() -> dict:
    gf = GateFlow()

    print("This example assumes simulation sources already exist in sim_1.")

    top = await gf.set_simulation_top(module="tb_top", sim_set="sim_1")
    compile_result = await gf.compile_simulation(sim_set="sim_1")
    elaborate_result = await gf.elaborate_simulation(sim_set="sim_1")
    launch = await gf.launch_simulation(
        sim_set="sim_1",
        top_module="tb_top",
        mode="behavioral",
        simulation_time="1us",
        run_mode="default",
    )
    wave_clk = await gf.probe_signal(signal="tb_top/clk", radix="binary")
    wave_data = await gf.probe_signal(signal="tb_top/data", radix="hex")
    force = await gf.add_force_signal(signal="tb_top/reset_n", value="0", after="0ns")
    run = await gf.run_simulation(time="100ns")
    value = await gf.get_signal_value(signal="tb_top/data")

    print("signal value:", value.get("value"))

    remove = await gf.remove_force_signal(signal="tb_top/reset_n")
    return {
        "top_success": top.get("success"),
        "compile_success": compile_result.get("success"),
        "elaborate_success": elaborate_result.get("success"),
        "launch_success": launch.get("success"),
        "wave_success": wave_clk.get("success") and wave_data.get("success"),
        "force_success": force.get("success"),
        "run_success": run.get("success"),
        "value_success": value.get("success"),
        "remove_success": remove.get("success"),
    }


if __name__ == "__main__":
    asyncio.run(main())
