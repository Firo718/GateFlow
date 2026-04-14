# GateFlow Agent 使用复盘与避坑指南

## 最新结论（含 TCP 实测）

- `subprocess/batch`：稳定，适合“尽快拿到 bit”场景。
- `TCP`：可以跑通，但前提是服务端必须是 **GateFlow 协议兼容的 tcl_server**。
- 本项目已在 `2026-04-08` 实测跑通 TCP 全流程（创建工程、综合、实现、生成 bit）。

## 本次 TCP 跑通记录

- 使用端口：`10099`
- 运行方式：手动执行 `vivado -mode tcl -source %USERPROFILE%\.gateflow\tcl_server.tcl`
- GateFlow 强制模式：`EngineMode.TCP`
- 结果：
- `create_project` 成功
- `run_synthesis` 成功
- `run_implementation` 成功
- `generate_bitstream` 成功

输出 bit：
- `manual_runs/zed_led_blink/build_output_tcp/zed_led_blink_tcp.runs/impl_1/zed_led_blink.bit`

## 关键坑点与解决方案

### 1. `9999` 端口虽通，但命令持续超时

现象：
- TCP 已连接，但 `puts` / `create_project` 一直超时。

根因：
- 连接到的是其他 Tcl/MCP 服务，不是 GateFlow 期望的 TCP 协议实现。

解决：
- 不要复用 `9999`，改用独立端口（如 `10099`）启动 GateFlow 的 `tcl_server.tcl`。
- 先做健康检查：`expr 1+2` 返回 `OK: 3` 再跑大流程。

### 2. GateFlow CLI 在 Windows `gbk` 控制台崩溃

现象：
- `gateflow install` 因 emoji 输出触发 `UnicodeEncodeError`。

现状：
- CLI 现在支持纯 ASCII 输出模式，优先用于重定向、日志归档和自动化。

解决：
- 设置：`GATEFLOW_ASCII_OUTPUT=1`
- 如需进一步稳妥，也可以同时设置：`PYTHONIOENCODING=utf-8`

### 3. `install` 提示已完成，但 `Vivado_init.tcl` 自动写入失败

现象：
- 日志含：`'VivadoInfo' object has no attribute 'init_tcl_path'`。

现状：
- 这个历史问题已经修复。
- 现在应优先看 `gateflow doctor --json` 中的分层 `tcl_server` 字段，而不是只看单一“已安装/未安装”。

若仍未自动注入：
- 这表示“运行态可能正常，但自动注入未完成”，不是旧版本那种误报。
- 可继续使用手动启动：
- `C:\Xilinx\Vivado\2023.1\bin\vivado.bat -mode tcl -source %USERPROFILE%\.gateflow\tcl_server.tcl`
- 要区分两种脚本形态：
- `Vivado_init.tcl` 中的自动注入必须是非阻塞的，只负责启动服务。
- `tcl_server.tcl` 的手动 `-source` 版本可以保持 Tcl 会话存活。
- 不要把包含 `vwait forever` 的手动脚本直接写入 `Vivado_init.tcl`，否则 Vivado GUI 可能卡在启动阶段。

### 4. TCP 默认超时太短导致误判失败

现象：
- `create_project` 等长命令在 30s 默认超时。

解决：
- 运行前提高超时：
- `GATEFLOW_TIMEOUT_SINGLE_COMMAND=600`
- `GATEFLOW_TIMEOUT_BATCH_TOTAL=3600`

### 5. Windows 路径转义

现象：
- Tcl 解析路径异常。

解决：
- 统一使用正斜杠路径（`F:/...`）。
- 或使用 `normalize_path(...)`。

### 6. 沙箱环境导致 Vivado 临时文件删除失败

现象：
- `.hdi.isWriteableTest.*` 删除失败，项目创建失败。

解决：
- 在受限沙箱中可能失败，需在允许删除临时文件的环境执行 Vivado。

## 推荐执行顺序（给智能体）

1. 先确认目标：只要 bit 就优先 `subprocess`；需要交互再用 `TCP`。
2. 若用 TCP：先启动 GateFlow 兼容 `tcl_server`（建议独立端口）。
3. 用小命令做健康检查（如 `expr 1+2`）确认协议通。
4. 把超时调大后再跑综合/实现/写 bit。
5. 成功判据用双条件：命令成功 + `.bit` 文件存在。

## 本次相关文件

- 复盘文档：`docs/AGENT_PITFALLS.md`
- TCP 构建脚本：`manual_runs/zed_led_blink/build_zed_led_tcp.py`
- 非 TCP 构建脚本：`manual_runs/zed_led_blink/build_zed_led.py`
- TCP 服务脚本（安装生成）：`%USERPROFILE%\.gateflow\tcl_server.tcl`

### 对 GateFlow 的可执行改进建议

1. 增加 `preflight` 命令：一次性检查 License/端口/协议匹配/Vivado 状态，并给出可复制修复命令。
2. TCP 默认策略加入“协议探测”：端口可连但协议不匹配时，明确提示“可能连到其他 Tcl/MCP 服务”。
3. 提供新手工具清单（10-20 个）与“全量工具”分层展示，降低学习成本。
4. 将 CLI 输出改为纯 ASCII 可选模式，避免 Windows `gbk` 控制台异常。

## 已修复项

- `doctor` 在 `TCP listener + protocol` 已经正常时，不再把整体状态误报为“未安装”。
- `install` 结束前会执行安装后自检，而不是只输出“脚本已生成”。
- CLI 已支持 `GATEFLOW_ASCII_OUTPUT=1`。
