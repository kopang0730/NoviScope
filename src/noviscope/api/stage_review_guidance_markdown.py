from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from noviscope.api.stage_review_guidance import StageReviewGuidanceResponse

EMPTY_SECTION_ITEM: Final = "No items recorded."


def single_line_text(value: str) -> str:
    return " ".join(value.split())


def markdown_list(items: list[str]) -> list[str]:
    if not items:
        return [f"- {EMPTY_SECTION_ITEM}"]
    return [f"- {single_line_text(item)}" for item in items]


def build_stage_review_guidance_markdown(guidance: StageReviewGuidanceResponse) -> str:
    lines = [
        "# NoviScope Stage Review Guidance",
        "",
        "## Stage",
        f"- Stage ID: `{guidance.stage_id}`",
        f"- Agent ID: `{guidance.agent_id}`",
        f"- Status: `{guidance.status.value}`",
        f"- Approval state: `{guidance.approval_state.value}`",
        f"- Confidence: `{guidance.confidence}`",
        f"- Review required: `{str(guidance.review_required).lower()}`",
        f"- Can approve: `{str(guidance.can_approve).lower()}`",
        "",
        "## Blocking Reason",
        guidance.blocking_reason or "No blocking reason.",
        "",
        "## Evidence Summary",
        *markdown_list(guidance.evidence_summary),
        "",
        "## Human Review Checklist",
        *markdown_list(guidance.checklist),
        "",
        "## Warnings",
        *markdown_list(guidance.warnings),
        "",
        "## Review Notes",
        guidance.review_notes or "No review notes recorded.",
        "",
    ]
    return "\n".join(lines)


def stage_review_guidance_markdown_filename(stage_id: str) -> str:
    return f"noviscope-stage-review-{stage_id}.md"
