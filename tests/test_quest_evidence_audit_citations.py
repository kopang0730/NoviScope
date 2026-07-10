import pytest
from fastapi.testclient import TestClient
from quest_evidence_audit_test_support import add_trusted_code_result_stage
from test_quest_evidence_audit_api import register_and_login
from test_quest_evidence_audit_trust import create_ready_quest, review_codes

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.main import create_app


@pytest.mark.parametrize(
    ("reference_key", "reference_value"),
    [
        ("arxiv_id", " arXiv:2401.12345"),
        ("doi", "Title without identifier"),
        ("doi", " https://doi.org/10.1234/valid.2026"),
        ("openalex_id", "not-an-openalex-id"),
        ("openalex_id", "https://openalex.org/W123 "),
        ("paper_ref", "not a URL"),
        ("paper_ref", " 10.1234/valid.2026"),
        ("paper_ref", " https://example.com/paper"),
        ("paper_ref", "https://bad host/paper"),
        ("url", "javascript:alert(1)"),
        ("url", "https://[broken"),
        ("url", "https://bad host/paper"),
        ("url", "https://example.com/paper "),
    ],
)
def test_audit_rejects_malformed_literature_identifiers(
    tmp_path,
    dev_admin_header_enabled: None,
    reference_key: str,
    reference_value: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'audit-{reference_key}-ref.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(
            client,
            f"AUDIT-{reference_key.upper()}-REF",
            f"audit-{reference_key}@example.com",
        )
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{reference_key: reference_value}]}},
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    assert "literature_sources_invalid" in review_codes(response.json())


def test_audit_rejects_a_malformed_identifier_mixed_with_a_valid_source(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-mixed-literature-ref.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-MIXED-REF", "audit-mixed-ref@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={
                "output_payload": {
                    "papers": [
                        {"doi": "10.1234/valid.2026"},
                        {"doi": "not-a-doi"},
                    ]
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "literature_sources_invalid" in review_codes(body)


def test_audit_accepts_mixed_case_openalex_url(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-openalex-case.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-OPENALEX-CASE", "audit-case@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{"openalex_id": "HTTPS://OPENALEX.ORG/W123"}]}},
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    assert "literature_sources_missing" not in review_codes(response.json())
    assert "literature_sources_invalid" not in review_codes(response.json())


def test_audit_ignores_a_null_optional_identifier_when_another_is_valid(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-null-optional-ref.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-NULL-REF", "audit-null-ref@example.com")
        quest_id, stage_ids = create_ready_quest(client, database_url)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={
                "output_payload": {
                    "papers": [
                        {
                            "doi": None,
                            "openalex_id": "https://openalex.org/W123",
                        }
                    ]
                }
            },
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    assert "literature_sources_missing" not in review_codes(response.json())
    assert "literature_sources_invalid" not in review_codes(response.json())
