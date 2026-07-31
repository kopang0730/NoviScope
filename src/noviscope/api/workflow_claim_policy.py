from typing import ClassVar, Final, Literal, TypeAlias

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

ClaimType: TypeAlias = Literal[
    "experiment_result_unavailable",
    "human_review_required",
    "model_generated_hypothesis",
    "source_supported_claim",
    "verified_fact",
]

router = APIRouter()

PAPER_ARTIFACT_FIELDS: Final[tuple[str, ...]] = (
    "chinese_research_brief_markdown",
    "english_research_brief_markdown",
    "meeting_outline_markdown",
    "ieee_paper_skeleton_markdown",
)


class LocalizedTextResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    en: str
    zh: str


class ClaimCategoryResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    allowed_in_artifacts: tuple[str, ...]
    claim_type: ClaimType
    description: LocalizedTextResponse
    output_field: str
    requires_human_review: bool
    requires_source_reference: bool


class ProhibitedClaimResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    pattern: str
    reason: LocalizedTextResponse


class WorkflowClaimPolicyResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    categories: tuple[ClaimCategoryResponse, ...]
    default_result_section_notice: LocalizedTextResponse
    prohibited_claims: tuple[ProhibitedClaimResponse, ...]
    version: str


CLAIM_CATEGORIES: Final[tuple[ClaimCategoryResponse, ...]] = (
    ClaimCategoryResponse(
        allowed_in_artifacts=PAPER_ARTIFACT_FIELDS,
        claim_type="verified_fact",
        description=LocalizedTextResponse(
            en="A factual statement directly supported by saved workflow evidence.",
            zh="由已保存工作流证据直接支撑的事实性陈述。",
        ),
        output_field="verified_facts",
        requires_human_review=False,
        requires_source_reference=True,
    ),
    ClaimCategoryResponse(
        allowed_in_artifacts=PAPER_ARTIFACT_FIELDS,
        claim_type="source_supported_claim",
        description=LocalizedTextResponse(
            en="A claim grounded in cited literature, demand sources, or experiment plans.",
            zh="基于引用文献、需求来源或实验计划的论述。",
        ),
        output_field="source_stage_ids",
        requires_human_review=True,
        requires_source_reference=True,
    ),
    ClaimCategoryResponse(
        allowed_in_artifacts=PAPER_ARTIFACT_FIELDS,
        claim_type="model_generated_hypothesis",
        description=LocalizedTextResponse(
            en="A speculative research hypothesis generated from available evidence.",
            zh="基于已有证据生成、但仍属于推测的研究假设。",
        ),
        output_field="model_generated_hypotheses",
        requires_human_review=True,
        requires_source_reference=True,
    ),
    ClaimCategoryResponse(
        allowed_in_artifacts=PAPER_ARTIFACT_FIELDS,
        claim_type="experiment_result_unavailable",
        description=LocalizedTextResponse(
            en="A required notice that GPU experiments or benchmarks have not run yet.",
            zh="必须提示 GPU 实验或 benchmark 尚未运行。",
        ),
        output_field="experiment_results_not_available",
        requires_human_review=False,
        requires_source_reference=False,
    ),
    ClaimCategoryResponse(
        allowed_in_artifacts=PAPER_ARTIFACT_FIELDS,
        claim_type="human_review_required",
        description=LocalizedTextResponse(
            en="A claim or section that needs manual verification before submission use.",
            zh="投稿或汇报前需要人工确认的论点或章节。",
        ),
        output_field="human_review_required",
        requires_human_review=True,
        requires_source_reference=False,
    ),
)

PROHIBITED_CLAIMS: Final[tuple[ProhibitedClaimResponse, ...]] = (
    ProhibitedClaimResponse(
        pattern="completed benchmark, metric value, or leaderboard claim without run evidence",
        reason=LocalizedTextResponse(
            en="NoviScope must not report experimental results that were not actually produced.",
            zh="NoviScope 不能把未真实产生的实验结果写成已经完成。",
        ),
    ),
    ProhibitedClaimResponse(
        pattern="invented citation, DOI, venue, dataset, or repository",
        reason=LocalizedTextResponse(
            en="Unsupported references destroy traceability and review value.",
            zh="无来源引用会破坏可追溯性和复核价值。",
        ),
    ),
    ProhibitedClaimResponse(
        pattern="high-confidence conclusion from model-only reasoning",
        reason=LocalizedTextResponse(
            en="Conclusions require evidence or experiments, not only language-model synthesis.",
            zh="结论必须有证据或实验支撑，不能只依赖模型综合。",
        ),
    ),
)

DEFAULT_RESULT_SECTION_NOTICE: Final = LocalizedTextResponse(
    en=(
        "No experiment results are available yet. Keep Results and Conclusion sections "
        "as placeholders until reproducible runs produce reviewed metrics."
    ),
    zh=(
        "目前还没有可用实验结果。Results 和 Conclusion 应保持占位，直到可复现实验产出"
        "经过复核的指标。"
    ),
)


@router.get("/workflow/claim-policy", response_model=WorkflowClaimPolicyResponse)
def get_workflow_claim_policy() -> WorkflowClaimPolicyResponse:
    return WorkflowClaimPolicyResponse(
        categories=CLAIM_CATEGORIES,
        default_result_section_notice=DEFAULT_RESULT_SECTION_NOTICE,
        prohibited_claims=PROHIBITED_CLAIMS,
        version="2026-07-claim-policy-v1",
    )
