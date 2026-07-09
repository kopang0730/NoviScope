import pytest
from fastapi.testclient import TestClient
from quest_evidence_audit_test_support import (
    add_trusted_code_result_stage,
    set_server_paper_stage,
)
from test_quest_evidence_audit_api import (
    complete_research_gates,
    create_quest_with_stage_map,
    register_and_login,
)

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.core.json_types import JsonObject
from noviscope.core.stage_policy import (
    DEMAND_VALIDATOR_AGENT_ID,
    EXPERIMENT_PLANNER_AGENT_ID,
    IDEA_GENERATOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.main import create_app


def create_ready_quest(
    client: TestClient,
    database_url: str,
) -> tuple[str, dict[str, str]]:
    quest_id, stage_ids = create_quest_with_stage_map(client)
    complete_research_gates(
        client,
        stage_ids,
        database_url=database_url,
        paper_approved=True,
        verified_result=True,
    )
    return quest_id, stage_ids


def review_codes(body: JsonObject) -> set[str]:
    review_items = body["review_items"]
    assert isinstance(review_items, list)
    return {
        str(item["code"])
        for item in review_items
        if isinstance(item, dict) and "code" in item
    }


def blocking_codes(body: JsonObject) -> set[str]:
    blocking_issues = body["blocking_issues"]
    assert isinstance(blocking_issues, list)
    return {
        str(item["code"])
        for item in blocking_issues
        if isinstance(item, dict) and "code" in item
    }


def test_audit_rejects_model_only_demand_evidence(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-demand-trust.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-DEMAND-TRUST", "audit-demand@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[DEMAND_VALIDATOR_AGENT_ID]}",
            json={
                "evidence_payload": {},
                "human_approved": True,
                "output_payload": {
                    "evidence_for_demand": ["Model-generated demand statement."],
                },
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "demand_sources_missing" in review_codes(body)


def test_audit_keeps_planner_verified_results_out_of_formal_claims(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-planner-result.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-PLANNER-RESULT", "audit-planner@example.com")
        quest_id, stage_ids = create_quest_with_stage_map(client)
        complete_research_gates(
            client,
            stage_ids,
            database_url=database_url,
            paper_approved=True,
            verified_result=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "experiment_results_missing" in review_codes(body)


@pytest.mark.parametrize(
    ("human_approved", "selected_idea_id"),
    [(False, "idea_temporal_consistency"), (True, "idea_not_generated")],
)
def test_audit_requires_an_approved_generated_idea(
    tmp_path,
    dev_admin_header_enabled: None,
    human_approved: bool,
    selected_idea_id: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'audit-idea-{selected_idea_id}.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(
            client,
            f"AUDIT-IDEA-{selected_idea_id}",
            f"audit-idea-{selected_idea_id}@example.com",
        )
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[IDEA_GENERATOR_AGENT_ID]}",
            json={
                "human_approved": human_approved,
                "output_payload": {
                    "ideas": [{"idea_id": "idea_temporal_consistency"}],
                    "selected_idea_ids": [selected_idea_id],
                },
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["audit_status"] == "blocked"
    assert "idea_not_selected" in blocking_codes(body)


def test_audit_rejects_title_only_literature_entries(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-literature-ref.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-LIT-REF", "audit-lit@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{"title": "Title without identifier"}]}},
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "literature_sources_missing" in review_codes(body)


def test_audit_rejects_generic_text_as_a_literature_source(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-literature-text.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-LIT-TEXT", "audit-lit-text@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={
                "output_payload": {
                    "evidence_for_demand": ["Model-authored text is not a paper reference."],
                    "papers": [],
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "literature_sources_missing" in review_codes(body)


def test_audit_accepts_an_openalex_identifier_as_a_literature_source(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-openalex-ref.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-OPENALEX", "audit-openalex@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={
                "output_payload": {
                    "papers": [{"openalex_id": "https://openalex.org/W123"}],
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    assert "literature_sources_missing" not in review_codes(response.json())


def test_audit_requires_all_downloadable_paper_artifacts(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-paper-artifacts.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-PAPER-ARTIFACT", "audit-paper@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": "",
                "english_research_brief_markdown": "# Research Brief",
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "verified_facts": ["Verified experiment result: accuracy = 78.4%."],
            },
            human_approved=True,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert "paper_draft_not_generated" in blocking_codes(body)


def test_audit_rejects_paper_artifacts_without_server_guardrail_provenance(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-paper-provenance.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-PAPER-PROVENANCE", "audit-provenance@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        set_server_paper_stage(
            database_url,
            stage_ids[PAPER_MEETING_WRITER_AGENT_ID],
            {
                "chinese_research_brief_markdown": "# 中文研究 Brief",
                "english_research_brief_markdown": "# Research Brief",
                "ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton",
                "meeting_outline_markdown": "# Group Meeting Outline",
                "verified_facts": [],
            },
            human_approved=True,
            guardrailed=False,
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert "paper_artifacts_untrusted" in blocking_codes(body)


def test_audit_requires_a_finite_measured_metric_value(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-metric-value.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-METRIC-VALUE", "audit-metric@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(
            database_url,
            quest_id,
            {
                "artifact_uri": "/data/run/metrics.json",
                "metric_name": "Accuracy",
                "result_status": "verified",
                "run_id": "run-without-value",
            },
        )
        patch_response = client.patch(
            f"/stages/{stage_ids[EXPERIMENT_PLANNER_AGENT_ID]}",
            json={
                "output_payload": {
                    "experiment_results": [
                        {
                            "artifact_uri": "/data/run/metrics.json",
                            "metric_name": "Accuracy",
                            "result_status": "verified",
                        }
                    ],
                    "first_runnable_script_plan": ["Run baseline."],
                    "metrics": ["Accuracy"],
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "experiment_results_missing" in review_codes(body)
