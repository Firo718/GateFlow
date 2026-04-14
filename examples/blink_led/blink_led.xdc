##
## LED 闪烁项目约束文件
##
## 目标器件: xc7a35tcpg236-1 (Artix-7 35T CPG236 封装)
## 开发板: 通用 Artix-7 开发板 (可根据实际开发板修改引脚约束)
##

## ============================================================================
## 时钟约束
## ============================================================================

## 创建 100MHz 主时钟 (周期 10ns)
create_clock -name clk -period 10.000 [get_ports clk]

## 时钟不确定性 (可根据实际情况调整)
set_clock_uncertainty -setup 0.100 [get_clocks clk]
set_clock_uncertainty -hold  0.050 [get_clocks clk]

## ============================================================================
## 引脚约束
## ============================================================================

## 时钟引脚 (根据实际开发板修改)
## 示例: 使用 E3 引脚 (常见于 Artix-7 开发板)
set_property PACKAGE_PIN E3 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]

## 复位引脚 (根据实际开发板修改)
## 示例: 使用 C12 引脚
set_property PACKAGE_PIN C12 [get_ports rst_n]
set_property IOSTANDARD LVCMOS33 [get_ports rst_n]

## LED 引脚 (根据实际开发板修改)
## 示例: 使用 H5 引脚
set_property PACKAGE_PIN H5 [get_ports led]
set_property IOSTANDARD LVCMOS33 [get_ports led]

## ============================================================================
## 时序约束
## ============================================================================

## 输入延迟约束 (复位信号)
set_input_delay -clock clk -max 2.000 [get_ports rst_n]
set_input_delay -clock clk -min 0.500 [get_ports rst_n]

## 输出延迟约束 (LED 信号)
set_output_delay -clock clk -max 2.000 [get_ports led]
set_output_delay -clock clk -min 0.500 [get_ports led]

## ============================================================================
## 综合策略
## ============================================================================

## 保持层次结构 (便于调试)
set_property KEEP_HIERARCHY soft [get_cells *]

## 使用 DSP 切片 (如果需要)
# set_property USE_DSP yes [get_cells *]

## ============================================================================
## 实现策略
## ============================================================================

## 设置实现策略
# set_property strategy "Performance_Explore" [get_runs impl_1]

## ============================================================================
## 其他约束
## ============================================================================

## 禁用未使用的端口优化 (防止优化掉调试信号)
# set_property DONT_TOUCH yes [get_cells counter_reg]

## 配置比特流属性
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]

## ============================================================================
## 注释说明
## ============================================================================

## 常见 Artix-7 开发板引脚参考:
##
## Nexys A7-100T:
##   - 时钟: E3 (100MHz)
##   - CPU_RESET: C12 (复位按钮)
##   - LED[0]: H5
##
## Basys 3:
##   - 时钟: W5 (100MHz)
##   - CPU_RESET: U18 (复位按钮)
##   - LED[0]: U16
##
## Arty A7:
##   - 时钟: E3 (100MHz)
##   - RESET: C2 (复位按钮)
##   - LED[0]: H5
##
## 请根据实际使用的开发板修改上述引脚约束。
