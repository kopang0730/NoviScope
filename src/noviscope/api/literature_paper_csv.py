import csv
from io import StringIO
from typing import Final, TypedDict

from noviscope.api.literature_paper_table import (
    LiteraturePaperRow,
    LiteraturePaperTableResponse,
)

CSV_HEADERS: Final[tuple[str, ...]] = (
    "source",
    "search_query",
    "score_basis",
    "paper_ref",
    "title",
    "authors",
    "year",
    "venue",
    "url",
    "doi",
    "abstract_summary",
    "relevance_score",
    "reliability_level",
    "source_type",
    "publication_type",
    "recency_bucket",
    "why_relevant",
    "limitations",
    "source_quality_signals",
)


class LiteraturePaperCsvRow(TypedDict):
    source: str
    search_query: str
    score_basis: str
    paper_ref: str
    title: str
    authors: str
    year: str
    venue: str
    url: str
    doi: str
    abstract_summary: str
    relevance_score: str
    reliability_level: str
    source_type: str
    publication_type: str
    recency_bucket: str
    why_relevant: str
    limitations: str
    source_quality_signals: str


def joined_csv_items(items: list[str]) -> str:
    return "; ".join(items)


def paper_csv_row(
    table: LiteraturePaperTableResponse,
    paper: LiteraturePaperRow,
) -> LiteraturePaperCsvRow:
    return LiteraturePaperCsvRow(
        abstract_summary=paper.abstract_summary,
        authors=joined_csv_items(paper.authors),
        doi=paper.doi,
        limitations=joined_csv_items(paper.limitations),
        paper_ref=paper.paper_ref,
        publication_type=paper.publication_type,
        recency_bucket=paper.recency_bucket,
        relevance_score=str(paper.relevance_score),
        reliability_level=paper.reliability_level,
        score_basis=table.score_basis,
        search_query=table.search_query,
        source=table.source,
        source_quality_signals=joined_csv_items(paper.source_quality_signals),
        source_type=paper.source_type,
        title=paper.title,
        url=paper.url,
        venue=paper.venue,
        why_relevant=paper.why_relevant,
        year="" if paper.year is None else str(paper.year),
    )


def build_literature_paper_csv(table: LiteraturePaperTableResponse) -> str:
    with StringIO() as buffer:
        writer = csv.DictWriter(buffer, fieldnames=CSV_HEADERS, lineterminator="\n")
        writer.writeheader()
        for paper in table.papers:
            writer.writerow(paper_csv_row(table, paper))
        return buffer.getvalue()


def literature_paper_csv_filename(stage_id: str) -> str:
    return f"noviscope-literature-papers-{stage_id}.csv"
