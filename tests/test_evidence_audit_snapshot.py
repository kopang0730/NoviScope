import math

import pytest
from pydantic import JsonValue

from noviscope.api.evidence_audit_contract import EVIDENCE_AUDIT_POLICY_VERSION
from noviscope.api.evidence_audit_readers import (
    evidence_auditor_is_approved,
    find_current_evidence_auditor,
)
from noviscope.api.evidence_audit_snapshot import (
    EVIDENCE_AUDIT_FINGERPRINT_KEY,
    evidence_audit_stage_fingerprint,
)
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EVIDENCE_AUDITOR_AGENT_ID,
)
from noviscope.models.quest import StageCard, StageStatus


@pytest.mark.parametrize("metric_value", [math.nan, math.inf, -math.inf])
def test_snapshot_rejects_non_finite_json_numbers(metric_value: float) -> None:
    stage = StageCard(
        agent_id=DEMAND_VALIDATOR_AGENT_ID,
        output_payload={"metric_value": metric_value},
        quest_id="quest-snapshot",
        status=StageStatus.COMPLETE,
        title="Demand validator",
    )

    assert evidence_audit_stage_fingerprint([stage]) is None


@pytest.mark.parametrize("metric_value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("include_null_fingerprint", [False, True])
def test_evidence_auditor_rejects_non_finite_snapshot_without_a_real_fingerprint(
    metric_value: float,
    include_null_fingerprint: bool,
) -> None:
    upstream = StageCard(
        agent_id=DEMAND_VALIDATOR_AGENT_ID,
        output_payload={"metric_value": metric_value},
        quest_id="quest-non-finite",
        status=StageStatus.COMPLETE,
        title="Demand validator",
    )
    evidence_payload: dict[str, JsonValue] = {
        "audit_artifact_uri": "/data/noviscope/audits/non-finite.json",
        "audit_policy_version": EVIDENCE_AUDIT_POLICY_VERSION,
        "claim_reference_alignment": True,
        "experiment_claim_alignment": True,
    }
    if include_null_fingerprint:
        evidence_payload[EVIDENCE_AUDIT_FINGERPRINT_KEY] = None
    auditor = StageCard(
        agent_id=EVIDENCE_AUDITOR_AGENT_ID,
        evidence_payload=evidence_payload,
        human_approved=True,
        quest_id="quest-non-finite",
        status=StageStatus.COMPLETE,
        title="Evidence auditor",
    )

    assert evidence_auditor_is_approved(auditor, [upstream, auditor]) is False


@pytest.mark.parametrize(
    "artifact_uri",
    [
        "https://example.com/audit.json",
        "../audit.json",
        "javascript:alert(1)",
        "//remote-host/audit.json",
        "/data//audit.json",
        "/data/\x00/audit.json",
        "/data/../secrets.json",
    ],
)
def test_evidence_auditor_rejects_non_local_or_traversing_artifact_uri(
    artifact_uri: str,
) -> None:
    upstream = StageCard(
        agent_id=DEMAND_VALIDATOR_AGENT_ID,
        quest_id="quest-artifact",
        status=StageStatus.COMPLETE,
        title="Demand validator",
    )
    fingerprint = evidence_audit_stage_fingerprint([upstream])
    assert fingerprint is not None
    auditor = StageCard(
        agent_id=EVIDENCE_AUDITOR_AGENT_ID,
        evidence_payload={
            "audit_artifact_uri": artifact_uri,
            "audit_policy_version": EVIDENCE_AUDIT_POLICY_VERSION,
            "claim_reference_alignment": True,
            "experiment_claim_alignment": True,
            EVIDENCE_AUDIT_FINGERPRINT_KEY: fingerprint,
        },
        human_approved=True,
        quest_id="quest-artifact",
        status=StageStatus.COMPLETE,
        title="Evidence auditor",
    )

    assert evidence_auditor_is_approved(auditor, [upstream, auditor]) is False


def test_current_auditor_fails_closed_when_completed_timestamps_tie() -> None:
    created_at = "2026-07-10T05:00:00+00:00"
    older_auditor = StageCard(
        id="stage_zzzz",
        agent_id=EVIDENCE_AUDITOR_AGENT_ID,
        created_at=created_at,
        quest_id="quest-auditor-tie",
        status=StageStatus.COMPLETE,
        title="Older approved auditor",
    )
    newer_auditor = StageCard(
        id="stage_aaaa",
        agent_id=EVIDENCE_AUDITOR_AGENT_ID,
        created_at=created_at,
        quest_id="quest-auditor-tie",
        status=StageStatus.COMPLETE,
        title="Newer rejected auditor",
    )

    assert find_current_evidence_auditor([older_auditor, newer_auditor]) is None
