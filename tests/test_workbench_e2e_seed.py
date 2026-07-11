from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlmodel import Session, select

from noviscope.agents.demand_validation import DemandValidationOutput
from noviscope.auth.passwords import verify_password
from noviscope.core.crypto import SecretBox
from noviscope.db.session import create_db_engine, create_schema
from noviscope.models.agent import AgentAssignment
from noviscope.models.provider import ModelProvider, ProviderScope
from noviscope.models.quest import Quest, StageCard, StageStatus
from noviscope.models.user import InviteCode, User, UserRole
from scripts.seed_workbench_e2e import E2ESeedError, seed_workbench_e2e
from tests.e2e_support.fake_openai_provider import app as fake_provider_app

PROVIDER_SECRET = SecretStr("test-e2e-provider-secret-0123456789-ABCD")
PROVIDER_BASE_URL = "http://127.0.0.1:8999/v1"


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_seed_rejects_non_sqlite_database_urls() -> None:
    with pytest.raises(E2ESeedError, match="SQLite"):
        seed_workbench_e2e(
            "postgresql://noviscope@example.test/noviscope",
            PROVIDER_BASE_URL,
            PROVIDER_SECRET,
        )


@pytest.mark.parametrize(
    "provider_base_url",
    [
        "https://api.anthropic.com/v1",
        "http://10.0.0.8:8999/v1",
        "http://192.168.1.20:8999/v1",
        "http://172.16.0.4:8999/v1",
    ],
)
def test_seed_rejects_non_loopback_provider_urls_before_database_mutation(
    tmp_path: Path,
    provider_base_url: str,
) -> None:
    database_path = tmp_path / "external-provider.db"

    with pytest.raises(E2ESeedError, match="loopback"):
        seed_workbench_e2e(
            sqlite_url(database_path),
            provider_base_url,
            PROVIDER_SECRET,
        )

    assert database_path.exists() is False


@pytest.mark.parametrize(
    "provider_base_url",
    [
        "http://localhost:8999/v1",
        "https://127.0.0.2:8999/v1",
        "http://[::1]:8999/v1",
    ],
)
def test_seed_accepts_http_loopback_provider_urls(
    tmp_path: Path,
    provider_base_url: str,
) -> None:
    database_url = sqlite_url(tmp_path / f"loopback-{provider_base_url.count(':')}.db")

    seed_workbench_e2e(database_url, provider_base_url, PROVIDER_SECRET)

    with Session(create_db_engine(database_url)) as session:
        providers = list(session.exec(select(ModelProvider)).all())
    assert {provider.base_url for provider in providers} == {provider_base_url}


def test_seed_refuses_a_database_that_already_contains_users(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "refusal.db")
    seed_workbench_e2e(database_url, PROVIDER_BASE_URL, PROVIDER_SECRET)

    with pytest.raises(E2ESeedError, match="already contains NoviScope data"):
        seed_workbench_e2e(database_url, PROVIDER_BASE_URL, PROVIDER_SECRET)


def test_seed_refuses_non_user_application_data_before_mutation(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "invite-refusal.db")
    engine = create_db_engine(database_url)
    create_schema(engine)
    with Session(engine) as session:
        session.add(InviteCode(code="EXISTING-INVITE"))
        session.commit()

    with pytest.raises(E2ESeedError, match="already contains NoviScope data"):
        seed_workbench_e2e(database_url, PROVIDER_BASE_URL, PROVIDER_SECRET)

    with Session(engine) as session:
        assert [invite.code for invite in session.exec(select(InviteCode)).all()] == [
            "EXISTING-INVITE"
        ]
        assert list(session.exec(select(User)).all()) == []
        assert list(session.exec(select(ModelProvider)).all()) == []
        assert list(session.exec(select(Quest)).all()) == []


def test_seed_creates_exact_provider_and_quest_ownership(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "ownership.db")
    result = seed_workbench_e2e(database_url, PROVIDER_BASE_URL, PROVIDER_SECRET)

    with Session(create_db_engine(database_url)) as session:
        users = list(session.exec(select(User)).all())
        providers = list(session.exec(select(ModelProvider)).all())
        assignments = list(session.exec(select(AgentAssignment)).all())
        quests = list(session.exec(select(Quest)).all())
        stages = list(session.exec(select(StageCard)).all())

    admin = next(user for user in users if user.role == UserRole.ADMIN)
    member = next(user for user in users if user.role == UserRole.MEMBER)
    shared = next(provider for provider in providers if provider.scope == ProviderScope.SHARED)
    personal = next(
        provider for provider in providers if provider.scope == ProviderScope.PERSONAL
    )

    assert len(users) == 2
    assert admin.email == "admin.e2e@example.test"
    assert member.email == "member.e2e@example.test"
    assert verify_password("NoviScope-e2e-admin-2026", admin.password_hash)
    assert verify_password("NoviScope-e2e-member-2026", member.password_hash)
    assert len(providers) == 2
    assert shared.owner_user_id is None
    assert shared.created_by_user_id == admin.id
    assert personal.owner_user_id == member.id
    assert personal.created_by_user_id == member.id
    assert shared.is_active is True
    assert personal.is_active is True
    assert shared.default_model == "noviscope-e2e-model"
    assert personal.default_model == "noviscope-e2e-model"
    assert shared.base_url == PROVIDER_BASE_URL
    assert personal.base_url == PROVIDER_BASE_URL
    secret_box = SecretBox(PROVIDER_SECRET.get_secret_value())
    assert secret_box.decrypt(shared.api_key_ciphertext) == "local-e2e-key"
    assert secret_box.decrypt(personal.api_key_ciphertext) == "local-e2e-key"
    assert len(assignments) == 1
    assert assignments[0].agent_id == "demand_validator"
    assert assignments[0].provider_id == shared.id
    assert assignments[0].model_name == "noviscope-e2e-model"
    assert len(quests) == 1
    assert quests[0].owner_user_id == member.id
    assert "Badminton" in quests[0].title
    assert len(stages) == 5
    assert {stage.quest_id for stage in stages} == {quests[0].id}
    assert {stage.status for stage in stages} == {StageStatus.PENDING}
    assert result.quest_id == quests[0].id


def test_fake_provider_lists_only_the_e2e_model() -> None:
    with TestClient(fake_provider_app) as client:
        response = client.get("/v1/models")

    assert response.status_code == 200
    assert response.json() == {"data": [{"id": "noviscope-e2e-model"}]}


def test_fake_provider_returns_a_review_gated_demand_result() -> None:
    with TestClient(fake_provider_app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"content": "Validate badminton demand", "role": "user"}],
                "model": "noviscope-e2e-model",
                "temperature": 0.2,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body["choices"]) == 1
    output = DemandValidationOutput.model_validate_json(body["choices"][0]["message"]["content"])
    assert output.confidence == "medium"
    assert output.go_or_no_go_recommendation == "go_with_human_review"
    assert any("unverified" in item.lower() for item in output.risks)
    assert any("no experiment" in item.lower() for item in output.risks)
