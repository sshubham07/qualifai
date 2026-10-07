---
name: write-adr
description: Record an architecture decision for QualifAI as a numbered ADR (MADR style) in .claude/architecture/adr/, including context, options considered, decision, and consequences.
---

# Write an ADR

1. Next number = highest in `.claude/architecture/adr/` + 1, zero-padded to 4 digits.
2. File: `NNNN-short-kebab-title.md` using this template:
   ```markdown
   # ADR-NNNN: <Title>
   - Status: Proposed | Accepted | Superseded by ADR-XXXX
   - Date: YYYY-MM-DD

   ## Context
   What problem / force made this decision necessary.
   ## Options considered
   1. ... (pros / cons)
   ## Decision
   What we chose, in one or two sentences.
   ## Consequences
   Good, bad, and what we will watch.
   ```
3. Never rewrite an Accepted ADR's decision — supersede it with a new one and update the old
   status line.
4. Add a row to `.claude/architecture/adr/README.md`.
