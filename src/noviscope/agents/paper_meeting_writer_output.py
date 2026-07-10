import json

from pydantic import ValidationError

from noviscope.agents.paper_meeting_writer_artifacts import (
    MODEL_MARKDOWN_REPLACED_WARNING,
    PAPER_ARTIFACT_POLICY_VERSION,
    build_guardrailed_artifacts,
)
from noviscope.agents.paper_meeting_writer_results import (
    NEEDS_REVIEW_WARNING,
    experiment_results_context,
)
from noviscope.agents.paper_meeting_writer_types import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    Confidence,
    PaperMeetingWriterOutput,
    PaperMeetingWriterRequest,
)
from noviscope.agents.stage_runner import StageRunContext
from noviscope.core.json_types import JsonObject

INVALID_STRUCTURED_RESPONSE_NOTICE = "The model response was not valid structured JSON."


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
                "structured_response_valid": True,
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
            structured_response_valid=False,
            summary=INVALID_STRUCTURED_RESPONSE_NOTICE,
            verified_facts=[],
            warnings=[INVALID_STRUCTURED_RESPONSE_NOTICE],
        )
    return constrain_output(output, request)


def constrain_output(
    output: PaperMeetingWriterOutput,
    request: PaperMeetingWriterRequest,
) -> PaperMeetingWriterOutput:
    result_context = experiment_results_context(
        request.experiment_plan,
        request.verified_experiment_results,
    )
    warnings = list(output.warnings)
    if MODEL_MARKDOWN_REPLACED_WARNING not in warnings:
        warnings.append(MODEL_MARKDOWN_REPLACED_WARNING)
    verified_facts = list(result_context.verified_facts)
    artifacts = build_guardrailed_artifacts(request, result_context)
    experiment_results_not_available = list(output.experiment_results_not_available)
    human_review_required = list(output.human_review_required)
    if result_context.has_verified_results:
        experiment_results_not_available = []
    elif NO_RESULTS_NOTICE not in experiment_results_not_available:
        experiment_results_not_available.append(NO_RESULTS_NOTICE)
    for review_note in result_context.human_review_required:
        if review_note not in human_review_required:
            human_review_required.append(review_note)
    if result_context.needs_review_count > 0 and NEEDS_REVIEW_WARNING not in warnings:
        warnings.append(NEEDS_REVIEW_WARNING)
    if HUMAN_REVIEW_NOTICE not in human_review_required:
        human_review_required.append(HUMAN_REVIEW_NOTICE)
    summary = INVALID_STRUCTURED_RESPONSE_NOTICE
    if output.structured_response_valid:
        if result_context.has_verified_results:
            result_label = "result" if result_context.verified_count == 1 else "results"
            summary = (
                "Generated four review-only Markdown artifacts from "
                f"{result_context.verified_count} verified experiment {result_label}."
            )
        else:
            summary = (
                "Generated four review-only Markdown artifacts without verified "
                "experiment results."
            )
    return output.model_copy(
        update={
            "chinese_research_brief_markdown": artifacts.chinese_research_brief_markdown,
            "confidence": cap_confidence(output.confidence),
            "english_research_brief_markdown": artifacts.english_research_brief_markdown,
            "experiment_results_not_available": experiment_results_not_available,
            "human_review_required": human_review_required,
            "ieee_paper_skeleton_markdown": artifacts.ieee_paper_skeleton_markdown,
            "meeting_outline_markdown": artifacts.meeting_outline_markdown,
            "summary": summary,
            "verified_facts": verified_facts,
            "warnings": warnings,
        }
    )


def cap_confidence(confidence: str) -> Confidence:
    if confidence == "high" or confidence == "medium":
        return "medium"
    return "low"


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
        "artifact_policy_version": PAPER_ARTIFACT_POLICY_VERSION,
        "can_run": True,
        "download_format": "markdown",
        "experiment_results_require_review": has_result_review_items(output),
        "no_experiment_results": not has_verified_result_items(output),
        "provider_id": context.provider.id,
        "provider_model": context.provider.model,
        "provider_name": context.provider.name,
        "requires_human_review": True,
        "source_stage_ids": output.source_stage_ids,
        "warning_count": len(output.warnings),
    }


def has_result_review_items(output: PaperMeetingWriterOutput) -> bool:
    for review_item in output.human_review_required:
        if review_item.startswith("Experiment result run "):
            return True
    return False


def has_verified_result_items(output: PaperMeetingWriterOutput) -> bool:
    for fact in output.verified_facts:
        if fact.startswith("Verified experiment result:"):
            return True
    return False
