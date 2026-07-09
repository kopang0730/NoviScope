import hashlib
import json
from collections.abc import Sequence
from typing import Final

from noviscope.core.stage_policy import EVIDENCE_AUDITOR_AGENT_ID
from noviscope.models.quest import StageCard

EVIDENCE_AUDIT_FINGERPRINT_KEY: Final = "audited_stage_fingerprint"


def evidence_audit_stage_fingerprint(stages: Sequence[StageCard]) -> str | None:
    snapshot = [
        {
            "agent_id": stage.agent_id,
            "evidence_payload": stage.evidence_payload,
            "human_approved": stage.human_approved,
            "id": stage.id,
            "input_payload": stage.input_payload,
            "output_payload": stage.output_payload,
            "review_notes": stage.review_notes,
            "status": stage.status.value,
            "summary": stage.summary,
            "title": stage.title,
        }
        for stage in sorted(stages, key=lambda item: item.id)
        if stage.agent_id != EVIDENCE_AUDITOR_AGENT_ID
    ]
    try:
        canonical_snapshot = json.dumps(
            snapshot,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
    except ValueError:
        return None
    return hashlib.sha256(canonical_snapshot).hexdigest()
