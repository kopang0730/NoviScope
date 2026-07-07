from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.user import User, UserRole

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


def test_admin_cannot_assign_inactive_provider_to_agent(
    tmp_path,
    dev_admin_header_enabled: None,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'agent-assignment-inactive.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        register_and_login(client, "ASSIGNMENT-INACTIVE", "admin@example.com")
        promote_user_to_admin(database_url, "admin@example.com")
        shared_response = client.post(
            "/providers",
            json={
                "api_key": "shared-key",
                "base_url": "https://api.openai.com/v1",
                "default_model": "gpt-4.1",
                "kind": "openai_compatible",
                "name": "inactive-shared-openai",
                "scope": "shared",
            },
        )
        assert shared_response.status_code == 201
        shared = shared_response.json()
        deactivate_response = client.patch(
            f"/providers/{shared['id']}",
            json={"is_active": False},
        )
        assert deactivate_response.status_code == 200

        response = client.put(
            "/agent-assignments/demand_validator",
            json={"provider_id": shared["id"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Agent defaults must use an active provider."
