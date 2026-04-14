# GateFlow CLI 使用指南

GateFlow 提供了功能完善的命令行接口（CLI），用于管理 Vivado 集成和启动 MCP 服务器。

## 安装

```bash
pip install gateflow
```

## 基本命令

### 查看版本

```bash
gateflow --version
```

输出：
```
GateFlow v0.1.0
```

### 启动 MCP 服务器

```bash
gateflow
```

这将启动 GateFlow MCP 服务器，AI 工具可以通过 MCP 协议与之交互。

### 查看帮助

```bash
gateflow --help
```

## 子命令

### install - 安装 Tcl Server

自动检测并安装 Tcl Server 到 Vivado：

```bash
gateflow install
```

指定 Vivado 安装路径：

```bash
gateflow install C:/Xilinx/Vivado/2024.1
```

指定 TCP 端口：

```bash
gateflow install --port 8888
```

**功能说明：**
- 自动检测系统中的 Vivado 安装
- 生成 Tcl Server 脚本（唯一权威实现）
- 尝试安装到 Vivado_init.tcl（Vivado 启动时自动加载）
- 创建独立启动脚本（方便手动启动）
- 保存配置信息到 `~/.gateflow/config.json`
- 在结束前执行安装后自检：
  - `import gateflow.cli`
  - `gateflow --version`
  - 当前解释器导入路径校验

**注意：**
- 某些环境下自动写入 `Vivado_init.tcl` 可能失败。
- 即使写入失败，也可以使用 `~/.gateflow/start_server.bat` 或手动 `-source ~/.gateflow/tcl_server.tcl` 正常运行。
- `Vivado_init.tcl` 中的 GateFlow 注入代码用于 Vivado GUI 自动加载，必须是非阻塞的。
- `~/.gateflow/tcl_server.tcl` 和 `start_server.bat` 用于手动 `-source` 启动，会保持当前 Tcl 会话存活，这是预期行为。
- 如果当前目录是 repo 根目录，安装后自检会额外输出：
  - 当前实际导入路径
  - 预期工作目录
- 安装后自检失败时，CLI 会直接给出可复制的修复建议：
  - `pip uninstall gateflow`
  - `pip install -e <repo-root>`

**安装位置：**
- Tcl Server 脚本：`~/.gateflow/tcl_server.tcl`
- 启动脚本：`~/.gateflow/start_server.bat`
- Vivado_init.tcl：`%APPDATA%/Xilinx/Vivado/Vivado_init.tcl`

**标记块机制：**
安装时会在 Vivado_init.tcl 中添加标记块：
```tcl
# ===== GateFlow Tcl Server BEGIN =====
# ... server script ...
# ===== GateFlow Tcl Server END =====
```

说明：
- 自动注入到 `Vivado_init.tcl` 的版本只负责启动 TCP 服务，不会在这里执行 `vwait forever`。
- 手动启动脚本 `~/.gateflow/tcl_server.tcl` 仍会保持 Tcl 会话存活，适合 `vivado -mode tcl -source ...`。
- 不要把手动脚本整段复制进 `Vivado_init.tcl`，否则 Vivado GUI 可能在启动阶段卡住。

**输出示例：**
``` 
============================================================
GateFlow Tcl Server 安装
============================================================

🔍 正在检测 Vivado 安装...
✓ 检测到 Vivado 2024.1
  路径: C:/Xilinx/Vivado/2024.1

📝 保存配置...

📦 创建 Tcl Server 脚本...
✓ Tcl Server 脚本已创建: C:\Users\YourName\.gateflow\tcl_server.tcl

📦 安装到 Vivado_init.tcl...
⚠ 安装到 Vivado_init.tcl 失败（可继续使用手动启动方式）

📦 创建启动脚本...
✓ 启动脚本已创建: C:\Users\YourName\.gateflow\start_server.bat

🔹 安装后自检:
  ✅ 导入 gateflow.cli: 当前解释器可以导入 gateflow.cli
  ✅ gateflow --version: gateflow --version 可运行
  ✅ 导入路径校验: 导入路径位于当前 Python 环境可接受的安装目录

============================================================
✓ 安装完成
============================================================

配置信息:
  Vivado 版本: 2024.1
  Vivado 路径: C:/Xilinx/Vivado/2024.1
  TCP 端口:    9999
  配置文件:    C:\Users\YourName\.gateflow\config.json

启动 Tcl Server:
  方式1: 启动 Vivado（自动加载 Tcl Server）
  方式2: C:\Users\YourName\.gateflow\start_server.bat

或手动启动:
  C:/Xilinx/Vivado/2024.1/bin/vivado.bat -mode tcl -source C:\Users\YourName\.gateflow\tcl_server.tcl

现在可以运行 'gateflow' 启动 MCP 服务器了!
```

**ASCII 模式：**

适合 Windows 重定向、日志归档和自动化。

```bash
set GATEFLOW_ASCII_OUTPUT=1
gateflow install
```

启用后会将 `✅/⚠/❌` 等字符改为 `[OK]/[WARN]/[FAIL]`。

### uninstall - 卸载 Tcl Server

卸载 GateFlow 配置和脚本：

```bash
gateflow uninstall
```

指定 Vivado 安装路径：

```bash
gateflow uninstall C:/Xilinx/Vivado/2024.1
```

**功能说明：**
- 从 Vivado_init.tcl 移除 Tcl Server（保留其他内容）
- 删除配置文件
- 删除 Tcl Server 脚本
- 删除启动脚本

**卸载特点：**
- 使用标记块机制，精准移除 GateFlow 代码
- 保留 Vivado_init.tcl 中的其他配置
- 可重复执行，不会出错

### status - 检查状态

检查 Vivado 安装和连接状态：

```bash
gateflow status
```

指定端口检查：

```bash
gateflow status --port 8888
```

**输出示例：**
```
============================================================
GateFlow 状态检查
============================================================

📋 配置信息:
  ✓ 配置文件: C:\Users\YourName\.gateflow\config.json
  ✓ Vivado 路径: C:/Xilinx/Vivado/2024.1
  ✓ TCP 端口: 9999

🔍 Vivado 安装检测:
  ✓ 检测到 Vivado 2024.1
  ✓ 安装路径: C:/Xilinx/Vivado/2024.1
  ✓ 可执行文件: C:/Xilinx/Vivado/2024.1/bin/vivado.bat

🔹 Tcl Server 分层状态:
  ✓ 配置文件: True
  ✓ tcl_server.tcl: True
  ✓ start_server.bat: True
  ✓ Vivado_init.tcl: True
  ✓ Vivado_init.tcl 包含 GateFlow 注入: False
  ✓ TCP 监听: True
  ✓ TCP 协议: True
  ✓ 有效运行态: True
  ✓ 总结: tcl_server 可运行，但 Vivado_init.tcl 未自动注入 GateFlow
    listener: 127.0.0.1:9999 正在监听
    protocol: 端口 9999 返回 GateFlow 协议响应

🔌 Vivado 连接测试:
  ✓ Vivado 连接正常
  ✓ 执行时间: 2.34秒

============================================================
```

`status` 不再只给出单一“已安装/未安装”结论，而是会展示以下分层字段：

- `config_present`
- `script_present`
- `startup_script_present`
- `vivado_init_present`
- `vivado_init_contains_gateflow`
- `tcp_listener_ok`
- `tcp_protocol_ok`
- `effective_runtime_ok`

如果 `tcp_listener_ok=true` 且 `tcp_protocol_ok=true`，CLI 不会再把整体状态误报成“未安装”。

### doctor - 诊断环境

```bash
gateflow doctor
gateflow doctor --json
gateflow doctor --port 10099
```

`doctor --json` 除了原有 `results` 外，还会额外输出一个 `tcl_server` 对象，便于 AI 或脚本区分：

- 已生成配置但还没自动注入 `Vivado_init.tcl`
- TCP 已经可运行，但安装不完整
- 端口被其他协议占用
- 当前 `doctor/status` 与真实运行态不一致

**ASCII 模式：**

```bash
set GATEFLOW_ASCII_OUTPUT=1
gateflow status
gateflow doctor --json
gateflow capabilities --write
```

### activate - 激活许可证

GateFlow 是开源软件，无需激活许可证：

```bash
gateflow activate your-key
```

**输出：**
```
============================================================
GateFlow 许可证激活
============================================================

ℹ GateFlow 是开源软件，无需激活许可证
  您可以直接使用所有功能

如果您购买了商业支持，请联系 support@gateflow.dev
```

### capabilities - 能力清单导出

基于真实运行时工具注册，输出或导出能力清单：

```bash
# 终端打印能力统计
gateflow capabilities

# JSON 打印完整 manifest
gateflow capabilities --json

# 写入 docs/CAPABILITIES.md 与 docs/CAPABILITIES.json
gateflow capabilities --write
```

可自定义输出路径：

```bash
gateflow capabilities --write \
  --markdown-path ./tmp/CAPABILITIES.md \
  --manifest-path ./tmp/CAPABILITIES.json
```

### runs - 查询和控制 Vivado run

`runs` 命令用于把 `launch_runs` 与等待/观察解耦，适合长时间综合、实现和 bitstream 阶段的可观测性需求。

```bash
gateflow runs launch synth_1 --jobs 4
gateflow runs wait synth_1 --timeout 3600 --poll-interval 2
gateflow runs status synth_1
gateflow runs progress impl_1
gateflow runs messages impl_1 --limit 50 --severity warning
```

输出至少包含：
- `run_name`
- `status`
- `status_source`
- `is_running`
- `is_complete`
- `is_failed`
- `last_known_step`
- `progress_hint`
- `artifacts`

如果 `launch_runs` 已成功提交但等待超时，CLI 会返回最后一次从 Vivado 读取到的状态快照，并使用 `run_wait_timeout` 表示“等待阶段失败”，而不是误报为“未启动”。

### gui - 启动或关闭 Vivado GUI 会话

GUI 命令用于显式切换到“Vivado GUI 可见”模式。该模式会启动一个新的 Vivado GUI 实例，自动加载 GateFlow 非阻塞 `tcl_server`，并让后续命令走同一 TCP 会话。

```bash
gateflow gui open F:/path/to/project.xpr --port 10124
gateflow gui attach --port 10124 F:/path/to/project.xpr
gateflow gui status
gateflow gui close
gateflow gui logs --tail 50
```

`gui open` 的目标不是连接任意已有 GUI，而是启动一个新的、由 GateFlow 管理的 GUI 会话。

`gui attach` 用于附着到一个已经运行、并且已经加载 GateFlow TCP server 的 Vivado GUI 会话。当前要求你显式提供 TCP 端口，不支持自动枚举或自动选择多个 GUI 实例。

### GUI 开关

如果你希望默认工作时开启 GUI，可使用环境变量：

```bash
set GATEFLOW_GUI_ENABLED=1
set GATEFLOW_GUI_TCP_PORT=10124
```

关闭 GUI 模式时：

```bash
set GATEFLOW_GUI_ENABLED=0
```

默认值：
- `GATEFLOW_GUI_ENABLED=0`
- `GATEFLOW_GUI_TCP_PORT=10099`

默认工作流选择顺序：

- 当 `GATEFLOW_GUI_ENABLED=1` 时：
  1. `gui_session`
  2. 常规 TCP
  3. subprocess
- 当 `GATEFLOW_GUI_ENABLED=0` 时：
  1. 常规 TCP
  2. subprocess

这意味着你不必每次都显式执行 `gateflow gui open`。如果启用了 GUI 开关，默认工作流会优先尝试复用或创建一个由 GateFlow 管理的 Vivado GUI 会话。

## 配置文件

配置文件位于 `~/.gateflow/config.json`，包含以下信息：

```json
{
  "vivado_path": "C:/Xilinx/Vivado/2024.1",
  "tcp_port": 9999
}
```

## 工作流程

### 1. 首次使用

```bash
# 1. 安装 Tcl Server（会尝试自动安装到 Vivado_init.tcl）
gateflow install

# 2. 启动 Vivado（Tcl Server 会自动加载）
# 或者使用独立启动脚本：
C:\Users\YourName\.gateflow\start_server.bat

# 3. 启动 MCP 服务器
gateflow
```

### 2. 日常使用

```bash
# 方式1: 启动 Vivado（Tcl Server 自动加载）
# 直接打开 Vivado 即可

# 方式2: 使用独立启动脚本
C:\Users\YourName\.gateflow\start_server.bat

# 启动 MCP 服务器
gateflow
```

### 3. 检查状态

```bash
# 检查配置和连接状态
gateflow status
```

### 4. 更新配置

```bash
# 更新端口或其他配置
gateflow uninstall
gateflow install --port 8888
```

## 详细日志

使用 `--verbose` 参数查看详细日志：

```bash
gateflow --verbose
gateflow install --verbose
gateflow status --verbose
```

## 故障排除

### Tcl Server 启动失败

如果运行 `start_server.bat` 时出现错误，请按以下步骤排查：

1. **检查 Vivado 安装**
   - 确认 Vivado 已正确安装
   - 确认 Vivado 版本为 2018.1 或更高
   - 确认有权限访问 Vivado 安装目录

2. **检查启动脚本**
   - 确认 `~/.gateflow/start_server.bat` 文件存在
   - 确认 `~/.gateflow/tcl_server.tcl` 文件存在
   - 尝试手动运行脚本查看详细错误信息

3. **检查端口占用**
   - 确认 TCP 端口（默认 9999）未被其他程序占用
   - 可以使用 `netstat -ano | findstr 9999` 检查端口状态
   - 如需更改端口，使用 `gateflow install --port <新端口>`

4. **重新安装**
   ```bash
   gateflow uninstall
   gateflow install
   ```

5. **手动启动测试**
   ```bash
   # 使用完整路径手动启动 Vivado Tcl 模式
   C:/Xilinx/Vivado/2024.1/bin/vivado.bat -mode tcl -source C:\Users\YourName\.gateflow\tcl_server.tcl
   ```

### 未检测到 Vivado

如果 `gateflow install` 未检测到 Vivado，请：

1. 确认 Vivado 已正确安装
2. 设置环境变量 `XILINX_VIVADO`：
   ```bash
   # Windows PowerShell
   $env:XILINX_VIVADO = "C:\Xilinx\Vivado\2024.1"

   # Linux/Mac
   export XILINX_VIVADO=/opt/Xilinx/Vivado/2024.1
   ```
3. 或手动指定路径：
   ```bash
   gateflow install C:/Xilinx/Vivado/2024.1
   ```

### 连接失败

如果 `gateflow status` 显示连接失败：

1. 确认 Tcl Server 正在运行
2. 检查端口是否被占用
3. 检查防火墙设置

### 清理配置

如果需要重新配置：

```bash
gateflow uninstall
gateflow install
```

## 开发者信息(待补充)

- **项目地址**: 
- **文档**: 
- **问题反馈**: 

## 许可证

GateFlow 是开源软件，采用 MIT 许可证。
