# ADR-0006: Text-first interface; voice and avatar deferred

- Status: Accepted
- Date: 2026-10-07

## Context
Real-time voice (VAD, STT, TTS, barge-in) and avatars are the riskiest, most time-consuming parts and do not improve judgement quality — the core value.

## Options considered
1. Full voice + avatar in MVP.
2. Text MVP, keep an event contract so voice plugs in later.

## Decision
Option 2. The engine consumes `candidate_turn_ended(text)` and emits `say(text)`; transport is REST + SSE.

## Consequences
Latency budget relaxes (two clean LLM calls per turn; larger live models viable). New risks handled: copy-paste (integrity events) and less time pressure (soft per-answer timer).
