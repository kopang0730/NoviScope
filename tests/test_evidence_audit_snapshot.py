import math

import pytest

from noviscope.api.evidence_audit_contract import EVIDENCE_AUDIT_POLICY_VERSION
from noviscope.api.evidence_audit_readers import evidence_auditor_is_approved
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


@pytest.mark.parametrize(
    "artifact_uri",
    [
        "https://example.com/audit.json",
        "../audit.json",
        "javascript:alert(1)",
        "//remote-host/audit.json",
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
            "claim_reference_alignment": "verified",
            "experiment_claim_alignment": "verified",
            EVIDENCE_AUDIT_FINGERPRINT_KEY: fingerprint,
        },
        human_approved=True,
        quest_id="quest-artifact",
        status=StageStatus.COMPLETE,
        title="Evidence auditor",
    )

    assert evidence_auditor_is_approved(auditor, [upstream, auditor]) is False
