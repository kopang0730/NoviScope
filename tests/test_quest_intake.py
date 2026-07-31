from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session

from noviscope.db.session import create_db_engine, create_schema
from noviscope.main import create_app
from noviscope.quests.intake import QuestCreateSpec, QuestIntake, QuestIntakeUpdateSpec
from noviscope.quests.service import QuestService

DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": "test-dev-admin-token-0123456789abcdef"}


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
    # Given: a developer-enabled invite flow for one test member.
    invite_response = client.post(
        "/admin/invites",
        json={"code": invite_code, "max_uses": 1},
        headers=DEV_ADMIN_HEADERS,
    )
    assert invite_response.status_code == 201

    register_response = client.post(
        "/auth/register",
        json={
            "invite_code": invite_code,
            "email": email,
            "display_name": email.split("@")[0],
            "password": "password",
        },
    )
    assert register_response.status_code == 201

    # When: the member signs in.
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password"},
    )

    # Then: subsequent API calls use the member session cookie.
    assert login_response.status_code == 200


def test_create_quest_from_intake_persists_structured_payload(
    db_session: Session,
) -> None:
    # Given: a structured research intake with user-facing fields.
    service = QuestService(db_session)
    intake = QuestIntake(
        research_direction="  hand-written text erasure  ",
        real_world_scenario="restore used exam papers for reuse",
        target_user_or_customer="education hardware company",
        input_and_output="input: scanned worksheet; output: clean worksheet",
        existing_data="internal scanned exams",
        known_baselines="image inpainting, document cleanup",
        evaluation_metrics="OCR consistency, erasure quality, background fidelity",
        preferred_language="both",
    )

    # When: the service creates a Quest from the typed intake contract.
    quest = service.create_quest_from_intake(
        QuestCreateSpec(title="Handwriting erasure", intake=intake)
    )

    # Then: structured fields stay queryable and a readable fallback is rendered.
    assert quest.intake_payload == {
        "research_direction": "hand-written text erasure",
        "real_world_scenario": "restore used exam papers for reuse",
        "target_user_or_customer": "education hardware company",
        "input_and_output": "input: scanned worksheet; output: clean worksheet",
        "existing_data": "internal scanned exams",
        "known_baselines": "image inpainting, document cleanup",
        "evaluation_metrics": "OCR consistency, erasure quality, background fidelity",
        "preferred_language": "both",
    }
    assert "Research direction: hand-written text erasure" in quest.initial_direction
    assert "Preferred output language: both" in quest.initial_direction
    assert len(service.list_stage_cards(quest.id)) == 5


def test_legacy_create_quest_keeps_empty_intake_payload(db_session: Session) -> None:
    # Given: the legacy text-only Quest creation path.
    service = QuestService(db_session)

    # When: a Quest is created without structured intake.
    quest = service.create_quest(
        title="Badminton trajectory",
        initial_direction="AI+Sports badminton trajectory recognition",
    )

    # Then: legacy behavior is preserved without inventing structured fields.
    assert quest.initial_direction == "AI+Sports badminton trajectory recognition"
    assert quest.intake_payload == {}


def test_update_quest_intake_renders_direction_when_not_overridden(
    db_session: Session,
) -> None:
    # Given: an existing text-only Quest.
    service = QuestService(db_session)
    quest = service.create_quest(title="Draft", initial_direction="old direction")

    # When: structured intake is saved without an explicit text override.
    updated = service.update_quest_intake(
        QuestIntakeUpdateSpec(
            quest_id=quest.id,
            intake=QuestIntake(
                research_direction="badminton shuttle trajectory recognition",
                real_world_scenario="sports coaching feedback",
                preferred_language="en",
            ),
        )
    )

    # Then: the persisted payload and readable direction both reflect the intake.
    assert updated.intake_payload == {
        "research_direction": "badminton shuttle trajectory recognition",
        "real_world_scenario": "sports coaching feedback",
        "preferred_language": "en",
    }
    assert "Research direction: badminton shuttle trajectory recognition" in (
        updated.initial_direction
    )
    assert "Real-world scenario: sports coaching feedback" in updated.initial_direction


def test_create_schema_upgrades_legacy_quest_table_with_intake_payload(
    tmp_path: Path,
) -> None:
    # Given: a legacy Quest table created before structured intake existed.
    engine = create_db_engine(f"sqlite:///{tmp_path / 'legacy-intake.db'}")
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
                    'quest_legacy_intake',
                    'Legacy Quest',
                    'AI+Sports',
                    'draft',
                    '2026-07-05T00:00:00+00:00',
                    '2026-07-05T00:00:00+00:00'
                )
                """
            )
        )

    # When: startup schema creation runs more than once.
    create_schema(engine)
    create_schema(engine)

    # Then: the legacy table has a non-null JSON intake payload column.
    with engine.begin() as connection:
        columns = {
            row[1]: row for row in connection.execute(text("PRAGMA table_info('quest')")).fetchall()
        }
        assert "intake_payload" in columns
        assert (
            connection.execute(
                text("SELECT intake_payload FROM quest WHERE id = 'quest_legacy_intake'")
            ).scalar_one()
            == "{}"
        )


def test_quest_intake_endpoint_updates_and_reads_structured_payload(
    dev_admin_header_enabled: None,
) -> None:
    # Given: an authenticated member with a legacy-created Quest.
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INTAKE-INVITE", "intake@example.com")
        quest_response = client.post(
            "/quests",
            json={"title": "Handwriting erasure", "initial_direction": "draft"},
        )
        quest_id = quest_response.json()["id"]

        # When: the frontend saves structured intake for that Quest.
        update_response = client.put(
            f"/quests/{quest_id}/intake",
            json={
                "intake_payload": {
                    "research_direction": "handwritten answer erasure",
                    "real_world_scenario": "reusable exam paper restoration",
                    "target_user_or_customer": "education hardware vendor",
                    "input_and_output": "scanned used paper to clean paper",
                    "existing_data": "scanned worksheets",
                    "known_baselines": "inpainting baseline",
                    "evaluation_metrics": "OCR consistency",
                    "preferred_language": "zh",
                }
            },
        )
        read_response = client.get(f"/quests/{quest_id}/intake")

    # Then: API callers receive the typed intake and rendered direction.
    assert update_response.status_code == 200
    assert read_response.status_code == 200
    assert read_response.json()["intake_payload"]["preferred_language"] == "zh"
    assert (
        "Research direction: handwritten answer erasure"
        in read_response.json()["initial_direction"]
    )


def test_quest_intake_endpoint_rejects_other_members(
    dev_admin_header_enabled: None,
) -> None:
    # Given: one member owns a Quest.
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "OWNER-INTAKE", "owner-intake@example.com")
        quest_response = client.post(
            "/quests",
            json={"title": "Owner Quest", "initial_direction": "owned"},
        )
        quest_id = quest_response.json()["id"]

        # When: another member tries to read the intake.
        client.post("/auth/logout")
        register_and_login(client, "OTHER-INTAKE", "other-intake@example.com")
        response = client.get(f"/quests/{quest_id}/intake")

    # Then: member-level ownership is enforced.
    assert response.status_code == 403
