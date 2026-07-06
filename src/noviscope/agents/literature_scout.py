import re
from dataclasses import dataclass
from datetime import date

from noviscope.agents.literature_source_quality import (
    RECENT_YEAR_WINDOW,
    build_source_quality,
    reliability_level,
    source_quality_signals,
)
from noviscope.agents.openalex_client import (
    OpenAlexClientConfig,
    OpenAlexSearchClient,
    OpenAlexWork,
    OpenAlexWorksClient,
)
from noviscope.agents.stage_runner import StageRunContext, StageRunner, StageRunResult
from noviscope.core.config import get_settings
from noviscope.core.json_types import JsonObject
from noviscope.models.provider import ProviderKind

LITERATURE_SCOUT_AGENT_ID = "literature_scout"
OPENALEX_SOURCE = "openalex_works_api"
ABSTRACT_SUMMARY_CHARS = 420
QUERY_CHARS = 240

QUERY_STOP_WORDS = frozenset(
    {"about", "and", "for", "from", "into", "noviscope", "quest", "research", "the", "with"}
)


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
                "score_basis": "OpenAlex relevance_score with a NoviScope recency boost.",
                "search_query": query,
                "source": OPENALEX_SOURCE,
            },
            input_payload=self.build_input_payload(context),
            output_payload={
                "papers": papers,
                "score_basis": (
                    "OpenAlex relevance_score with a 1.25x boost for papers from "
                    "the last three years."
                ),
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
    source_quality = build_source_quality(work, venue, current_year)
    abstract = abstract_summary(work.abstract_inverted_index)
    return {
        "abstract_summary": abstract,
        "arxiv_id": arxiv_id(work),
        "authors": work_authors(work),
        "doi": work.doi,
        "limitations": ["OpenAlex metadata only; verify the full paper before citing."],
        "openalex_id": work.id,
        "paper_ref": work.id,
        "publication_type": source_quality.publication_type,
        "recency_bucket": source_quality.recency_bucket,
        "relevance_score": relevance_score(work, current_year),
        "reliability_level": reliability_level(work, venue, source_quality),
        "source_quality_signals": source_quality_signals(source_quality),
        "source_type": source_quality.source_type,
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


def arxiv_id(work: OpenAlexWork) -> str:
    if work.ids is None or work.ids.arxiv is None:
        return ""
    arxiv_url = work.ids.arxiv.strip()
    if not arxiv_url:
        return ""
    return arxiv_url.rstrip("/").rsplit("/", 1)[-1]


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


def why_relevant(title: str, abstract: str, query_terms: list[str]) -> str:
    matched_terms = [term for term in query_terms if term in f"{title} {abstract}".lower()]
    if matched_terms:
        return f"Matches query terms in OpenAlex metadata: {', '.join(matched_terms[:5])}."
    return "Returned by OpenAlex for this query; verify topical fit before citing."


def get_literature_scout_runner() -> LiteratureScoutStageRunner:
    settings = get_settings()
    config = OpenAlexClientConfig(api_key=settings.openalex_api_key, email=settings.openalex_email)
    return LiteratureScoutStageRunner(OpenAlexWorksClient(config))
