import re
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, assert_never

from noviscope.agents.openalex_client import FIVE_YEAR_LOOKBACK, OpenAlexWork

RECENT_YEAR_WINDOW: Final = 3
TOP_VENUE_MARKERS: Final = tuple("acl cvpr eccv emnlp iccv iclr icml ijcai kdd neurips".split())
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


def top_venue_marker(venue: str) -> str:
    normalized_venue = venue.lower()
    for marker in TOP_VENUE_MARKERS:
        if re.search(rf"(^|[^a-z0-9]){re.escape(marker)}([^a-z0-9]|$)", normalized_venue):
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
