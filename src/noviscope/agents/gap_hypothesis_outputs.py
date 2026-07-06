import json
from dataclasses import dataclass

from pydantic import ValidationError

from noviscope.agents.gap_hypothesis_contracts import (
    Confidence,
    GapEvidence,
    GapHypothesisOutput,
    GapHypothesisRequest,
    HypothesisIdea,
)
from noviscope.agents.gap_hypothesis_payloads import known_paper_refs
from noviscope.core.json_types import JsonObject


@dataclass(frozen=True, slots=True)
class ConstrainedGap:
    gap: GapEvidence
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ConstrainedIdea:
    idea: HypothesisIdea
    warnings: list[str]


def parse_gap_hypothesis_output(
    raw_content: str,
    request: GapHypothesisRequest,
) -> GapHypothesisOutput:
    try:
        parsed_content = json.loads(raw_content)
        output = GapHypothesisOutput.model_validate(
            {
                **parsed_content,
                "raw_response": raw_content,
                "selected_idea_ids": [],
                "selection_status": "pending_human_selection",
                "source_stage_ids": request.source_stage_ids,
            }
        )
    except (json.JSONDecodeError, TypeError, ValidationError):
        return GapHypothesisOutput(
            confidence="low",
            gaps=[],
            ideas=[],
            raw_response=raw_content,
            selected_idea_ids=[],
            selection_status="pending_human_selection",
            source_stage_ids=request.source_stage_ids,
            summary="The model response was not valid structured JSON.",
            warnings=["The model response was not valid structured JSON."],
        )
    return constrain_output_to_known_papers(output, request.papers)


def constrain_output_to_known_papers(
    output: GapHypothesisOutput,
    papers: list[JsonObject],
) -> GapHypothesisOutput:
    known_refs = known_paper_refs(papers)
    warnings = list(output.warnings)
    gaps: list[GapEvidence] = []
    ideas: list[HypothesisIdea] = []

    for gap in output.gaps:
        constrained_gap = constrain_gap(gap, known_refs)
        gaps.append(constrained_gap.gap)
        warnings.extend(constrained_gap.warnings)

    for idea in output.ideas:
        constrained_idea = constrain_idea(idea, known_refs)
        ideas.append(constrained_idea.idea)
        warnings.extend(constrained_idea.warnings)

    return output.model_copy(
        update={
            "confidence": cap_confidence(output.confidence),
            "gaps": gaps,
            "ideas": ideas,
            "warnings": warnings,
        }
    )


def constrain_gap(gap: GapEvidence, known_refs: set[str]) -> ConstrainedGap:
    valid_refs = [ref for ref in gap.supporting_papers if ref in known_refs]
    warnings: list[str] = []
    if len(valid_refs) != len(gap.supporting_papers):
        warnings.append(
            "Removed unrecognized supporting paper references from "
            f"{gap.gap_title}; verify citations."
        )
    if not valid_refs:
        warnings.append(f"{gap.gap_title} has no recognized supporting paper reference.")
    return ConstrainedGap(
        gap=gap.model_copy(update={"supporting_papers": valid_refs}),
        warnings=warnings,
    )


def constrain_idea(idea: HypothesisIdea, known_refs: set[str]) -> ConstrainedIdea:
    valid_refs = [ref for ref in idea.based_on_which_papers if ref in known_refs]
    warnings: list[str] = []
    if len(valid_refs) != len(idea.based_on_which_papers):
        warnings.append(
            f"Removed unrecognized paper references from {idea.idea_id}; verify citations."
        )
    confidence = cap_confidence(idea.confidence)
    if not valid_refs:
        confidence = "low"
        warnings.append(f"{idea.idea_id} has no recognized paper reference.")
    return ConstrainedIdea(
        idea=idea.model_copy(
            update={
                "based_on_which_papers": valid_refs,
                "confidence": confidence,
            }
        ),
        warnings=warnings,
    )


def cap_confidence(confidence: str) -> Confidence:
    if confidence == "high":
        return "medium"
    if confidence == "medium":
        return "medium"
    return "low"


def build_no_paper_output(source_stage_ids: JsonObject) -> GapHypothesisOutput:
    return GapHypothesisOutput(
        confidence="low",
        gaps=[],
        ideas=[],
        raw_response="",
        selected_idea_ids=[],
        selection_status="pending_human_selection",
        source_stage_ids=source_stage_ids,
        summary="No hypotheses generated because Literature Scout returned no papers.",
        warnings=["Literature Scout returned no papers; NoviScope did not fabricate ideas."],
    )


def build_stage_output_payload(output: GapHypothesisOutput) -> JsonObject:
    return {
        "confidence": output.confidence,
        "gaps": [gap.model_dump() for gap in output.gaps],
        "ideas": [idea.model_dump() for idea in output.ideas],
        "raw_response": output.raw_response,
        "selected_idea_ids": output.selected_idea_ids,
        "selection_status": output.selection_status,
        "source_stage_ids": output.source_stage_ids,
        "summary": output.summary,
        "warnings": output.warnings,
    }
