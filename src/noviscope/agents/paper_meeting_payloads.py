import json
from typing import assert_never

from pydantic import JsonValue, ValidationError

from noviscope.agents.paper_meeting_contracts import (
    Confidence,
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
)
from noviscope.agents.stage_runner import StageRunContext
from noviscope.core.json_types import JsonObject

MAX_TEXT_FIELD_CHARS = 900
MAX_PAPERS_FOR_PROMPT = 8
NO_RESULTS_NOTICE = (
    "No experiment results are available yet; result sections must stay as placeholders."
)
HUMAN_REVIEW_NOTICE = (
    "Human review is required before any draft can be used as a paper or meeting claim."
)


def parse_paper_meeting_writer_output(
    raw_content: str,
    request: PaperMeetingWriterRequest,
) -> PaperMeetingWriterOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = PaperMeetingWriterOutput.model_validate(
            {
                **parsed_content,
                "raw_response": raw_content,
                "source_stage_ids": request.source_stage_ids,
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return PaperMeetingWriterOutput(
            chinese_research_brief_markdown="",
            confidence="low",
            english_research_brief_markdown="",
            experiment_results_not_available=[NO_RESULTS_NOTICE],
            human_review_required=[HUMAN_REVIEW_NOTICE],
            ieee_paper_skeleton_markdown="",
            meeting_outline_markdown="",
            model_generated_hypotheses=[],
            raw_response=raw_content,
            source_stage_ids=request.source_stage_ids,
            summary="The model response was not valid structured JSON.",
            verified_facts=[],
            warnings=["The model response was not valid structured JSON."],
        )
    return constrain_output(output)


def constrain_output(output: PaperMeetingWriterOutput) -> PaperMeetingWriterOutput:
    warnings = list(output.warnings)
    experiment_results_not_available = list(output.experiment_results_not_available)
    human_review_required = list(output.human_review_required)
    if NO_RESULTS_NOTICE not in experiment_results_not_available:
        experiment_results_not_available.append(NO_RESULTS_NOTICE)
    if HUMAN_REVIEW_NOTICE not in human_review_required:
        human_review_required.append(HUMAN_REVIEW_NOTICE)
    return output.model_copy(
        update={
            "confidence": cap_confidence(output.confidence),
            "experiment_results_not_available": experiment_results_not_available,
            "human_review_required": human_review_required,
            "warnings": warnings,
        }
    )


def cap_confidence(confidence: Confidence) -> Confidence:
    match confidence:
        case "high" | "medium":
            return "medium"
        case "low":
            return "low"
        case unreachable:
            assert_never(unreachable)


def build_stage_output_payload(output: PaperMeetingWriterOutput) -> JsonObject:
    return {
        "chinese_research_brief_markdown": output.chinese_research_brief_markdown,
        "confidence": output.confidence,
        "english_research_brief_markdown": output.english_research_brief_markdown,
        "experiment_results_not_available": output.experiment_results_not_available,
        "human_review_required": output.human_review_required,
        "ieee_paper_skeleton_markdown": output.ieee_paper_skeleton_markdown,
        "meeting_outline_markdown": output.meeting_outline_markdown,
        "model_generated_hypotheses": output.model_generated_hypotheses,
        "raw_response": output.raw_response,
        "source_stage_ids": output.source_stage_ids,
        "summary": output.summary,
        "verified_facts": output.verified_facts,
        "warnings": output.warnings,
    }


def build_stage_evidence_payload(
    context: StageRunContext,
    output: PaperMeetingWriterOutput,
) -> JsonObject:
    return {
        "artifact_count": 4,
        "can_run": True,
        "download_format": "markdown",
        "no_experiment_results": True,
        "provider_id": context.provider.id,
        "provider_model": context.provider.model,
        "provider_name": context.provider.name,
        "requires_human_review": True,
        "source_stage_ids": output.source_stage_ids,
        "warning_count": len(output.warnings),
    }


def compact_payload(payload: JsonObject) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        match value:
            case str():
                compacted[key] = trim_text(value)
            case list():
                compacted[key] = compact_json_list(value)
            case int() | float() | bool() | dict() | None:
                compacted[key] = value
            case unreachable:
                assert_never(unreachable)
    return compacted


def compact_json_list(values: list[JsonValue]) -> list[JsonValue]:
    compacted: list[JsonValue] = []
    for value in values[:10]:
        match value:
            case str():
                compacted.append(trim_text(value))
            case int() | float() | bool() | dict():
                compacted.append(value)
            case list() | None:
                continue
            case unreachable:
                assert_never(unreachable)
    return compacted


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]
