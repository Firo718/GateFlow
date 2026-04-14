# GateFlow 改进 Sprint 计划

基于 Cursor AI 的分析报告，制定以下 Sprint 安排，覆盖所有改进项目。

---

## Sprint A：安全边界 + 协议统一（P0 高优先级）

**目标**：把最容易出事故的能力加上硬边界，统一 TCP 协议

| 任务 | 说明 | 影响文件 |
|------|------|----------|
| M1-1 文件工具沙箱 | 约束文件操作到白名单目录，危险操作需显式开关 | `tools/file_tools.py` |
| M1-2 Tcl 执行分级 | `execute_tcl` 标为高级工具，默认约束危险命令 | `tools/tcl_tools.py` |
| M1-3 TCP 协议统一 | 编写 `docs/TCP_PROTOCOL.md`，统一 prompt/OK/ERROR 格式 | `tcp_client.py`, `cli.py` |
| M1-4 Tcl Server 收敛 | 统一生成/安装逻辑，避免两套实现漂移 | `cli.py`, `tcl_server.py` |

**验收标准**：
- [ ] 文件操作默认拒绝白名单外路径
- [ ] Tcl 执行有策略控制
- [ ] TCP 协议文档与实现一致
- [ ] install/uninstall 可逆

---

## Sprint B：执行层稳定性 + SDK 规范化（P0 高优先级）

**目标**：降低卡死/超时/会话失效概率，修复事件循环冲突

| 任务 | 说明 | 影响文件 |
|------|------|----------|
| M2-3 SDK 事件循环修复 | 移除 `@property` 内的 `run_until_complete` | `api.py` |
| M2-2 TCP 断线/超时恢复 | 定义断线后行为，增加 request_id | `tcp_client.py`, `engine.py` |
| M2-1 Engine 超时语义统一 | 统一单命令/批量超时含义 | `engine.py` |

**验收标准**：
- [ ] Jupyter 环境下 SDK 不崩溃
- [ ] 断线后可恢复或给出清晰错误
- [ ] 超时行为文档化

---

## Sprint C：配置统一 + 诊断工具（P1 中优先级）

**目标**：统一配置来源，降低使用门槛

| 任务 | 说明 | 影响文件 |
|------|------|----------|
| M3-1 统一配置系统 | 使用 `pydantic-settings` 管理所有配置 | `cli.py`, `engine.py`, `tools/*` |
| M3-2 gateflow doctor | 一键诊断 Vivado/端口/权限等问题 | `cli.py` |
| M1-5 安全策略配置入口 | 集中管理沙箱 roots、Tcl policy 等 | 新增 `settings.py` |

**验收标准**：
- [ ] 配置可通过环境变量/文件/CLI 参数覆盖
- [ ] `gateflow doctor` 输出可复制的修复建议

---

## Sprint D：项目化基础（P1 中优先级）

**目标**：建立清晰的基线和规范

| 任务 | 说明 | 影响文件 |
|------|------|----------|
| M0-1 能力清单梳理 | 列出所有 MCP tools，标注风险等级 | `docs/` |
| M2-4 错误模型统一 | 统一返回结构字段命名 | `tcl_engine.py`, `tcp_client.py` |
| M3-3 CI 分层跨平台 | 增加 Linux job，分层跑测试 | `.github/workflows/ci.yml` |

**验收标准**：
- [ ] 文档列出所有工具及风险等级
- [ ] 错误返回结构一致
- [ ] Linux CI 跑通纯 Python 测试

---

## Sprint E：可延后项（P2 低优先级）

**目标**：锦上添花的改进

| 任务 | 说明 | 影响文件 |
|------|------|----------|
| M0-2 术语规范 | 统一错误/警告/返回值术语 | `docs/` |
| M3-4 Tools 注册开关 | 按配置开关危险工具 | `server.py` |

**验收标准**：
- [ ] 术语文档化
- [ ] 可按配置禁用工具

---

## 执行顺序

```
Sprint A (1-2周) → Sprint B (1-2周) → Sprint C (1周) → Sprint D (1周) → Sprint E (可选)
```

## 风险与回滚

每个 Sprint 的具体风险和回滚方案见各任务的 Issue 模板。

---

*计划创建时间: 2026-03-11*
