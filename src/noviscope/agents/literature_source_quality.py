import re
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, assert_never

from noviscope.agents.openalex_client import FIVE_YEAR_LOOKBACK, OpenAlexWork

RECENT_YEAR_WINDOW: Final = 3
TOP_VENUE_ALIASES: Final = (
    (
        "cvpr",
        (
            "cvpr",
            "computer vision and pattern recognition",
            "conference on computer vision and pattern recognition",
        ),
    ),
    ("iccv", ("iccv", "international conference on computer vision")),
    ("eccv", ("eccv", "european conference on computer vision")),
    (
        "tpami",
        (
            "tpami",
            "t-pami",
            "transactions on pattern analysis and machine intelligence",
        ),
    ),
    ("ijcv", ("ijcv", "international journal of computer vision")),
    ("tip", ("tip", "transactions on image processing")),
    ("aaai", ("aaai", "association for the advancement of artificial intelligence")),
    ("acl", ("acl", "annual meeting of the association for computational linguistics")),
    ("emnlp", ("emnlp", "empirical methods in natural language processing")),
    ("iclr", ("iclr", "international conference on learning representations")),
    ("icml", ("icml", "international conference on machine learning")),
    ("ijcai", ("ijcai", "international joint conference on artificial intelligence")),
    ("kdd", ("kdd", "knowledge discovery and data mining")),
    ("neurips", ("neurips", "neural information processing systems")),
)
PEER_REVIEWED_WORK_TYPES: Final = frozenset(
    "article book-chapter journal-article proceedings-article".split()
)
PEER_REVIEWED_SOURCE_TYPES: Final = frozenset({"conference", "journal"})

RecencyBucket: TypeAlias = Literal[
    "last_5_years",
    "older_than_5_years",
    "recent_3_years",
    "unknown_year",
]


@dataclass(frozen=True, slots=True)
class SourceQualityContext:
    publication_type: str
    publication_year: int | None
    recency_bucket: RecencyBucket
    source_type: str
    top_venue_marker: str


def work_source_type(work: OpenAlexWork) -> str:
    source = work.primary_location.source if work.primary_location is not None else None
    return source.type if source is not None and source.type else "unknown"


def recency_bucket(work: OpenAlexWork, current_year: int) -> RecencyBucket:
    if work.publication_year is None:
        return "unknown_year"
    recent_start_year = current_year - RECENT_YEAR_WINDOW + 1
    if work.publication_year >= recent_start_year:
        return "recent_3_years"
    five_year_start = current_year - FIVE_YEAR_LOOKBACK
    if work.publication_year >= five_year_start:
        return "last_5_years"
    return "older_than_5_years"


def build_source_quality(
    work: OpenAlexWork,
    venue: str,
    current_year: int,
) -> SourceQualityContext:
    return SourceQualityContext(
        publication_type=work.type or "unknown",
        publication_year=work.publication_year,
        recency_bucket=recency_bucket(work, current_year),
        source_type=work_source_type(work),
        top_venue_marker=top_venue_marker(venue),
    )


def normalize_venue_alias(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def venue_alias_matches(normalized_venue: str, alias: str) -> bool:
    normalized_alias = normalize_venue_alias(alias)
    return bool(re.search(rf"(^| ){re.escape(normalized_alias)}($| )", normalized_venue))


def top_venue_marker(venue: str) -> str:
    normalized_venue = normalize_venue_alias(venue)
    for marker, aliases in TOP_VENUE_ALIASES:
        if any(venue_alias_matches(normalized_venue, alias) for alias in aliases):
            return marker
    return ""


def reliability_level(
    work: OpenAlexWork,
    venue: str,
    source_quality: SourceQualityContext,
) -> str:
    if "arxiv" in venue.lower() or work.type == "posted-content":
        return "arxiv_preprint"
    if source_quality.top_venue_marker:
        return "top_conference_or_journal"
    if (
        source_quality.publication_type in PEER_REVIEWED_WORK_TYPES
        or source_quality.source_type in PEER_REVIEWED_SOURCE_TYPES
    ):
        return "peer_reviewed"
    return "unknown"


def source_quality_signals(source_quality: SourceQualityContext) -> list[str]:
    signals: list[str] = []
    if source_quality.top_venue_marker:
        signals.append(
            f"Venue matched a top AI/CV venue marker: {source_quality.top_venue_marker}."
        )
    signals.append(f"OpenAlex source type is {source_quality.source_type}.")
    signals.append(f"OpenAlex work type is {source_quality.publication_type}.")
    match source_quality.recency_bucket:
        case "recent_3_years":
            if source_quality.publication_year is not None:
                signals.append(
                    "Publication year "
                    f"{source_quality.publication_year} is within the recent "
                    "3-year priority window."
                )
        case "last_5_years":
            if source_quality.publication_year is not None:
                signals.append(
                    f"Publication year {source_quality.publication_year} "
                    "is within the 5-year search window."
                )
        case "older_than_5_years":
            if source_quality.publication_year is not None:
                signals.append(
                    f"Publication year {source_quality.publication_year} "
                    "is outside the 5-year search window."
                )
        case "unknown_year":
            signals.append("Publication year is unavailable in OpenAlex metadata.")
        case unreachable:
            assert_never(unreachable)
    return signals
