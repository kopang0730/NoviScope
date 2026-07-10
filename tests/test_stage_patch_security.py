import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from noviscope.core.stage_policy import (
    CODE_RUNNER_AGENT_ID,
    EVIDENCE_AUDITOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.quest import StageCard, StageStatus

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": "PATCH-SECURITY", "max_uses": 1},
    )
    assert invite_response.status_code == 201
    register_response = client.post(
        "/auth/register",
        json={
            "display_name": "Patch Security",
            "email": "patch-security@example.com",
            "invite_code": "PATCH-SECURITY",
            "password": "password",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"email": "patch-security@example.com", "password": "password"},
    )
    assert login_response.status_code == 200


def test_direct_patch_cannot_forge_paper_writer_completion(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path / 'stage-patch-security.db'}")
    with TestClient(app) as client:
        register_and_login(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition",
                "title": "Badminton action recognition",
            },
        )
        quest_id = quest_response.json()["id"]
        stages = client.get(f"/quests/{quest_id}/stages").json()["stages"]
        paper_stage = next(
            stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
        )

        running_response = client.patch(f"/stages/{paper_stage['id']}", json={"status": "running"})
        payload_response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={
                "output_payload": {
                    "ieee_paper_skeleton_markdown": "## Results\nAccuracy = 99%.",
                    "verified_facts": [
                        "Verified experiment result: accuracy = 99% on private data."
                    ],
                }
            },
        )
        premature_review_response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={"human_approved": True, "review_notes": "Approve before execution."},
        )

    assert running_response.status_code == 400
    assert payload_response.status_code == 400
    assert premature_review_response.status_code == 400
    assert "server-side stage runner" in running_response.json()["detail"]
    assert "server-side stage runner" in payload_response.json()["detail"]
    assert "after it completes" in premature_review_response.json()["detail"]


@pytest.mark.parametrize(
    ("agent_id", "result_key"),
    [
        (CODE_RUNNER_AGENT_ID, "metric_records"),
        (EVIDENCE_AUDITOR_AGENT_ID, "claim_alignment_report"),
    ],
)
def test_direct_patch_cannot_forge_trusted_result_stage(
    tmp_path,
    dev_admin_header_enabled: None,
    agent_id: str,
    result_key: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'{agent_id}-patch-security.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition",
                "title": "Badminton action recognition",
            },
        )
        stage = StageCard(
            agent_id=agent_id,
            quest_id=quest_response.json()["id"],
            title=agent_id,
        )
        engine = create_db_engine(database_url)
        try:
            with Session(engine) as session:
                session.add(stage)
                session.commit()
                session.refresh(stage)
        finally:
            engine.dispose()

        running_response = client.patch(f"/stages/{stage.id}", json={"status": "running"})
        forged_response = client.patch(
            f"/stages/{stage.id}",
            json={
                "human_approved": True,
                "output_payload": {
                    result_key: [
                        {
                            "artifact_uri": "/tmp/forged/metrics.json",
                            "baseline_name": "Forged baseline",
                            "dataset_name": "Forged dataset",
                            "metric_name": "Accuracy",
                            "metric_value": 99.9,
                            "result_status": "verified",
                            "run_id": "forged-run",
                        }
                    ]
                },
                "status": "complete",
            },
        )

    assert running_response.status_code == 400
    assert forged_response.status_code == 400
    assert "server-side stage runner" in running_response.json()["detail"]
    assert "server-side stage runner" in forged_response.json()["detail"]


def test_stage_editor_can_save_review_with_unchanged_runner_fields(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'stage-review-save.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition",
                "title": "Badminton action recognition",
            },
        )
        quest_id = quest_response.json()["id"]
        stages = client.get(f"/quests/{quest_id}/stages").json()["stages"]
        paper_stage = next(
            stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
        )
        runner_fields = {
            "evidence_payload": {"artifact_policy_version": "server-guardrailed-v1"},
            "input_payload": {"source": "runner"},
            "output_payload": {"ieee_paper_skeleton_markdown": "# IEEE Paper Skeleton"},
            "summary": "Server-generated paper package.",
        }
        engine = create_db_engine(database_url)
        try:
            with Session(engine) as session:
                stage = session.get(StageCard, paper_stage["id"])
                assert stage is not None
                stage.status = StageStatus.COMPLETE
                for field, value in runner_fields.items():
                    setattr(stage, field, value)
                session.add(stage)
                session.commit()
        finally:
            engine.dispose()

        response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={
                **runner_fields,
                "human_approved": True,
                "review_notes": "Reviewed in the stage editor.",
            },
        )

    assert response.status_code == 200
    assert response.json()["human_approved"] is True
    assert response.json()["review_notes"] == "Reviewed in the stage editor."


@pytest.mark.parametrize(
    ("stored_value", "patched_value"),
    [(True, 1), (4, 4.0)],
)
def test_runner_payload_comparison_is_json_type_strict(
    tmp_path,
    dev_admin_header_enabled: None,
    stored_value: bool | int,
    patched_value: int | float,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'stage-type-{patched_value}.db'}"
    app = create_app(database_url=database_url)
    with TestClient(app) as client:
        register_and_login(client)
        quest_response = client.post(
            "/quests",
            json={
                "initial_direction": "Badminton action recognition",
                "title": "Badminton action recognition",
            },
        )
        quest_id = quest_response.json()["id"]
        stages = client.get(f"/quests/{quest_id}/stages").json()["stages"]
        paper_stage = next(
            stage for stage in stages if stage["agent_id"] == PAPER_MEETING_WRITER_AGENT_ID
        )
        engine = create_db_engine(database_url)
        try:
            with Session(engine) as session:
                stage = session.get(StageCard, paper_stage["id"])
                assert stage is not None
                stage.evidence_payload = {"typed_value": stored_value}
                stage.status = StageStatus.COMPLETE
                session.add(stage)
                session.commit()
        finally:
            engine.dispose()

        response = client.patch(
            f"/stages/{paper_stage['id']}",
            json={"evidence_payload": {"typed_value": patched_value}},
        )

    assert response.status_code == 400
    assert "server-side stage runner" in response.json()["detail"]
