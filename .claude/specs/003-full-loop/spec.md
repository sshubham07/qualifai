# Spec 003 — Full loop, R3 HLD, HR, real-question retrieval — DRAFT

- Full loop per tier (e.g. Product: R1 → R2 → R3 → R4 → HR); each round its own session/kit/report.
- Later rounds read earlier findings (weak skills probed again); combined loop report.
- Optional "realistic mode": next round unlocks only on pass.
- R3 HLD: requirements → estimates → design → deep-dive → bottlenecks; text design first,
  diagram tool later.
- Real-question corpus: user contributions (paraphrased), LLM normalisation, pgvector dedupe,
  moderation, freshness weighting; retrieval by round × tier × skill with fallback chain.
- Voice (push-to-talk) as an adapter on the existing event contract.
