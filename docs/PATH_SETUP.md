# GateFlow CLI PATH Setup

This note explains what to do when `gateflow` is installed successfully but the shell still says the command cannot be found.

## Root Cause

In most cases, GateFlow is already installed into the current Python environment.
The missing piece is that the Python `Scripts` directory for that environment is not in the user's `PATH`.

This path is different for different users and environments:

- Official Python installs
- `pythoncore` installs from the Microsoft distribution
- virtual environments
- conda environments

Do not copy another user's `Scripts` path.

## Fastest Workaround

Run GateFlow through the active interpreter without relying on `PATH`:

```bash
python -m gateflow.cli --version
python -m gateflow.cli doctor
python -m gateflow.cli status
```

If these commands work, GateFlow is installed correctly.

## Find The Right Scripts Directory

Ask the active Python interpreter where its `Scripts` directory is:

```bash
python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```

Use the printed path for the current user and the current Python environment.

## Add It To User PATH On Windows

PowerShell:

```powershell
$scripts = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
[Environment]::SetEnvironmentVariable(
  "Path",
  $env:Path + ";" + $scripts,
  "User"
)
```

Then close and reopen the terminal, and verify:

```bash
gateflow --version
```

## If You Do Not Want To Change PATH

Keep using the module form:

```bash
python -m gateflow.cli <subcommand>
```

Examples:

```bash
python -m gateflow.cli install F:/Xilinx/Vivado/2023.1
python -m gateflow.cli doctor --json
python -m gateflow.cli gui status
```

## For Repo Developers

Editable installs work the same way:

```bash
python -m pip install -e .
```

If `gateflow` is still not found afterwards, it is still a `PATH` issue, not an installation failure.
