from noviscope.agents.literature_source_quality import (
    build_source_quality,
    reliability_level,
)
from noviscope.agents.openalex_client import (
    OpenAlexAuthor,
    OpenAlexAuthorship,
    OpenAlexLocation,
    OpenAlexSource,
    OpenAlexWork,
)


def make_work(*, venue: str, work_type: str = "proceedings-article") -> OpenAlexWork:
    return OpenAlexWork(
        abstract_inverted_index={},
        authorships=[OpenAlexAuthorship(author=OpenAlexAuthor(display_name="Ada Chen"))],
        doi="https://doi.org/10.0000/example",
        id="https://openalex.org/W1",
        primary_location=OpenAlexLocation(
            landing_page_url="https://example.org/paper",
            source=OpenAlexSource(display_name=venue, type="conference"),
        ),
        publication_year=2025,
        relevance_score=80.0,
        title="Visual recognition paper",
        type=work_type,
    )


def test_top_venue_marker_recognizes_cvpr_full_name() -> None:
    venue = "IEEE/CVF Conference on Computer Vision and Pattern Recognition"
    work = make_work(venue=venue)

    source_quality = build_source_quality(work, venue, current_year=2026)

    assert source_quality.top_venue_marker == "cvpr"
    assert reliability_level(work, venue, source_quality) == "top_conference_or_journal"


def test_top_venue_marker_recognizes_top_cv_journal_alias() -> None:
    venue = "IEEE Transactions on Pattern Analysis and Machine Intelligence"
    work = make_work(venue=venue, work_type="journal-article")

    source_quality = build_source_quality(work, venue, current_year=2026)

    assert source_quality.top_venue_marker == "tpami"
    assert reliability_level(work, venue, source_quality) == "top_conference_or_journal"


def test_top_venue_marker_recognizes_hyphenated_top_cv_journal_alias() -> None:
    venue = "IEEE T-PAMI"
    work = make_work(venue=venue, work_type="journal-article")

    source_quality = build_source_quality(work, venue, current_year=2026)

    assert source_quality.top_venue_marker == "tpami"
    assert reliability_level(work, venue, source_quality) == "top_conference_or_journal"
