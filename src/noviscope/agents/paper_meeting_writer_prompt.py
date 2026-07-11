import json
from typing import assert_never

from noviscope.agents.paper_meeting_writer_results import experiment_results_context
from noviscope.agents.paper_meeting_writer_types import (
    MAX_PAPERS_FOR_PROMPT,
    MAX_TEXT_FIELD_CHARS,
    PaperMeetingWriterRequest,
)
from noviscope.agents.provider_chat import ChatCompletionPayload
from noviscope.core.json_types import JsonObject


def build_chat_completion_payload(request: PaperMeetingWriterRequest) -> ChatCompletionPayload:
    result_context = experiment_results_context(
        request.experiment_plan,
        request.verified_experiment_results,
    )
    prompt_payload = {
        "demand_validation": compact_payload(request.demand_validation),
        "experiment_plan": experiment_plan_prompt_payload(request.experiment_plan),
        "experiment_result_context": result_context.as_prompt_payload(),
        "papers": request.papers[:MAX_PAPERS_FOR_PROMPT],
        "quest": {
            "initial_direction": request.initial_direction,
            "title": request.quest_title,
        },
        "selected_ideas": request.selected_ideas,
        "source_stage_ids": request.source_stage_ids,
    }
    return {
        "messages": [
            {
                "content": (
                    "You are NoviScope's Paper & Meeting Writer. Return only valid JSON with "
                    "keys summary, confidence, chinese_research_brief_markdown, "
                    "english_research_brief_markdown, meeting_outline_markdown, "
                    "ieee_paper_skeleton_markdown, verified_facts, "
                    "model_generated_hypotheses, experiment_results_not_available, "
                    "human_review_required, warnings. Use Markdown strings for the four "
                    "artifacts. Clearly separate verified facts from generated hypotheses. "
                    "Do not invent citations, metric values, benchmark scores, or completed "
                    "experiments. If experiment_result_context.verified_result_facts is empty, "
                    "the IEEE skeleton must keep Results and Conclusion sections as "
                    "placeholders. If verified_result_facts exist, cite only those facts as "
                    "completed results with run and artifact provenance. Results requiring "
                    "review must appear in human_review_required and must not be written as "
                    "verified facts."
                ),
                "role": "system",
            },
            {
                "content": json.dumps(prompt_payload, ensure_ascii=False),
                "role": "user",
            },
        ],
        "model": request.model,
        "temperature": 0.25,
    }


def experiment_plan_prompt_payload(experiment_plan: JsonObject) -> JsonObject:
    payload = compact_payload(experiment_plan)
    if "experiment_results" in payload:
        del payload["experiment_results"]
        payload["experiment_results_redacted"] = True
    return payload


def compact_payload(payload: JsonObject) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        match value:
            case str() as text:
                compacted[key] = trim_text(text)
            case list() as items:
                compacted[key] = [
                    trim_text(item) if isinstance(item, str) else item
                    for item in items[:10]
                    if isinstance(item, str | int | float | bool | dict)
                ]
            case int() | float() | bool() | dict() | None:
                compacted[key] = value
            case unreachable:
                assert_never(unreachable)
    return compacted


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]
