from fastapi.testclient import TestClient
from quest_evidence_audit_test_support import (
    add_approved_evidence_auditor_stage,
    add_trusted_code_result_stage,
)
from test_quest_evidence_audit_api import (
    complete_research_gates,
    create_quest_with_stage_map,
    register_and_login,
)

from noviscope.core.stage_policy import DEMAND_VALIDATOR_AGENT_ID
from noviscope.main import create_app


def test_evidence_audit_rejects_a_scalar_human_demand_source(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-demand-source-shape.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-DEMAND-SHAPE", "audit-demand-shape@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)
        demand_patch = client.patch(
            f"/stages/{stage_ids[DEMAND_VALIDATOR_AGENT_ID]}",
            json={
                "evidence_payload": {
                    "human_demand_sources": "not-a-list",
                    "human_demand_verdict": "verified",
                }
            },
        )
        add_approved_evidence_auditor_stage(database_url, quest_id)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert demand_patch.status_code == 200
    body = response.json()
    assert body["audit_status"] == "needs_review"
    assert body["ready_for_formal_claims"] is False
    assert "demand_sources_missing" in {
        item["code"] for item in body["review_items"]
    }
