"""
Minimal example: create high-frequency Zynq block design templates.
"""

import asyncio

from gateflow.vivado.block_design import BlockDesignManager
from gateflow.vivado.tcl_engine import TclEngine


async def main() -> dict:
    manager = BlockDesignManager(TclEngine())

    a_create = await manager.create_design("system_gpio_uart_bram")
    a_build = await manager.build_zynq_design()
    a_gpio = await manager.create_axi_gpio("axi_gpio_0", width=8)
    a_dma = await manager.create_axi_dma("axi_dma_0", include_sg=False)
    a_save = await manager.save_design()
    a_wrap = await manager.generate_wrapper()
    print("template A done")

    b_create = await manager.create_design("system_gpio_uart_timer_dma")
    b_build = await manager.build_zynq_design()
    b_gpio = await manager.create_axi_gpio("axi_gpio_0", width=8)
    b_dma = await manager.create_axi_dma("axi_dma_0", include_sg=False)
    b_save = await manager.save_design()
    b_wrap = await manager.generate_wrapper()
    print("template B done")
    return {
        "template_a": all(
            item.get("success")
            for item in (a_create, a_build, a_gpio, a_dma, a_save, a_wrap)
        ),
        "template_b": all(
            item.get("success")
            for item in (b_create, b_build, b_gpio, b_dma, b_save, b_wrap)
        ),
    }


if __name__ == "__main__":
    asyncio.run(main())
