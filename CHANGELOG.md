# Changelog

All notable changes to GateFlow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Linux support (planned)
- Power analysis tools (planned)
- More IP core support (planned)

### Changed

- `gateflow install` now runs post-install self-checks for `import gateflow.cli`,
  `gateflow --version`, and import-path sanity in editable installs.
- `gateflow doctor --json` now exposes layered `tcl_server` fields including
  `config_present`, `script_present`, `startup_script_present`,
  `vivado_init_present`, `vivado_init_contains_gateflow`, `tcp_listener_ok`,
  `tcp_protocol_ok`, and `effective_runtime_ok`.
- CLI commands `install`, `status`, `doctor`, and `capabilities` now support a
  pure ASCII output mode via `GATEFLOW_ASCII_OUTPUT=1`.
- High-frequency Python API coverage now includes DRC/methodology/power reports,
  simulation debug helpers, hardware debug helpers, and a minimal
  `export_xsa` / `build_standalone_elf` software-closure path.

## [0.1.0] - 2026-03-03

### Added

#### Core Features

- **MCP Server Implementation**
  - FastMCP-based server architecture
  - Async Tcl execution engine
  - Comprehensive error handling and logging

#### Project Management Tools (5 tools)

- `create_project` - Create new Vivado projects
- `open_project` - Open existing Vivado projects
- `add_source_files` - Add source files (Verilog, VHDL, XDC, etc.)
- `set_top_module` - Set top-level module
- `get_project_info` - Get current project information

#### Build Tools (5 tools)

- `run_synthesis` - Run synthesis flow
- `run_implementation` - Run implementation flow
- `generate_bitstream` - Generate bitstream file
- `get_utilization_report` - Get resource utilization report
- `get_timing_report` - Get timing analysis report

#### Constraint Management Tools (9 tools)

- `create_clock` - Create clock constraints
- `create_generated_clock` - Create generated clock constraints
- `set_input_delay` - Set input delay constraints
- `set_output_delay` - Set output delay constraints
- `set_false_path` - Set false path constraints
- `set_multicycle_path` - Set multicycle path constraints
- `get_clocks` - Get all clock constraints
- `read_xdc` - Read XDC constraint files
- `write_xdc` - Write XDC constraint files

#### Hardware Programming Tools (6 tools)

- `connect_hw_server` - Connect to hardware server
- `disconnect_hw_server` - Disconnect from hardware server
- `get_hw_devices` - Get hardware device list
- `program_fpga` - Program FPGA device
- `refresh_hw_device` - Refresh device status
- `get_hw_server_status` - Get hardware server status

#### IP Configuration Tools (10 tools)

- `create_clocking_wizard` - Create Clocking Wizard IP
- `create_fifo` - Create FIFO Generator IP
- `create_bram` - Create Block Memory IP
- `create_axi_interconnect` - Create AXI Interconnect IP
- `create_zynq_ps` - Create Zynq Processing System IP
- `list_ips` - List all IPs in project
- `get_ip_info` - Get IP detailed information
- `upgrade_ip` - Upgrade IP to latest version
- `generate_ip_outputs` - Generate IP output products
- `remove_ip` - Remove IP from project

#### Block Design Tools (15 tools)

- `create_bd_design` - Create new Block Design
- `open_bd_design` - Open existing Block Design
- `close_bd_design` - Close current Block Design
- `save_bd_design` - Save current Block Design
- `add_bd_ip` - Add IP instance to Block Design
- `create_bd_port` - Create Block Design external port
- `connect_bd_ports` - Connect Block Design ports
- `apply_bd_automation` - Apply Block Design automation
- `validate_bd_design` - Validate Block Design
- `generate_bd_wrapper` - Generate HDL Wrapper
- `get_bd_cells` - Get all IP instances in Block Design
- `remove_bd_cell` - Remove IP instance from Block Design
- `set_bd_cell_property` - Set IP instance properties
- `get_bd_ports` - Get all ports in Block Design
- `get_bd_connections` - Get all connections in Block Design

#### Simulation Tools (11 tools)

- `set_simulator` - Set simulator type
- `create_simulation_set` - Create simulation set
- `add_simulation_files` - Add simulation files
- `set_simulation_top` - Set simulation top module
- `launch_simulation` - Launch simulation
- `run_simulation` - Run simulation
- `stop_simulation` - Stop simulation
- `restart_simulation` - Restart simulation
- `add_wave_signal` - Add waveform signal
- `get_simulation_status` - Get simulation status
- `export_simulation` - Export simulation scripts

### Documentation

- Comprehensive README with installation guide
- MCP tools reference documentation
- Usage examples and best practices
- LED blink example project
- Simple project creation example

### Testing

- Unit tests for all modules
- Integration tests for Tcl engine
- Test coverage for core functionality

### Dependencies

- Python 3.10+
- mcp[cli] >= 1.0.0
- pydantic >= 2.0.0

## [0.0.1] - 2026-02-01

### Added

- Initial project structure
- Basic MCP server setup
- Tcl engine prototype

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 0.1.0 | 2026-03-03 | First public release with 61 MCP tools |
| 0.0.1 | 2026-02-01 | Initial development version |

## Roadmap

### Version 0.2.0 (Planned)

- Linux platform support
- Power analysis tools
- More comprehensive error messages
- Performance optimizations

### Version 0.3.0 (Planned)

- Vivado 2024.x support
- Advanced timing analysis
- Design rule check (DRC) tools
- Report generation enhancements

### Version 1.0.0 (Future)

- Stable API
- Complete documentation
- Full test coverage
- Production-ready release

---

## How to Read This Changelog

### Categories

- **Added**: New features
- **Changed**: Changes to existing features
- **Deprecated**: Features to be removed
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security improvements

### Version Numbers

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

---

For more details about each release, see the [GitHub Releases](https://github.com/Firo718/GateFlow/releases) page.
