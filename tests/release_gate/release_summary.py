"""Lightweight release summary runner."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


SUMMARY_RE = re.compile(
    r"=+\s+(?:(?P<passed>\d+) passed)?(?:,\s*)?(?:(?P<failed>\d+) failed)?(?:,\s*)?(?:(?P<skipped>\d+) skipped)?"
)


def _run(label: str, args: list[str]) -> dict[str, int | str]:
    result = subprocess.run(args, capture_output=True, text=True)
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    passed = failed = skipped = 0
    for line in output.splitlines():
        match = SUMMARY_RE.search(line)
        if match:
            passed = int(match.group("passed") or 0)
            failed = int(match.group("failed") or 0)
            skipped = int(match.group("skipped") or 0)
    return {
        "label": label,
        "returncode": result.returncode,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    python = sys.executable
    runs = [
        _run(
            "release_gate",
            [python, "-m", "pytest", "-q", "-m", "release_gate"],
        ),
        _run(
            "ai_real_usage",
            [python, "-m", "pytest", "-q", "-m", "ai_real_usage"],
        ),
        _run(
            "hardware_smoke",
            [python, "-m", "pytest", "-q", "tests/hardware_smoke", "-m", "vivado and integration"],
        ),
    ]

    print("GateFlow Release Summary")
    print("========================")
    for run in runs:
        print(
            f"{run['label']}: pass={run['passed']} fail={run['failed']} skipped={run['skipped']} rc={run['returncode']}"
        )
    return 0 if all(run["returncode"] == 0 for run in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
