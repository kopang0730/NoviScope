import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import NotRequired, Protocol, TypedDict

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.config import get_settings
from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind

LITERATURE_SCOUT_AGENT_ID = "literature_scout"
OPENALEX_SOURCE = "openalex_works_api"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"
MAX_PAPER_RESULTS = 8
RECENT_YEAR_WINDOW = 3
FIVE_YEAR_LOOKBACK = 5
ABSTRACT_SUMMARY_CHARS = 420
QUERY_CHARS = 240

TOP_VENUE_MARKERS = frozenset("acl cvpr eccv emnlp iccv iclr icml ijcai kdd neurips".split())
PEER_REVIEWED_WORK_TYPES = frozenset(
    "article book-chapter journal-article proceedings-article".split()
)
QUERY_STOP_WORDS = frozenset(
    {"about", "and", "for", "from", "into", "noviscope", "quest", "research", "the", "with"}
)


class OpenAlexQueryParams(TypedDict):
    search: str
    filter: str
    sort: str
    per_page: int
    mailto: NotRequired[str]
    api_key: NotRequired[str]


class OpenAlexAuthor(BaseModel):
    model_config = ConfigDict(frozen=True)
    display_name: str = ""


class OpenAlexAuthorship(BaseModel):
    model_config = ConfigDict(frozen=True)
    author: OpenAlexAuthor | None = None


class OpenAlexSource(BaseModel):
    model_config = ConfigDict(frozen=True)
    display_name: str | None = None
    type: str | None = None


class OpenAlexLocation(BaseModel):
    model_config = ConfigDict(frozen=True)
    landing_page_url: str | None = None
    source: OpenAlexSource | None = None


class OpenAlexWork(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str
    title: str | None = None
    display_name: str | None = None
    publication_year: int | None = None
    primary_location: OpenAlexLocation | None = None
    doi: str | None = None
    authorships: list[OpenAlexAuthorship] = Field(default_factory=list)
    abstract_inverted_index: dict[str, list[int]] | None = None
    relevance_score: float | None = None
    type: str | None = None


class OpenAlexWorksResponse(BaseModel):
    model_config = ConfigDict(frozen=True)
    results: list[OpenAlexWork] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class LiteratureScoutRunError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


class OpenAlexHTTPClient(Protocol):
    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str | int],
        headers: Mapping[str, str],
    ) -> httpx.Response: ...


class OpenAlexSearchClient(Protocol):
    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]: ...


@dataclass(frozen=True, slots=True)
class OpenAlexClientConfig:
    api_key: SecretStr | None = None
    email: str | None = None
    works_url: str = OPENALEX_WORKS_URL


@dataclass(frozen=True, slots=True)
class OpenAlexWorksClient:
    config: OpenAlexClientConfig
    http_client: OpenAlexHTTPClient | None = None

    def search(self, query: str, *, current_year: int) -> list[OpenAlexWork]:
        if self.config.api_key is None:
            raise LiteratureScoutRunError(
                "Configure NOVISCOPE_OPENALEX_API_KEY before running Literature Scout."
            )
        params: OpenAlexQueryParams = {
            "filter": f"from_publication_date:{current_year - FIVE_YEAR_LOOKBACK}-01-01",
            "per_page": MAX_PAPER_RESULTS,
            "search": query,
            "sort": "relevance_score:desc",
        }
        if self.config.email:
            params["mailto"] = self.config.email
        if self.config.api_key is not None:
            params["api_key"] = self.config.api_key.get_secret_value()
        try:
            response = self._get(params)
            response.raise_for_status()
            return OpenAlexWorksResponse.model_validate(response.json()).results
        except httpx.HTTPStatusError as exc:
            raise LiteratureScoutRunError(
                f"OpenAlex request failed with HTTP status {exc.response.status_code}."
            ) from exc
        except httpx.RequestError as exc:
            raise LiteratureScoutRunError(
                "OpenAlex request failed before a response was received."
            ) from exc
        except (ValueError, ValidationError) as exc:
            raise LiteratureScoutRunError("OpenAlex returned an invalid works response.") from exc

    def _get(self, params: OpenAlexQueryParams) -> httpx.Response:
        headers = {"User-Agent": "NoviScope/0.1"}
        if self.config.email:
            headers["User-Agent"] = f"NoviScope/0.1 (mailto:{self.config.email})"
        if self.http_client is not None:
            return self.http_client.get(self.config.works_url, params=params, headers=headers)
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            return client.get(self.config.works_url, params=params, headers=headers)


@dataclass(frozen=True, slots=True)
class LiteratureScoutStageRunner(StageRunner):
    client: OpenAlexSearchClient
    current_year: int | None = None

    @property
    def agent_id(self) -> str:
        return LITERATURE_SCOUT_AGENT_ID

    @property
    def supported_provider_kinds(self) -> frozenset[ProviderKind]:
        return frozenset()

    def build_input_payload(self, context: StageRunContext) -> JsonObject:
        search_query = build_search_query(context.quest.title, context.quest.initial_direction)
        return {
            "agent_id": context.stage.agent_id,
            "search_query": search_query,
            "source": OPENALEX_SOURCE,
        }

    def run(self, context: StageRunContext) -> StageRunResult:
        current_year = self.current_year or date.today().year
        query = build_search_query(context.quest.title, context.quest.initial_direction)
        query_terms = extract_query_terms(query)
        works = self.client.search(query, current_year=current_year)
        papers = [build_paper(work, query_terms, current_year) for work in works]
        papers.sort(key=lambda paper: paper["relevance_score"], reverse=True)
        summary = (
            f"Found {len(papers)} OpenAlex papers for Literature Scout review."
            if papers
            else "No papers found in OpenAlex for the Literature Scout query."
        )
        return StageRunResult(
            confidence="medium" if papers else "low",
            evidence_payload={
                "can_run": True,
                "paper_count": len(papers),
                "requires_human_review": True,
                "search_query": query,
                "source": OPENALEX_SOURCE,
            },
            input_payload=self.build_input_payload(context),
            output_payload={
                "papers": papers,
                "search_query": query,
                "source": OPENALEX_SOURCE,
                "summary": summary,
            },
            summary=summary,
        )


def build_search_query(title: str, initial_direction: str) -> str:
    return " ".join(f"{title} {initial_direction}".split())[:QUERY_CHARS]


def extract_query_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", query.lower()):
        if term in QUERY_STOP_WORDS or term in seen:
            continue
        seen.add(term)
        terms.append(term)
    return terms[:12]


def build_paper(work: OpenAlexWork, query_terms: list[str], current_year: int) -> JsonObject:
    venue = work_venue(work)
    abstract = abstract_summary(work.abstract_inverted_index)
    return {
        "abstract_summary": abstract,
        "authors": work_authors(work),
        "doi": work.doi,
        "limitations": ["OpenAlex metadata only; verify the full paper before citing."],
        "openalex_id": work.id,
        "relevance_score": relevance_score(work, current_year),
        "reliability_level": reliability_level(work, venue),
        "title": work.title or work.display_name or "Untitled OpenAlex work",
        "url": work_url(work),
        "venue": venue,
        "why_relevant": why_relevant(work.title or "", abstract, query_terms),
        "year": work.publication_year,
    }


def work_venue(work: OpenAlexWork) -> str:
    source = work.primary_location.source if work.primary_location is not None else None
    if source is not None and source.display_name:
        return source.display_name
    return "Unknown venue"


def work_authors(work: OpenAlexWork) -> list[str]:
    return [
        authorship.author.display_name
        for authorship in work.authorships
        if authorship.author is not None and authorship.author.display_name
    ]


def work_url(work: OpenAlexWork) -> str:
    if work.primary_location is not None and work.primary_location.landing_page_url:
        return work.primary_location.landing_page_url
    return work.doi or work.id


def abstract_summary(abstract_index: dict[str, list[int]] | None) -> str:
    if not abstract_index:
        return "No abstract available from OpenAlex metadata."
    positions = [position for values in abstract_index.values() for position in values]
    if not positions:
        return "No abstract available from OpenAlex metadata."
    words = [""] * (max(positions) + 1)
    for word, values in abstract_index.items():
        for position in values:
            words[position] = word
    return " ".join(word for word in words if word)[:ABSTRACT_SUMMARY_CHARS]


def relevance_score(work: OpenAlexWork, current_year: int) -> float:
    score = work.relevance_score or 0.0
    recent_start_year = current_year - RECENT_YEAR_WINDOW + 1
    if work.publication_year is not None and work.publication_year >= recent_start_year:
        score *= 1.25
    return round(score, 3)


def reliability_level(work: OpenAlexWork, venue: str) -> str:
    source_type = None
    if work.primary_location is not None and work.primary_location.source is not None:
        source_type = work.primary_location.source.type
    if "arxiv" in venue.lower() or work.type == "posted-content":
        return "arxiv_preprint"
    if any(marker in venue.lower() for marker in TOP_VENUE_MARKERS):
        return "top_conference_or_journal"
    if work.type in PEER_REVIEWED_WORK_TYPES or source_type in {"conference", "journal"}:
        return "peer_reviewed"
    return "unknown"


def why_relevant(title: str, abstract: str, query_terms: list[str]) -> str:
    matched_terms = [term for term in query_terms if term in f"{title} {abstract}".lower()]
    if matched_terms:
        return f"Matches query terms in OpenAlex metadata: {', '.join(matched_terms[:5])}."
    return "Returned by OpenAlex for this query; verify topical fit before citing."


def get_literature_scout_runner() -> LiteratureScoutStageRunner:
    settings = get_settings()
    config = OpenAlexClientConfig(api_key=settings.openalex_api_key, email=settings.openalex_email)
    return LiteratureScoutStageRunner(OpenAlexWorksClient(config))
