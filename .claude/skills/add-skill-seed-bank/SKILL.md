---
name: add-skill-seed-bank
description: Add a skill to the QualifAI taxonomy and write its seed bank (subtopics, anchored levels 1-4, red flags, follow-ups) used to ground LLM-generated questions and rubrics.
---

# Add a skill seed bank

Seed banks are **reference anchors**, not question lists. The prep LLM adapts them into
personalised questions; the evaluator uses the level anchors for consistent scoring.

1. **Taxonomy** — add the canonical id + aliases to `content/skills/_taxonomy.yaml`.
   Prefer a `parent` (e.g. `mysql → relational_db`) so generic anchors are reused.
2. **Seed bank** — create `content/skills/<skill>.yaml`:
   ```yaml
   skill: <id>
   parent: <optional parent id>
   subtopics:
     - name: <subtopic>
       levels: {1: "...", 2: "...", 3: "...", 4: "..."}   # what an answer at each level shows
       red_flags: ["..."]
       follow_ups: ["..."]
   ```
   Aim for ~5 subtopics. Level text describes *observable answer content*, not adjectives.
3. Write in your own words — never copy third-party question banks.
4. If a role family should test it, add it with a weight 1–3 in `content/role_families/*.yaml`.
5. Run `python scripts/seed_content.py` and `pytest tests/unit/test_taxonomy.py`.
