"""Stop: if src/ or tests/ changed, run unit + architecture tests; feed failures back to Claude.
Loop-safe: when Claude is already continuing because of this hook, we don't block again."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, read_input

data = read_input()
if data.get("stop_hook_active"):
    sys.exit(0)

root = os.environ.get("CLAUDE_PROJECT_DIR", ".")
changed = subprocess.run(
    ["git", "status", "--porcelain", "--", "src", "tests"], cwd=root, capture_output=True, text=True
).stdout.strip()
if not changed:
    sys.exit(0)

runner = (
    ["uv", "run"] if subprocess.run(["which", "uv"], capture_output=True).returncode == 0 else []
)
res = subprocess.run(
    [*runner, "pytest", "-m", "unit or architecture", "-q", "-x", "--no-header"],
    cwd=root,
    capture_output=True,
    text=True,
)
if res.returncode not in (0, 5):  # 5 = no tests collected
    block("Fast tests are failing — fix before finishing:\n" + res.stdout[-3000:])
sys.exit(0)
