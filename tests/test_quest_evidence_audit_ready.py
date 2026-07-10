import pytest
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

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
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
        add_approved_evidence_auditor_stage(database_url, quest_id)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "ready"
    assert body["ready_for_formal_claims"] is True
    assert body["blocking_issue_count"] == 0
    assert body["review_item_count"] == 0
    assert body["evidence_source_count"] >= 2
    assert "verified_experiment_result_recorded" in body["passed_checks"]
    assert "evidence_audit_approved" in body["passed_checks"]


@pytest.mark.parametrize("alignment_value", ["verified", 1])
def test_evidence_audit_requires_strict_boolean_alignment_markers(
    tmp_path,
    dev_admin_header_enabled: None,
    alignment_value: str | int,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'evidence-audit-alignment-{alignment_value}.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(
            client,
            f"AUDIT-ALIGNMENT-{alignment_value}",
            f"audit-alignment-{alignment_value}@example.com",
        )
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)
        add_approved_evidence_auditor_stage(
            database_url,
            quest_id,
            alignment_value=alignment_value,
        )

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert body["ready_for_formal_claims"] is False
    assert {issue["code"] for issue in body["blocking_issues"]} == {
        "evidence_audit_not_approved"
    }


def test_evidence_audit_blocks_formal_claims_without_evidence_auditor(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-auditor-missing.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-NO-AUDITOR", "audit-no-auditor@example.com")
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

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert body["ready_for_formal_claims"] is False
    assert {issue["code"] for issue in body["blocking_issues"]} == {
        "evidence_audit_not_approved"
    }


def test_evidence_audit_rejects_an_auditor_without_server_evidence_contract(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-auditor-invalid.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-BAD-AUDITOR", "audit-bad-auditor@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)
        add_approved_evidence_auditor_stage(
            database_url,
            quest_id,
            valid_contract=False,
        )

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert body["ready_for_formal_claims"] is False
    assert {issue["code"] for issue in body["blocking_issues"]} == {
        "evidence_audit_not_approved"
    }


def test_evidence_audit_rejects_a_stale_auditor_after_upstream_changes(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-auditor-stale.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-STALE-AUDITOR", "audit-stale-auditor@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)
        add_approved_evidence_auditor_stage(database_url, quest_id)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{"doi": "10.9999/changed.2026"}]}},
        )

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "blocked"
    assert body["ready_for_formal_claims"] is False
    assert {issue["code"] for issue in body["blocking_issues"]} == {
        "evidence_audit_not_approved"
    }


def test_evidence_audit_accepts_a_fresh_auditor_after_an_older_one_becomes_stale(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'evidence-auditor-refreshed.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-REFRESHED", "audit-refreshed@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        add_trusted_code_result_stage(database_url, quest_id)
        add_approved_evidence_auditor_stage(database_url, quest_id)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{"doi": "10.9999/changed.2026"}]}},
        )
        add_approved_evidence_auditor_stage(database_url, quest_id)

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "ready"
    assert body["ready_for_formal_claims"] is True
    assert body["blocking_issue_count"] == 0
    assert "evidence_audit_approved" in body["passed_checks"]
