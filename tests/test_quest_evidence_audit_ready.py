from fastapi.testclient import TestClient
from quest_evidence_audit_test_support import add_trusted_code_result_stage
from test_quest_evidence_audit_api import (
    complete_research_gates,
    create_quest_with_stage_map,
    register_and_login,
)

from noviscope.main import create_app


def test_evidence_audit_allows_formal_claims_when_gates_and_results_are_verified(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-audit-ready.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-READY", "audit-ready@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "ready"
    assert body["ready_for_formal_claims"] is True
    assert body["blocking_issue_count"] == 0
    assert body["review_item_count"] == 0
    assert body["evidence_source_count"] >= 2
    assert "verified_experiment_result_recorded" in body["passed_checks"]
