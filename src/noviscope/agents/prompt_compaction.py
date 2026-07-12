from typing import assert_never

from pydantic import JsonValue

from noviscope.core.json_types import JsonObject


def compact_prompt_payload(
    payload: JsonObject,
    *,
    max_list_items: int,
    max_text_chars: int,
) -> JsonObject:
    compacted: JsonObject = {}
    for key, value in payload.items():
        if key == "raw_response":
            continue
        compacted[key] = compact_prompt_value(
            value,
            max_list_items=max_list_items,
            max_text_chars=max_text_chars,
        )
    return compacted


def compact_prompt_value(
    value: JsonValue,
    *,
    max_list_items: int,
    max_text_chars: int,
) -> JsonValue:
    match value:
        case str() as text:
            return trim_prompt_text(text, max_text_chars=max_text_chars)
        case list() as items:
            return [
                compact_prompt_value(
                    item,
                    max_list_items=max_list_items,
                    max_text_chars=max_text_chars,
                )
                for item in items[:max_list_items]
            ]
        case dict() as nested_payload:
            return compact_prompt_payload(
                nested_payload,
                max_list_items=max_list_items,
                max_text_chars=max_text_chars,
            )
        case bool() | int() | float() | None:
            return value
        case unreachable:
            assert_never(unreachable)


def trim_prompt_text(value: str, *, max_text_chars: int) -> str:
    return " ".join(value.split())[:max_text_chars]
