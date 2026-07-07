from collections.abc import Sequence

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.evidence_audit_contract import (
    DEMAND_APPROVED,
    DEMAND_NOT_APPROVED,
    DEMAND_SOURCES_MISSING,
    EXPERIMENT_PLAN_APPROVED,
    EXPERIMENT_PLAN_MISSING_METRICS,
    EXPERIMENT_PLAN_MISSING_SCRIPT,
    EXPERIMENT_PLAN_NOT_APPROVED,
    EXPERIMENT_RESULTS_MISSING,
    IDEA_NOT_SELECTED,
    IDEA_SELECTED,
    LITERATURE_NOT_COMPLETE,
    LITERATURE_SOURCES_MISSING,
    LITERATURE_SOURCES_PRESENT,
    PAPER_DRAFT_GENERATED,
    PAPER_DRAFT_NEEDS_REVIEW,
    PAPER_DRAFT_NOT_GENERATED,
    VERIFIED_EXPERIMENT_RESULT_RECORDED,
    EvidenceAuditIssueResponse,
    EvidenceAuditStatus,
    QuestEvidenceAuditResponse,
    StageAuditOutcome,
    make_issue,
    make_outcome,
)
from noviscope.api.evidence_audit_readers import (
    completed_stage,
    count_evidence_sources,
    find_stage,
    has_selected_idea,
    has_verified_experiment_result,
    read_payload_refs,
    stage_is_complete,
)
from noviscope.api.evidence_ledger import collect_source_refs
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.models.quest import StageCard


def audit_demand(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or complete_stage.human_approved is not True:
        return make_outcome(blocking_issues=(make_issue(stage, DEMAND_NOT_APPROVED),))
    demand_refs = (
        read_payload_refs(complete_stage.evidence_payload, "human_demand_sources")
        or read_payload_refs(complete_stage.output_payload, "evidence_for_demand")
    )
    if not demand_refs:
        return make_outcome(
            passed_checks=(DEMAND_APPROVED,),
            review_items=(make_issue(complete_stage, DEMAND_SOURCES_MISSING),),
        )
    return make_outcome(passed_checks=(DEMAND_APPROVED,))


def audit_literature(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None:
        return make_outcome(blocking_issues=(make_issue(stage, LITERATURE_NOT_COMPLETE),))
    if collect_source_refs(complete_stage):
        return make_outcome(passed_checks=(LITERATURE_SOURCES_PRESENT,))
    return make_outcome(
        review_items=(make_issue(complete_stage, LITERATURE_SOURCES_MISSING),),
    )


def audit_idea(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or not has_selected_idea(complete_stage):
        return make_outcome(blocking_issues=(make_issue(stage, IDEA_NOT_SELECTED),))
    return make_outcome(passed_checks=(IDEA_SELECTED,))


def audit_experiment(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or complete_stage.human_approved is not True:
        return make_outcome(
            blocking_issues=(make_issue(stage, EXPERIMENT_PLAN_NOT_APPROVED),),
        )
    review_items: list[EvidenceAuditIssueResponse] = []
    if not read_payload_refs(complete_stage.output_payload, "metrics"):
        review_items.append(make_issue(complete_stage, EXPERIMENT_PLAN_MISSING_METRICS))
    if not read_payload_refs(complete_stage.output_payload, "first_runnable_script_plan"):
        review_items.append(make_issue(complete_stage, EXPERIMENT_PLAN_MISSING_SCRIPT))
    passed_checks = (EXPERIMENT_PLAN_APPROVED,)
    if has_verified_experiment_result(complete_stage):
        passed_checks = (EXPERIMENT_PLAN_APPROVED, VERIFIED_EXPERIMENT_RESULT_RECORDED)
    else:
        review_items.append(make_issue(complete_stage, EXPERIMENT_RESULTS_MISSING))
    return make_outcome(passed_checks=passed_checks, review_items=tuple(review_items))


def audit_paper(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None:
        return make_outcome(blocking_issues=(make_issue(stage, PAPER_DRAFT_NOT_GENERATED),))
    if complete_stage.human_approved is not True:
        return make_outcome(
            passed_checks=(PAPER_DRAFT_GENERATED,),
            review_items=(make_issue(complete_stage, PAPER_DRAFT_NEEDS_REVIEW),),
        )
    return make_outcome(passed_checks=(PAPER_DRAFT_GENERATED,))


def combine_outcomes(outcomes: Sequence[StageAuditOutcome]) -> StageAuditOutcome:
    return StageAuditOutcome(
        blocking_issues=tuple(
            issue for outcome in outcomes for issue in outcome.blocking_issues
        ),
        passed_checks=tuple(check for outcome in outcomes for check in outcome.passed_checks),
        review_items=tuple(item for outcome in outcomes for item in outcome.review_items),
    )


def build_audit_status(outcome: StageAuditOutcome) -> EvidenceAuditStatus:
    if outcome.blocking_issues:
        return EvidenceAuditStatus.BLOCKED
    if outcome.review_items:
        return EvidenceAuditStatus.NEEDS_REVIEW
    return EvidenceAuditStatus.READY


def build_quest_evidence_audit(
    quest_id: str,
    stages: Sequence[StageCard],
) -> QuestEvidenceAuditResponse:
    outcome = combine_outcomes(
        (
            audit_demand(find_stage(stages, DEMAND_VALIDATOR_AGENT_ID)),
            audit_literature(find_stage(stages, LITERATURE_SCOUT_AGENT_ID)),
            audit_idea(find_stage(stages, IDEA_GENERATOR_AGENT_ID)),
            audit_experiment(find_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)),
            audit_paper(find_stage(stages, PAPER_MEETING_WRITER_AGENT_ID)),
        )
    )
    audit_status = build_audit_status(outcome)
    return QuestEvidenceAuditResponse(
        audit_status=audit_status,
        blocking_issue_count=len(outcome.blocking_issues),
        blocking_issues=outcome.blocking_issues,
        evidence_source_count=count_evidence_sources(stages),
        passed_checks=outcome.passed_checks,
        quest_id=quest_id,
        ready_for_formal_claims=audit_status == EvidenceAuditStatus.READY,
        review_item_count=len(outcome.review_items),
        review_items=outcome.review_items,
        reviewed_stage_count=sum(stage_is_complete(stage) for stage in stages),
        total_stage_count=len(stages),
    )
