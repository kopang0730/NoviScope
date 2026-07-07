import pytest

from noviscope.agents.literature_source_quality import (
    build_source_quality,
    recency_bucket,
    reliability_level,
    source_quality_signals,
)
from noviscope.agents.openalex_client import OpenAlexLocation, OpenAlexSource, OpenAlexWork


def build_work(
    *,
    publication_year: int | None,
    source_type: str | None = "journal",
    work_type: str | None = "journal-article",
) -> OpenAlexWork:
    return OpenAlexWork(
        id="https://openalex.org/W1",
        primary_location=OpenAlexLocation(
            source=OpenAlexSource(display_name="Example venue", type=source_type)
        ),
        publication_year=publication_year,
        type=work_type,
    )


@pytest.mark.parametrize(
    ("publication_year", "expected_bucket"),
    [
        (2026, "recent_3_years"),
        (2024, "recent_3_years"),
        (2023, "last_5_years"),
        (2021, "last_5_years"),
        (2020, "older_than_5_years"),
        (None, "unknown_year"),
    ],
)
def test_recency_bucket_classifies_priority_windows(
    publication_year: int | None,
    expected_bucket: str,
) -> None:
    work = build_work(publication_year=publication_year)

    bucket = recency_bucket(work, current_year=2026)

    assert bucket == expected_bucket


def test_reliability_level_treats_arxiv_venue_as_preprint() -> None:
    work = build_work(publication_year=2026)
    source_quality = build_source_quality(work, "arXiv", current_year=2026)

    level = reliability_level(work, "arXiv", source_quality)

    assert level == "arxiv_preprint"


def test_reliability_level_treats_peer_reviewed_journal_metadata_as_peer_reviewed() -> None:
    work = build_work(publication_year=2026)
    source_quality = build_source_quality(work, "Journal of Badminton Vision", current_year=2026)

    level = reliability_level(work, "Journal of Badminton Vision", source_quality)

    assert level == "peer_reviewed"


def test_source_quality_signals_report_metadata_and_recency() -> None:
    work = build_work(publication_year=2023, source_type="conference", work_type="proceedings-article")
    source_quality = build_source_quality(work, "Workshop on Sports Vision", current_year=2026)

    signals = source_quality_signals(source_quality)

    assert "OpenAlex source type is conference." in signals
    assert "OpenAlex work type is proceedings-article." in signals
    assert "Publication year 2023 is within the 5-year search window." in signals
