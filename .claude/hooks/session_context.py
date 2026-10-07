"""SessionStart: inject the golden rules and the next open spec tasks into Claude's context."""

import os
import re
from pathlib import Path

root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
print(
    "QualifAI golden rules: LLM proposes, policy disposes · deterministic core stays pure · "
    "only qualifai.llm calls models · bounded context · evidence or no score · content is config."
)

specs = sorted((root / ".claude" / "specs").glob("[0-9][0-9][0-9]-*/tasks.md"))
for tasks in specs:
    open_tasks = [
        ln.strip() for ln in tasks.read_text().splitlines() if re.match(r"^- \[ \] ", ln.strip())
    ]
    if open_tasks:
        print(f"\nActive spec: {tasks.parent.name} — next open tasks:")
        print("\n".join(open_tasks[:5]))
        break
