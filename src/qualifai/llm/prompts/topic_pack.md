Prepare interviewer material for ONE topic. Output JSON only.

Round: {round_name} · Tier: {tier_name} · Depth target: {max_depth} · Start difficulty: {difficulty}/4
Round rules: {round_rules}
Topic: {topic_title}
Resume claim (if any): {claim}
Skill to probe (from the JD or the round): {jd_skill}

Reference anchors (expert-written, adapt — do not copy blindly):
{seed_anchors}

Commonly reported real questions for this round/tier/skill (may be empty):
{real_questions}

If the topic is "fundamentals: <skill>", ask about the skill itself and NOT about the candidate's
projects: how it works underneath, core concepts, common pitfalls, and one small "how would you
write / approach this" problem that can be answered aloud without an editor.

If the skill is problem_solving, pose one data-structures-and-algorithms problem in your own
words, sized to be solved aloud: approach, complexity and edge cases, no editor.

Produce:
- opening_questions: 2–3, in this round's style, personalised to the claim / requirement (general for a fundamentals topic)
- rubric.expected_points: 4–6 short bullet keywords a strong answer covers
- rubric.red_flags: 2–4
- rubric.follow_up_hooks: 3–5 "if they mention X → ask Y" lines
