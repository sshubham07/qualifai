"""PreToolUse(Bash): a `git commit` must carry an up-to-date README.md.
Blocks the commit unless README.md is part of it. If the README was re-read and really needs no
change, prefix the command with README_OK=1 to pass."""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, read_input

cmd = str((read_input().get("tool_input") or {}).get("command", ""))
commit = re.search(r"\bgit\b[^|;&\n]*?\bcommit\b([^|;&\n]*)", cmd)
if not commit or "README_OK=1" in cmd:
    sys.exit(0)

root = os.environ.get("CLAUDE_PROJECT_DIR", ".")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()


staged = "README.md" in git("diff", "--cached", "--name-only").splitlines()
# The same command may stage it just before committing (`git add -A && git commit`, `commit -a`).
dirty = bool(git("status", "--porcelain", "--", "README.md"))
stages_it = bool(
    re.search(r"\bgit\s+add\b[^|;&\n]*(\s-A\b|\s--all\b|\s-u\b|\s\.(\s|$)|README\.md)", cmd)
    or re.search(r"\s(-[a-zA-Z]*a[a-zA-Z]*|--all)\b|README\.md", commit.group(1).split(" -m")[0])
)
if staged or (dirty and stages_it):
    sys.exit(0)

block(
    "Commit blocked: README.md is not part of this commit.\n"
    "1. Look at what is being committed and update README.md so it still tells the truth.\n"
    "2. Keep the README style: eye-catching, animated (SVGs in docs/assets/), very little text — "
    "a visitor should understand QualifAI in under a minute. Detail belongs in docs/deep-dive.md.\n"
    "3. `git add README.md` and commit again.\n"
    "If you re-read the README and nothing in it needs to change, re-run the commit as "
    "`README_OK=1 git commit ...`."
)
