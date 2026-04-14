"""
运行 pytest 测试并输出结果。
"""

import subprocess
import sys

# 运行测试
result = subprocess.run(
    [sys.executable, '-m', 'pytest', 'f:/GateFlow/tests/', '-v', '--tb=short'],
    capture_output=True,
    text=True,
    cwd='f:/GateFlow'
)

print("STDOUT:")
print(result.stdout)
print("\nSTDERR:")
print(result.stderr)
print("\nReturn code:", result.returncode)
