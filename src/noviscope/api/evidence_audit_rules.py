from collections.abc import Sequence

from noviscope.agents.experiment_planner import has_selected_idea
from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.api.evidence_audit_contract import (
    DEMAND_APPROVED,
    DEMAND_NOT_APPROVED,
    DEMAND_SOURCES_MISSING,
    EVIDENCE_AUDIT_APPROVED,
    EVIDENCE_AUDIT_NOT_APPROVED,
    EXPERIMENT_PLAN_APPROVED,
    EXPERIMENT_PLAN_MISSING_METRICS,
    EXPERIMENT_PLAN_MISSING_SCRIPT,
    EXPERIMENT_PLAN_NOT_APPROVED,
    EXPERIMENT_RESULTS_INVALID,
    EXPERIMENT_RESULTS_MISSING,
    IDEA_NOT_SELECTED,
    IDEA_SELECTED,
    LITERATURE_NOT_COMPLETE,
    LITERATURE_SOURCES_INVALID,
    LITERATURE_SOURCES_MISSING,
    LITERATURE_SOURCES_PRESENT,
    PAPER_ARTIFACTS_UNTRUSTED,
    PAPER_DRAFT_GENERATED,
    PAPER_DRAFT_NEEDS_REVIEW,
    PAPER_DRAFT_NOT_GENERATED,
    PAPER_RESULTS_NOT_ALIGNED,
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
    evidence_auditor_is_approved,
    find_current_evidence_auditor,
    find_stage,
    has_downloadable_paper_artifacts,
    has_recorded_human_demand_evidence,
    has_trusted_paper_artifact_policy,
    paper_results_are_aligned,
    read_payload_refs,
    stage_is_complete,
    trusted_result_stage_with_invalid_entries,
    trusted_verified_experiment_result_records,
)
from noviscope.api.evidence_audit_reference_rules import (
    paper_collections_have_invalid_references,
)
from noviscope.api.evidence_ledger import collect_paper_source_refs
from noviscope.core.json_types import JsonObject
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
    if not has_recorded_human_demand_evidence(complete_stage):
        return make_outcome(
            passed_checks=(DEMAND_APPROVED,),
            review_items=(make_issue(complete_stage, DEMAND_SOURCES_MISSING),),
        )
    return make_outcome(passed_checks=(DEMAND_APPROVED,))


def audit_literature(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None:
        return make_outcome(blocking_issues=(make_issue(stage, LITERATURE_NOT_COMPLETE),))
    source_refs = collect_paper_source_refs(complete_stage)
    if paper_collections_have_invalid_references(complete_stage):
        return make_outcome(
            passed_checks=(LITERATURE_SOURCES_PRESENT,) if source_refs else (),
            review_items=(make_issue(complete_stage, LITERATURE_SOURCES_INVALID),),
        )
    if source_refs:
        return make_outcome(passed_checks=(LITERATURE_SOURCES_PRESENT,))
    return make_outcome(
        review_items=(make_issue(complete_stage, LITERATURE_SOURCES_MISSING),),
    )


def audit_idea(stage: StageCard | None) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or not has_selected_idea(complete_stage):
        return make_outcome(blocking_issues=(make_issue(stage, IDEA_NOT_SELECTED),))
    return make_outcome(passed_checks=(IDEA_SELECTED,))


def audit_experiment(
    stage: StageCard | None,
    *,
    invalid_result_stage: StageCard | None,
    verified_results: Sequence[JsonObject],
) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or complete_stage.human_approved is not True:
        return make_outcome(
            blocking_issues=(make_issue(stage, EXPERIMENT_PLAN_NOT_APPROVED),),
        )
    blocking_issues: list[EvidenceAuditIssueResponse] = []
    review_items: list[EvidenceAuditIssueResponse] = []
    if not read_payload_refs(complete_stage.output_payload, "metrics"):
        review_items.append(make_issue(complete_stage, EXPERIMENT_PLAN_MISSING_METRICS))
    if not read_payload_refs(complete_stage.output_payload, "first_runnable_script_plan"):
        review_items.append(make_issue(complete_stage, EXPERIMENT_PLAN_MISSING_SCRIPT))
    passed_checks = (EXPERIMENT_PLAN_APPROVED,)
    if invalid_result_stage is not None:
        blocking_issues.append(
            make_issue(invalid_result_stage, EXPERIMENT_RESULTS_INVALID)
        )
    if verified_results:
        passed_checks = (EXPERIMENT_PLAN_APPROVED, VERIFIED_EXPERIMENT_RESULT_RECORDED)
    else:
        blocking_issues.append(make_issue(None, EXPERIMENT_RESULTS_MISSING))
    return make_outcome(
        blocking_issues=tuple(blocking_issues),
        passed_checks=passed_checks,
        review_items=tuple(review_items),
    )


def audit_evidence_auditor(
    *,
    stages: Sequence[StageCard],
) -> StageAuditOutcome:
    stage = find_current_evidence_auditor(stages)
    if not evidence_auditor_is_approved(stage, stages):
        return make_outcome(
            blocking_issues=(make_issue(stage, EVIDENCE_AUDIT_NOT_APPROVED),)
        )
    return make_outcome(passed_checks=(EVIDENCE_AUDIT_APPROVED,))


def audit_paper(
    stage: StageCard | None,
    *,
    verified_results: Sequence[JsonObject],
) -> StageAuditOutcome:
    complete_stage = completed_stage(stage)
    if complete_stage is None or not has_downloadable_paper_artifacts(complete_stage):
        return make_outcome(blocking_issues=(make_issue(stage, PAPER_DRAFT_NOT_GENERATED),))
    if not has_trusted_paper_artifact_policy(complete_stage):
        return make_outcome(
            blocking_issues=(make_issue(complete_stage, PAPER_ARTIFACTS_UNTRUSTED),)
        )
    if complete_stage.human_approved is not True:
        return make_outcome(
            passed_checks=(PAPER_DRAFT_GENERATED,),
            review_items=(make_issue(complete_stage, PAPER_DRAFT_NEEDS_REVIEW),),
        )
    if (
        verified_results
        and not paper_results_are_aligned(complete_stage, verified_results)
    ):
        return make_outcome(
            passed_checks=(PAPER_DRAFT_GENERATED,),
            review_items=(make_issue(complete_stage, PAPER_RESULTS_NOT_ALIGNED),),
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
    experiment_stage = find_stage(stages, EXPERIMENT_PLANNER_AGENT_ID)
    verified_results = trusted_verified_experiment_result_records(stages)
    invalid_result_stage = trusted_result_stage_with_invalid_entries(stages)
    outcome = combine_outcomes(
        (
            audit_demand(find_stage(stages, DEMAND_VALIDATOR_AGENT_ID)),
            audit_literature(find_stage(stages, LITERATURE_SCOUT_AGENT_ID)),
            audit_idea(find_stage(stages, IDEA_GENERATOR_AGENT_ID)),
            audit_experiment(
                experiment_stage,
                invalid_result_stage=invalid_result_stage,
                verified_results=verified_results,
            ),
            audit_paper(
                find_stage(stages, PAPER_MEETING_WRITER_AGENT_ID),
                verified_results=verified_results,
            ),
            audit_evidence_auditor(stages=stages),
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
