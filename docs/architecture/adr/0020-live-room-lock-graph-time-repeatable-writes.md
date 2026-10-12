# ADR-0020: The live room locks the interview row, the graph keeps its own time, and transcript writes are repeatable

- Status: Accepted
- Date: 2026-10-12

## Context
Phase 2 puts three callers on one interview: `POST /start`, `POST /answers` and the scheduled hard stop. A double-clicked submit or a hard stop firing mid-answer would run the same checkpoint thread twice. The graph also needs two durations per turn (how long the answer took, how long the candidate waited on us), and a node that crashed after writing a turn runs again when the turn is retried.

## Options considered
1. A Redis lock per interview. Works across processes, but a crashed holder leaves a lock to expire and Redis becomes part of correctness (ADR-0005 keeps it disposable).
2. Lock the `interviews` row for the whole turn (`SELECT … FOR NO KEY UPDATE`). Released by commit, rollback or a dead connection; transcript inserts from other sessions still pass because they only need a key-share lock.
3. Take timings from the browser (`shown_at`, `submitted_at`) versus measuring them in the graph from the injected clock.
4. Make the sink reject a repeated `seq` (error) versus accept it silently (`ON CONFLICT DO NOTHING`).

## Decision
- **Option 2.** `interview/room.py` locks the row first in start, answer and hard stop, then re-reads status and the last turn. An answer must name the `question_seq` it answers; anything else is 409. The sink writes turns in its own short transactions and never touches the `interviews` row, which only the lock holder changes (window, latency credit, COMPLETED).
- **The graph keeps time.** `question_at` is stamped when a question is committed and `resumed_at` when the answer arrives; answer seconds and system latency come from those. The browser sends only offsets (first keystroke, longest idle gap, paste events), stored as integrity signals and never used for decisions. The total latency becomes the window's credit (ADR-0012); the room stores it so the hard-stop job, scheduled once at start, checks the moved `hard_end` and puts itself back if it is early.
- **Repeatable writes.** A turn is keyed by `(interview_id, seq)`; writing it again changes nothing. If a turn dies after the answer was committed, sending the same answer again continues from the checkpoint instead of resuming the interrupt.
- The graph state carries `graph_version`; `BUILDERS` keeps a builder per version so an interview finishes on the graph it started on (ADR-0003).
- LangGraph's `checkpoint*` tables are created by its own `setup()` at startup, over a small psycopg pool; Alembic ignores them.

## Consequences
A turn holds one database connection for its few seconds, which is fine at this scale. A reloaded page asks `GET /room` for the pending question and its draft. If a turn dies and the page is reloaded before resending, there is no question to show until the hard stop closes the interview. A question re-phrased after a crash is not stored (the first one wins), so the state can briefly hold wording the transcript does not. Streamed tokens are best effort over Redis pub/sub; the response to `POST /answers` is the question of record.
