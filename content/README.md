# Content (config-as-content)

Everything that makes an interview *realistic* lives here as reviewed YAML — not in code.
`python scripts/seed_content.py` validates every file against its Pydantic schema.

| Folder | What | Drives |
|---|---|---|
| `rounds/` | Round templates (R1 Technical, DSA, R2 LLD, R3 HLD, R4 Managerial, HR); the setup page's "interview focus" | phases, rubric dimensions, rules, the round's own topics (`skills`) |
| `tiers/` | Company tier presets (service, startup, product, MAANG) | difficulty, depth, verdict thresholds |
| `role_families/` | Which roles are supported and with which skills/rounds | intake gate |
| `skills/` | `_taxonomy.yaml` (aliases → canonical) + per-skill seed banks | normalisation, rubric anchors |
| `coding_problems/` | Curated problems with hidden + performance tests (V2) | coding round |
| `real_questions/` | User-contributed, paraphrased real questions tagged round × tier × skill (V2) | topic-pack realism |
| `interviewer.yaml` | The interviewer's name and the greeting said before the first question | start of every interview |
| `models.yaml` | LLM task → provider/model routing | every LLM call |

Rules: write content in your own words; never copy LeetCode/Glassdoor text or tests.
