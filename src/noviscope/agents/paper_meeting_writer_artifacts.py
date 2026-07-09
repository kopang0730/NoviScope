from dataclasses import dataclass

from noviscope.agents.paper_meeting_writer_results import ExperimentResultsContext
from noviscope.agents.paper_meeting_writer_types import (
    HUMAN_REVIEW_NOTICE,
    NO_RESULTS_NOTICE,
    PaperMeetingWriterRequest,
)

MODEL_MARKDOWN_REPLACED_WARNING = (
    "Model-generated Markdown was retained only in raw_response; downloadable "
    "artifacts were rebuilt from trusted result context."
)
PAPER_ARTIFACT_POLICY_VERSION = "server-guardrailed-v1"


@dataclass(frozen=True, slots=True)
class GuardrailedArtifacts:
    chinese_research_brief_markdown: str
    english_research_brief_markdown: str
    meeting_outline_markdown: str
    ieee_paper_skeleton_markdown: str


def build_guardrailed_artifacts(
    request: PaperMeetingWriterRequest,
    result_context: ExperimentResultsContext,
) -> GuardrailedArtifacts:
    title = single_line(request.quest_title)
    direction = single_line(request.initial_direction)
    results = bullet_lines(result_context.verified_facts or [NO_RESULTS_NOTICE])
    reviews = bullet_lines(
        unique_items([HUMAN_REVIEW_NOTICE, *result_context.human_review_required])
    )
    framing = (
        f"- User-provided title (unverified): {title}\n"
        f"- User-provided direction (unverified): {direction}"
    )
    return GuardrailedArtifacts(
        chinese_research_brief_markdown=(
            "# 中文研究 Brief\n\n"
            "## 用户提供的研究框架（未验证）\n"
            f"{framing}\n\n"
            "## 已验证实验结果\n"
            f"{results}\n\n"
            "## 人工复核\n"
            f"{reviews}"
        ),
        english_research_brief_markdown=(
            "# Research Brief\n\n"
            "## User-provided research framing (unverified)\n"
            f"{framing}\n\n"
            "## Verified experiment results\n"
            f"{results}\n\n"
            "## Human review\n"
            f"{reviews}"
        ),
        meeting_outline_markdown=(
            "# Group Meeting Outline\n\n"
            "## 1. Research framing to review\n"
            f"{framing}\n\n"
            "## 2. Verified experiment results\n"
            f"{results}\n\n"
            "## 3. Review decisions\n"
            f"{reviews}"
        ),
        ieee_paper_skeleton_markdown=(
            "# IEEE Paper Skeleton\n\n"
            "## Abstract\n"
            "Placeholder pending evidence-backed drafting and human review.\n\n"
            "## Introduction\n"
            f"{framing}\n\n"
            "## Related Work\n"
            "Placeholder pending citation and claim-reference verification.\n\n"
            "## Method\n"
            "Placeholder pending an approved hypothesis and implementation record.\n\n"
            "## Experiments\n"
            "Placeholder pending reproducible run provenance.\n\n"
            "## Results\n"
            f"{results}\n\n"
            "## Conclusion\n"
            "Placeholder pending verified results and human review.\n\n"
            "## Evidence and Review\n"
            f"{reviews}"
        ),
    )


def single_line(value: str) -> str:
    return " ".join(value.split())


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {single_line(item)}" for item in items)


def unique_items(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
