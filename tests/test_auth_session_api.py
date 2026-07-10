from pathlib import Path

from fastapi.testclient import TestClient
from sqlmodel import Session

from noviscope.auth.passwords import hash_password
from noviscope.db.session import create_db_engine, create_schema
from noviscope.main import create_app
from noviscope.models.user import User


def test_optional_session_returns_null_without_a_cookie(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'optional-session.db'}"

    with TestClient(create_app(database_url=database_url)) as client:
        response = client.get("/auth/session")

    assert response.status_code == 200
    assert response.json() is None


def test_optional_session_returns_the_authenticated_user(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'authenticated-session.db'}"
    engine = create_db_engine(database_url)
    create_schema(engine)
    with Session(engine) as session:
        session.add(
            User(
                display_name="Session Member",
                email="session@example.test",
                password_hash=hash_password("session-password"),
            )
        )
        session.commit()

    with TestClient(create_app(database_url=database_url)) as client:
        login_response = client.post(
            "/auth/login",
            json={"email": "session@example.test", "password": "session-password"},
        )
        response = client.get("/auth/session")

    assert login_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["email"] == "session@example.test"
