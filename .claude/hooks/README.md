# Hooks

| Event | Script | What it does | Blocks? |
|---|---|---|---|
| SessionStart | `session_context.py` | Prints golden rules + open tasks from the active spec into context | no |
| PreToolUse (Edit/Write) | `protect_files.py` | Refuses edits to `.env*`, keys, lockfiles and already-applied migrations | yes (exit 2) |
| PreToolUse (Bash) | `guard_bash.py` | Refuses destructive commands (volume wipes, force-push to main, `rm -rf /`) | yes (exit 2) |
| PostToolUse (Edit/Write) | `architecture_guard.py` | Deterministic modules must not import LLM/DB/LangGraph — immediate feedback | yes (exit 2) |
| PostToolUse (Edit/Write) | `format_python.sh` | `ruff format` + `ruff check --fix` on the edited `.py` file | no |
| Stop | `run_fast_tests.py` | Runs unit + architecture tests if `src/` changed; failures are fed back to Claude | yes (exit 2), loop-safe via `stop_hook_active` |

All hooks read the hook JSON from stdin. Exit code 2 = block, stderr is shown to Claude.
Personal overrides go in `.claude/settings.local.json` (git-ignored).
