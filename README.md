# GateFlow

<p align="center">
  <a href="https://github.com/Firo718/GateFlow/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
  <a href="https://github.com/Firo718/GateFlow/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Firo718/GateFlow/ci.yml?branch=main" alt="CI"></a>
</p>

<p align="center">
  <strong>AI-assisted MCP server and Python SDK for AMD Vivado FPGA workflows.</strong>
</p>

<p align="center">
  面向 Claude、Cursor 等 AI 工具的 Vivado FPGA 自动化接口，覆盖项目创建、约束、综合、实现、仿真、硬件调试与 Block Design。
</p>

> Status: `0.1.0` alpha. Current primary platform is Windows. Vivado-dependent workflows require a local Vivado installation.

<p align="center">
  <strong>开源的 AI 辅助 Vivado FPGA 开发 MCP 服务器</strong>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> -
  <a href="#快速开始">快速开始</a> -
  <a href="#使用指南">使用指南</a> -
  <a href="#mcp-工具列表">MCP 工具列表</a> -
  <a href="#贡献指南">贡献指南</a>
</p>

---

## 简介

GateFlow 是一个开源的 MCP (Model Context Protocol) 服务器，让 AI 编程工具能够操控 AMD (Xilinx) Vivado FPGA 开发软件。通过自然语言交互，完成从项目创建到比特流生成的完整 FPGA 开发流程。

### 为什么选择 GateFlow?

- **自然语言驱动**: 无需记忆复杂的 Tcl 命令，用自然语言描述需求即可
- **AI 原生设计**: 专为 AI 编程助手优化，支持 Claude、Cursor、Trae 等主流 AI 工具
- **完整工作流**: 覆盖 FPGA 开发的全流程，从项目创建到硬件编程
- **开源免费**: MIT 许可证，完全开源，社区驱动

## 功能特性

- **项目管理** - 创建、打开、配置 Vivado 项目
- **源文件管理** - 添加 Verilog/VHDL 源文件和约束文件
- **综合与实现** - 运行综合、实现，生成比特流
- **时序约束** - 创建时钟约束、IO 延迟、时序例外
- **硬件编程** - 连接硬件服务器，编程 FPGA
- **IP 配置** - 配置 Clocking Wizard、FIFO、BRAM 等 IP
- **Block Design** - 创建和管理 Block Design
- **仿真支持** - 行为仿真、Testbench 管理
- **报告分析** - 资源利用率、时序、功耗报告

## 系统要求

- Python 3.10+
- Vivado 2018.1+ (需要添加到 PATH 或设置 XILINX_VIVADO 环境变量)
- Windows 10/11 (Linux 支持计划中)

## 快速开始

### 安装

```bash
# 使用 pip 安装
pip install gateflow

# 或使用 uv 安装
uv tool install gateflow
```

### 安装后配置

安装完成后，如果提示 `gateflow` 命令找不到，请将以下路径添加到系统 PATH：

Windows:
```
C:\Users\<用户名>\AppData\Local\Python\pythoncore-3.14-64\Scripts
```

或使用完整路径运行：
```bash
C:\Users\<用户名>\AppData\Local\Python\pythoncore-3.14-64\Scripts\gateflow.exe
```

### 配置 AI 工具

#### Claude Desktop

编辑配置文件 `~/AppData/Roaming/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "gateflow": {
      "command": "gateflow"
    }
  }
}
```

#### Cursor

在设置中添加 MCP 服务器配置:

```json
{
  "mcp.servers": {
    "gateflow": {
      "command": "gateflow"
    }
  }
}
```

### 验证安装

```bash
# 检查 GateFlow 是否正确安装
gateflow --version

# 诊断环境与连接配置
gateflow doctor

# 检查当前连接状态
gateflow status

# 生成能力清单（docs/CAPABILITIES.md + docs/CAPABILITIES.json）
gateflow capabilities --write
```

发布前的用户视角验证请参考 [docs/RELEASE_TEST_PLAN.md](docs/RELEASE_TEST_PLAN.md)。
从“AI 协助人类做 FPGA 开发”的完整真实路径测试，请参考 [docs/AI_FPGA_REAL_USAGE_TEST_PLAN.md](docs/AI_FPGA_REAL_USAGE_TEST_PLAN.md)。

### 安装自检与 ASCII 输出

- `gateflow install` 结束前会自动执行安装后自检：
  - `import gateflow.cli`
  - `gateflow --version`
  - 当前解释器的导入路径校验
- 如果你是在 repo 中做 editable install，CLI 会同时输出：
  - 当前实际导入路径
  - 预期工作目录
- 适合 Windows 重定向、日志归档和自动化的纯 ASCII 输出模式：

```bash
set GATEFLOW_ASCII_OUTPUT=1
gateflow status
gateflow doctor --json
```

- `gateflow doctor --json` 现在会额外给出分层的 `tcl_server` 状态字段，便于区分：
  - 已配置但未注入 `Vivado_init.tcl`
  - TCP 已可运行但安装不完整
  - 端口被其他协议占用

### GUI 模式开关

如果你希望 GateFlow 工作时自动启动并使用 Vivado GUI 会话，可以开启 GUI 模式：

```bash
set GATEFLOW_GUI_ENABLED=1
set GATEFLOW_GUI_TCP_PORT=10124
```

此时默认工作流会优先选择：

1. `gui_session`
2. 常规 TCP
3. subprocess

也可以显式使用 CLI：

```bash
gateflow gui open F:/path/to/project.xpr --port 10124
gateflow gui status
gateflow gui close
```

Python API 也支持显式切换：

```python
gf = GateFlow(gui_enabled=True, gui_tcp_port=10124)
await gf.open_project_gui("F:/path/to/project.xpr")
```

### 使用示例

在 AI 工具中直接使用自然语言:

```
"帮我创建一个 Artix-7 项目，目标器件是 xc7a35tcpg236-1"
"添加 top.v 源文件并设置为顶层模块"
"创建一个 100MHz 的时钟约束"
"运行综合并查看资源利用率报告"
"连接硬件服务器并编程 FPGA"
```

## 使用指南

GateFlow 提供两种使用方式：

1. **MCP 工具** - 通过 AI 助手（Claude、Cursor 等）使用自然语言控制
2. **Python SDK** - 直接在 Python 代码中使用 API

### Python SDK

查看 [Python SDK 文档](docs/PYTHON_SDK.md) 了解如何在 Python 代码中使用 GateFlow API。

```python
import asyncio
from gateflow import GateFlow

async def main():
    gf = GateFlow()
    await gf.create_project("my_proj", "./projects", "xc7a35tcpg236-1")
    await gf.run_synthesis()
    result = await gf.generate_bitstream()
    print(f"比特流: {result['bitstream_path']}")

asyncio.run(main())
```

### FPGA 型号格式

GateFlow 使用 Vivado 标准器件型号格式：`<家族><型号><封装><速度等级>`

**正确格式示例**：
- `xc7z020clg484-2` (Zynq-7000)
- `xc7a35tcpg236-1` (Artix-7)
- `xc7k325tffg900-2` (Kintex-7)

**错误格式示例**：
- `xc7z020-2clg484i` (速度等级位置错误)
- `xc7z020-2clg484` (缺少速度等级)

### 基本工作流程

#### 1. 创建项目

```
创建一个名为 "led_blink" 的项目，目标器件 xc7a35tcpg236-1，保存在 D:/projects/led_blink
```

#### 2. 添加源文件

```
添加 Verilog 源文件 top.v 和约束文件 top.xdc
将 top 模块设置为顶层模块
```

#### 3. 添加约束

```
创建一个 100MHz 的时钟约束，目标端口为 clk
设置 LED 输出引脚约束
```

#### 4. 综合与实现

```
运行综合
查看资源利用率报告
运行实现
生成比特流
```

#### 5. 硬件编程

```
连接本地硬件服务器
获取设备列表
编程 FPGA
```

### 进阶用法

#### 使用 IP 核

```
创建一个 Clocking Wizard IP，输入 100MHz，输出 50MHz 和 200MHz
创建一个 32位宽、2048深度的 FIFO
创建一个双端口 BRAM，深度 4096
```

#### Block Design

```
创建一个名为 system 的 Block Design
添加 Zynq Processing System IP
添加 AXI GPIO IP
自动连接所有接口
验证设计并生成 HDL Wrapper
```

#### 仿真

```
创建仿真集 sim_1，添加 testbench.v
设置仿真顶层模块为 tb_top
启动行为仿真，运行 1ms
添加波形信号 clk 和 data
```

## MCP 工具列表

GateFlow 的真实工具面以运行时注册结果为准，不再在 README 中手工维护整份工具表。

单一事实来源：
- [docs/CAPABILITIES.md](docs/CAPABILITIES.md)
- [docs/CAPABILITIES.json](docs/CAPABILITIES.json)
- `gateflow capabilities --write`

高频能力示例：
- 项目与构建：`create_project`、`add_source_files`、`run_synthesis_async`、`run_full_flow`
- 报告与检查：`get_utilization_report`、`get_timing_report`、`check_drc`、`check_methodology`
- 仿真调试：`compile_simulation`、`elaborate_simulation`、`launch_simulation`、`probe_signal`、`add_force_signal`
- 硬件调试运行时：`list_hardware_targets`、`set_probe_file`、`hw_ila_run`、`hw_vio_get_input`、`hw_axi_read`
- Block Design 高频模板：`bd_create_zynq_gpio_uart_bram_system`、`bd_create_zynq_gpio_uart_timer_dma_system`

最小可运行示例：
- [examples/README.md](examples/README.md)
- [examples/simple_project.py](examples/simple_project.py)
- [examples/build_zed_led_tcp.py](examples/build_zed_led_tcp.py)
- [examples/report_checks_example.py](examples/report_checks_example.py)
- [examples/simulation_debug_example.py](examples/simulation_debug_example.py)
- [examples/zynq_template_example.py](examples/zynq_template_example.py)
- [examples/hardware_debug_runtime_example.py](examples/hardware_debug_runtime_example.py)

## 项目结构

```
gateflow/
├── src/gateflow/
│   ├── server.py           # MCP 服务器入口
│   ├── vivado/             # Vivado 交互模块
│   │   ├── tcl_engine.py   # Tcl 执行引擎
│   │   ├── project.py      # 项目管理
│   │   ├── synthesis.py    # 综合
│   │   ├── implementation.py # 实现
│   │   ├── constraints.py  # 约束管理
│   │   ├── hardware.py     # 硬件编程
│   │   ├── ip_config.py    # IP 配置
│   │   ├── block_design.py # Block Design
│   │   └── simulation.py   # 仿真支持
│   ├── tools/              # MCP 工具
│   │   ├── project_tools.py
│   │   ├── build_tools.py
│   │   ├── constraint_tools.py
│   │   ├── hardware_tools.py
│   │   ├── ip_tools.py
│   │   ├── block_design_tools.py
│   │   └── simulation_tools.py
│   └── utils/              # 工具函数
│       └── parser.py
├── tests/                  # 测试文件
├── examples/               # 示例项目
│   ├── simple_project.py   # 简单项目示例
│   └── blink_led/          # LED 闪烁示例
└── docs/                   # 文档
```

## 示例项目

### 简单项目创建

查看 [examples/simple_project.py](examples/simple_project.py) 了解如何使用 GateFlow 创建基本项目。

### LED 闪烁示例

查看 [examples/blink_led/](examples/blink_led/) 目录，包含完整的 LED 闪烁项目示例:

- `blink_led.v` - Verilog 源码
- `blink_led.xdc` - 约束文件
- `build.py` - 构建脚本

## 故障排除

### Tcl Server 启动失败

如果运行 `start_server.bat` 时出现错误，请检查：
1. Vivado 是否正确安装
2. Vivado 版本是否为 2018.1 或更高
3. 是否有权限访问 Vivado 安装目录
4. `start_server.bat` / `tcl_server.tcl` 属于手动启动链路，会保持 Tcl 会话存活，这与 `Vivado_init.tcl` 的自动注入行为不同
5. 不要把手动 `tcl_server.tcl` 直接复制到 `%APPDATA%/Xilinx/Vivado/Vivado_init.tcl`，自动注入版本必须是非阻塞的，否则 Vivado GUI 可能启动卡死

### 命令找不到

如果 `gateflow` 命令找不到，请参考"安装后配置"章节。

### Vivado 检测失败

如果 `gateflow status` 显示未检测到 Vivado，请手动指定路径：
```bash
gateflow install F:\Xilinx\Vivado\2023.1
```

## 常见问题

### Q: GateFlow 支持哪些 Vivado 版本?

A: GateFlow 支持 Vivado 2018.1 及以上版本。推荐使用 Vivado 2020.1 或更高版本以获得最佳体验。

### Q: 如何设置 Vivado 环境变量?

A: 有两种方式:

1. 将 Vivado 添加到系统 PATH:
   ```bash
   # Windows (PowerShell)
   $env:Path += ";C:\Xilinx\Vivado\2023.1\bin"
   ```

2. 设置 XILINX_VIVADO 环境变量:
   ```bash
   # Windows (PowerShell)
   $env:XILINX_VIVADO = "C:\Xilinx\Vivado\2023.1"
   ```

### Q: GateFlow 支持 Linux 吗?

A: 目前 GateFlow 主要支持 Windows 平台。Linux 支持正在开发中，预计在下一个版本中提供。

### Q: 如何调试 GateFlow?

A: 可以通过设置日志级别来调试:

```bash
# 设置调试模式
set GATEFLOW_DEBUG=1
gateflow
```

### Q: GateFlow 与传统 Tcl 脚本有什么区别?

A: GateFlow 提供了更高级的抽象，让 AI 工具能够理解 FPGA 开发流程。同时，GateFlow 生成的 Tcl 命令可以导出，方便与传统流程集成。

## 贡献指南

欢迎贡献! 请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/Firo718/GateFlow.git
cd gateflow

# 安装开发依赖
pip install -e ".[dev]"

# 运行测试
pytest tests/

# 代码格式化
ruff format src/
```

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 致谢

- 感谢 Xilinx/AMD 提供的 Vivado 工具链
- 感谢 MCP 协议团队提供的优秀框架

## 联系方式
- 电子邮箱: levelup718@126.com
- 项目主页: https://github.com/Firo718/GateFlow

---

<p align="center">
  Made with love by the GateFlow Team
</p>
