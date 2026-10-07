"""Sandbox client (V2). Candidate code NEVER runs in the API/worker process or near the DB.

Default: self-hosted Judge0 (isolate). Hardened alternative: Docker + gVisor with
--network none, read-only rootfs, cpu/mem/pids limits, non-root, wall-clock timeout.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RunResult:
    passed: int
    total: int
    timed_out: int
    stdout: str
    stderr: str
    wall_ms: int


class Sandbox(Protocol):
    async def run(
        self, language: str, source: str, tests: list[dict[str, str]], time_limit_s: float
    ) -> RunResult: ...
