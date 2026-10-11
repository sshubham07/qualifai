# ADR-0018: A resume–JD match check stops prep; FAILED is terminal

- Status: Accepted
- Date: 2026-10-11

## Context
The intake gate (ADR-0016) only checks that the resume and the JD are both software roles. A frontend resume with a backend JD passes it, and prep then spends the large model writing an interview made entirely of gap questions about skills the candidate never claimed. The lifecycle also let a FAILED interview go back to PREPARING ("retry"), although nothing used it and a failure caused by the inputs can never succeed on a retry.

## Options considered
1. Ask the gate model whether the resume fits the JD. One call, but a small model would be making a decision (ADR-0002), with no explanation to show.
2. Compare role families (frontend ≠ backend → fail). Cheap, but too coarse: a full-stack resume fits a backend JD.
3. Compute the match in code from the extraction: which JD skills the resume shows any evidence for.
4. Option 3 with a minimum score (first built with 30% of the JD's skill weight). It failed a Python backend resume against a Python full-stack JD at 0.27, an interview that was worth running.

## Decision
Option 3. After extraction, `prep/match.py` builds a `MatchReport` over every JD skill, including skills outside the taxonomy (kept by their lowercased name so an unknown skill present in both documents still counts). A skill counts as shown if a claim carries it or the resume text names it or one of its taxonomy aliases as a whole word: the extraction model does not tag every skill a sentence mentions ("Django/DRF REST APIs" came back tagged `django` only), and a missed tag must not fail an interview. Only a totally-off pair stops prep: no matched skill → `resume_jd_no_match`, with a reason naming the skills the JD asks for. Any overlap goes ahead; the missing skills become test-gap questions, which is what the interview is for. The weighted score is stored in the kit for the record and decides nothing. The check runs before planning, topic packs and the opening question, so a mismatch costs two extraction calls. `no_known_skills` is checked first: with nothing askable there is no interview whatever the match.

FAILED has no outgoing transitions. The reason stays on the interview; trying again is a new submission and a new interview (failed interviews are already excluded from kit reuse).

## Consequences
The candidate is told which skills are missing instead of sitting a hopeless interview. The match is only as good as extraction and name matching: an unknown skill written two ways ("React" / "ReactJS") does not match until the taxonomy has an alias, which is one more reason only zero overlap stops prep. A transient prep error is also a dead end; the candidate resubmits. Supersedes the `FAILED → PREPARING` retry edge in the HLD lifecycle.
