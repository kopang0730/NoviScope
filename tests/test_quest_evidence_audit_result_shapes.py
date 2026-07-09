import pytest
from fastapi.testclient import TestClient
from pydantic import JsonValue
from quest_evidence_audit_test_support import add_trusted_code_result_stage
from test_quest_evidence_audit_api import register_and_login
from test_quest_evidence_audit_trust import blocking_codes, create_ready_quest

from noviscope.main import create_app


@pytest.mark.parametrize(
    "field",
    [
        "artifact_uri",
        "baseline_name",
        "dataset_name",
        "metric_name",
        "metric_unit",
        "run_id",
    ],
)
def test_audit_rejects_list_valued_result_identity_fields(
    tmp_path,
    dev_admin_header_enabled: None,
    field: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'audit-list-{field}.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(
            client,
            f"AUDIT-LIST-{field.upper()}",
            f"audit-list-{field}@example.com",
        )
        quest_id, _ = create_ready_quest(client, database_url)
        result_record: dict[str, JsonValue] = {
            "artifact_uri": "/data/noviscope/runs/run-001/metrics.json",
            "baseline_name": "Pose-based action classifier",
            "dataset_name": "Badminton clips v1",
            "metric_name": "Action classification accuracy",
            "metric_unit": "%",
            "metric_value": 78.4,
            "result_status": "verified",
            "run_id": "run-001",
        }
        result_record[field] = [result_record[field], "forged-value"]
        add_trusted_code_result_stage(database_url, quest_id, result_record)
        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["ready_for_formal_claims"] is False
    assert "experiment_results_invalid" in blocking_codes(body)


def test_audit_rejects_a_malformed_verified_result_mixed_with_a_valid_result(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'audit-mixed-result.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client, "AUDIT-MIXED-RESULT", "audit-mixed-result@example.com")
        quest_id, _ = create_ready_quest(client, database_url)
        add_trusted_code_result_stage(database_url, quest_id)
        add_trusted_code_result_stage(
            database_url,
            quest_id,
            {
                "artifact_uri": ["/data/metrics.json"],
                "baseline_name": "Pose-based action classifier",
                "dataset_name": "Badminton clips v1",
                "metric_name": "Accuracy",
                "metric_unit": "%",
                "metric_value": float("nan"),
                "result_status": "verified",
                "run_id": "run-forged",
            },
        )

        response = client.get(f"/quests/{quest_id}/evidence-audit")

    body = response.json()
    assert body["audit_status"] == "blocked"
    assert body["ready_for_formal_claims"] is False
    assert "experiment_results_invalid" in blocking_codes(body)
    issue = next(
        item
        for item in body["blocking_issues"]
        if item["code"] == "experiment_results_invalid"
    )
    assert issue["agent_id"] == "code_runner"
    assert issue["stage_id"]
