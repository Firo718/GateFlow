# GateFlow AI-FPGA Real-Usage Test Plan

## Goal

This plan validates GateFlow from the point of view of an AI assistant helping a human finish real FPGA work.

It focuses on full user journeys instead of isolated functions:

- install and diagnose GateFlow
- create and build a minimal RTL project
- create and build a ZedBoard PS+PL design
- inspect reports and lint findings
- run simulation debug flows
- connect hardware, bind probes, and inspect runtime debug endpoints
- recover from common failures with actionable hints

## Fixed Baselines

- Board: `ZedBoard`
- Device: `xc7z020clg484-1`
- Platform: Windows + Vivado
- Minimal project baseline: `examples/blink_led`
- PS+PL baseline: existing Zynq template tools
  - `bd_create_zynq_gpio_uart_bram_system`
  - `bd_create_zynq_gpio_uart_timer_dma_system`

External references are used only as human design sanity checks, not as runtime dependencies:

- Digilent ZedBoard user material and IPI onboarding path
- Xilinx UG940 Zynq embedded design flow guidance

## Test Layers

### L0 Environment and Preflight

- `gateflow --version`
- `gateflow install`
- `gateflow doctor --json`
- `gateflow status`
- `gateflow capabilities --write`
- verify install post-check output:
  - `import gateflow.cli`
  - `gateflow --version`
  - import path sanity / editable-install path disclosure
- verify layered `tcl_server` doctor fields:
  - `config_present`
  - `script_present`
  - `startup_script_present`
  - `vivado_init_present`
  - `vivado_init_contains_gateflow`
  - `tcp_listener_ok`
  - `tcp_protocol_ok`
  - `effective_runtime_ok`
- verify ASCII-safe CLI mode:
  - `GATEFLOW_ASCII_OUTPUT=1 gateflow status`
  - `GATEFLOW_ASCII_OUTPUT=1 gateflow doctor --json`
  - `GATEFLOW_ASCII_OUTPUT=1 gateflow capabilities --write`

### L1 Minimal RTL Project

Using `examples/blink_led`:

- `create_project`
- `add_source_files` for RTL and XDC
- `set_top_module`
- `run_synthesis`
- `run_implementation`
- `generate_bitstream`
- async status path: `run_synthesis_async`, `run_implementation_async`, `get_run_status`

### L2 ZedBoard PS+PL Flow

Using existing template tools:

- BRAM template path
- Timer/DMA template path
- `validate_bd_design`
- `generate_bd_wrapper`
- downstream synth / impl / bitstream

### L2 Reports and Checks

- `get_utilization_report`
- `get_timing_report`
- `get_power_report`
- `get_drc_report`
- `get_methodology_report`
- `check_drc`
- `check_methodology`

### L2 Simulation Debug

Using `examples/blink_led/tb_blink_led.v`:

- `create_simulation_set`
- `set_simulation_top`
- `compile_simulation`
- `elaborate_simulation`
- `launch_simulation`
- `probe_signal`
- `add_force_signal`
- `run_simulation`
- `get_signal_value`
- `remove_force_signal`
- failure classification must be explicit enough for AI recovery:
  - simulation not started
  - top not set
  - simulation set missing
  - `xvlog/xelab/xsim` invocation failed
  - TCP interaction failed

### L3 Hardware Debug and Recovery

When hardware exists:

- `connect_hw_server`
- `list_hardware_targets`
- `open_hardware_target`
- `quick_program` or `program_fpga`
- `set_probe_file`
- `hw_ila_*`
- `hw_vio_*`
- `hw_axi_*`

### L3 Minimal Software Closure

Using the `manual_runs/job1_zed_video` pattern:

- `export_xsa`
- `vitis_export_xsa`
- `xsct_create_workspace`
- `vitis_create_standalone_app`
- `vitis_create_bsp`
- `vitis_build_elf`
- `build_standalone_elf`

Expected artifacts:

- `xsa_path`
- `workspace_path`
- `bsp_path`
- `elf_path`
- `size_report_path`

Recovery paths:

- Vivado missing
- TCP port conflict
- TCP protocol mismatch
- bit/ltx missing
- board missing
- execution_context mismatch

## Execution

Core AI real-usage suite:

```bash
python -m pytest -m ai_real_usage
```

Release gate + AI real-usage:

```bash
python -m pytest -m "release_gate or ai_real_usage"
```

Hardware smoke:

```bash
python -m pytest tests/hardware_smoke -m "vivado and integration"
```

## Pass / Skip Policy

- AI real-usage tests must pass in release qualification environments.
- Hardware smoke is conditional:
  - board present: must pass
  - board absent: may skip, but skip reason must be explicit
- TCP lane may skip only if TCP environment is intentionally not configured.

## Manual Experience Checklist

- AI can follow README high-frequency prompts without internal repo knowledge.
- `doctor/status` gives copyable remediation for TCP mismatch, Vivado missing, and port issues.
- Reports are structured enough for the AI to explain next steps.
- Hardware failures are distinguishable from build/report failures.
