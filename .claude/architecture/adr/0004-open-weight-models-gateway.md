# ADR-0004: Open-weight models behind an OpenAI-compatible gateway with per-task routing

- Status: Accepted
- Date: 2026-10-07

## Context
Portfolio project; must run free. Model availability and free-tier quotas change often (e.g. hosted free tiers rotate models; quotas are per model).

## Options considered
1. Hard-code one provider/model.
2. Gateway + task→model routing in content/models.yaml.

## Decision
Option 2. All providers (Ollama, free hosted open-weight, vLLM) are called through one OpenAI-compatible client. Three tiers: small (phrasing), medium (live analysis), large (prep/eval). Only `qualifai.llm` imports provider SDKs.

## Consequences
Swapping models is a config change; quotas are spread by assigning phases to different models; telemetry (tokens/latency per task) enables later comparison.
