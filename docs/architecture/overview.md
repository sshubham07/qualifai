# QualifAI — Project Overview

## Problem
Candidates prepare for technical interviews with question lists or a chatbot. Neither behaves
like a real interviewer: no time pressure, no plan, no cross-questioning of resume claims, no
company-appropriate bar, and feedback that is vague and unverifiable.

## What QualifAI is
An **interview simulation platform**: the candidate submits a resume, a JD, the round type and a
company tier; QualifAI prepares a personalised interview kit, runs a time-boxed adaptive
interview, and produces an evidence-backed assessment.

It is **not** "upload resume → send everything to an LLM". The software owns the plan, the clock,
the questioning strategy and the verdict. LLMs do narrow language jobs inside it.

It is **not a RAG application.** Retrieval appears only as a supporting component in prep (V2).

## Goals
- Realistic: round × tier structure, resume-claim verification, JD-gap testing, follow-ups.
- Adaptive: depth and difficulty change from the candidate's answers, within time budgets.
- Trustworthy: every score cites a transcript quote; verdict is computed, explainable, and
  honest about coverage and confidence.
- Free to run: open-weight models (local or free hosted tiers) behind one gateway.

## Non-goals (MVP)
- Server-side speech models, avatar, webcam (deferred — ADR-0006; the room's voice is the browser's own, ADR-0022).
- Non-technical roles (declined at intake — ADR-0013).
- Company-by-company logic (replaced by round × tier — ADR-0009).
- Screening real candidates for employers.

## The three phases
| Phase | Trigger | Output | Mode |
|---|---|---|---|
| 1. Prep | Submission accepted by intake gate | Interview kit (plan + topic packs), status READY, email if one was given (ADR-0017) | async worker, large model |
| 2. Live interview | Candidate starts within 7 days | Append-only transcript + per-turn signals | LangGraph loop, fast models |
| 3. Evaluation | Interview ends (natural / hard stop) | Report JSON + rendered HTML, email | async worker, large model |

## Inputs
Resume (text) · JD (text) · Round (R1 Technical, R2 LLD, R3 HLD, R4 Managerial, HR, or full loop) ·
Company tier (service, startup, product, MAANG) · Experience range · Target duration ·
Company name (optional, flavour only).

## Glossary
| Term | Meaning |
|---|---|
| Interview kit | Everything prepared before the interview: profile, gap matrix, plan, topic packs |
| Topic | One thread: an opening question plus its follow-ups |
| Topic pack | Opening questions + rubric (expected points, red flags) + follow-up hooks for one topic |
| Gap matrix | JD skill × resume evidence → verify claim / test gap / light |
| Match check | Which JD skills the resume shows; none at all → FAILED with the skills named (ADR-0018) |
| Claims ledger | Resume statements extracted with ownership level, verified during the interview |
| Policy engine | Pure Python deciding the next action from signals + time |
| Turn signals | Turn Analyzer output: rubric points covered, specificity, consistency, hooks |
| Time window | soft_start / target_end / hard_end (e.g. 40 / 45 / 50 min) |
| Coverage guard | Follow-ups may spend only time not reserved for unvisited must-cover topics |
| Seed bank | Expert-written anchors per skill (levels 1–4, red flags) grounding LLM output |
| Gates | Rules that cap or withhold a verdict (coverage, must-have, claim, coding, integrity) |
