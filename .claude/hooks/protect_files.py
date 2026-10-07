"""PreToolUse: block edits to secrets, lockfiles and applied migrations."""

import fnmatch
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, edited_path, read_input

PROTECTED = [".env", ".env.*", "*.pem", "*.key", "uv.lock", "poetry.lock"]

data = read_input()
path = edited_path(data)
name = os.path.basename(path)

if any(fnmatch.fnmatch(name, pat) for pat in PROTECTED) and name != ".env.example":
    block(
        f"Blocked: '{name}' is protected (secrets/lockfile). "
        "Edit .env.example or run the tool instead."
    )

if "/migrations/versions/" in path and os.path.exists(path):
    block('Blocked: never edit an existing migration. Create a new one: make migration m="..."')

sys.exit(0)
