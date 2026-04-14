# Contributing to GateFlow

Thanks for contributing to GateFlow.

## Development Setup

Requirements:

- Python 3.10+
- Vivado 2018.1+ for Vivado-dependent workflows
- Windows 10/11 for the currently supported primary environment

Recommended setup:

```bash
git clone https://github.com/Firo718/GateFlow.git
cd gateflow
pip install -e ".[dev]"
```

## Useful Commands

Run the default test suite:

```bash
pytest tests/ -v --tb=short -m "not vivado"
```

Run formatting and static checks:

```bash
ruff check src/ tests/
mypy src/gateflow
```

Generate capability docs after changing tool registration:

```bash
gateflow capabilities --write
```

## Pull Request Guidelines

- Keep changes scoped and reviewable.
- Add or update tests for behavior changes.
- Update `README.md`, `docs/`, or `CHANGELOG.md` when user-facing behavior changes.
- Do not commit local caches, Vivado generated artifacts, or secrets.

## Commit Guidance

- Use clear commit messages describing the behavior change.
- Prefer one logical change per commit.

## Reporting Issues

When opening an issue, include:

- GateFlow version
- Python version
- Vivado version
- Operating system
- Reproduction steps
- Relevant logs or traceback output
