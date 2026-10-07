"""Report narrative — the LLM explains numbers computed by code. It never changes them."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from qualifai.llm.gateway import LLM
from qualifai.llm.prompts import load_prompt
from qualifai.llm.tasks import LLMTask


class Narrative(BaseModel):
    summary: str
    strengths: list[str]
    gaps: list[str]
    deciding_gap: str
    prep_plan: list[str]


async def write_narrative(llm: LLM, aggregate: dict[str, Any]) -> Narrative:
    prompt = load_prompt("report_narrative").format(aggregate_json=json.dumps(aggregate, indent=1))
    return await llm.structured(LLMTask.REPORT_NARRATIVE, "JSON only.", prompt, Narrative)
