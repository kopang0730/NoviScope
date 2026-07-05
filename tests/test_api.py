import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope.core.config import Settings
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.user import User, UserRole

DEV_ADMIN_TOKEN = "test-dev-admin-token-0123456789abcdef"
DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": DEV_ADMIN_TOKEN}
STRONG_PROVIDER_SECRET = "provider-secret-0123456789abcdef-strong"
STRONG_SESSION_SECRET = "session-secret-0123456789abcdef-strong"
STRONG_BOOTSTRAP_TOKEN = "bootstrap-token-0123456789abcdef-strong"


def register_and_login(client: TestClient, invite_code: str, email: str) -> None:
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

    login_response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert login_response.status_code == 200


def promote_user_to_admin(database_url: str, email: str) -> None:
    engine = create_db_engine(database_url)
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).one()
        user.role = UserRole.ADMIN
        session.add(user)
        session.commit()


def test_health_endpoint():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_agents_endpoint_lists_nine_agents():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/agents")

        assert response.status_code == 200
        body = response.json()
        assert len(body["agents"]) == 9
        assert body["agents"][0]["agent_id"] == "demand_validator"
        assert body["agents"][0]["tool_permissions"] == [
            "web_search",
            "read_pdf",
            "github_search",
            "write_files",
        ]


def test_deployment_safe_auth_defaults(monkeypatch):
    monkeypatch.delenv("NOVISCOPE_DEV_ADMIN_HEADER_ENABLED", raising=False)
    monkeypatch.delenv("NOVISCOPE_DEV_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("NOVISCOPE_SESSION_COOKIE_SECURE", raising=False)
    settings = Settings(_env_file=None)

    assert settings.dev_admin_header_enabled is False
    assert settings.dev_admin_token is None
    assert settings.session_cookie_secure is True


def test_sqlite_startup_allows_placeholder_secrets(monkeypatch):
    settings = Settings(_env_file=None)
    seen_database_urls: list[str] = []

    def fake_create_db_engine(database_url: str) -> object:
        seen_database_urls.append(database_url)
        return object()

    monkeypatch.setattr("noviscope.main.get_settings", lambda: settings)
    monkeypatch.setattr("noviscope.main.create_db_engine", fake_create_db_engine)

    create_app(database_url="sqlite:///:memory:")

    assert seen_database_urls == ["sqlite:///:memory:"]


@pytest.mark.parametrize(
    ("settings_kwargs", "expected_env_var"),
    [
        (
            {"session_secret_key": STRONG_SESSION_SECRET},
            "NOVISCOPE_PROVIDER_SECRET_KEY",
        ),
        (
            {"provider_secret_key": STRONG_PROVIDER_SECRET},
            "NOVISCOPE_SESSION_SECRET_KEY",
        ),
        (
            {
                "provider_secret_key": "replace-with-a-long-random-secret",
                "session_secret_key": STRONG_SESSION_SECRET,
            },
            "NOVISCOPE_PROVIDER_SECRET_KEY",
        ),
        (
            {
                "provider_secret_key": STRONG_PROVIDER_SECRET,
                "session_secret_key": "replace-with-a-different-long-random-secret",
            },
            "NOVISCOPE_SESSION_SECRET_KEY",
        ),
        (
            {
                "provider_secret_key": "short",
                "session_secret_key": STRONG_SESSION_SECRET,
            },
            "NOVISCOPE_PROVIDER_SECRET_KEY",
        ),
        (
            {
                "provider_secret_key": STRONG_PROVIDER_SECRET,
                "session_secret_key": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            },
            "NOVISCOPE_SESSION_SECRET_KEY",
        ),
        (
            {
                "provider_secret_key": STRONG_PROVIDER_SECRET,
                "session_secret_key": STRONG_SESSION_SECRET,
                "dev_admin_header_enabled": True,
            },
            "NOVISCOPE_DEV_ADMIN_TOKEN",
        ),
        (
            {
                "provider_secret_key": STRONG_PROVIDER_SECRET,
                "session_secret_key": STRONG_SESSION_SECRET,
                "dev_admin_header_enabled": True,
                "dev_admin_token": "short",
            },
            "NOVISCOPE_DEV_ADMIN_TOKEN",
        ),
    ],
)
def test_shared_deployment_rejects_weak_secrets_before_engine_creation(
    monkeypatch,
    settings_kwargs: dict[str, object],
    expected_env_var: str,
):
    settings = Settings(_env_file=None, **settings_kwargs)
    engine_calls: list[str] = []

    def fake_create_db_engine(database_url: str) -> object:
        engine_calls.append(database_url)
        return object()

    monkeypatch.setattr("noviscope.main.get_settings", lambda: settings)
    monkeypatch.setattr("noviscope.main.create_db_engine", fake_create_db_engine)

    with pytest.raises(ValueError, match=expected_env_var):
        create_app(database_url="postgresql://user:pass@localhost:5432/noviscope")

    assert engine_calls == []


def test_shared_deployment_accepts_non_placeholder_secrets(monkeypatch):
    settings = Settings(
        _env_file=None,
        provider_secret_key=STRONG_PROVIDER_SECRET,
        session_secret_key=STRONG_SESSION_SECRET,
    )
    seen_database_urls: list[str] = []

    def fake_create_db_engine(database_url: str) -> object:
        seen_database_urls.append(database_url)
        return object()

    monkeypatch.setattr("noviscope.main.get_settings", lambda: settings)
    monkeypatch.setattr("noviscope.main.create_db_engine", fake_create_db_engine)

    create_app(database_url="postgresql://user:pass@localhost:5432/noviscope")

    assert seen_database_urls == ["postgresql://user:pass@localhost:5432/noviscope"]


def test_shared_deployment_accepts_strong_bootstrap_token(monkeypatch):
    settings = Settings(
        _env_file=None,
        provider_secret_key=STRONG_PROVIDER_SECRET,
        session_secret_key=STRONG_SESSION_SECRET,
        dev_admin_header_enabled=True,
        dev_admin_token=STRONG_BOOTSTRAP_TOKEN,
    )
    seen_database_urls: list[str] = []

    def fake_create_db_engine(database_url: str) -> object:
        seen_database_urls.append(database_url)
        return object()

    monkeypatch.setattr("noviscope.main.get_settings", lambda: settings)
    monkeypatch.setattr("noviscope.main.create_db_engine", fake_create_db_engine)

    create_app(database_url="postgresql://user:pass@localhost:5432/noviscope")

    assert seen_database_urls == ["postgresql://user:pass@localhost:5432/noviscope"]


def test_provider_crud_endpoints_do_not_return_api_key(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INVITE-PROVIDER", "provider@example.com")
        create_response = client.post(
            "/providers",
            json={
                "name": "primary-openai",
                "kind": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "sk-realistic-test-key",
            },
        )

        assert create_response.status_code == 201
        provider = create_response.json()
        assert provider["name"] == "primary-openai"
        assert "api_key" not in provider
        assert "api_key_ciphertext" not in provider

        provider_id = provider["id"]
        list_response = client.get("/providers")
        assert list_response.status_code == 200
        assert list_response.json()["providers"][0]["id"] == provider_id

        get_response = client.get(f"/providers/{provider_id}")
        assert get_response.status_code == 200
        assert get_response.json()["default_model"] == "gpt-4.1"

        update_response = client.patch(
            f"/providers/{provider_id}",
            json={"default_model": "gpt-4.1-mini", "is_active": False},
        )
        assert update_response.status_code == 200
        assert update_response.json()["default_model"] == "gpt-4.1-mini"
        assert update_response.json()["is_active"] is False

        delete_response = client.delete(f"/providers/{provider_id}")
        assert delete_response.status_code == 204

        missing_response = client.get(f"/providers/{provider_id}")
        assert missing_response.status_code == 404


def test_provider_routes_require_authentication(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "AUTH-PROVIDER", "provider@example.com")
        provider = client.post(
            "/providers",
            json={
                "name": "auth-openai",
                "kind": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "auth-key",
            },
        ).json()
        client.post("/auth/logout")

        create_response = client.post(
            "/providers",
            json={
                "name": "missing-auth",
                "kind": "openai_compatible",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "missing-auth-key",
            },
        )
        list_response = client.get("/providers")
        get_response = client.get(f"/providers/{provider['id']}")
        update_response = client.patch(
            f"/providers/{provider['id']}",
            json={"default_model": "gpt-4.1-mini"},
        )
        delete_response = client.delete(f"/providers/{provider['id']}")

        assert create_response.status_code == 401
        assert list_response.status_code == 401
        assert get_response.status_code == 401
        assert update_response.status_code == 401
        assert delete_response.status_code == 401


def test_provider_visibility_shared_and_personal(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INVITE-ONE", "one@example.com")
        personal = client.post(
            "/providers",
            json={
                "name": "one-personal",
                "kind": "openai_compatible",
                "scope": "personal",
                "base_url": "https://api.deepseek.com",
                "default_model": "deepseek-chat",
                "api_key": "one-key",
            },
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "INVITE-TWO", "two@example.com")
        response = client.get("/providers")

        assert response.status_code == 200
        provider_ids = [provider["id"] for provider in response.json()["providers"]]
        assert personal["id"] not in provider_ids


def test_provider_detail_update_and_delete_reject_other_users_personal_provider(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "PROVIDER-ONE", "one@example.com")
        personal = client.post(
            "/providers",
            json={
                "name": "one-personal",
                "kind": "openai_compatible",
                "scope": "personal",
                "base_url": "https://api.deepseek.com",
                "default_model": "deepseek-chat",
                "api_key": "one-key",
            },
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "PROVIDER-TWO", "two@example.com")
        get_response = client.get(f"/providers/{personal['id']}")
        update_response = client.patch(
            f"/providers/{personal['id']}",
            json={"default_model": "deepseek-reasoner"},
        )
        delete_response = client.delete(f"/providers/{personal['id']}")

        assert get_response.status_code == 403
        assert update_response.status_code == 403
        assert delete_response.status_code == 403


def test_member_cannot_create_shared_provider(tmp_path, dev_admin_header_enabled: None):
    database_url = f"sqlite:///{tmp_path / 'providers-access.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        register_and_login(client, "PROVIDER-MEMBER", "member@example.com")
        response = client.post(
            "/providers",
            json={
                "name": "shared-openai",
                "kind": "openai_compatible",
                "scope": "shared",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "shared-key",
            },
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Admin access required"


def test_member_cannot_update_or_delete_shared_provider(
    tmp_path,
    dev_admin_header_enabled: None,
):
    database_url = f"sqlite:///{tmp_path / 'shared-provider.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        register_and_login(client, "PROVIDER-ADMIN", "admin@example.com")
        promote_user_to_admin(database_url, "admin@example.com")
        shared = client.post(
            "/providers",
            json={
                "name": "shared-openai",
                "kind": "openai_compatible",
                "scope": "shared",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "api_key": "shared-key",
            },
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "PROVIDER-MEMBER", "member@example.com")
        get_response = client.get(f"/providers/{shared['id']}")
        update_response = client.patch(
            f"/providers/{shared['id']}",
            json={"default_model": "gpt-4.1-mini"},
        )
        delete_response = client.delete(f"/providers/{shared['id']}")

        assert get_response.status_code == 200
        assert update_response.status_code == 403
        assert delete_response.status_code == 403


def test_create_quest_endpoint(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "QUEST-INVITE", "quest@example.com")
        response = client.post(
            "/quests",
            json={"title": "AI+Sports Badminton", "initial_direction": "AI+体育，羽毛球"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["owner_user_id"]
        assert body["title"] == "AI+Sports Badminton"
        assert body["status"] == "draft"
        assert body["first_stage"]["agent_id"] == "demand_validator"
        assert body["first_stage"]["status"] == "pending"


def test_quest_list_returns_only_current_user_quests(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INVITE-ONE", "one@example.com")
        first = client.post(
            "/quests",
            json={"title": "One", "initial_direction": "AI+体育"},
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "INVITE-TWO", "two@example.com")
        second = client.post(
            "/quests",
            json={"title": "Two", "initial_direction": "手写文本擦除"},
        ).json()

        response = client.get("/quests")

        assert response.status_code == 200
        quests = response.json()["quests"]
        assert [quest["title"] for quest in quests] == ["Two"]
        assert [quest["id"] for quest in quests] == [second["id"]]
        assert first["id"] not in [quest["id"] for quest in quests]


def test_quest_detail_rejects_other_users(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "DETAIL-ONE", "owner@example.com")
        quest = client.post(
            "/quests",
            json={"title": "Owner Quest", "initial_direction": "AI+体育"},
        ).json()
        owner_response = client.get(f"/quests/{quest['id']}")
        assert owner_response.status_code == 200
        assert owner_response.json()["id"] == quest["id"]
        assert owner_response.json()["owner_user_id"] == quest["owner_user_id"]

        client.post("/auth/logout")

        register_and_login(client, "DETAIL-TWO", "other@example.com")
        response = client.get(f"/quests/{quest['id']}")

        assert response.status_code == 403
        assert "not accessible" in response.json()["detail"]


def test_stage_routes_reject_cross_user_access(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "OWNER-INVITE", "owner@example.com")
        quest = client.post(
            "/quests",
            json={"title": "Owner Quest", "initial_direction": "AI+体育"},
        ).json()
        stage_id = quest["first_stage"]["id"]
        client.post("/auth/logout")

        register_and_login(client, "OTHER-INVITE", "other@example.com")

        list_response = client.get(f"/quests/{quest['id']}/stages")
        update_response = client.patch(
            f"/stages/{stage_id}",
            json={"status": "running"},
        )

        assert list_response.status_code == 403
        assert "not accessible" in list_response.json()["detail"]
        assert update_response.status_code == 403
        assert "not accessible" in update_response.json()["detail"]


def test_stage_flow_endpoints_record_review_payloads(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "STAGE-INVITE", "stage@example.com")
        quest_response = client.post(
            "/quests",
            json={"title": "Handwritten Text Erasure", "initial_direction": "手写文本擦除"},
        )
        quest = quest_response.json()
        stage_id = quest["first_stage"]["id"]

        stages_response = client.get(f"/quests/{quest['id']}/stages")
        assert stages_response.status_code == 200
        assert stages_response.json()["stages"][0]["id"] == stage_id

        running_response = client.patch(
            f"/stages/{stage_id}",
            json={
                "status": "running",
                "input_payload": {"direction": "手写文本擦除"},
            },
        )
        assert running_response.status_code == 200
        assert running_response.json()["status"] == "running"

        complete_response = client.patch(
            f"/stages/{stage_id}",
            json={
                "status": "complete",
                "summary": "Demand has concrete education scenario evidence.",
                "output_payload": {"confidence": 0.82},
                "evidence_payload": {"sources": ["enterprise-demand-note"]},
                "human_approved": True,
                "review_notes": "Proceed to idea generation.",
            },
        )
        body = complete_response.json()
        assert complete_response.status_code == 200
        assert body["status"] == "complete"
        assert body["output_payload"] == {"confidence": 0.82}
        assert body["evidence_payload"] == {"sources": ["enterprise-demand-note"]}
        assert body["human_approved"] is True


def test_stage_endpoint_rejects_invalid_transition(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "TRANSITION-INVITE", "transition@example.com")
        quest_response = client.post(
            "/quests",
            json={"title": "Badminton", "initial_direction": "AI+体育"},
        )
        stage_id = quest_response.json()["first_stage"]["id"]

        response = client.patch(f"/stages/{stage_id}", json={"status": "complete"})

        assert response.status_code == 400
        assert "pending to complete" in response.json()["detail"]


def test_create_quest_endpoint_rejects_missing_direction(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "MISSING-DIRECTION-INVITE", "missing-direction@example.com")
        response = client.post("/quests", json={"title": "AI+Sports Badminton"})

        assert response.status_code == 422


def test_dev_admin_header_rejected_by_default():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/admin/invites",
            json={"code": "DEFAULT-DISABLED", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )

        assert response.status_code == 403


def test_dev_admin_header_explicit_opt_in_permits_bootstrap(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/admin/invites",
            json={"code": "OPT-IN-BOOTSTRAP", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )

        assert response.status_code == 201
        assert response.json()["code"] == "OPT-IN-BOOTSTRAP"


def test_dev_admin_header_rejects_literal_true_when_token_is_configured(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/admin/invites",
            json={"code": "LITERAL-TRUE-BOOTSTRAP", "max_uses": 1},
            headers={"X-NoviScope-Dev-Admin": "true"},
        )

        assert response.status_code == 403


def test_register_rejects_weak_password(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        invite_response = client.post(
            "/admin/invites",
            json={"code": "WEAK-PASSWORD", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        assert invite_response.status_code == 201

        response = client.post(
            "/auth/register",
            json={
                "invite_code": "WEAK-PASSWORD",
                "email": "student@example.com",
                "display_name": "Student",
                "password": "short",
            },
        )

        assert response.status_code == 422


def test_register_rejects_whitespace_only_password(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        invite_response = client.post(
            "/admin/invites",
            json={"code": "WHITESPACE-PASSWORD", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        assert invite_response.status_code == 201

        response = client.post(
            "/auth/register",
            json={
                "invite_code": "WHITESPACE-PASSWORD",
                "email": "student@example.com",
                "display_name": "Student",
                "password": "        ",
            },
        )

        assert response.status_code == 422


def test_login_preserves_intentional_password_whitespace(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        invite_response = client.post(
            "/admin/invites",
            json={"code": "SPACED-PASSWORD", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        assert invite_response.status_code == 201

        register_response = client.post(
            "/auth/register",
            json={
                "invite_code": "SPACED-PASSWORD",
                "email": "student@example.com",
                "display_name": "Student",
                "password": " student-password ",
            },
        )
        assert register_response.status_code == 201

        stripped_login_response = client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": "student-password"},
        )
        assert stripped_login_response.status_code == 401

        exact_login_response = client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": " student-password "},
        )
        assert exact_login_response.status_code == 200


def test_create_invite_rejects_invalid_max_uses(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/admin/invites",
            json={"code": "BAD-MAX-USES", "max_uses": 0},
            headers=DEV_ADMIN_HEADERS,
        )

        assert response.status_code == 422


def test_create_invite_rejects_duplicate_code_with_conflict(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        first_response = client.post(
            "/admin/invites",
            json={"code": "DUPLICATE-INVITE", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        second_response = client.post(
            "/admin/invites",
            json={"code": "DUPLICATE-INVITE", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        recovery_response = client.post(
            "/admin/invites",
            json={"code": "DUPLICATE-INVITE-RECOVERY", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )

        assert first_response.status_code == 201
        assert second_response.status_code == 409
        assert second_response.json()["detail"] == "Invite code already exists"
        assert recovery_response.status_code == 201


def test_register_rejects_duplicate_email_with_conflict_and_rolls_back_invite(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        first_invite_response = client.post(
            "/admin/invites",
            json={"code": "DUPLICATE-EMAIL-ONE", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        second_invite_response = client.post(
            "/admin/invites",
            json={"code": "DUPLICATE-EMAIL-TWO", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        assert first_invite_response.status_code == 201
        assert second_invite_response.status_code == 201

        first_register_response = client.post(
            "/auth/register",
            json={
                "invite_code": "DUPLICATE-EMAIL-ONE",
                "email": "student@example.com",
                "display_name": "Student",
                "password": "student-password",
            },
        )
        duplicate_register_response = client.post(
            "/auth/register",
            json={
                "invite_code": "DUPLICATE-EMAIL-TWO",
                "email": "student@example.com",
                "display_name": "Student Again",
                "password": "student-password",
            },
        )
        rollback_register_response = client.post(
            "/auth/register",
            json={
                "invite_code": "DUPLICATE-EMAIL-TWO",
                "email": "other@example.com",
                "display_name": "Other",
                "password": "student-password",
            },
        )

        assert first_register_response.status_code == 201
        assert duplicate_register_response.status_code == 409
        assert duplicate_register_response.json()["detail"] == "Email is already registered"
        assert rollback_register_response.status_code == 201


def test_invite_registration_login_and_me_flow(dev_admin_header_enabled: None):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        invite_response = client.post(
            "/admin/invites",
            json={"code": "LAB-INVITE", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )
        assert invite_response.status_code == 201

        register_response = client.post(
            "/auth/register",
            json={
                "invite_code": "LAB-INVITE",
                "email": "student@example.com",
                "display_name": "Student",
                "password": "student-password",
            },
        )
        assert register_response.status_code == 201
        assert register_response.json()["email"] == "student@example.com"
        assert "password_hash" not in register_response.json()

        login_response = client.post(
            "/auth/login",
            json={"email": "student@example.com", "password": "student-password"},
        )
        assert login_response.status_code == 200
        assert login_response.cookies.get("noviscope_session")

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == "student@example.com"

        logout_response = client.post("/auth/logout")
        assert logout_response.status_code == 204
        assert client.get("/auth/me").status_code == 401


def test_logged_in_member_cannot_use_dev_admin_header_for_invites(
    dev_admin_header_enabled: None,
):
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "MEMBER-INVITE", "member@example.com")

        response = client.post(
            "/admin/invites",
            json={"code": "SECOND-INVITE", "max_uses": 1},
            headers=DEV_ADMIN_HEADERS,
        )

        assert response.status_code == 403


def test_protected_quest_create_requires_login():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/quests",
            json={"title": "Badminton", "initial_direction": "AI+体育"},
        )

        assert response.status_code == 401


def test_openapi_has_quest_response_schema():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/openapi.json")

        quest_schema = response.json()["paths"]["/quests"]["post"]["responses"]["201"]
        assert quest_schema["content"]["application/json"]["schema"]["$ref"].endswith(
            "QuestCreateResponse"
        )
