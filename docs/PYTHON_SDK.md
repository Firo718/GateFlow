# GateFlow Python SDK

GateFlow 提供两种使用方式：
1. **MCP 工具** - 通过 AI 助手使用
2. **Python API** - 直接在 Python 代码中使用

本文档介绍 Python API 的使用方法。

## 快速开始

### 安装

```bash
pip install gateflow
```

### 基本使用

```python
import asyncio
from gateflow import GateFlow

async def main():
    # 创建 GateFlow 实例
    gf = GateFlow()
    
    # 创建项目
    await gf.create_project(
        name="my_project",
        path="./projects",
        part="xc7a35tcpg236-1"
    )
    
    # 添加源文件
    await gf.add_source_files(["src/top.v", "src/module.v"])
    
    # 设置顶层模块
    await gf.set_top_module("top")
    
    # 运行综合
    result = await gf.run_synthesis()
    print(f"综合状态: {result['status']}")
    
    # 运行实现
    result = await gf.run_implementation()
    
    # 生成比特流
    result = await gf.generate_bitstream()
    print(f"比特流路径: {result['bitstream_path']}")

asyncio.run(main())
```

## 高级 API

### 项目管理

```python
# 创建项目
await gf.create_project(name, path, part)

# 打开项目
await gf.open_project(path)

# 获取项目信息
info = await gf.get_project_info()
```

### 构建流程

```python
# 运行综合
result = await gf.run_synthesis(jobs=4)
# 返回: {"success": True, "status": "completed", "report_path": "..."}

# 运行实现
result = await gf.run_implementation(jobs=4)

# 生成比特流
result = await gf.generate_bitstream(jobs=4)
# 返回: {"success": True, "bitstream_path": ".../project.runs/impl_1/top.bit"}
```

### Block Design

```python
# 创建 Block Design
await gf.create_bd_design("system")

# 添加 IP
await gf.add_bd_ip("xilinx.com:ip:axi_gpio:2.0", "axi_gpio_0")

# 应用自动连接
await gf.apply_bd_automation()

# 生成 HDL Wrapper
await gf.generate_bd_wrapper()
```

### 约束管理

```python
# 创建时钟约束
await gf.create_clock(
    name="clk_100m",
    period=10.0,
    target="clk"
)

# 创建约束文件
await gf.create_constraint_file("constraints.xdc", content)
```

## 会话管理

GateFlow 支持两种执行模式：

### TCP 模式（推荐）

需要先启动 Vivado Tcl Server：
```bash
gateflow install  # 安装 Tcl Server
# 启动 Vivado 后自动运行 Tcl Server
```

TCP 模式优势：
- 持久连接，状态保持
- 执行速度快
- 支持实时交互

### Subprocess 模式

无需额外配置，每次执行启动新的 Vivado 进程：
```python
# 自动回退到 subprocess 模式
gf = GateFlow()
```

## API 参考

### GateFlow 类

#### 初始化

```python
GateFlow(
    vivado_path: str | None = None,
    gui_enabled: bool | None = None,
    gui_tcp_port: int | None = None
)
```

**参数：**
- `vivado_path`: Vivado 安装路径（可选，自动检测）
- `gui_enabled`: 是否默认通过 Vivado GUI 会话执行
- `gui_tcp_port`: GUI 会话使用的 TCP 端口

GUI 模式示例：
```python
gf = GateFlow(gui_enabled=True, gui_tcp_port=10124)
await gf.open_project_gui("F:/path/to/project.xpr")
info = await gf.get_session_mode_info()
print(info["gui_session"])
```

如果 GUI 已经由其他方式启动，并且该会话已经加载了 GateFlow TCP server，也可以直接附着：

```python
gf = GateFlow()
await gf.attach_gui_session(10124, project_path="F:/path/to/project.xpr")
```

如果 `gui_enabled=True`，默认工作流会优先尝试：

1. `gui_session`
2. 常规 TCP
3. subprocess

也就是说，后续像下面这些调用会优先落在 GUI 会话里：

```python
gf = GateFlow(gui_enabled=True, gui_tcp_port=10124)
await gf.open_project("F:/path/to/project.xpr")
await gf.get_run_status("synth_1")
await gf.run_synthesis()
```

如果 GUI 会话不可用，GateFlow 才会回退到常规 TCP / subprocess 路径。

#### 管理器获取方法

##### get_clock_manager

获取时钟管理器实例（异步）。

```python
async def get_clock_manager() -> ClockManager
```

**返回：**
- `ClockManager`: 时钟管理器实例

**示例：**
```python
# 获取时钟管理器
clock_mgr = await gf.get_clock_manager()

# 使用时钟管理器
await clock_mgr.create_clock("clk0", 10.0)
await clock_mgr.connect_clock("clk0", ["ip_0/clk"])
```

**注意：**
- 此方法是异步的，必须在 async 函数中使用 `await` 调用
- 在 Jupyter Notebook 中可以直接使用 `await`
- 返回的管理器实例会被缓存，多次调用返回同一实例

##### get_interrupt_manager

获取中断管理器实例（异步）。

```python
async def get_interrupt_manager() -> InterruptManager
```

**返回：**
- `InterruptManager`: 中断管理器实例

**示例：**
```python
# 获取中断管理器
irq_mgr = await gf.get_interrupt_manager()

# 使用中断管理器
await irq_mgr.connect_interrupt("gpio_0/ip2intc_irpt", irq_number=0)
interrupts = await irq_mgr.list_interrupts()
```

**注意：**
- 此方法是异步的，必须在 async 函数中使用 `await` 调用
- 在 Jupyter Notebook 中可以直接使用 `await`
- 返回的管理器实例会被缓存，多次调用返回同一实例

#### 项目管理方法

##### create_project

创建新的 Vivado 项目。

```python
async def create_project(
    name: str,
    path: str,
    part: str,
) -> dict[str, Any]
```

**参数：**
- `name`: 项目名称
- `path`: 项目保存路径
- `part`: 目标器件型号（如 `xc7a35tcpg236-1`）

**返回：**
```python
{
    "success": True,
    "project": {
        "name": "my_project",
        "path": "/path/to/project",
        "part": "xc7a35tcpg236-1"
    },
    "message": "项目创建成功"
}
```

##### open_project

打开现有项目。

```python
async def open_project(path: str) -> dict[str, Any]
```

**参数：**
- `path`: 项目文件路径（.xpr 文件）

##### get_project_info

获取当前项目信息。

```python
async def get_project_info() -> dict[str, Any]
```

**返回：**
```python
{
    "success": True,
    "project": {
        "name": "my_project",
        "directory": "/path/to/project",
        "part": "xc7a35tcpg236-1",
        "language": "Verilog"
    }
}
```

##### close_project

关闭当前项目。

```python
async def close_project() -> dict[str, Any]
```

#### 源文件管理方法

##### add_source_files

添加源文件到项目。

```python
async def add_source_files(
    files: list[str],
    file_type: str = "verilog"
) -> dict[str, Any]
```

**参数：**
- `files`: 文件路径列表
- `file_type`: 文件类型（`verilog`, `vhdl`, `xdc` 等）

##### set_top_module

设置顶层模块。

```python
async def set_top_module(module_name: str) -> dict[str, Any]
```

#### 构建方法

##### run_synthesis

运行综合。

```python
async def run_synthesis(jobs: int = 4) -> dict[str, Any]
```

**参数：**
- `jobs`: 并行任务数

**返回：**
```python
{
    "success": True,
    "status": "completed",
    "message": "综合运行成功"
}
```

##### run_implementation

运行实现。

```python
async def run_implementation(jobs: int = 4) -> dict[str, Any]
```

##### generate_bitstream

生成比特流。

```python
async def generate_bitstream(jobs: int = 4) -> dict[str, Any]
```

**返回：**
```python
{
    "success": True,
    "bitstream_path": "/path/to/project.runs/impl_1/top.bit",
    "message": "比特流生成成功"
}
```

##### get_utilization_report

获取资源利用率报告。

```python
async def get_utilization_report() -> dict[str, Any]
```

**返回：**
```python
{
    "success": True,
    "utilization": {
        "slice_lut": {"used": 1000, "available": 20800, "utilization": 4.8},
        "slice_registers": {"used": 500, "available": 41600, "utilization": 1.2},
        "bram": {"used": 10, "available": 50, "utilization": 20.0},
        "dsp": {"used": 5, "available": 90, "utilization": 5.6}
    }
}
```

##### get_timing_report

获取时序报告。

```python
async def get_timing_report() -> dict[str, Any]
```

**返回：**
```python
{
    "success": True,
    "timing": {
        "wns": 2.5,  # Worst Negative Slack
        "tns": 0.0,  # Total Negative Slack
        "whs": 0.1,  # Worst Hold Slack
        "ths": 0.0,  # Total Hold Slack
        "timing_met": True
    }
}
```

#### Block Design 方法

##### create_bd_design

创建 Block Design。

```python
async def create_bd_design(name: str) -> dict[str, Any]
```

##### add_bd_ip

添加 IP 到 Block Design。

```python
async def add_bd_ip(
    ip_type: str,
    instance_name: str,
    config: dict[str, Any] | None = None
) -> dict[str, Any]
```

**参数：**
- `ip_type`: IP 类型（如 `xilinx.com:ip:axi_gpio:2.0`）
- `instance_name`: 实例名称
- `config`: IP 配置属性

**示例：**
```python
await gf.add_bd_ip(
    ip_type="xilinx.com:ip:axi_gpio:2.0",
    instance_name="axi_gpio_0",
    config={"CONFIG.C_GPIO_WIDTH": "8"}
)
```

##### apply_bd_automation

应用 Block Design 自动连接。

```python
async def apply_bd_automation(rule: str = "all") -> dict[str, Any]
```

**参数：**
- `rule`: 自动连接规则（`all`, `axi`, `clock`, `reset`）

##### generate_bd_wrapper

生成 HDL Wrapper。

```python
async def generate_bd_wrapper() -> dict[str, Any]
```

##### validate_bd_design

验证 Block Design。

```python
async def validate_bd_design() -> dict[str, Any]
```

#### 约束管理方法

##### create_clock

创建时钟约束。

```python
async def create_clock(
    name: str,
    period: float,
    target: str
) -> dict[str, Any]
```

**参数：**
- `name`: 时钟名称
- `period`: 时钟周期（纳秒）
- `target`: 目标端口名称

**示例：**
```python
# 创建 100MHz 时钟约束
await gf.create_clock(
    name="clk_100m",
    period=10.0,  # 10ns = 100MHz
    target="clk"
)
```

##### create_constraint_file

创建约束文件。

```python
async def create_constraint_file(
    filename: str,
    content: str
) -> dict[str, Any]
```

## 完整示例

### 示例 1: 简单项目创建

```python
import asyncio
from gateflow import GateFlow

async def simple_project():
    gf = GateFlow()
    
    # 创建项目
    await gf.create_project(
        name="led_blink",
        path="./projects/led_blink",
        part="xc7a35tcpg236-1"
    )
    
    # 添加源文件
    await gf.add_source_files(["led_blink.v"])
    await gf.add_source_files(["led_blink.xdc"], file_type="xdc")
    
    # 设置顶层模块
    await gf.set_top_module("led_blink")
    
    # 创建时钟约束
    await gf.create_clock("clk_100m", 10.0, "clk")
    
    # 运行综合
    synth_result = await gf.run_synthesis()
    if synth_result["success"]:
        print("综合完成")
        
        # 查看资源利用率
        util = await gf.get_utilization_report()
        print(f"LUT 使用率: {util['utilization']['slice_lut']['utilization']}%")
    
    # 运行实现
    impl_result = await gf.run_implementation()
    if impl_result["success"]:
        print("实现完成")
        
        # 检查时序
        timing = await gf.get_timing_report()
        if timing["timing"]["timing_met"]:
            print("时序满足要求")
    
    # 生成比特流
    bit_result = await gf.generate_bitstream()
    if bit_result["success"]:
        print(f"比特流: {bit_result['bitstream_path']}")

asyncio.run(simple_project())
```

### 示例 2: Block Design 项目

```python
import asyncio
from gateflow import GateFlow

async def block_design_project():
    gf = GateFlow()
    
    # 创建项目
    await gf.create_project(
        name="zynq_system",
        path="./projects/zynq_system",
        part="xc7z020clg484-2"
    )
    
    # 创建 Block Design
    await gf.create_bd_design("system")
    
    # 添加 Zynq PS
    # 注意：IP 版本号因 Vivado 版本而异
    # Vivado 2023.1 使用 5.5 版本
    # Vivado 2024.1 使用 5.7 版本
    await gf.add_bd_ip(
        ip_type="xilinx.com:ip:processing_system7:5.5",
        instance_name="processing_system7_0"
    )
    
    # 添加 AXI GPIO
    await gf.add_bd_ip(
        ip_type="xilinx.com:ip:axi_gpio:2.0",
        instance_name="axi_gpio_0",
        config={"CONFIG.C_GPIO_WIDTH": "8"}
    )
    
    # 应用自动连接
    await gf.apply_bd_automation("all")
    
    # 验证设计
    validate_result = await gf.validate_bd_design()
    if validate_result["success"]:
        print("Block Design 验证通过")
        
        # 生成 Wrapper
        await gf.generate_bd_wrapper()
        
        # 运行综合和实现
        await gf.run_synthesis()
        await gf.run_implementation()
        result = await gf.generate_bitstream()
        print(f"比特流: {result['bitstream_path']}")

asyncio.run(block_design_project())
```

### 示例 3: 使用 IP 核

```python
import asyncio
from gateflow import GateFlow

async def ip_project():
    gf = GateFlow()
    
    # 创建项目
    await gf.create_project(
        name="clock_demo",
        path="./projects/clock_demo",
        part="xc7a35tcpg236-1"
    )
    
    # 创建 Block Design
    await gf.create_bd_design("system")
    
    # 添加 Clock Wizard
    await gf.add_bd_ip(
        ip_type="xilinx.com:ip:clk_wiz:6.0",
        instance_name="clk_wiz_0",
        config={
            "CONFIG.PRIM_IN_FREQ": "100.0",
            "CONFIG.CLKOUT1_REQUESTED_OUT_FREQ": "50.0",
            "CONFIG.CLKOUT2_REQUESTED_OUT_FREQ": "200.0",
        }
    )
    
    # 添加其他 IP...
    await gf.apply_bd_automation()
    await gf.validate_bd_design()
    await gf.generate_bd_wrapper()
    
    # 构建流程
    await gf.run_synthesis()
    await gf.run_implementation()
    result = await gf.generate_bitstream()

asyncio.run(ip_project())
```

## 错误处理

所有 API 方法都返回包含 `success` 字段的字典，建议使用以下模式处理错误：

```python
result = await gf.run_synthesis()

if result["success"]:
    print("操作成功")
    # 处理成功结果
else:
    print(f"操作失败: {result.get('error', '未知错误')}")
    # 处理错误
```

## IP 版本兼容性

不同 Vivado 版本包含不同版本的 IP 核，使用时需要注意版本匹配：

| Vivado 版本 | processing_system7 版本 | 其他常用 IP 版本 |
|------------|------------------------|-----------------|
| 2023.1     | 5.5                   | axi_gpio:2.0  |
| 2023.2     | 5.5                   | axi_gpio:2.0  |
| 2024.1     | 5.7                   | axi_gpio:2.0  |
| 2024.2     | 5.7                   | axi_gpio:2.0  |

**使用建议：**
- 查看 Vivado 中 IP 核的实际版本号
- 在 `add_bd_ip` 方法中使用正确的版本号
- 如果不确定版本号，可以使用 `get_ip_version` 命令查询

## 迁移指南

### 从 v0.x 迁移到 v1.0

#### 事件循环冲突修复

**问题：** 在 Jupyter Notebook 或已有 event loop 的环境中，使用同步属性访问会导致异常：

```python
# ❌ 旧版本（v0.x）- 在 Jupyter 中会崩溃
gf = GateFlow()
clock_mgr = gf.clock_manager  # RuntimeError: This event loop is already running
```

**解决方案：** 改用异步方法：

```python
# ✅ 新版本（v1.0）- 在所有环境中都能正常工作
async def main():
    gf = GateFlow()
    clock_mgr = await gf.get_clock_manager()
    irq_mgr = await gf.get_interrupt_manager()
```

#### API 变更对照表

| 旧版本（v0.x） | 新版本（v1.0） | 说明 |
|--------------|--------------|------|
| `gf.clock_manager` | `await gf.get_clock_manager()` | 获取时钟管理器 |
| `gf.interrupt_manager` | `await gf.get_interrupt_manager()` | 获取中断管理器 |

#### 完整迁移示例

**旧代码：**
```python
from gateflow import GateFlow

gf = GateFlow()
# 同步访问属性
clock_mgr = gf.clock_manager
irq_mgr = gf.interrupt_manager
```

**新代码：**
```python
import asyncio
from gateflow import GateFlow

async def main():
    gf = GateFlow()
    # 异步获取管理器
    clock_mgr = await gf.get_clock_manager()
    irq_mgr = await gf.get_interrupt_manager()

asyncio.run(main())
```

#### 在 Jupyter Notebook 中使用

在 Jupyter Notebook 中，可以直接使用 `await`：

```python
# Jupyter Notebook 环境
gf = GateFlow()

# 直接使用 await（Jupyter 原生支持）
clock_mgr = await gf.get_clock_manager()
irq_mgr = await gf.get_interrupt_manager()

# 后续操作
await gf.create_project("my_proj", "./projects", "xc7a35tcpg236-1")
```

## 最佳实践

### 1. 项目组织

```python
# 使用清晰的目录结构
project_structure = {
    "src/": "源文件",
    "constraints/": "约束文件",
    "sim/": "仿真文件",
    "ip/": "IP 核配置"
}
```

### 2. 约束管理

```python
# 先创建时钟约束
await gf.create_clock("clk_main", 10.0, "clk")

# 再添加 IO 约束
xdc_content = """
set_property PACKAGE_PIN E3 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
"""
await gf.create_constraint_file("pins.xdc", xdc_content)
```

### 3. 构建流程

```python
# 分步执行并检查结果
synth_result = await gf.run_synthesis()
if not synth_result["success"]:
    print("综合失败，请检查设计")
    return

# 检查资源利用率
util = await gf.get_utilization_report()
if util["utilization"]["slice_lut"]["utilization"] > 80:
    print("警告: LUT 使用率超过 80%")

# 继续实现
impl_result = await gf.run_implementation()
if impl_result["success"]:
    # 检查时序
    timing = await gf.get_timing_report()
    if not timing["timing"]["timing_met"]:
        print("时序违例，需要优化设计")
```

### 4. 使用上下文管理器

```python
from gateflow import GateFlow

async def build_project():
    # GateFlow 会自动管理连接
    gf = GateFlow()
    
    try:
        await gf.create_project("my_proj", "./projects", "xc7a35tcpg236-1")
        # ... 其他操作
    finally:
        # 清理资源
        await gf.close_project()
```

## 调试技巧

### 启用日志

```python
import logging

# 启用 GateFlow 调试日志
logging.basicConfig(level=logging.DEBUG)
```

### 检查引擎状态

```python
from gateflow import get_engine_manager

manager = get_engine_manager()
info = manager.get_mode_info()
print(f"引擎模式: {info['mode']}")
print(f"连接状态: {info['is_connected']}")
```

## 相关资源

- [CLI 使用指南](CLI_USAGE.md)
- [Block Design 模块文档](block_design_module.md)
- [示例项目](../examples/)
- [GitHub 仓库](https://github.com/Firo718/GateFlow)
