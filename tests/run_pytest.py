"""Run pytest from the current repository root and print the result."""

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]

result = subprocess.run(
    [sys.executable, "-m", "pytest", str(REPO_ROOT / "tests"), "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd=REPO_ROOT,
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)
