# ADR-0023: A verified skill is also asked about on its own terms

- Status: Accepted
- Date: 2026-10-12

## Context
The gap matrix gave one topic per JD skill. With a strong resume every topic became "verify claim", so a 45-minute interview was three walk-throughs of the candidate's own projects: no general Python question, nothing a candidate without that project could have been asked. With only three topics, each closed after one scaffold, it also ran out of topics after 7 minutes and wrapped up with 38 minutes left. The taxonomy made this worse: JD skills it did not know ("REST APIs", AWS, CI/CD, MongoDB) were dropped from the plan.

## Options considered
1. Leave the plan as it is and let the live policy stay longer on each topic.
2. Let the live model invent extra topics when the plan runs out.
3. Have the deterministic planner add a "fundamentals" topic for each skill whose claim is verified, and widen the taxonomy.

## Decision
Option 3. `with_fundamentals` adds a FUNDAMENTALS row (no claim, factor 0.8) for every VERIFY_CLAIM row in what the interview asks; the claim is still verified first because it scores higher. The topic-pack prompt writes these about the skill itself: how it works, concepts, pitfalls, and one small problem answered aloud. The taxonomy gains `nosql`, `cloud`, `ci_cd`, `testing` and the plural REST aliases. A round template can name skills it always asks about (`always:`); R1 Technical uses it for one problem-solving topic talked through aloud. The closing line no longer says "out of time", since an interview can also end because its topics are done.

## Consequences
The plan stays deterministic and each strong skill is checked twice, from the project and from first principles; both topics feed the same skill score. Prep writes more topic packs (more model calls, longer prep). Interviews already prepared keep their old plan. An interview can still end early if the candidate is weak on every topic, because the policy moves on after one scaffold and nothing refills the plan; a real coding question still needs the coding round (spec 002). The new taxonomy skills have no seed bank yet, so their questions are unanchored.
