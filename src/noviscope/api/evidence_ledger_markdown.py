from typing import Final, Protocol, assert_never

from noviscope.core.stage_policy import StageConfidence
from noviscope.models.quest import StageStatus

MARKDOWN_MEDIA_TYPE: Final = "text/markdown; charset=utf-8"


class EvidenceLedgerEntryView(Protocol):
    agent_id: str
    confidence: StageConfidence
    human_approved: bool | None
    provider_id: str
    provider_model: str
    requires_human_review: bool
    review_notes: str
    source_policy: str
    source_refs: tuple[str, ...]
    stage_id: str
    stage_status: StageStatus
    stage_title: str
    summary: str


class QuestEvidenceLedgerView(Protocol):
    entries: tuple[EvidenceLedgerEntryView, ...]
    evidence_entry_count: int
    missing_evidence_count: int
    quest_id: str
    requires_human_review_count: int
    total_stage_count: int


def evidence_ledger_filename(quest_id: str) -> str:
    return f"noviscope-evidence-ledger-{quest_id}.md"


def bool_label(value: bool) -> str:
    return "Yes" if value else "No"


def human_approval_label(value: bool | None) -> str:
    match value:
        case True:
            return "Yes"
        case False:
            return "No"
        case None:
            return "Not recorded"
        case unreachable:
            assert_never(unreachable)


def text_or_fallback(value: str, fallback: str) -> str:
    return value if value else fallback


def source_refs_label(entry: EvidenceLedgerEntryView) -> str:
    return "; ".join(entry.source_refs) if entry.source_refs else "None recorded"


def provider_label(entry: EvidenceLedgerEntryView) -> str:
    if entry.provider_id and entry.provider_model:
        return f"{entry.provider_id} / {entry.provider_model}"
    if entry.provider_id:
        return entry.provider_id
    if entry.provider_model:
        return entry.provider_model
    return "None recorded"


def render_evidence_ledger_markdown(ledger: QuestEvidenceLedgerView) -> str:
    lines = [
        f"# NoviScope Evidence Ledger: {ledger.quest_id}",
        "",
        (
            "Review-only export. This ledger records saved stage evidence, source "
            "references, confidence, and human-review state; it does not claim "
            "unrun experiments were completed."
        ),
        "",
        "## Trust Summary",
        f"- Total stages: {ledger.total_stage_count}",
        f"- Evidence-bearing stages: {ledger.evidence_entry_count}",
        f"- Missing evidence stages: {ledger.missing_evidence_count}",
        f"- Stages requiring human review: {ledger.requires_human_review_count}",
        "",
        "## Stage Evidence",
    ]
    for entry in ledger.entries:
        lines.extend(
            [
                "",
                f"### {entry.stage_title} (`{entry.stage_id}`)",
                f"- Agent: {entry.agent_id}",
                f"- Status: {entry.stage_status.value}",
                f"- Confidence: {entry.confidence}",
                f"- Human approved: {human_approval_label(entry.human_approved)}",
                f"- Requires human review: {bool_label(entry.requires_human_review)}",
                f"- Provider: {provider_label(entry)}",
                f"- Source policy: {entry.source_policy}",
                f"- Source refs: {source_refs_label(entry)}",
                f"- Review notes: {text_or_fallback(entry.review_notes, 'None recorded')}",
                f"- Summary: {text_or_fallback(entry.summary, 'None recorded')}",
            ]
        )
    return "\n".join(lines) + "\n"
