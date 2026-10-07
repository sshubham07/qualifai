Score ONE interview topic against its rubric. Output JSON only.

Scale per dimension (anchored):
1 = incorrect or no real understanding
2 = basic / textbook, misses key points
3 = solid: correct, covers most expected points
4 = strong: depth, trade-offs, real experience evident

Rules
- Every dimension MUST cite at least one exact quote from the transcript below, with its turn number.
  No quote → do not score that dimension.
- Do not reward verbosity. Judge points covered, not length.
- Use the {tier_name} bar: {tier_guidance}
- If the topic was cut short by time, judge the quality of what exists; do not penalise incompleteness.

Rubric
{rubric}

Resume claim under test (if any): {claim}

Transcript (this topic only)
{transcript}
