"""Minimal example: use high-level IP query and blink_led simulation helpers."""

import asyncio
from pathlib import Path

from gateflow import GateFlow


async def main() -> dict:
    gf = GateFlow()

    here = Path(__file__).resolve().parent / "blink_led"
    tb_path = here / "tb_blink_led.v"

    ip_result = await gf.find_ip("axi_gpio")
    ip_list_result = await gf.list_available_ips("axi*")

    simset = await gf.create_simulation_set("sim_blink_led", [str(tb_path)])
    top = await gf.set_simulation_top("tb_blink_led", sim_set="sim_blink_led")
    compile_result = await gf.compile_simulation(sim_set="sim_blink_led")
    elaborate_result = await gf.elaborate_simulation(sim_set="sim_blink_led")
    launch = await gf.launch_simulation(
        sim_set="sim_blink_led",
        top_module="tb_blink_led",
        mode="behavioral",
        simulation_time="1us",
    )
    probe = await gf.probe_signal("tb_blink_led/clk")
    force = await gf.add_force_signal("tb_blink_led/rst_n", "0", after="0ns")
    run = await gf.run_simulation("100ns")
    value = await gf.get_signal_value("tb_blink_led/clk")
    unforce = await gf.remove_force_signal("tb_blink_led/rst_n")

    return {
        "find_ip_success": ip_result.get("success"),
        "list_available_ips_success": ip_list_result.get("success"),
        "simulation_success": all(
            item.get("success")
            for item in [
                simset,
                top,
                compile_result,
                elaborate_result,
                launch,
                probe,
                force,
                run,
                value,
                unforce,
            ]
        ),
        "ip_count": ip_list_result.get("count", 0),
        "signal_value": value.get("value"),
    }


if __name__ == "__main__":
    asyncio.run(main())
