# Block Design 模块

## 概述

Block Design 模块提供完整的 Vivado Block Design 创建和管理功能，支持 IP 实例化、连接管理、Zynq PS 配置等操作。

## 主要功能

### 1. 数据结构

#### BDPort - Block Design 端口
```python
from gateflow.vivado.block_design import BDPort, BDInterfaceType

# 创建普通端口
port = BDPort(
    name="clk",
    direction="input",  # "input", "output", "inout"
    width=1
)

# 创建接口端口
axi_port = BDPort(
    name="M_AXI",
    direction="output",
    interface_type=BDInterfaceType.AXI4LITE
)
```

#### BDIPInstance - IP 实例
```python
from gateflow.vivado.block_design import BDIPInstance

instance = BDIPInstance(
    name="axi_gpio_0",
    ip_type="xilinx.com:ip:axi_gpio:2.0",
    config={
        "C_GPIO_WIDTH": 32,
        "C_IS_DUAL": False
    }
)
```

#### BDConnection - 连接
```python
from gateflow.vivado.block_design import BDConnection

connection = BDConnection(
    name="conn1",  # 可选
    source="processing_system7_0/M_AXI_GP0",
    destination="axi_interconnect_0/S00_AXI"
)
```

#### ZynqPSConfig - Zynq PS 配置
```python
from gateflow.vivado.block_design import ZynqPSConfig

ps_config = ZynqPSConfig(
    enable_fabric_reset=True,
    enable_fabric_clock=True,
    enable_uart0=True,
    enable_enet0=True,
    enable_sd0=True,
    enable_usb0=False
)
```

### 2. Tcl 命令生成器

`BlockDesignTclGenerator` 类提供静态方法生成各种 Tcl 命令：

#### 创建和管理 Block Design
```python
from gateflow.vivado.block_design import BlockDesignTclGenerator

# 创建 Block Design
cmd = BlockDesignTclGenerator.create_bd_design_tcl("my_bd")

# 打开 Block Design
cmd = BlockDesignTclGenerator.open_bd_design_tcl("my_bd")

# 关闭 Block Design
cmd = BlockDesignTclGenerator.close_bd_design_tcl()

# 保存 Block Design
cmd = BlockDesignTclGenerator.save_bd_design_tcl()

# 验证 Block Design
cmd = BlockDesignTclGenerator.validate_bd_design_tcl()

# 生成 HDL Wrapper
cmd = BlockDesignTclGenerator.generate_bd_wrapper_tcl("my_bd")
```

#### 创建 IP 实例
```python
# 创建 IP 实例
cmd = BlockDesignTclGenerator.create_bd_cell_tcl(instance)

# 创建并配置 IP 实例
commands = BlockDesignTclGenerator.create_bd_cell_with_config_tcl(instance)

# 设置 IP 属性
cmd = BlockDesignTclGenerator.set_bd_property_tcl(
    "axi_gpio_0",
    {"C_GPIO_WIDTH": 32, "C_IS_DUAL": False}
)
```

#### 创建端口和连接
```python
# 创建外部端口
cmd = BlockDesignTclGenerator.create_bd_port_tcl(port)

# 创建接口端口
cmd = BlockDesignTclGenerator.create_bd_intf_port_tcl(
    name="M_AXI",
    mode="Master",
    vlnv="xilinx.com:interface:axi4lite_rtl:1.0"
)

# 连接接口
cmd = BlockDesignTclGenerator.connect_bd_intf_net_tcl(connection)

# 连接普通网络
cmd = BlockDesignTclGenerator.connect_bd_net_tcl(
    source="clk_wiz_0/clk_out1",
    destinations=["axi_gpio_0/s_axi_aclk", "axi_uart_0/s_axi_aclk"]
)
```

#### 常用 IP 创建
```python
# 创建 Zynq PS
commands = BlockDesignTclGenerator.create_zynq_ps_tcl(
    name="processing_system7_0",
    config=ps_config
)

# 创建 Zynq UltraScale+ PS
commands = BlockDesignTclGenerator.create_zynq_ultra_ps_tcl(
    name="zynq_ultra_ps_e_0",
    preset="zu7ev"
)

# 创建 AXI Interconnect
commands = BlockDesignTclGenerator.create_axi_interconnect_tcl(
    name="axi_interconnect_0",
    num_mi=2,  # 主接口数量
    num_si=1   # 从接口数量
)

# 创建 Clock Wizard
commands = BlockDesignTclGenerator.create_clock_wizard_tcl(
    name="clk_wiz_0",
    input_freq=100.0,
    output_freqs=[50.0, 200.0]
)

# 创建 Processor System Reset
cmd = BlockDesignTclGenerator.create_processor_reset_tcl("proc_sys_reset_0")

# 创建 AXI GPIO
commands = BlockDesignTclGenerator.create_axi_gpio_tcl(
    name="axi_gpio_0",
    width=32,
    is_dual=False
)

# 创建 AXI DMA
commands = BlockDesignTclGenerator.create_axi_dma_tcl(
    name="axi_dma_0",
    include_sg=True
)

# 创建 AXI BRAM Controller
commands = BlockDesignTclGenerator.create_axi_bram_tcl(
    name="axi_bram_ctrl_0",
    data_width=32,
    memory_depth=8192
)

# 创建 AXI-Stream Data FIFO
commands = BlockDesignTclGenerator.create_axis_data_fifo_tcl(
    name="axis_data_fifo_0",
    depth=1024,
    width=32
)
```

#### 自动连接
```python
# 应用自动连接规则
cmd = BlockDesignTclGenerator.apply_bd_automation_tcl("all")

# 自动连接 AXI 时钟和复位
commands = BlockDesignTclGenerator.auto_connect_axi_clock_reset_tcl(
    axi_cell="axi_gpio_0",
    clock_source="processing_system7_0/FCLK_CLK0",
    reset_source="proc_sys_reset_0/peripheral_aresetn"
)
```

#### 查询操作
```python
# 获取所有 IP 实例
cmd = BlockDesignTclGenerator.get_bd_cells_tcl()

# 获取指定 IP 实例
cmd = BlockDesignTclGenerator.get_bd_cell_tcl("axi_gpio_0")

# 获取接口引脚
cmd = BlockDesignTclGenerator.get_bd_intf_pins_tcl("axi_gpio_0")

# 获取普通引脚
cmd = BlockDesignTclGenerator.get_bd_pins_tcl("axi_gpio_0")

# 获取所有接口端口
cmd = BlockDesignTclGenerator.get_bd_intf_ports_tcl()

# 获取所有普通端口
cmd = BlockDesignTclGenerator.get_bd_ports_tcl()
```

#### 删除操作
```python
# 删除 IP 实例
cmd = BlockDesignTclGenerator.delete_bd_cell_tcl("axi_gpio_0")

# 删除端口
cmd = BlockDesignTclGenerator.delete_bd_port_tcl("clk")

# 删除接口端口
cmd = BlockDesignTclGenerator.delete_bd_intf_port_tcl("M_AXI")
```

#### 导入导出
```python
# 导出 Block Design 为 Tcl 脚本
cmd = BlockDesignTclGenerator.export_bd_tcl(
    bd_name="my_bd",
    output_path=Path("./my_bd.tcl")
)

# 从 Tcl 脚本导入 Block Design
cmd = BlockDesignTclGenerator.import_bd_tcl(Path("./my_bd.tcl"))
```

### 3. Block Design 管理器

`BlockDesignManager` 类提供高级管理接口，结合 TclEngine 执行 Tcl 命令：

#### 基本操作
```python
from gateflow.vivado import TclEngine
from gateflow.vivado.block_design import BlockDesignManager

# 创建 Tcl 引擎
engine = TclEngine()

# 创建 Block Design 管理器
bd_manager = BlockDesignManager(engine)

# 创建新的 Block Design
result = await bd_manager.create_design("my_bd")
if result['success']:
    print("Block Design 创建成功")

# 打开 Block Design
result = await bd_manager.open_design("my_bd")

# 关闭 Block Design
result = await bd_manager.close_design()

# 保存设计
result = await bd_manager.save_design()

# 验证设计
result = await bd_manager.validate_design()

# 生成 HDL Wrapper
result = await bd_manager.generate_wrapper()
```

#### IP 实例管理
```python
# 添加 IP 实例
instance = BDIPInstance(
    name="axi_gpio_0",
    ip_type="xilinx.com:ip:axi_gpio:2.0",
    config={"C_GPIO_WIDTH": 32}
)
result = await bd_manager.add_ip_instance(instance)

# 移除 IP 实例
result = await bd_manager.remove_ip_instance("axi_gpio_0")

# 获取所有 IP 实例
cells = await bd_manager.get_cells()
for cell in cells:
    print(f"IP: {cell['name']}")
```

#### 端口和连接管理
```python
# 创建外部端口
port = BDPort(name="clk", direction="input", width=1)
result = await bd_manager.create_external_port(port)

# 连接端口
result = await bd_manager.connect_ports(
    source="processing_system7_0/FCLK_CLK0",
    destination="axi_gpio_0/s_axi_aclk"
)

# 连接接口
result = await bd_manager.connect_interface(
    source="processing_system7_0/M_AXI_GP0",
    destination="axi_interconnect_0/S00_AXI"
)

# 应用自动连接
result = await bd_manager.apply_automation("all")

# 获取所有连接
connections = await bd_manager.get_connections()
```

#### 快速创建常用 IP
```python
# 创建 Zynq PS
ps_config = ZynqPSConfig(
    enable_fabric_reset=True,
    enable_fabric_clock=True,
    enable_uart0=True
)
result = await bd_manager.create_zynq_ps("processing_system7_0", ps_config)

# 创建 Zynq UltraScale+ PS
result = await bd_manager.create_zynq_ultra_ps("zynq_ultra_ps_e_0", "zu7ev")

# 创建 AXI Interconnect
result = await bd_manager.create_axi_interconnect(
    "axi_interconnect_0",
    num_mi=2,
    num_si=1
)

# 创建 Clock Wizard
result = await bd_manager.create_clock_wizard(
    "clk_wiz_0",
    input_freq=100.0,
    output_freqs=[50.0, 200.0]
)

# 创建 Processor Reset
result = await bd_manager.create_processor_reset("proc_sys_reset_0")

# 创建 AXI GPIO
result = await bd_manager.create_axi_gpio("axi_gpio_0", width=32)

# 创建 AXI DMA
result = await bd_manager.create_axi_dma("axi_dma_0", include_sg=True)
```

#### 快速构建 Zynq 系统
```python
# 配置 PS
ps_config = ZynqPSConfig(
    enable_fabric_reset=True,
    enable_fabric_clock=True,
    enable_uart0=True,
    enable_enet0=True
)

# 快速构建完整的 Zynq 系统
result = await bd_manager.build_zynq_design(
    ps_config=ps_config,
    axi_peripherals=['axi_gpio', 'axi_uart']
)

if result['success']:
    print("Zynq 系统构建成功！")
else:
    print(f"构建失败: {result['errors']}")
```

#### 导入导出
```python
# 导出 Block Design
result = await bd_manager.export_bd_tcl(Path("./my_bd.tcl"))

# 导入 Block Design
result = await bd_manager.import_bd_tcl(Path("./my_bd.tcl"))
```

## 完整示例

### 示例 1：创建简单的 Zynq 系统

```python
import asyncio
from pathlib import Path
from gateflow.vivado import TclEngine
from gateflow.vivado.block_design import (
    BlockDesignManager,
    ZynqPSConfig,
    BDIPInstance,
)

async def main():
    # 创建 Tcl 引擎
    engine = TclEngine()
    bd_manager = BlockDesignManager(engine)

    # 创建 Block Design
    await bd_manager.create_design("zynq_system")

    # 配置 PS
    ps_config = ZynqPSConfig(
        enable_fabric_reset=True,
        enable_fabric_clock=True,
        enable_uart0=True
    )

    # 创建 Zynq PS
    await bd_manager.create_zynq_ps("processing_system7_0", ps_config)

    # 创建 Processor Reset
    await bd_manager.create_processor_reset("proc_sys_reset_0")

    # 连接时钟和复位
    await bd_manager.connect_ports(
        "processing_system7_0/FCLK_CLK0",
        "proc_sys_reset_0/slowest_sync_clk"
    )
    await bd_manager.connect_ports(
        "processing_system7_0/FCLK_RESET0_N",
        "proc_sys_reset_0/ext_reset_in"
    )

    # 创建 AXI Interconnect
    await bd_manager.create_axi_interconnect("axi_interconnect_0", num_mi=1)

    # 连接 PS 到 Interconnect
    await bd_manager.connect_interface(
        "processing_system7_0/M_AXI_GP0",
        "axi_interconnect_0/S00_AXI"
    )

    # 创建 AXI GPIO
    await bd_manager.create_axi_gpio("axi_gpio_0", width=8)

    # 连接 GPIO 到 Interconnect
    await bd_manager.connect_interface(
        "axi_interconnect_0/M00_AXI",
        "axi_gpio_0/S_AXI"
    )

    # 应用自动连接
    await bd_manager.apply_automation("all")

    # 验证设计
    result = await bd_manager.validate_design()
    if result['success']:
        print("设计验证成功！")

        # 保存设计
        await bd_manager.save_design()

        # 生成 HDL Wrapper
        await bd_manager.generate_wrapper()
    else:
        print(f"设计验证失败: {result['errors']}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 示例 2：使用快速构建方法

```python
import asyncio
from gateflow.vivado import TclEngine
from gateflow.vivado.block_design import BlockDesignManager, ZynqPSConfig

async def main():
    # 创建 Tcl 引擎
    engine = TclEngine()
    bd_manager = BlockDesignManager(engine)

    # 创建 Block Design
    await bd_manager.create_design("zynq_system")

    # 配置 PS
    ps_config = ZynqPSConfig(
        enable_fabric_reset=True,
        enable_fabric_clock=True,
        enable_uart0=True,
        enable_enet0=True,
        enable_sd0=True
    )

    # 快速构建 Zynq 系统
    result = await bd_manager.build_zynq_design(
        ps_config=ps_config,
        axi_peripherals=['axi_gpio', 'axi_uart']
    )

    if result['success']:
        print("Zynq 系统构建成功！")

        # 生成 HDL Wrapper
        await bd_manager.generate_wrapper()
    else:
        print(f"构建失败: {result['errors']}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 支持的接口类型

- AXI4-Lite
- AXI4 Memory Mapped
- AXI4-Stream
- Clock
- Reset
- Interrupt
- GPIO

## 支持的 IP

- Processing System 7 (Zynq-7000)
- Zynq UltraScale+ PS
- AXI Interconnect
- Clock Wizard
- Processor System Reset
- AXI GPIO
- AXI DMA
- AXI BRAM Controller
- AXI-Stream Data FIFO

## 注意事项

1. 使用前需要安装 Vivado 并配置环境变量 `XILINX_VIVADO`
2. 所有异步方法需要在 async 函数中调用
3. Tcl 命令生成器可以独立使用，无需 Vivado 环境
4. BlockDesignManager 需要结合 TclEngine 使用

## 版本兼容性

支持 Vivado 2019.1 到 2024.2 版本。
