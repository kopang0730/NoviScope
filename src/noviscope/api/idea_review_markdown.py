from dataclasses import dataclass
from typing import Final, assert_never

from pydantic import JsonValue

from noviscope.core.json_types import JsonObject

EMPTY_VALUE: Final = "Not recorded."
HUMAN_REVIEW_REMINDER: Final = (
    "Select ideas only after checking paper basis, required data, baseline, "
    "feasibility, novelty risk, and application value."
)


@dataclass(frozen=True, slots=True)
class IdeaReviewItem:
    idea_id: str
    idea_title: str
    core_hypothesis: str
    based_on_which_papers: list[str]
    expected_improvement: str
    required_data: str
    required_baseline: str
    experiment_feasibility: str
    novelty_risk: str
    application_value: str
    confidence: str


def read_text(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    match value:
        case str() as text:
            return text.strip()
        case None | bool() | int() | float() | list() | dict():
            return ""
        case unreachable:
            assert_never(unreachable)


def read_string_items(values: list[JsonValue]) -> list[str]:
    strings: list[str] = []
    for value in values:
        match value:
            case str() as text:
                cleaned = text.strip()
                if cleaned:
                    strings.append(cleaned)
            case None | bool() | int() | float() | list() | dict():
                continue
            case unreachable:
                assert_never(unreachable)
    return strings


def read_string_list(payload: JsonObject, key: str) -> list[str]:
    value = payload.get(key)
    match value:
        case list() as items:
            return read_string_items(items)
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def text_or_empty(value: str) -> str:
    return value if value else EMPTY_VALUE


def joined_items(items: list[str]) -> str:
    if not items:
        return EMPTY_VALUE
    return "; ".join(items)


def idea_review_item(payload: JsonObject) -> IdeaReviewItem:
    return IdeaReviewItem(
        application_value=read_text(payload, "application_value"),
        based_on_which_papers=read_string_list(payload, "based_on_which_papers"),
        confidence=read_text(payload, "confidence"),
        core_hypothesis=read_text(payload, "core_hypothesis"),
        expected_improvement=read_text(payload, "expected_improvement"),
        experiment_feasibility=read_text(payload, "experiment_feasibility"),
        idea_id=read_text(payload, "idea_id"),
        idea_title=read_text(payload, "idea_title"),
        novelty_risk=read_text(payload, "novelty_risk"),
        required_baseline=read_text(payload, "required_baseline"),
        required_data=read_text(payload, "required_data"),
    )


def idea_section(item: IdeaReviewItem) -> list[str]:
    title = text_or_empty(item.idea_title)
    idea_id = text_or_empty(item.idea_id)
    return [
        f"## {idea_id}: {title}",
        "",
        f"- Based on papers: {joined_items(item.based_on_which_papers)}",
        f"- Core hypothesis: {text_or_empty(item.core_hypothesis)}",
        f"- Expected improvement: {text_or_empty(item.expected_improvement)}",
        f"- Required data: {text_or_empty(item.required_data)}",
        f"- Required baseline: {text_or_empty(item.required_baseline)}",
        f"- Experiment feasibility: {text_or_empty(item.experiment_feasibility)}",
        f"- Novelty risk: {text_or_empty(item.novelty_risk)}",
        f"- Application value: {text_or_empty(item.application_value)}",
        f"- Confidence: {text_or_empty(item.confidence)}",
        "",
    ]


def build_idea_review_markdown(stage_id: str, output_payload: JsonObject) -> str:
    selection_status = read_text(output_payload, "selection_status") or "pending_human_selection"
    ideas = [idea_review_item(idea) for idea in read_idea_payloads(output_payload)]
    lines = [
        "# NoviScope Idea Review Packet",
        "",
        "## Stage",
        f"- Stage ID: `{stage_id}`",
        f"- Selection status: `{selection_status}`",
        f"- Candidate idea count: `{len(ideas)}`",
        "",
        "## Human Review Reminder",
        HUMAN_REVIEW_REMINDER,
        "",
    ]
    for idea in ideas:
        lines.extend(idea_section(idea))
    if not ideas:
        lines.extend(["## Candidate Ideas", "", f"- {EMPTY_VALUE}", ""])
    return "\n".join(lines)


def read_idea_payloads(output_payload: JsonObject) -> list[JsonObject]:
    value = output_payload.get("ideas")
    match value:
        case list() as items:
            ideas: list[JsonObject] = []
            for item in items:
                match item:
                    case dict() as idea:
                        ideas.append(idea)
                    case None | str() | bool() | int() | float() | list():
                        continue
                    case unreachable:
                        assert_never(unreachable)
            return ideas
        case None | str() | bool() | int() | float() | dict():
            return []
        case unreachable:
            assert_never(unreachable)


def idea_review_markdown_filename(stage_id: str) -> str:
    return f"noviscope-idea-review-{stage_id}.md"
