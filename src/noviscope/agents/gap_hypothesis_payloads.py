from dataclasses import dataclass
from typing import cast

from pydantic import JsonValue

from noviscope.core.json_types import JsonObject
from noviscope.models.quest import StageCard

MAX_PAPERS_FOR_PROMPT = 8
MAX_TEXT_FIELD_CHARS = 500


@dataclass(frozen=True, slots=True)
class CompactedValue:
    value: JsonValue


def read_literature_papers(stage: StageCard | None) -> list[JsonObject]:
    if stage is None:
        return []
    paper_values = stage.output_payload.get("papers")
    if not isinstance(paper_values, list):
        return []
    papers: list[JsonObject] = []
    for value in paper_values[:MAX_PAPERS_FOR_PROMPT]:
        if isinstance(value, dict):
            paper = normalize_paper_payload(cast(JsonObject, value))
            if paper is not None:
                papers.append(paper)
    return papers


def normalize_paper_payload(value: JsonObject) -> JsonObject | None:
    title = string_value(value.get("title"))
    paper_ref = first_present_string(
        value.get("openalex_id"),
        value.get("doi"),
        value.get("url"),
        title,
    )
    if not paper_ref:
        return None
    return {
        "abstract_summary": trim_text(string_value(value.get("abstract_summary"))),
        "limitations": string_list(value.get("limitations")),
        "paper_ref": paper_ref,
        "relevance_score": number_value(value.get("relevance_score")),
        "reliability_level": string_value(value.get("reliability_level")),
        "title": title or paper_ref,
        "venue": string_value(value.get("venue")),
        "why_relevant": trim_text(string_value(value.get("why_relevant"))),
        "year": year_value(value.get("year")),
    }


def known_paper_refs(papers: list[JsonObject]) -> set[str]:
    refs: set[str] = set()
    for paper in papers:
        for key in ("paper_ref", "title"):
            value = paper.get(key)
            if isinstance(value, str) and value:
                refs.add(value)
    return refs


def compact_payload(payload: JsonObject) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        compacted_value = compact_value(value)
        if compacted_value is not None:
            compacted[key] = compacted_value.value
    return compacted


def compact_value(value: JsonValue) -> CompactedValue | None:
    if isinstance(value, str):
        return CompactedValue(trim_text(value))
    if isinstance(value, list):
        return CompactedValue(compact_list(value))
    if isinstance(value, int | float | bool | dict) or value is None:
        return CompactedValue(value)
    return None


def compact_list(values: list[JsonValue]) -> list[JsonValue]:
    compacted: list[JsonValue] = []
    for value in values[:MAX_PAPERS_FOR_PROMPT]:
        item = compact_list_item(value)
        if item is not None:
            compacted.append(item)
    return compacted


def compact_list_item(value: JsonValue) -> JsonValue | None:
    if isinstance(value, str):
        return trim_text(value)
    if isinstance(value, int | float | bool | dict):
        return value
    return None


def trim_text(value: str) -> str:
    return " ".join(value.split())[:MAX_TEXT_FIELD_CHARS]


def string_value(value: JsonValue | None) -> str:
    return value if isinstance(value, str) else ""


def first_present_string(*values: JsonValue | None) -> str:
    for value in values:
        if isinstance(value, str) and value:
            return value
    return ""


def string_list(value: JsonValue | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def number_value(value: JsonValue | None) -> float:
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return 0.0


def year_value(value: JsonValue | None) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None
