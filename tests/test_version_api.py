from fastapi.testclient import TestClient
from sqlmodel import Session, select

from noviscope import versioning
from noviscope.db.session import create_db_engine
from noviscope.main import create_app
from noviscope.models.user import User, UserRole

DEV_ADMIN_TOKEN = "test-dev-admin-token-0123456789abcdef"
DEV_ADMIN_HEADERS = {"X-NoviScope-Dev-Admin": DEV_ADMIN_TOKEN}


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


def test_package_version_uses_source_version_when_distribution_metadata_is_missing(
    monkeypatch,
):
    def missing_distribution_metadata(_: str) -> str:
        raise versioning.PackageNotFoundError

    monkeypatch.setattr(versioning, "version", missing_distribution_metadata)

    assert versioning.package_version() == "0.1.0"


def test_public_version_endpoint_returns_only_version(monkeypatch):
    monkeypatch.setattr("noviscope.versioning.package_version", lambda: "9.9.9")

    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.get("/version")

        assert response.status_code == 200
        assert response.json() == {"app_version": "9.9.9"}


def test_admin_version_endpoint_reports_update_status(
    monkeypatch,
    tmp_path,
    dev_admin_header_enabled: None,
):
    monkeypatch.setattr("noviscope.versioning.local_commit", lambda settings: "abc1234local")
    monkeypatch.setattr("noviscope.versioning.local_branch", lambda: "main")
    monkeypatch.setattr("noviscope.versioning.local_dirty", lambda: False)
    monkeypatch.setattr(
        "noviscope.versioning.remote_version",
        lambda settings, local_sha: versioning.RemoteVersion(
            check_error=None,
            remote_commit="def5678remote",
            update_available=True,
        ),
    )

    database_url = f"sqlite:///{tmp_path / 'version-status.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        register_and_login(client, "VERSION-ADMIN", "version-admin@example.com")
        promote_user_to_admin(database_url, "version-admin@example.com")

        response = client.get("/admin/version")

        assert response.status_code == 200
        body = response.json()
        assert body["app_version"] == "0.1.0"
        assert body["local_commit"] == "abc1234local"
        assert body["local_commit_short"] == "abc1234"
        assert body["local_branch"] == "main"
        assert body["local_dirty"] is False
        assert body["remote_commit"] == "def5678remote"
        assert body["remote_commit_short"] == "def5678"
        assert body["github_repo"] == "kopang0730/NoviScope"
        assert body["github_branch"] == "main"
        assert body["update_available"] is True
        assert body["check_error"] is None
        assert body["checked_at"]


def test_admin_version_endpoint_requires_admin(tmp_path, dev_admin_header_enabled: None):
    database_url = f"sqlite:///{tmp_path / 'version-admin.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        unauthenticated_response = client.get("/admin/version")
        assert unauthenticated_response.status_code == 401

        register_and_login(client, "VERSION-MEMBER", "version-member@example.com")
        member_response = client.get("/admin/version")

        assert member_response.status_code == 403
        assert member_response.json()["detail"] == "Admin access required"
