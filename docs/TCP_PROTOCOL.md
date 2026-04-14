# GateFlow TCP 协议规范

## 概述

本文档定义了 GateFlow 与 Vivado Tcl Server 之间的 TCP 通信协议。该协议用于实现 AI 工具与 Vivado 的实时交互。

**版本**: 1.0  
**最后更新**: 2026-03-12

## 架构

```
AI Tool <--MCP--> GateFlow <--TCP:9999--> Vivado (tcl_server)
```

## 编码

- **字符编码**: UTF-8
- **行结束符**: `\n` (LF, Unix 风格)
- **二进制传输**: 不支持，所有数据均为文本

## 命令格式

### 发送命令

客户端发送的每条命令必须满足以下格式：

```
<command>\n
```

**规则**：
- 命令以换行符 `\n` 结尾
- 命令内容为有效的 Tcl 语法
- 空命令（仅 `\n`）将被忽略

**示例**：
```
puts "Hello Vivado"\n
current_project\n
create_project my_project ./my_project\n
```

## 响应格式

### 单行响应

服务器执行命令后，返回以下格式的响应：

**成功响应**：
```
OK: <result>\n
% \n
```

**失败响应**：
```
ERROR: <error_message>\n
% \n
```

**示例**：
```
OK: my_project\n
% \n
```

```
ERROR: invalid command name "unknown_cmd"\n
% \n
```

### 多行响应

当命令返回多行结果时，格式如下：

```
<line1>\n
<line2>\n
...
<lineN>\n
OK: <summary>\n
% \n
```

或错误时：

```
<line1>\n
<line2>\n
...
ERROR: <error_message>\n
% \n
```

**示例**：
```
Processing IP: clk_wiz\n
Processing IP: axi_gpio\n
OK: 2 IPs processed\n
% \n
```

## 提示符

### 定义

提示符用于标识命令执行完成，客户端应等待提示符以判断响应结束。

**格式**: `% \n`

**特征**：
- 以 `%` 字符开头
- 后跟一个空格
- 以换行符 `\n` 结尾
- 整行匹配正则表达式：`^%\s*$`

### 客户端识别

客户端应使用以下正则表达式识别提示符：

```python
PROMPT_PATTERN = re.compile(r'^%\s*$', re.MULTILINE)
```

**注意**：部分 Vivado 版本可能使用 `#` 作为提示符，因此客户端应同时支持：

```python
PROMPT_PATTERN = re.compile(r'^[%#]\s*$', re.MULTILINE)
```

## 超时设置

### 默认超时

| 操作类型 | 默认超时 | 说明 |
|---------|---------|------|
| 连接超时 | 30 秒 | 建立 TCP 连接的超时时间 |
| 单命令超时 | 30 秒 | 执行单个 Tcl 命令的超时时间 |
| 批量命令超时 | 可配置 | 建议设置为 `单命令超时 × 命令数量` |

### 超时处理

客户端在超时后应：
1. 关闭当前连接
2. 清理接收缓冲区
3. 返回超时错误给调用方
4. 可选：尝试自动重连

## 错误处理

### 错误类型

#### 1. 命令执行错误

服务器返回的错误信息格式：

```
ERROR: <error_message>\n
% \n
```

常见错误模式：
- `ERROR: invalid command name "xxx"`
- `ERROR: wrong # args: should be ...`
- `ERROR: can't read "xxx": no such variable`

#### 2. 连接错误

客户端应处理的连接错误：
- **连接被拒绝**: 服务器未启动或端口错误
- **连接超时**: 网络问题或服务器无响应
- **连接重置**: 服务器意外关闭
- **读取不完整**: 连接中断

#### 3. 解析错误

客户端在解析响应失败时应：
1. 返回原始响应数据
2. 提供详细的错误信息
3. 不应抛出未捕获的异常

### 错误响应格式

客户端应返回统一的错误响应结构：

```python
@dataclass
class TclResponse:
    success: bool          # 是否成功
    result: str           # 执行结果（成功时）
    error: str | None     # 错误信息（失败时）
    execution_time: float # 执行时间（秒）
    raw_output: str       # 原始输出
    warnings: list[str]   # 警告信息列表
```

## 警告信息

服务器可能在响应中包含警告信息：

```
WARNING: <warning_message>\n
OK: <result>\n
% \n
```

客户端应：
1. 提取所有警告信息
2. 不影响成功/失败判断
3. 在响应对象中包含警告列表

**警告识别正则表达式**：
```python
WARNING_PATTERN = re.compile(r'^WARNING:\s*(.+)$', re.MULTILINE)
```

## 连接管理

### 连接生命周期

```
1. 客户端发起连接
2. 服务器接受连接
3. 命令-响应循环
4. 客户端或服务器关闭连接
```

### 重连机制

客户端应实现自动重连机制：

**参数**：
- 最大重连次数：5 次（可配置）
- 重连延迟：2 秒（可配置）
- 重连延迟策略：固定延迟或指数退避

**重连触发条件**：
- 连接意外断开
- 执行命令时连接错误
- 心跳检测失败

### 心跳机制

为保持连接活跃，客户端可定期发送心跳命令：

**心跳命令**: `puts "heartbeat"` 或 `expr 1`

**心跳间隔**: 30 秒（可配置）

**心跳失败处理**: 尝试重连

## 完整示例

### 示例 1: 简单命令

**客户端发送**：
```
puts "Hello Vivado"\n
```

**服务器响应**：
```
OK: Hello Vivado\n
% \n
```

### 示例 2: 获取项目信息

**客户端发送**：
```
current_project\n
```

**服务器响应**：
```
OK: my_project\n
% \n
```

### 示例 3: 错误命令

**客户端发送**：
```
unknown_command\n
```

**服务器响应**：
```
ERROR: invalid command name "unknown_command"\n
% \n
```

### 示例 4: 多行输出

**客户端发送**：
```
get_ips\n
```

**服务器响应**：
```
clk_wiz_0\n
axi_gpio_0\n
axi_uart_0\n
OK: 3 IPs found\n
% \n
```

### 示例 5: 带警告的命令

**客户端发送**：
```
create_project my_project ./my_project\n
```

**服务器响应**：
```
WARNING: Project directory already exists\n
OK: my_project\n
% \n
```

## 协议版本兼容性

### 版本标识

客户端可通过以下命令查询协议版本：

```
set ::gateflow_protocol_version\n
```

**响应**：
```
OK: 1.0\n
% \n
```

### 向后兼容

- 客户端应支持 `%` 和 `#` 两种提示符
- 服务器应保持响应格式的一致性
- 新增字段不应破坏现有解析逻辑

## 安全考虑

### 当前实现

- 仅支持本地连接（localhost）
- 无身份验证机制
- 无加密传输

### 生产环境建议

- 使用防火墙限制端口访问
- 仅允许可信的客户端连接
- 考虑添加身份验证机制
- 考虑使用 TLS 加密传输

## 实现检查清单

### 服务器端

- [ ] 所有响应以 `OK:` 或 `ERROR:` 开头
- [ ] 响应后发送提示符 `% \n`
- [ ] 正确处理多行输出
- [ ] 正确编码 UTF-8 字符
- [ ] 正确处理异常和错误

### 客户端

- [ ] 正确识别提示符（支持 `%` 和 `#`）
- [ ] 正确解析 `OK:` 和 `ERROR:` 响应
- [ ] 提取警告信息
- [ ] 实现超时机制
- [ ] 实现重连机制
- [ ] 处理连接异常
- [ ] 返回原始响应数据

## 参考资料

- [Tcl 语言文档](https://www.tcl.tk/man/)
- [Vivado Tcl 命令参考](https://docs.xilinx.com/r/en-US/ug835-vivado-tcl-commands)
- [TCP Socket 编程](https://docs.python.org/3/library/asyncio-protocol.html)

## 变更历史

| 版本 | 日期 | 变更内容 |
|-----|------|---------|
| 1.0 | 2026-03-12 | 初始版本，定义基础协议规范 |
