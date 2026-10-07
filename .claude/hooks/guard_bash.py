"""PreToolUse(Bash): refuse destructive commands."""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, read_input

DANGEROUS = [
    (r"rm\s+-rf\s+(/|~|\$HOME)(\s|$)", "recursive delete of root/home"),
    (r"docker\s+compose\s+down\s+.*-v", "wipes database volumes"),
    (r"git\s+push\s+.*--force.*\b(main|master)\b", "force-push to main"),
    (r"DROP\s+(DATABASE|SCHEMA)", "drops the database"),
]

cmd = str((read_input().get("tool_input") or {}).get("command", ""))
for pattern, why in DANGEROUS:
    if re.search(pattern, cmd, re.IGNORECASE):
        block(f"Blocked command ({why}). Ask the user to run it manually if it's really intended.")
sys.exit(0)
