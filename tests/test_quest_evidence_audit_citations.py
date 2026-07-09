import pytest
from fastapi.testclient import TestClient
from test_quest_evidence_audit_api import register_and_login
from test_quest_evidence_audit_trust import create_ready_quest, review_codes

from noviscope.agents.literature_scout import LITERATURE_SCOUT_AGENT_ID
from noviscope.main import create_app


@pytest.mark.parametrize(
    ("reference_key", "reference_value"),
    [
        ("doi", "Title without identifier"),
        ("openalex_id", "not-an-openalex-id"),
        ("paper_ref", "not a URL"),
        ("url", "javascript:alert(1)"),
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
        quest_id, stage_ids = create_ready_quest(client)
        patch_response = client.patch(
            f"/stages/{stage_ids[LITERATURE_SCOUT_AGENT_ID]}",
            json={"output_payload": {"papers": [{reference_key: reference_value}]}},
        )
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    assert patch_response.status_code == 200
    assert "literature_sources_missing" in review_codes(response.json())
