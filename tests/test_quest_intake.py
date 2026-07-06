from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from noviscope.db.session import create_db_engine, create_schema
from noviscope.main import create_app
from noviscope.models.quest import Quest
from noviscope.quests.intake import QuestCreateSpec, QuestIntake
from noviscope.quests.service import QuestService

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
    invite_response = client.post(
        "/admin/invites",
        headers=DEV_ADMIN_HEADERS,
        json={"code": invite_code, "max_uses": 1},
    )
    assert invite_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "display_name": email.split("@")[0],
            "email": email,
            "invite_code": invite_code,
            "password": "password123",
        },
    )
    assert register_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200


def test_create_quest_from_intake_persists_structured_payload(db_session: Session) -> None:
    intake = QuestIntake(
        evaluation_metrics="Action classification accuracy and trajectory error",
        existing_data="/data/badminton/videos",
        input_and_output="Input: match videos. Output: shuttle trajectory and action labels.",
        known_baselines="Pose estimation, shuttle tracking, temporal action recognition",
        preferred_language="Chinese and English",
        real_world_scenario="Badminton training replay analysis for coaches.",
        research_direction="Badminton shuttle trajectory and action recognition",
        target_user_or_customer="Badminton coaches and athletes",
    )

    quest = QuestService(db_session).create_quest_from_intake(
        QuestCreateSpec(title="AI+Sports Badminton", intake=intake)
    )

    assert quest.intake_payload == intake.model_dump()
    assert "Research direction: Badminton shuttle trajectory" in quest.initial_direction
    assert "Real-world scenario: Badminton training replay analysis" in quest.initial_direction


def test_legacy_create_quest_keeps_empty_intake_payload(db_session: Session) -> None:
    quest = QuestService(db_session).create_quest(
        title="Handwritten Text Erasure",
        initial_direction="Erase handwritten answers from scanned worksheets.",
    )

    assert quest.initial_direction == "Erase handwritten answers from scanned worksheets."
    assert quest.intake_payload == {}


def test_create_schema_upgrades_legacy_quest_table_with_intake_payload(tmp_path) -> None:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'legacy-quest-intake.db'}")

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE quest (
                    id VARCHAR NOT NULL PRIMARY KEY,
                    title VARCHAR NOT NULL,
                    initial_direction VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    updated_at VARCHAR NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO quest (
                    id,
                    title,
                    initial_direction,
                    status,
                    created_at,
                    updated_at
                ) VALUES (
                    'quest_legacy_1',
                    'Legacy Quest',
                    'AI+Sports',
                    'draft',
                    '2026-07-05T00:00:00+00:00',
                    '2026-07-05T00:00:00+00:00'
                )
                """
            )
        )

    create_schema(engine)
    create_schema(engine)

    with Session(engine) as session:
        quest = session.get(Quest, "quest_legacy_1")

    assert quest is not None
    assert quest.intake_payload == {}


def test_quest_intake_endpoint_updates_structured_payload(
    dev_admin_header_enabled: None,
) -> None:
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INTAKE-OWNER", "intake-owner@example.com")
        quest = client.post(
            "/quests",
            json={"title": "Badminton", "initial_direction": "AI+Sports"},
        ).json()

        update_response = client.put(
            f"/quests/{quest['id']}/intake",
            json={
                "intake_payload": {
                    "evaluation_metrics": "Trajectory error and action classification accuracy",
                    "existing_data": "/data/badminton",
                    "input_and_output": "Input video, output shuttle trajectory and action labels",
                    "known_baselines": "Pose estimation and temporal action recognition",
                    "preferred_language": "Chinese and English",
                    "real_world_scenario": "Badminton training replay analysis",
                    "research_direction": "Badminton trajectory and action recognition",
                    "target_user_or_customer": "Coaches and athletes",
                }
            },
        )

        assert update_response.status_code == 200
        body = update_response.json()
        assert body["quest_id"] == quest["id"]
        assert body["intake_payload"]["research_direction"] == (
            "Badminton trajectory and action recognition"
        )
        assert "Research direction: Badminton trajectory" in body["initial_direction"]

        get_response = client.get(f"/quests/{quest['id']}/intake")
        assert get_response.status_code == 200
        assert get_response.json()["intake_payload"] == body["intake_payload"]


def test_quest_intake_endpoint_rejects_other_users(dev_admin_header_enabled: None) -> None:
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INTAKE-FIRST", "first@example.com")
        quest = client.post(
            "/quests",
            json={"title": "Owned", "initial_direction": "AI+Sports"},
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "INTAKE-SECOND", "second@example.com")
        response = client.get(f"/quests/{quest['id']}/intake")

        assert response.status_code == 403
