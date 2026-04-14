# GateFlow Release Test Plan

This document defines the user-facing release gate for GateFlow.

## Goal

GateFlow must be validated as a real user would use it:

- first install and diagnosis
- project creation and build flow
- report and lint inspection
- simulation debug flow
- block design template flow
- hardware debug runtime flow

## Test Layers

### Must Pass

Run on every release candidate:

```bash
python -m pytest -m release_gate
```

Coverage:

- CLI diagnostics: `--version`, `doctor --json`, `status`, `capabilities --write`
- Build flow: subprocess flow, and TCP flow when TCP env is configured
- Report snapshots: utilization, timing, power, drc, methodology
- Runtime example smoke: TCP build, reports, simulation debug, hardware debug, BD templates

### Hardware Conditional

Run when hardware is available:

```bash
python -m pytest tests/hardware_smoke -m "vivado and integration"
```

Required environment:

- `GATEFLOW_HW_SMOKE_ENABLE=1`
- `GATEFLOW_HW_SERVER_URL`
- `GATEFLOW_HW_BITSTREAM`
- `GATEFLOW_HW_PROBE`
- optional: `GATEFLOW_HW_TARGET`

If hardware is absent, tests must be reported as `skipped` with the exact reason.

### Manual Experience Regression

Manual checklist for release notes sign-off:

- `doctor/status` gives copyable remediation for Vivado missing, TCP mismatch, port conflict
- README examples and release test plan stay aligned
- AI-agent high-frequency prompts match the documented paths

## Failure Policy

- Missing Vivado in a required release environment: fail release gate
- Missing TCP configuration for TCP-specific gate: test is skipped only when TCP lane is not part of the current environment
- Missing board for hardware smoke: allowed skip, but skip reason must be explicit
- Snapshot drift: fail release gate

## Summary Output

Use the helper:

```bash
python tests/release_gate/release_summary.py
```

It prints pass/fail/skipped counts for:

- `release_gate`
- `hardware_smoke`
