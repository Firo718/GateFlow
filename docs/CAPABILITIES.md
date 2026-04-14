# GateFlow MCP Tools Capability Manifest

This file is generated from the actual FastMCP tool registrations.
Do not edit it manually; regenerate it from `gateflow.capabilities`.

- Total tools: `169`

| Tool | Category | Risk | Vivado | Description |
|------|----------|------|--------|-------------|
| `add_bd_ip` | `block_design` | `NORMAL` | Yes | 向 Block Design 添加 IP 实例。 |
| `apply_bd_automation` | `block_design` | `NORMAL` | Yes | 应用 Block Design 自动连接。 |
| `bd_assign_addresses` | `block_design` | `NORMAL` | Yes | 自动分配 AXI 地址。 |
| `bd_check_output_status` | `block_design` | `NORMAL` | Yes | 检查输出状态。 |
| `bd_connect_ila_clock` | `block_design` | `NORMAL` | Yes | 连接 ILA 时钟。 |
| `bd_connect_ila_probe` | `block_design` | `NORMAL` | Yes | 连接 ILA 探针。 |
| `bd_connect_pins` | `block_design` | `NORMAL` | Yes | 连接两个引脚。 |
| `bd_create_axi_bram_ctrl_with_mem` | `block_design` | `NORMAL` | Yes | 创建 AXI BRAM Controller + Block Memory 组合。 |
| `bd_create_axi_gpio` | `block_design` | `NORMAL` | Yes | 创建 AXI GPIO IP。 |
| `bd_create_axi_timer` | `block_design` | `NORMAL` | Yes | 创建 AXI Timer IP。 |
| `bd_create_axi_uartlite` | `block_design` | `NORMAL` | Yes | 创建 AXI UART Lite IP。 |
| `bd_create_concat` | `block_design` | `NORMAL` | Yes | 创建 Concat IP（信号合并）。 |
| `bd_create_constant` | `block_design` | `NORMAL` | Yes | 创建 Constant IP。 |
| `bd_create_ila` | `block_design` | `NORMAL` | Yes | 创建 ILA (Integrated Logic Analyzer) IP。 |
| `bd_create_inverter` | `block_design` | `NORMAL` | Yes | 创建 Inverter IP（信号反相）。 |
| `bd_create_ps7` | `block_design` | `NORMAL` | Yes | 创建 Zynq PS7 IP 实例。 |
| `bd_create_slice` | `block_design` | `NORMAL` | Yes | 创建 Slice IP（信号切片）。 |
| `bd_create_vector_logic` | `block_design` | `NORMAL` | Yes | 创建 Vector Logic IP。 |
| `bd_create_vio` | `block_design` | `NORMAL` | Yes | 创建 VIO (Virtual Input/Output) IP。 |
| `bd_create_zynq_gpio_uart_bram_system` | `block_design` | `NORMAL` | Yes | 一键创建常见 Zynq 基础系统模板。 |
| `bd_create_zynq_gpio_uart_timer_dma_system` | `block_design` | `NORMAL` | Yes | 一键创建带 GPIO/UART/Timer/DMA 的 Zynq 系统模板。 |
| `bd_disconnect_net` | `block_design` | `NORMAL` | Yes | 断开网络连接。 |
| `bd_generate_output_and_wrapper` | `block_design` | `NORMAL` | Yes | 生成输出产品和 HDL Wrapper。 |
| `bd_get_address_map` | `block_design` | `NORMAL` | Yes | 获取地址映射表。 |
| `bd_get_ip_properties` | `block_design` | `NORMAL` | Yes | 获取 IP 属性。 |
| `bd_get_ps7_config` | `block_design` | `NORMAL` | Yes | 获取 PS7 当前配置。 |
| `bd_get_unconnected_pins` | `block_design` | `NORMAL` | Yes | 获取未连接的引脚列表。 |
| `bd_gpio_enable_interrupt` | `block_design` | `NORMAL` | Yes | 启用 GPIO 中断。 |
| `bd_gpio_set_direction` | `block_design` | `NORMAL` | Yes | 设置 GPIO 方向。 |
| `bd_gpio_set_width` | `block_design` | `NORMAL` | Yes | 设置 GPIO 位宽。 |
| `bd_list_interface_ports` | `block_design` | `NORMAL` | Yes | 列出所有接口端口。 |
| `bd_list_ip_interfaces` | `block_design` | `NORMAL` | Yes | 列出 IP 接口。 |
| `bd_list_ip_pins` | `block_design` | `NORMAL` | Yes | 列出 IP 引脚。 |
| `bd_list_ips` | `block_design` | `NORMAL` | Yes | 列出所有 IP 实例。 |
| `bd_list_nets` | `block_design` | `NORMAL` | Yes | 列出所有网络。 |
| `bd_list_ports` | `block_design` | `NORMAL` | Yes | 列出所有端口。 |
| `bd_list_ps7_presets` | `block_design` | `NORMAL` | Yes | 列出所有可用的 Zynq PS7 预设配置。 |
| `bd_make_intf_pin_external` | `block_design` | `NORMAL` | Yes | 将接口引脚导出为外部接口端口。 |
| `bd_make_pin_external` | `block_design` | `NORMAL` | Yes | 将引脚导出为外部端口。 |
| `bd_ps7_enable_axi_port` | `block_design` | `NORMAL` | Yes | 启用 PS7 的 AXI 端口。 |
| `bd_ps7_enable_gpio` | `block_design` | `NORMAL` | Yes | 启用 PS7 的 GPIO。 |
| `bd_ps7_enable_interrupt` | `block_design` | `NORMAL` | Yes | 启用 PS7 的 Fabric 中断 (IRQ_F2P)。 |
| `bd_ps7_enable_uart` | `block_design` | `NORMAL` | Yes | 启用 PS7 的 UART。 |
| `bd_ps7_set_fclk` | `block_design` | `NORMAL` | Yes | 设置 PS7 的 Fabric 时钟。 |
| `bd_regenerate_layout` | `block_design` | `NORMAL` | Yes | 重新生成布局。 |
| `bd_run_automation` | `block_design` | `NORMAL` | Yes | 运行 Block Design 自动化。 |
| `bd_uartlite_set_baudrate` | `block_design` | `NORMAL` | Yes | 设置 UART 波特率。 |
| `bd_validate_design` | `block_design` | `NORMAL` | Yes | 验证设计。 |
| `close_bd_design` | `block_design` | `NORMAL` | Yes | 关闭当前 Block Design。 |
| `connect_bd_ports` | `block_design` | `NORMAL` | Yes | 连接 Block Design 端口。 |
| `create_bd_design` | `block_design` | `NORMAL` | Yes | 创建新的 Block Design。 |
| `create_bd_port` | `block_design` | `NORMAL` | Yes | 创建 Block Design 外部端口。 |
| `generate_bd_wrapper` | `block_design` | `NORMAL` | Yes | 生成 Block Design HDL Wrapper。 |
| `get_bd_cells` | `block_design` | `SAFE` | Yes | 获取 Block Design 中的所有 IP 实例。 |
| `get_bd_connections` | `block_design` | `SAFE` | Yes | 获取 Block Design 中的所有连接。 |
| `get_bd_ports` | `block_design` | `SAFE` | Yes | 获取 Block Design 中的所有端口。 |
| `open_bd_design` | `block_design` | `NORMAL` | Yes | 打开现有的 Block Design。 |
| `remove_bd_cell` | `block_design` | `NORMAL` | Yes | 移除 Block Design 中的 IP 实例。 |
| `save_bd_design` | `block_design` | `NORMAL` | Yes | 保存当前 Block Design。 |
| `set_bd_cell_property` | `block_design` | `NORMAL` | Yes | 设置 Block Design IP 实例的属性。 |
| `validate_bd_design` | `block_design` | `NORMAL` | Yes | 验证 Block Design。 |
| `check_drc` | `build` | `SAFE` | Yes | 检查 DRC 报告并提取问题摘要。 |
| `check_methodology` | `build` | `SAFE` | Yes | 检查 methodology 报告并提取问题摘要。 |
| `generate_bitstream` | `build` | `NORMAL` | Yes | 生成比特流。 |
| `get_drc_report` | `build` | `SAFE` | Yes | 获取实现后的 DRC 报告。 |
| `get_methodology_report` | `build` | `SAFE` | Yes | 获取实现后的 methodology 报告。 |
| `get_power_report` | `build` | `SAFE` | Yes | 获取实现后的功耗报告。 |
| `get_run_messages` | `build` | `SAFE` | Yes | 从 run 日志中提取最近消息。 |
| `get_run_progress` | `build` | `SAFE` | Yes | 获取 run 的文本进度提示和最近已知 step。 |
| `get_run_status` | `build` | `SAFE` | Yes | 获取综合或实现 run 的当前状态。 |
| `get_timing_report` | `build` | `SAFE` | Yes | 获取时序报告。 |
| `get_utilization_report` | `build` | `SAFE` | Yes | 获取资源利用率报告。 |
| `launch_run` | `build` | `NORMAL` | Yes | 启动指定 run，但不等待完成。 |
| `lint_drc` | `build` | `NORMAL` | Yes | DRC lint 别名（等价于 check_drc）。 |
| `lint_methodology` | `build` | `NORMAL` | Yes | methodology lint 别名（等价于 check_methodology）。 |
| `run_full_flow` | `build` | `NORMAL` | Yes | 执行综合、实现和 bitstream 生成的完整流程。 |
| `run_implementation` | `build` | `NORMAL` | Yes | 运行实现。 |
| `run_implementation_async` | `build` | `NORMAL` | Yes | 启动实现但不等待完成。 |
| `run_synthesis` | `build` | `NORMAL` | Yes | 运行综合。 |
| `run_synthesis_async` | `build` | `NORMAL` | Yes | 启动综合但不等待完成。 |
| `wait_for_run` | `build` | `NORMAL` | Yes | 等待指定 run 完成，使用状态轮询而不是单次 wait_on_run。 |
| `create_clock` | `constraint` | `NORMAL` | Yes | 创建时钟约束。 |
| `create_generated_clock` | `constraint` | `NORMAL` | Yes | 创建派生时钟约束。 |
| `get_clocks` | `constraint` | `SAFE` | Yes | 获取所有时钟约束。 |
| `read_xdc` | `constraint` | `NORMAL` | Yes | 读取 XDC 约束文件。 |
| `set_false_path` | `constraint` | `NORMAL` | Yes | 设置虚假路径约束。 |
| `set_input_delay` | `constraint` | `NORMAL` | Yes | 设置输入延迟约束。 |
| `set_multicycle_path` | `constraint` | `NORMAL` | Yes | 设置多周期路径约束。 |
| `set_output_delay` | `constraint` | `NORMAL` | Yes | 设置输出延迟约束。 |
| `write_xdc` | `constraint` | `NORMAL` | Yes | 写入 XDC 约束文件。 |
| `append_file` | `file` | `NORMAL` | No | 追加内容到文件。 |
| `copy_file` | `file` | `NORMAL` | No | 复制文件。 |
| `create_directory` | `file` | `NORMAL` | No | 创建目录。 |
| `create_file` | `file` | `NORMAL` | No | 创建新文件。 |
| `delete_file` | `file` | `DANGEROUS` | No | 删除文件。 |
| `file_exists` | `file` | `SAFE` | No | 检查文件是否存在。 |
| `get_file_info` | `file` | `SAFE` | No | 获取文件信息。 |
| `list_files` | `file` | `SAFE` | No | 列出目录中的文件。 |
| `read_file` | `file` | `SAFE` | No | 读取文件内容。 |
| `write_file` | `file` | `DANGEROUS` | No | 写入文件（覆盖）。 |
| `connect_hw_server` | `hardware` | `NORMAL` | Yes | 连接硬件服务器。 |
| `disconnect_hw_server` | `hardware` | `NORMAL` | Yes | 断开硬件服务器连接。 |
| `get_hw_devices` | `hardware` | `SAFE` | Yes | 获取硬件设备列表。 |
| `get_hw_server_status` | `hardware` | `SAFE` | Yes | 获取硬件服务器状态。 |
| `hw_axi_list` | `hardware` | `NORMAL` | Yes | 列出当前硬件会话中的 AXI 调试接口。 |
| `hw_axi_read` | `hardware` | `NORMAL` | Yes | 通过硬件 AXI 调试接口读取寄存器/内存。 |
| `hw_axi_write` | `hardware` | `NORMAL` | Yes | 通过硬件 AXI 调试接口写寄存器/内存。 |
| `hw_ila_list` | `hardware` | `SAFE` | Yes | 列出当前硬件会话中的 ILA 核。 |
| `hw_ila_run` | `hardware` | `NORMAL` | Yes | 触发指定 ILA 核开始采集。 |
| `hw_ila_upload` | `hardware` | `NORMAL` | Yes | 上传指定 ILA 核的采集数据。 |
| `hw_vio_get_input` | `hardware` | `NORMAL` | Yes | 读取 VIO 输入探针值。 |
| `hw_vio_list` | `hardware` | `SAFE` | Yes | 列出当前硬件会话中的 VIO 核。 |
| `hw_vio_refresh` | `hardware` | `NORMAL` | Yes | 刷新指定 VIO 核。 |
| `hw_vio_set_output` | `hardware` | `NORMAL` | Yes | 设置 VIO 输出探针值并提交到硬件。 |
| `list_hardware_targets` | `hardware` | `SAFE` | Yes | 列出当前硬件服务器可见的硬件目标。 |
| `open_hardware_target` | `hardware` | `NORMAL` | Yes | 打开指定硬件目标。 |
| `program_fpga` | `hardware` | `NORMAL` | Yes | 编程 FPGA 设备。 |
| `quick_program` | `hardware` | `NORMAL` | Yes | 一键连接硬件服务器并下载 bitstream。 |
| `refresh_hw_device` | `hardware` | `NORMAL` | Yes | 刷新设备状态。 |
| `set_probe_file` | `hardware` | `NORMAL` | Yes | 将 .ltx 探针文件绑定到指定硬件设备。 |
| `create_axi_interconnect` | `ip` | `NORMAL` | Yes | 创建 AXI Interconnect IP。 |
| `create_bram` | `ip` | `NORMAL` | Yes | 创建 Block Memory IP。 |
| `create_clocking_wizard` | `ip` | `NORMAL` | Yes | 创建 Clocking Wizard IP。 |
| `create_fifo` | `ip` | `NORMAL` | Yes | 创建 FIFO Generator IP。 |
| `create_zynq_ps` | `ip` | `NORMAL` | Yes | 创建 Zynq Processing System IP。 |
| `generate_ip_outputs` | `ip` | `NORMAL` | Yes | 生成 IP 输出产品。 |
| `get_ip_info` | `ip` | `SAFE` | Yes | 获取 IP 详细信息。 |
| `list_ips` | `ip` | `SAFE` | Yes | 列出项目中的所有 IP。 |
| `remove_ip` | `ip` | `NORMAL` | Yes | 移除 IP。 |
| `upgrade_ip` | `ip` | `NORMAL` | Yes | 升级 IP 到最新版本。 |
| `add_source_files` | `project` | `NORMAL` | Yes | 添加源文件到当前项目。 |
| `create_project` | `project` | `NORMAL` | Yes | 创建新的 Vivado 项目。 |
| `get_project_info` | `project` | `SAFE` | Yes | 获取当前项目信息。 |
| `open_project` | `project` | `NORMAL` | Yes | 打开现有 Vivado 项目。 |
| `set_top_module` | `project` | `NORMAL` | Yes | 设置顶层模块。 |
| `add_force_signal` | `simulation` | `NORMAL` | Yes | 给仿真信号施加激励。 |
| `add_simulation_files` | `simulation` | `NORMAL` | Yes | 添加仿真文件。 |
| `add_wave_signal` | `simulation` | `NORMAL` | Yes | 添加波形信号。 |
| `compile_simulation` | `simulation` | `NORMAL` | Yes | 编译指定仿真集。 |
| `create_simulation_set` | `simulation` | `NORMAL` | Yes | 创建仿真集。 |
| `elaborate_simulation` | `simulation` | `NORMAL` | Yes | 对指定仿真集执行 elaboration。 |
| `export_simulation` | `simulation` | `NORMAL` | Yes | 导出仿真脚本。 |
| `get_signal_value` | `simulation` | `SAFE` | Yes | 读取仿真中指定信号的当前值。 |
| `get_simulation_status` | `simulation` | `SAFE` | Yes | 获取仿真状态。 |
| `launch_simulation` | `simulation` | `NORMAL` | Yes | 启动仿真。 |
| `list_simulation_sets` | `simulation` | `SAFE` | Yes | 列出工程中所有仿真集。 |
| `log_wave` | `simulation` | `NORMAL` | Yes | 启用波形记录。 |
| `probe_signal` | `simulation` | `NORMAL` | Yes | 将信号加入波形窗口，作为仿真 probe 入口。 |
| `remove_force_signal` | `simulation` | `NORMAL` | Yes | 移除仿真信号上的激励。 |
| `restart_simulation` | `simulation` | `NORMAL` | Yes | 重启仿真。 |
| `run_simulation` | `simulation` | `NORMAL` | Yes | 运行仿真。 |
| `set_simulation_time` | `simulation` | `NORMAL` | Yes | 设置仿真集的默认运行时间。 |
| `set_simulation_top` | `simulation` | `NORMAL` | Yes | 设置仿真顶层模块。 |
| `set_simulator` | `simulation` | `NORMAL` | Yes | 设置仿真器。 |
| `stop_simulation` | `simulation` | `NORMAL` | Yes | 停止仿真。 |
| `embedded_status` | `tcl` | `NORMAL` | Yes | 查询 embedded 非工程软件闭环模块状态。 |
| `evaluate_tcl_expression` | `tcl` | `NORMAL` | Yes | 计算 Tcl 表达式。 |
| `execute_tcl` | `tcl` | `DANGEROUS` | Yes | 执行自定义 Tcl 脚本。 |
| `execute_tcl_batch` | `tcl` | `DANGEROUS` | Yes | 批量执行 Tcl 脚本。 |
| `execute_tcl_file` | `tcl` | `DANGEROUS` | Yes | 执行 Tcl 脚本文件。 |
| `get_tcl_variable` | `tcl` | `NORMAL` | Yes | 获取 Tcl 变量值。 |
| `set_tcl_variable` | `tcl` | `NORMAL` | Yes | 设置 Tcl 变量值。 |
| `vitis_build_elf` | `tcl` | `NORMAL` | Yes | 编译 standalone app 并输出 `.elf`。 |
| `vitis_create_bsp` | `tcl` | `NORMAL` | Yes | 定位或创建 standalone app 对应 BSP。 |
| `vitis_create_standalone_app` | `tcl` | `NORMAL` | Yes | 基于 `.xsa` 创建 standalone app。 |
| `vitis_export_xsa` | `tcl` | `NORMAL` | Yes | 从已有 Vivado `.xpr` 导出最小 `.xsa`。 |
| `vitis_status` | `tcl` | `NORMAL` | Yes | 查询 Vitis/XSA 导出模块状态。 |
| `xsct_create_workspace` | `tcl` | `NORMAL` | Yes | 创建或准备 XSCT workspace 目录。 |
| `xsct_status` | `tcl` | `NORMAL` | Yes | 查询 XSCT 软件构建模块状态。 |
