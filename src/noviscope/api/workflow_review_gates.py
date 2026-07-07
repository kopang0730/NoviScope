from typing import ClassVar, Final

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)

router = APIRouter()


class LocalizedTextResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    en: str
    zh: str


class WorkflowReviewGateResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    blocks_agent_ids: tuple[str, ...]
    gate_id: str
    required_evidence: tuple[str, ...]
    review_endpoint_template: str
    risk_if_skipped: LocalizedTextResponse
    source_agent_id: str
    terminal_review: bool
    user_action_label: LocalizedTextResponse


class WorkflowReviewGatesResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    gates: tuple[WorkflowReviewGateResponse, ...]
    version: str


REVIEW_GATES: Final[tuple[WorkflowReviewGateResponse, ...]] = (
    WorkflowReviewGateResponse(
        blocks_agent_ids=(LITERATURE_SCOUT_AGENT_ID, IDEA_GENERATOR_AGENT_ID),
        gate_id="demand_truth_review",
        required_evidence=("real_world_source", "human_verdict", "go_or_no_go"),
        review_endpoint_template="/stages/{stage_id}/demand-review",
        risk_if_skipped=LocalizedTextResponse(
            en="A weak or fake demand can make all later experiments irrelevant.",
            zh="如果需求不真实，后续实验即使跑通也可能没有选题价值。",
        ),
        source_agent_id=DEMAND_VALIDATOR_AGENT_ID,
        terminal_review=False,
        user_action_label=LocalizedTextResponse(
            en="Review demand evidence",
            zh="复核需求真实性",
        ),
    ),
    WorkflowReviewGateResponse(
        blocks_agent_ids=(EXPERIMENT_PLANNER_AGENT_ID,),
        gate_id="idea_selection_review",
        required_evidence=("selected_idea_ids", "based_on_papers", "human_review_notes"),
        review_endpoint_template="/stages/{stage_id}/select-ideas",
        risk_if_skipped=LocalizedTextResponse(
            en="Experiment planning can drift away from evidence-linked research gaps.",
            zh="实验设计可能脱离已有文献证据和真实 gap。",
        ),
        source_agent_id=IDEA_GENERATOR_AGENT_ID,
        terminal_review=False,
        user_action_label=LocalizedTextResponse(
            en="Select idea for experiment design",
            zh="选择进入实验设计的创新点",
        ),
    ),
    WorkflowReviewGateResponse(
        blocks_agent_ids=(PAPER_MEETING_WRITER_AGENT_ID,),
        gate_id="experiment_plan_review",
        required_evidence=("dataset_access", "baseline_plan", "metrics", "review_notes"),
        review_endpoint_template="/stages/{stage_id}",
        risk_if_skipped=LocalizedTextResponse(
            en="Writing can present an unchecked plan as if it were validated experiment design.",
            zh="论文写作可能把未复核实验方案写得像已经验证过一样。",
        ),
        source_agent_id=EXPERIMENT_PLANNER_AGENT_ID,
        terminal_review=False,
        user_action_label=LocalizedTextResponse(
            en="Review experiment plan",
            zh="复核实验设计",
        ),
    ),
    WorkflowReviewGateResponse(
        blocks_agent_ids=(),
        gate_id="paper_artifact_review",
        required_evidence=(
            "verified_facts",
            "model_generated_hypotheses",
            "experiment_results_not_available",
            "human_review_required",
        ),
        review_endpoint_template="/stages/{stage_id}",
        risk_if_skipped=LocalizedTextResponse(
            en="The draft may imply unverified experiments or unsupported claims are complete.",
            zh="论文草稿可能暗示未验证实验已经完成，或把缺少支撑的观点写成结论。",
        ),
        source_agent_id=PAPER_MEETING_WRITER_AGENT_ID,
        terminal_review=True,
        user_action_label=LocalizedTextResponse(
            en="Review generated paper artifacts",
            zh="复核生成的论文与汇报材料",
        ),
    ),
)


@router.get("/workflow/review-gates", response_model=WorkflowReviewGatesResponse)
def get_workflow_review_gates() -> WorkflowReviewGatesResponse:
    return WorkflowReviewGatesResponse(
        gates=REVIEW_GATES,
        version="2026-07-review-gates-v1",
    )
