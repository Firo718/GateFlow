"""Minimal example: run high-frequency report and lint checks via GateFlow."""

import asyncio

from gateflow import GateFlow


async def main() -> dict:
    gf = GateFlow()

    print("This example assumes a project has already been opened.")

    util = await gf.get_utilization_report()
    timing = await gf.get_timing_report()
    drc = await gf.check_drc(min_severity="warning", max_findings=10)
    methodology = await gf.check_methodology(min_severity="warning", max_findings=10)
    power = await gf.get_power_report()

    print("utilization:", util.get("success"), util.get("message"))
    print("timing:", timing.get("success"), timing.get("message"))
    print("drc findings:", drc.get("matched_findings"))
    print("methodology findings:", methodology.get("matched_findings"))
    print("power:", power.get("success"), power.get("message"))

    return {
        "utilization_success": util.get("success"),
        "timing_success": timing.get("success"),
        "drc_findings": drc.get("matched_findings", 0),
        "methodology_findings": methodology.get("matched_findings", 0),
        "power_success": power.get("success"),
    }


if __name__ == "__main__":
    asyncio.run(main())
