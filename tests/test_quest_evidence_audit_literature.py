from fastapi.testclient import TestClient
from test_quest_evidence_audit_api import register_and_login
from test_quest_evidence_audit_trust import create_ready_quest, review_codes

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.main import create_app


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
    assert "literature_sources_invalid" in review_codes(body)


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
