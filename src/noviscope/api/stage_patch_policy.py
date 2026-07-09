from dataclasses import dataclass

from noviscope.core.stage_policy import PAPER_MEETING_WRITER_AGENT_ID
from noviscope.models.quest import StageCard, StageStatus

PAPER_WRITER_RUNNER_MANAGED_FIELDS = frozenset(
    {"evidence_payload", "input_payload", "output_payload", "summary"}
)
PAPER_WRITER_REVIEW_FIELDS = frozenset({"human_approved", "review_notes"})


@dataclass(frozen=True, slots=True)
class StagePatchPolicyError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


def ensure_paper_writer_patch_is_review_only(
    stage: StageCard,
    *,
    fields: set[str],
    target_status: StageStatus | None,
) -> None:
    if stage.agent_id != PAPER_MEETING_WRITER_AGENT_ID:
        return
    if fields & PAPER_WRITER_RUNNER_MANAGED_FIELDS:
        raise StagePatchPolicyError(
            "Paper Writer execution fields can only be changed by the server-side stage runner."
        )
    if fields & PAPER_WRITER_REVIEW_FIELDS and stage.status != StageStatus.COMPLETE:
        raise StagePatchPolicyError("Paper Writer can only be reviewed after it completes.")
    if (
        "status" in fields
        and target_status is not None
        and target_status != stage.status
        and not (
            stage.status == StageStatus.COMPLETE
            and stage.human_approved is False
            and target_status == StageStatus.BLOCKED
        )
    ):
        raise StagePatchPolicyError(
            "Paper Writer status can only be changed by the server-side stage runner."
        )
