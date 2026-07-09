from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.quest import StageCard

DEMAND_APPROVED: Final = "demand_approved"
LITERATURE_SOURCES_PRESENT: Final = "literature_sources_present"
IDEA_SELECTED: Final = "idea_selected"
EXPERIMENT_PLAN_APPROVED: Final = "experiment_plan_approved"
PAPER_DRAFT_GENERATED: Final = "paper_draft_generated"
VERIFIED_EXPERIMENT_RESULT_RECORDED: Final = "verified_experiment_result_recorded"


class EvidenceAuditStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class EvidenceAuditIssueSeverity(StrEnum):
    BLOCKER = "blocker"
    REVIEW = "review"


@dataclass(frozen=True, slots=True)
class EvidenceAuditIssueSpec:
    agent_id: str
    code: str
    fallback_stage_title: str
    message: str
    severity: EvidenceAuditIssueSeverity


@dataclass(frozen=True, slots=True)
class StageAuditOutcome:
    passed_checks: tuple[str, ...]
    blocking_issues: tuple["EvidenceAuditIssueResponse", ...]
    review_items: tuple["EvidenceAuditIssueResponse", ...]


class EvidenceAuditIssueResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    agent_id: str
    code: str
    message: str
    severity: EvidenceAuditIssueSeverity
    stage_id: str
    stage_title: str


class QuestEvidenceAuditResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    audit_status: EvidenceAuditStatus
    blocking_issue_count: int
    blocking_issues: tuple[EvidenceAuditIssueResponse, ...]
    evidence_source_count: int
    passed_checks: tuple[str, ...]
    quest_id: str
    ready_for_formal_claims: bool
    review_item_count: int
    review_items: tuple[EvidenceAuditIssueResponse, ...]
    reviewed_stage_count: int
    total_stage_count: int


def make_issue(
    stage: StageCard | None,
    spec: EvidenceAuditIssueSpec,
) -> EvidenceAuditIssueResponse:
    if stage is None:
        return EvidenceAuditIssueResponse(
            agent_id=spec.agent_id,
            code=spec.code,
            message=spec.message,
            severity=spec.severity,
            stage_id="",
            stage_title=spec.fallback_stage_title,
        )
    return EvidenceAuditIssueResponse(
        agent_id=stage.agent_id,
        code=spec.code,
        message=spec.message,
        severity=spec.severity,
        stage_id=stage.id,
        stage_title=stage.title,
    )


def make_outcome(
    passed_checks: tuple[str, ...] = (),
    blocking_issues: tuple[EvidenceAuditIssueResponse, ...] = (),
    review_items: tuple[EvidenceAuditIssueResponse, ...] = (),
) -> StageAuditOutcome:
    return StageAuditOutcome(
        blocking_issues=blocking_issues,
        passed_checks=passed_checks,
        review_items=review_items,
    )


DEMAND_NOT_APPROVED: Final = EvidenceAuditIssueSpec(
    agent_id=DEMAND_VALIDATOR_AGENT_ID,
    code="demand_not_approved",
    fallback_stage_title="Demand validation",
    message="Demand validation must be completed and human-approved.",
    severity=EvidenceAuditIssueSeverity.BLOCKER,
)
DEMAND_SOURCES_MISSING: Final = EvidenceAuditIssueSpec(
    agent_id=DEMAND_VALIDATOR_AGENT_ID,
    code="demand_sources_missing",
    fallback_stage_title="Demand validation",
    message="Demand is approved but lacks recorded real-world evidence sources.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
LITERATURE_NOT_COMPLETE: Final = EvidenceAuditIssueSpec(
    agent_id=LITERATURE_SCOUT_AGENT_ID,
    code="literature_not_complete",
    fallback_stage_title="Literature scout",
    message="Literature scouting must complete before formal claims are ready.",
    severity=EvidenceAuditIssueSeverity.BLOCKER,
)
LITERATURE_SOURCES_MISSING: Final = EvidenceAuditIssueSpec(
    agent_id=LITERATURE_SCOUT_AGENT_ID,
    code="literature_sources_missing",
    fallback_stage_title="Literature scout",
    message="Literature scout completed without DOI, URL, arXiv, or paper refs.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
IDEA_NOT_SELECTED: Final = EvidenceAuditIssueSpec(
    agent_id=IDEA_GENERATOR_AGENT_ID,
    code="idea_not_selected",
    fallback_stage_title="Gap & hypothesis generator",
    message="A human-selected idea is required before experiment claims.",
    severity=EvidenceAuditIssueSeverity.BLOCKER,
)
EXPERIMENT_PLAN_NOT_APPROVED: Final = EvidenceAuditIssueSpec(
    agent_id=EXPERIMENT_PLANNER_AGENT_ID,
    code="experiment_plan_not_approved",
    fallback_stage_title="Experiment planner",
    message="Experiment plan must be completed and human-approved.",
    severity=EvidenceAuditIssueSeverity.BLOCKER,
)
EXPERIMENT_PLAN_MISSING_METRICS: Final = EvidenceAuditIssueSpec(
    agent_id=EXPERIMENT_PLANNER_AGENT_ID,
    code="experiment_plan_missing_metrics",
    fallback_stage_title="Experiment planner",
    message="Approved experiment plan should record evaluation metrics.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
EXPERIMENT_PLAN_MISSING_SCRIPT: Final = EvidenceAuditIssueSpec(
    agent_id=EXPERIMENT_PLANNER_AGENT_ID,
    code="experiment_plan_missing_script",
    fallback_stage_title="Experiment planner",
    message="Approved experiment plan should include a first runnable script plan.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
EXPERIMENT_RESULTS_MISSING: Final = EvidenceAuditIssueSpec(
    agent_id=EXPERIMENT_PLANNER_AGENT_ID,
    code="experiment_results_missing",
    fallback_stage_title="Experiment planner",
    message="No verified experiment result record is available for paper claims.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
PAPER_DRAFT_NOT_GENERATED: Final = EvidenceAuditIssueSpec(
    agent_id=PAPER_MEETING_WRITER_AGENT_ID,
    code="paper_draft_not_generated",
    fallback_stage_title="Paper & meeting writer",
    message="Paper and meeting artifacts must be generated before formal claims.",
    severity=EvidenceAuditIssueSeverity.BLOCKER,
)
PAPER_DRAFT_NEEDS_REVIEW: Final = EvidenceAuditIssueSpec(
    agent_id=PAPER_MEETING_WRITER_AGENT_ID,
    code="paper_draft_needs_review",
    fallback_stage_title="Paper & meeting writer",
    message="Generated writing artifacts still need human review.",
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
PAPER_RESULTS_NOT_ALIGNED: Final = EvidenceAuditIssueSpec(
    agent_id=PAPER_MEETING_WRITER_AGENT_ID,
    code="paper_results_not_aligned",
    fallback_stage_title="Paper & meeting writer",
    message=(
        "Approved writing artifacts must be regenerated from the verified experiment result."
    ),
    severity=EvidenceAuditIssueSeverity.REVIEW,
)
