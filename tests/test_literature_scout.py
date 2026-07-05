from collections.abc import Mapping

import httpx
import pytest
from pydantic import SecretStr

from noviscope.agents.literature_scout import (
    LITERATURE_SCOUT_AGENT_ID,
    OPENALEX_SOURCE,
    LiteratureScoutStageRunner,
)
from noviscope.agents.openalex_client import (
    LiteratureScoutRunError,
    OpenAlexAuthor,
    OpenAlexAuthorship,
    OpenAlexClientConfig,
    OpenAlexLocation,
    OpenAlexSource,
    OpenAlexWork,
    OpenAlexWorksClient,
)
from noviscope.agents.stage_runner import ModelProviderCredentials, StageRunContext
from noviscope.models.provider import ProviderKind
from noviscope.models.quest import Quest, StageCard


class FakeSearchClient:
    def __init__(self, works: list[OpenAlexWork]) -> None:
        self.works = works
        self.query = ""

    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]:
        self.query = query
        return self.works


class FakeHTTPClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.params: dict[str, str | int] = {}
        self.headers: dict[str, str] = {}

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        headers: Mapping[str, str],
    ) -> httpx.Response:
        self.params = dict(params)
        self.headers = dict(headers)
        return self.response


def make_work(
    *,
    openalex_id: str,
    title: str,
    year: int,
    venue: str,
    score: float,
) -> OpenAlexWork:
    return OpenAlexWork(
        abstract_inverted_index={
            "badminton": [0],
            "action": [1],
            "recognition": [2],
            "benchmark": [3],
        },
        authorships=[OpenAlexAuthorship(author=OpenAlexAuthor(display_name="Ada Chen"))],
        doi="https://doi.org/10.0000/example",
        id=openalex_id,
        primary_location=OpenAlexLocation(
            landing_page_url="https://example.org/paper",
            source=OpenAlexSource(display_name=venue, type="conference"),
        ),
        publication_year=year,
        relevance_score=score,
        title=title,
        type="proceedings-article",
    )


def make_context() -> StageRunContext:
    quest = Quest(
        initial_direction="Badminton action recognition with wearable camera footage",
        title="Badminton action recognition",
    )
    return StageRunContext(
        provider=ModelProviderCredentials(
            api_key=SecretStr(""),
            base_url="https://api.openalex.org",
            id="server_openalex",
            kind=ProviderKind.CUSTOM,
            model="openalex-works",
            name="OpenAlex",
        ),
        quest=quest,
        stage=StageCard(
            agent_id=LITERATURE_SCOUT_AGENT_ID,
            quest_id=quest.id,
            title="Literature scout",
        ),
    )


def test_literature_scout_scores_recent_openalex_papers_first() -> None:
    older_work = make_work(
        openalex_id="https://openalex.org/W1",
        score=100.0,
        title="Badminton action recognition survey",
        venue="Pattern Recognition",
        year=2022,
    )
    recent_work = make_work(
        openalex_id="https://openalex.org/W2",
        score=90.0,
        title="Badminton action recognition benchmark",
        venue="CVPR",
        year=2025,
    )
    runner = LiteratureScoutStageRunner(
        FakeSearchClient([older_work, recent_work]),
        current_year=2026,
    )

    result = runner.run(make_context())

    papers = result.output_payload["papers"]
    assert result.output_payload["source"] == OPENALEX_SOURCE
    assert result.output_payload["search_query"].startswith("Badminton action recognition")
    assert result.output_payload["score_basis"] == (
        "OpenAlex relevance_score with a 1.25x boost for papers from the last three years."
    )
    assert isinstance(papers, list)
    assert papers[0]["openalex_id"] == "https://openalex.org/W2"
    assert papers[0]["relevance_score"] == 112.5
    assert papers[0]["reliability_level"] == "top_conference_or_journal"
    assert papers[0]["limitations"] == [
        "OpenAlex metadata only; verify the full paper before citing."
    ]
    assert set(papers[0]) == {
        "abstract_summary",
        "authors",
        "doi",
        "limitations",
        "openalex_id",
        "relevance_score",
        "reliability_level",
        "title",
        "url",
        "venue",
        "why_relevant",
        "year",
    }


def test_literature_scout_returns_empty_papers_without_fabrication() -> None:
    runner = LiteratureScoutStageRunner(FakeSearchClient([]), current_year=2026)

    result = runner.run(make_context())

    assert result.output_payload["papers"] == []
    assert result.summary == "No papers found in OpenAlex for the Literature Scout query."
    assert result.confidence == "low"


def test_openalex_client_uses_works_api_params_without_live_http() -> None:
    response = httpx.Response(
        200,
        json={"results": [{"id": "https://openalex.org/W1", "title": "A paper"}]},
        request=httpx.Request("GET", "https://api.openalex.org/works"),
    )
    http_client = FakeHTTPClient(response)
    client = OpenAlexWorksClient(
        OpenAlexClientConfig(
            api_key=SecretStr("openalex-secret"),
            email="researcher@example.com",
        ),
        http_client,
    )

    works = client.search("badminton action recognition", current_year=2026)

    assert works[0].id == "https://openalex.org/W1"
    assert http_client.params["search"] == "badminton action recognition"
    assert http_client.params["filter"] == "from_publication_date:2021-01-01"
    assert http_client.params["per_page"] == 8
    assert http_client.params["api_key"] == "openalex-secret"
    assert http_client.headers["User-Agent"] == "NoviScope/0.1 (mailto:researcher@example.com)"


def test_openalex_client_blocks_without_api_key_before_http() -> None:
    response = httpx.Response(
        200,
        json={"results": []},
        request=httpx.Request("GET", "https://api.openalex.org/works"),
    )
    http_client = FakeHTTPClient(response)
    client = OpenAlexWorksClient(OpenAlexClientConfig(), http_client)

    with pytest.raises(LiteratureScoutRunError) as exc_info:
        client.search("badminton action recognition", current_year=2026)

    assert str(exc_info.value) == (
        "Configure NOVISCOPE_OPENALEX_API_KEY before running Literature Scout."
    )
    assert http_client.params == {}


def test_openalex_client_blocks_blank_api_key_before_http() -> None:
    response = httpx.Response(
        200,
        json={"results": []},
        request=httpx.Request("GET", "https://api.openalex.org/works"),
    )
    http_client = FakeHTTPClient(response)
    client = OpenAlexWorksClient(OpenAlexClientConfig(api_key=SecretStr("  ")), http_client)

    with pytest.raises(LiteratureScoutRunError) as exc_info:
        client.search("badminton action recognition", current_year=2026)

    assert str(exc_info.value) == (
        "Configure NOVISCOPE_OPENALEX_API_KEY before running Literature Scout."
    )
    assert http_client.params == {}


def test_openalex_errors_do_not_expose_api_key() -> None:
    response = httpx.Response(
        429,
        request=httpx.Request(
            "GET",
            "https://api.openalex.org/works?api_key=openalex-secret",
        ),
    )
    client = OpenAlexWorksClient(
        OpenAlexClientConfig(api_key=SecretStr("openalex-secret")),
        FakeHTTPClient(response),
    )

    with pytest.raises(LiteratureScoutRunError) as exc_info:
        client.search("badminton action recognition", current_year=2026)

    assert "429" in str(exc_info.value)
    assert "openalex-secret" not in str(exc_info.value)
