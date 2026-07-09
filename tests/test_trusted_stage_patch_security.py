import pytest
from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlmodel import Session
from test_stage_patch_security import register_and_login

from noviscope.core.stage_policy import (
    CODE_RUNNER_AGENT_ID,
    EVIDENCE_AUDITOR_AGENT_ID,
    PAPER_MEETING_WRITER_AGENT_ID,
)
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.quest import StageCard, StageStatus


def add_complete_runner_stage(
    database_url: str,
    quest_id: str,
    agent_id: str,
) -> str:
    stage = StageCard(
        agent_id=agent_id,
        evidence_payload={"policy_version": "server-v1"},
        human_approved=True,
        output_payload={"experiment_results": []},
        quest_id=quest_id,
        status=StageStatus.COMPLETE,
        summary="Server-generated runner output.",
        title="Trusted runner",
    )
    engine = create_db_engine(database_url)
    try:
        with Session(engine) as session:
            session.add(stage)
            session.commit()
            session.refresh(stage)
            return stage.id
    finally:
        engine.dispose()


@pytest.mark.parametrize("agent_id", [CODE_RUNNER_AGENT_ID, EVIDENCE_AUDITOR_AGENT_ID])
@pytest.mark.parametrize(
    "patch",
    [
        {"evidence_payload": {"policy_version": "forged"}},
        {"output_payload": {"experiment_results": [{"metric_value": 99.9}]}},
        {"status": "running"},
        {"summary": "User-authored trusted result."},
    ],
)
def test_public_patch_cannot_mutate_trusted_runner_execution_fields(
    tmp_path,
    dev_admin_header_enabled: None,
    agent_id: str,
    patch: dict[str, JsonValue],
) -> None:
    database_url = f"sqlite:///{tmp_path / f'{agent_id}-{next(iter(patch))}.db'}"
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
        stage_id = add_complete_runner_stage(
            database_url,
            quest_response.json()["id"],
            agent_id,
        )

        response = client.patch(f"/stages/{stage_id}", json=patch)

    assert response.status_code == 400
    assert "server-side stage runner" in response.json()["detail"]


@pytest.mark.parametrize(
    "agent_id",
    [CODE_RUNNER_AGENT_ID, EVIDENCE_AUDITOR_AGENT_ID, PAPER_MEETING_WRITER_AGENT_ID],
)
def test_public_patch_cannot_block_a_rejected_runner_stage(
    tmp_path,
    dev_admin_header_enabled: None,
    agent_id: str,
) -> None:
    database_url = f"sqlite:///{tmp_path / f'{agent_id}-rejected-status.db'}"
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
        stage_id = add_complete_runner_stage(
            database_url,
            quest_response.json()["id"],
            agent_id,
        )
        review_response = client.patch(
            f"/stages/{stage_id}",
            json={"human_approved": False, "review_notes": "Rejected."},
        )

        block_response = client.patch(
            f"/stages/{stage_id}",
            json={"status": "blocked"},
        )

    assert review_response.status_code == 200
    assert review_response.json()["human_approved"] is False
    assert block_response.status_code == 400
    assert "server-side stage runner" in block_response.json()["detail"]
