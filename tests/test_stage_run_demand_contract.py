from fastapi.testclient import TestClient
from test_stage_run_api import (
    create_quest_with_stages,
    get_fake_literature_runner,
    register_and_login,
)

from noviscope.agents.literature_scout import get_literature_scout_runner
from noviscope.main import create_app


def test_run_literature_scout_rejects_mixed_malformed_human_demand_sources(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'literature-mixed-evidence.db'}")
    app.dependency_overrides[get_literature_scout_runner] = get_fake_literature_runner

    with TestClient(app) as client:
        register_and_login(client, "RUN-LIT-MIXED-EVIDENCE", "lit-mixed@example.com")
        _, demand_stage_id, literature_stage_id, _, _, _ = create_quest_with_stages(client)
        running_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={"status": "running"},
        )
        assert running_response.status_code == 200
        complete_response = client.patch(
            f"/stages/{demand_stage_id}",
            json={
                "evidence_payload": {
                    "human_demand_sources": ["Coach interview note.", None],
                    "human_demand_verdict": "verified",
                },
                "human_approved": True,
                "output_payload": {"confidence": "medium"},
                "status": "complete",
                "summary": "Demand validation complete.",
            },
        )
        assert complete_response.status_code == 200

        response = client.post(f"/stages/{literature_stage_id}/run", json={})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["evidence_payload"]["blocking_reason"] == (
        "demand_evidence_review_required"
    )
