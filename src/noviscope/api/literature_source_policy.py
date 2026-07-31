from typing import ClassVar, Final, Literal, TypeAlias

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from noviscope.agents.literature_scout import OPENALEX_SOURCE, RECENT_RELEVANCE_MULTIPLIER
from noviscope.agents.literature_source_quality import RECENT_YEAR_WINDOW, TOP_VENUE_MARKERS
from noviscope.agents.openalex_client import FIVE_YEAR_LOOKBACK, MAX_PAPER_RESULTS

router = APIRouter()

EvidenceStrength: TypeAlias = Literal["strong", "medium", "low", "unknown"]


class LiteraturePrimarySourceResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    display_name: str
    max_results_per_run: int
    source_id: str


class LiteratureRecencyPolicyResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    lookback_years: int
    older_than_lookback_guidance: str
    recent_priority_years: int
    recent_score_multiplier: float


class LiteratureReliabilityLevelResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    citation_guidance: str
    description: str
    evidence_strength: EvidenceStrength
    frontend_badge: str
    label: str
    level: str
    requires_human_review: bool
    rule_summary: str


class LiteratureSourcePolicyResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    anti_hallucination_rules: tuple[str, ...]
    human_review_required: bool
    primary_source: LiteraturePrimarySourceResponse
    recency_policy: LiteratureRecencyPolicyResponse
    reliability_levels: tuple[LiteratureReliabilityLevelResponse, ...]
    top_venue_markers: tuple[str, ...]
    version: str


PRIMARY_SOURCE: Final = LiteraturePrimarySourceResponse(
    display_name="OpenAlex Works API",
    max_results_per_run=MAX_PAPER_RESULTS,
    source_id=OPENALEX_SOURCE,
)

RECENCY_POLICY: Final = LiteratureRecencyPolicyResponse(
    lookback_years=FIVE_YEAR_LOOKBACK,
    older_than_lookback_guidance=(
        "Older papers can be useful background, but should not dominate novelty claims."
    ),
    recent_priority_years=RECENT_YEAR_WINDOW,
    recent_score_multiplier=RECENT_RELEVANCE_MULTIPLIER,
)

RELIABILITY_LEVELS: Final[tuple[LiteratureReliabilityLevelResponse, ...]] = (
    LiteratureReliabilityLevelResponse(
        citation_guidance=(
            "Use as strong discovery evidence, but verify the full paper, venue, "
            "and method claims before citing."
        ),
        description="Venue metadata matches NoviScope's curated top AI/CV venue marker list.",
        evidence_strength="strong",
        frontend_badge="Top venue",
        label="Top conference or journal",
        level="top_conference_or_journal",
        requires_human_review=True,
        rule_summary="The venue name contains one of the configured top venue markers.",
    ),
    LiteratureReliabilityLevelResponse(
        citation_guidance=(
            "Use as credible supporting evidence after checking the publisher page and paper type."
        ),
        description="OpenAlex marks the work or source as a conference, journal, or article type.",
        evidence_strength="medium",
        frontend_badge="Peer reviewed",
        label="Peer reviewed",
        level="peer_reviewed",
        requires_human_review=True,
        rule_summary="The OpenAlex work type or source type suggests peer review.",
    ),
    LiteratureReliabilityLevelResponse(
        citation_guidance=(
            "Use for trend discovery only; it should not be treated as peer-reviewed evidence."
        ),
        description="The venue looks like arXiv, or OpenAlex reports the work as posted content.",
        evidence_strength="low",
        frontend_badge="Preprint",
        label="arXiv or preprint",
        level="arxiv_preprint",
        requires_human_review=True,
        rule_summary="The venue contains arXiv, or the work type is posted-content.",
    ),
    LiteratureReliabilityLevelResponse(
        citation_guidance=(
            "Do not use as primary support until a human verifies the source "
            "and publication status."
        ),
        description="OpenAlex metadata does not provide enough source quality signal.",
        evidence_strength="unknown",
        frontend_badge="Unknown",
        label="Unknown",
        level="unknown",
        requires_human_review=True,
        rule_summary="No top venue, peer-review, or preprint signal was detected.",
    ),
)

ANTI_HALLUCINATION_RULES: Final[tuple[str, ...]] = (
    "Do not invent papers, venues, DOI values, arXiv identifiers, metrics, or conclusions.",
    "If OpenAlex returns no matching works, show an empty result and state that nothing was found.",
    "Treat metadata as a discovery aid; verify the original PDF or publisher page before citing.",
)


@router.get("/literature/source-policy")
def get_literature_source_policy() -> LiteratureSourcePolicyResponse:
    return LiteratureSourcePolicyResponse(
        anti_hallucination_rules=ANTI_HALLUCINATION_RULES,
        human_review_required=True,
        primary_source=PRIMARY_SOURCE,
        recency_policy=RECENCY_POLICY,
        reliability_levels=RELIABILITY_LEVELS,
        top_venue_markers=TOP_VENUE_MARKERS,
        version="2026-07-literature-source-policy-v1",
    )
