# GateFlow 术语规范

本文档定义了 GateFlow 项目中使用的统一术语和命名规范，确保代码、文档和 API 的一致性。

## 核心概念术语表

### 项目与工程

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **Project** | Project | Vivado 工程 | `my_project.xpr` | 使用 "项目" 而非 "工程" |
| **项目名称** | project_name | 项目的名称标识 | `my_project` | 参数名统一使用 `name` 或 `project_name` |
| **项目路径** | project_path | 项目保存的目录路径 | `D:/projects/my_project` | 参数名统一使用 `path` |
| **器件型号** | part | FPGA 目标器件型号 | `xc7a35tcpg236-1` | 参数名统一使用 `part` |

### Block Design

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **Block Design** | Block Design | 图形化设计环境 | `system.bd` | 统一使用 "Block Design" |
| **设计名称** | design_name | Block Design 的名称 | `system` | 参数名使用 `name` 或 `design_name` |
| **IP 实例** | IP Instance | IP 核的实例化 | `axi_gpio_0` | 使用 "实例" 而非 "实例化" |
| **实例名称** | instance_name | IP 实例的名称 | `gpio_0` | 参数名统一使用 `instance_name` |
| **IP 类型** | ip_type | IP 核的类型标识 | `axi_gpio` | 简称或完整 VLNV |
| **VLNV** | VLNV | IP 的完整标识 | `xilinx.com:ip:axi_gpio:2.0` | Vendor:Library:Name:Version |

### 端口与连接

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **端口** | Port | Block Design 的外部接口 | `clk`, `rst_n` | - |
| **端口名称** | port_name | 端口的标识符 | `clk` | 参数名使用 `name` 或 `port_name` |
| **端口方向** | direction | 端口的数据流向 | `input`, `output`, `inout` | - |
| **引脚** | Pin | IP 实例的接口点 | `gpio_0/gpio_io_o` | 格式：`instance/pin` |
| **接口引脚** | Interface Pin | 接口类型的引脚 | `axi_gpio_0/S_AXI` | 用于 AXI 等接口连接 |
| **连接** | Connection | 端口或引脚间的连线 | - | - |
| **源端口** | source | 连接的起始端 | `clk_wiz_0/clk_out1` | 参数名使用 `source` |
| **目标端口** | target | 连接的目的端 | `gpio_0/s_axi_aclk` | 参数名使用 `target` |

### 约束与时序

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **约束** | Constraint | 设计约束规则 | - | 包括时序、IO、面积约束 |
| **约束文件** | Constraint File | XDC 约束文件 | `constraints.xdc` | - |
| **时钟约束** | Clock Constraint | 时钟定义约束 | `create_clock` | - |
| **时钟名称** | clock_name | 时钟的标识符 | `clk_100m` | 参数名使用 `name` 或 `clock_name` |
| **时钟周期** | period | 时钟周期（纳秒） | `10.0` | 100MHz = 10ns |
| **目标端口** | target | 约束应用的目标 | `clk` | 参数名使用 `target` |

### 构建流程

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **综合** | Synthesis | RTL 到网表的转换 | `synth_1` | - |
| **实现** | Implementation | 网表到比特流的流程 | `impl_1` | - |
| **比特流** | Bitstream | FPGA 配置文件 | `top.bit` | - |
| **运行名称** | run_name | 综合/实现的运行标识 | `synth_1`, `impl_1` | 参数名使用 `run_name` |
| **并行任务数** | jobs | 并行执行的进程数 | `4` | 参数名使用 `jobs` |

### 文件与路径

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **源文件** | Source File | 设计源代码文件 | `top.v`, `module.vhd` | - |
| **文件类型** | file_type | 文件的格式类型 | `verilog`, `vhdl`, `xdc` | 参数名使用 `file_type` |
| **文件列表** | files | 文件路径的列表 | `["top.v", "module.v"]` | 参数名使用 `files` |
| **顶层模块** | top_module | 设计的顶层实体 | `top` | 参数名使用 `module_name` 或 `top_module` |

### 硬件与仿真

| 术语 | 英文 | 定义 | 示例 | 说明 |
|------|------|------|------|------|
| **硬件服务器** | Hardware Server | Vivado 硬件服务器 | `localhost:3121` | - |
| **设备** | Device | FPGA 硬件设备 | `xc7a35t_0` | - |
| **编程** | Program | 配置 FPGA | - | 使用 "编程" 而非 "烧录" |
| **仿真** | Simulation | 功能验证过程 | - | - |
| **仿真集** | Simulation Set | 仿真的配置集合 | `sim_1` | - |

## 返回值结构规范

### 统一返回结构

所有工具和 API 的返回值都应使用统一的 `Result` 结构：

#### 成功返回

```json
{
  "success": true,
  "data": {
    // 返回的数据内容
  },
  "warnings": ["可选的警告信息"],
  "execution_time": 0.123,
  "request_id": "abc12345"
}
```

#### 错误返回

```json
{
  "success": false,
  "error": {
    "code": 2001,
    "code_name": "COMMAND_FAILED",
    "message": "Tcl 命令执行失败",
    "details": {
      "command": "create_project",
      "error_output": "..."
    },
    "suggestion": "请检查 Tcl 命令语法",
    "request_id": "abc12345"
  },
  "execution_time": 0.123,
  "request_id": "abc12345"
}
```

### 错误码分类

错误码按照以下规则分类：

| 范围 | 分类 | 说明 |
|------|------|------|
| 1xxx | 连接错误 | 与 Vivado 连接相关的错误 |
| 2xxx | 执行错误 | Tcl 命令执行相关的错误 |
| 3xxx | 文件错误 | 文件操作相关的错误 |
| 4xxx | Tcl 错误 | Tcl 安全策略相关的错误 |
| 5xxx | 项目错误 | 项目管理相关的错误 |
| 6xxx | 配置错误 | 配置相关的错误 |
| 7xxx | 引擎错误 | 执行引擎相关的错误 |

### 常用错误码

| 错误码 | 名称 | 说明 | 修复建议 |
|--------|------|------|----------|
| 1001 | CONNECTION_FAILED | 无法连接到 Vivado | 确认 Vivado 已启动 |
| 1002 | CONNECTION_TIMEOUT | 连接超时 | 检查网络或增加超时时间 |
| 2001 | COMMAND_FAILED | 命令执行失败 | 检查命令语法 |
| 2002 | COMMAND_TIMEOUT | 命令执行超时 | 增加超时时间 |
| 3001 | FILE_NOT_FOUND | 文件不存在 | 确认文件路径正确 |
| 3003 | FILE_SANDBOX_VIOLATION | 文件访问违反沙箱规则 | 使用沙箱允许的路径 |
| 4001 | TCL_POLICY_VIOLATION | Tcl 命令违反安全策略 | 避免使用危险命令 |
| 5001 | PROJECT_NOT_FOUND | 项目不存在 | 确认项目路径正确 |
| 5002 | PROJECT_ALREADY_EXISTS | 项目已存在 | 使用不同的项目名称 |

## 命名规范

### 函数命名

使用动词前缀 + 名词的形式：

| 前缀 | 用途 | 示例 |
|------|------|------|
| `create_*` | 创建资源 | `create_project`, `create_bd_design` |
| `get_*` | 获取资源 | `get_project_info`, `get_bd_cells` |
| `set_*` | 设置属性 | `set_top_module`, `set_bd_cell_property` |
| `delete_*` | 删除资源 | `delete_bd_cell`, `delete_bd_port` |
| `remove_*` | 移除资源 | `remove_ip`, `remove_bd_cell` |
| `open_*` | 打开资源 | `open_project`, `open_bd_design` |
| `close_*` | 关闭资源 | `close_project`, `close_bd_design` |
| `save_*` | 保存资源 | `save_bd_design` |
| `validate_*` | 验证资源 | `validate_bd_design` |
| `generate_*` | 生成资源 | `generate_bitstream`, `generate_bd_wrapper` |
| `run_*` | 运行流程 | `run_synthesis`, `run_implementation` |
| `add_*` | 添加资源 | `add_source_files`, `add_bd_ip` |
| `connect_*` | 连接资源 | `connect_bd_ports`, `connect_hw_server` |
| `apply_*` | 应用规则 | `apply_bd_automation` |
| `list_*` | 列出资源 | `list_ips`, `list_platforms` |
| `find_*` | 查找资源 | `find_ip` |

### 参数命名

使用下划线分隔的小写形式：

| 参数名 | 用途 | 示例 |
|--------|------|------|
| `name` | 资源名称 | `name="my_project"` |
| `path` | 文件或目录路径 | `path="./projects"` |
| `part` | FPGA 器件型号 | `part="xc7a35tcpg236-1"` |
| `instance_name` | IP 实例名称 | `instance_name="gpio_0"` |
| `ip_type` | IP 类型 | `ip_type="axi_gpio"` |
| `module_name` | 模块名称 | `module_name="top"` |
| `files` | 文件列表 | `files=["top.v", "module.v"]` |
| `file_type` | 文件类型 | `file_type="verilog"` |
| `timeout` | 超时时间（秒） | `timeout=3600` |
| `jobs` | 并行任务数 | `jobs=4` |
| `run_name` | 运行标识 | `run_name="synth_1"` |
| `clock_name` | 时钟名称 | `clock_name="clk_100m"` |
| `period` | 时钟周期 | `period=10.0` |
| `target` | 目标对象 | `target="clk"` |
| `source` | 源对象 | `source="gpio_0/gpio_io_o"` |
| `direction` | 端口方向 | `direction="input"` |
| `width` | 位宽 | `width=8` |
| `config` | 配置字典 | `config={"C_GPIO_WIDTH": 8}` |

### 变量命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 类名 | 大驼峰命名 | `GateFlow`, `ProjectManager` |
| 函数名 | 小写下划线 | `create_project`, `get_bd_cells` |
| 变量名 | 小写下划线 | `project_name`, `instance_name` |
| 常量 | 全大写下划线 | `MAX_TIMEOUT`, `DEFAULT_PORT` |
| 私有变量 | 单下划线前缀 | `_engine`, `_project_manager` |
| 私有方法 | 单下划线前缀 | `_get_engine()`, `_ensure_initialized()` |

### 类属性命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 公共属性 | 小写下划线 | `self.project_path`, `self.vivado_path` |
| 私有属性 | 单下划线前缀 | `self._engine`, `self._ip_registry` |
| 属性访问器 | 小写下划线 | `@property def project_path(self)` |

## 文档术语规范

### 中文术语对照

| 英文术语 | 中文术语 | 错误用法 |
|----------|----------|----------|
| Project | 项目 | 工程、工程文件 |
| Block Design | Block Design | 块设计、模块设计 |
| IP Instance | IP 实例 | IP 实例化、IP 核实例 |
| Instance Name | 实例名称 | 实例名、实例化名称 |
| Port | 端口 | 接口、引脚 |
| Pin | 引脚 | 管脚、针脚 |
| Connection | 连接 | 连线、网线 |
| Constraint | 约束 | 限制、限制条件 |
| Synthesis | 综合 | 综合、编译 |
| Implementation | 实现 | 实现、布局布线 |
| Bitstream | 比特流 | 位流、配置文件 |
| Simulation | 仿真 | 模拟 |
| Program (FPGA) | 编程 | 烧录、下载、配置 |

### 文档标题规范

- 使用清晰的层级结构（最多 4 级）
- 标题使用中文，代码块使用英文
- 示例代码使用完整的代码块
- 参数说明使用表格形式

## 术语检查工具

GateFlow 提供术语检查工具，用于检查代码和文档中的术语使用是否规范：

```python
from gateflow.utils.terminology import check_terminology, TerminologyChecker

# 检查文本中的术语
issues = check_terminology("创建一个工程文件")
# 返回: ["应使用 '项目' 而非 '工程'"]

# 使用检查器进行批量检查
checker = TerminologyChecker()
issues = checker.check_file("docs/README.md")
issues = checker.check_directory("src/gateflow")
```

### 常见术语问题

| 错误用法 | 正确用法 | 说明 |
|----------|----------|------|
| 工程名称 | 项目名称 | 使用 "项目" 而非 "工程" |
| 工程路径 | 项目路径 | - |
| IP 实例化 | IP 实例 | "实例" 是名词，"实例化" 是动词 |
| 烧录 FPGA | 编程 FPGA | 使用 "编程" 而非 "烧录" |
| 下载比特流 | 编程 FPGA | - |
| 管脚约束 | 引脚约束 | 使用 "引脚" 而非 "管脚" |
| 时钟频率 | 时钟周期 | 参数使用周期（纳秒），频率用于描述 |

## API 文档规范

### 函数文档字符串格式

```python
async def create_project(
    name: str,
    path: str,
    part: str,
) -> dict[str, Any]:
    """
    创建新项目
    
    Args:
        name: 项目名称
        path: 项目保存路径
        part: 目标器件型号
    
    Returns:
        创建结果字典，包含：
        - success: 是否成功
        - project: 项目信息
        - message: 结果消息
    
    Raises:
        ValueError: 参数无效时抛出
        ConnectionError: 连接失败时抛出
    
    Example:
        ```python
        result = await gf.create_project(
            name="my_project",
            path="./projects",
            part="xc7a35tcpg236-1"
        )
        ```
    """
```

### 参数说明规范

- 使用完整的句子描述参数用途
- 说明参数的取值范围或格式
- 提供默认值说明（如果有）
- 标注可选参数

### 返回值说明规范

- 使用字典结构说明返回值
- 列出所有可能的字段
- 说明字段的数据类型
- 提供示例返回值

## 版本兼容性

本术语规范适用于 GateFlow v1.0 及以上版本。对于早期版本的迁移，请参考：

- [Python SDK 文档](PYTHON_SDK.md) - API 迁移指南
- [CHANGELOG.md](../CHANGELOG.md) - 版本变更记录

## 参考资源

- [Vivado Design Suite 用户指南](https://docs.xilinx.com)
- [AMD Xilinx 术语表](https://docs.xilinx.com/r/en-US/ug892-vivado-design-flows-overview)
- [Python 命名规范 (PEP 8)](https://peps.python.org/pep-0008/)

---

**维护者**: GateFlow 团队  
**最后更新**: 2026-03-12  
**版本**: 1.0.0
