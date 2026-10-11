# ADR-0019: The interview focus is the round; a focused round brings its own topics

- Status: Accepted
- Date: 2026-10-11

## Context
The setup page prepared one kind of interview: R1 Technical, with topics taken from the JD's skills. Candidates want to practise one thing at a time: DSA, low-level design, high-level design or the managerial round. `round_type` was already on the request and the round templates existed (ADR-0009), but the form never sent it, there was no DSA round, and the planner would have filled an "HLD" interview with JD skill topics such as PostgreSQL.

## Options considered
1. A new `focus` field next to `round_type`, with its own config. Two concepts for one choice.
2. Focus only changes the prompts (round name and rules). The plan, and so the time budget, would still be JD skills.
3. Focus is the round. A round template may list its own `skills` (skill → weight 1..3); when it does, they go through the gap matrix and planner in place of the JD's skills.

## Decision
Option 3. The form's "Interview focus" sends `round_type`: General = `r1_technical` (no `skills`, topics from the JD as before), plus `dsa` (new round), `r2_lld`, `r3_hld`, `r4_managerial`. Round skills use the same deterministic path as JD skills, so a round skill the resume shows (`system_design`) is still verified against the claim and the rest are test-gap topics. Topic packs now receive the round's `rules`, so questions are written in that round's style. The intake gate and the resume–JD match check (ADR-0018) are unchanged: the JD decides whether there is a fair interview, the round decides what is asked. `no_known_skills` only applies when the round has no skills of its own. Without an explicit `target_minutes`, the API uses the round's `default_minutes`.

## Consequences
Adding a focus is content: a `RoundType` value, a YAML file and a card on the form. Focused rounds ignore the JD's skill list for topics, so a "Kafka-heavy" JD does not shape an HLD interview beyond tier and experience. DSA and LLD are talked through in text until the editor and sandbox arrive (spec-002); `needs_editor` is not acted on yet. Each topic pack is written on its own, so an LLD or HLD interview is several short exercises, not one design carried through all phases; that needs a round-level problem (spec-002 / spec-003). Round skills have no seed banks yet, so their packs are unanchored (ADR-0011). `role_families/*.yaml` `rounds` is still not enforced. The form mirrors the round ids and lengths by hand.
