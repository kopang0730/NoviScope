from typing import assert_never

from pydantic import JsonValue

from noviscope.api.evidence_ledger import (
    PAPER_COLLECTION_KEYS,
    PAPER_REF_KEYS,
    paper_reference_is_valid,
)
from noviscope.models.quest import StageCard


def paper_collections_have_invalid_references(stage: StageCard) -> bool:
    for collection_key in PAPER_COLLECTION_KEYS:
        value = stage.output_payload.get(collection_key)
        match value:
            case None:
                continue
            case list() as items:
                if any(paper_record_has_invalid_references(item) for item in items):
                    return True
            case bool() | int() | float() | str() | dict():
                return True
            case unreachable:
                assert_never(unreachable)
    return False


def paper_record_has_invalid_references(value: JsonValue) -> bool:
    match value:
        case dict() as record:
            references_found = False
            for key in PAPER_REF_KEYS:
                if key not in record:
                    continue
                references_found = True
                reference = record[key]
                if not isinstance(reference, str) or not reference.strip():
                    return True
                if not paper_reference_is_valid(key, reference):
                    return True
            return not references_found
        case None | bool() | int() | float() | str() | list():
            return True
        case unreachable:
            assert_never(unreachable)
