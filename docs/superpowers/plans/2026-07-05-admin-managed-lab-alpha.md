# Admin-Managed Lab Alpha Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first group-usable NoviScope release where an admin deploys the service, creates invite codes and shared model providers, and members log in to create and review their own research quests.

**Architecture:** Extend the existing FastAPI + SQLModel backend with user authentication, invitation-code registration, admin/member roles, quest ownership, and shared/personal provider visibility. Keep the Web MVP lightweight with React + Vite + Tailwind, backed by the same API, and postpone real worker execution, Redis, and GPU experiment automation.

**Tech Stack:** FastAPI, SQLModel, Pydantic, PostgreSQL for lab deployment, SQLite for tests/development, password hashing via Passlib/bcrypt, signed HTTP-only session cookies or JWT, React + TypeScript + Vite + Tailwind, pytest, ruff.

---

## Scope

This plan implements the Admin-managed Lab Alpha foundation. It does not implement literature retrieval, real agent execution, Redis queues, GPU experiment running, paper generation, or PPT generation.

The deliverable is a working authenticated Web/API shell:

```text
admin bootstrap
-> admin creates invite
-> user registers and logs in
-> admin creates shared provider
-> member can use shared provider or personal provider
-> member creates quest
-> member sees own quest and stages
-> admin sees all quests
-> stage can be manually updated/reviewed
```

## File Structure

Create:

```text
src/noviscope/auth/__init__.py
src/noviscope/auth/passwords.py
src/noviscope/auth/service.py
src/noviscope/auth/dependencies.py
src/noviscope/api/dependencies.py
src/noviscope/models/user.py
src/noviscope/web/__init__.py
tests/test_auth.py
tests/test_provider_scope.py
tests/test_quest_ownership.py
web/package.json
web/index.html
web/vite.config.ts
web/tsconfig.json
web/tailwind.config.js
web/postcss.config.js
web/src/main.tsx
web/src/app.tsx
web/src/api/client.ts
web/src/api/auth.ts
web/src/api/providers.ts
web/src/api/quests.ts
web/src/components/badge.tsx
web/src/components/button.tsx
web/src/components/card.tsx
web/src/components/input.tsx
web/src/components/json-view.tsx
web/src/components/table.tsx
web/src/pages/login.tsx
web/src/pages/register.tsx
web/src/pages/quest-list.tsx
web/src/pages/create-quest.tsx
web/src/pages/provider-settings.tsx
web/src/pages/stage-detail.tsx
web/src/styles/globals.css
.env.example
```

Modify:

```text
pyproject.toml
src/noviscope/api/routes.py
src/noviscope/core/config.py
src/noviscope/db/session.py
src/noviscope/main.py
src/noviscope/models/agent.py
src/noviscope/models/provider.py
src/noviscope/models/quest.py
src/noviscope/providers/service.py
src/noviscope/quests/service.py
tests/conftest.py
tests/test_api.py
tests/test_quests.py
README.md
README.zh-CN.md
```

Responsibilities:

- `models/user.py`: persisted `User`, `InviteCode`, `UserRole`, `InviteStatus`.
- `auth/passwords.py`: password hashing and verification.
- `auth/service.py`: registration, login validation, invite creation and invite consumption.
- `api/dependencies.py`: shared FastAPI dependencies, starting with the DB session dependency.
- `auth/dependencies.py`: current-user, optional-user, and admin/dev-bootstrap dependencies for FastAPI routes.
- `api/routes.py`: auth, invite, quest, provider, and stage HTTP endpoints.
- `providers/service.py`: shared/personal provider visibility and ownership rules.
- `quests/service.py`: quest ownership, list/detail, and owner/admin access rules.
- `web/`: thin Web MVP for auth, providers, quests, stages.

## Task 1: Add Auth Dependencies and User Models

**Files:**
- Modify: `pyproject.toml`
- Create: `src/noviscope/models/user.py`
- Modify: `src/noviscope/db/session.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Add database and password hashing dependencies**

Edit `pyproject.toml` dependencies to include:

```toml
  "passlib[bcrypt]>=1.7.4",
  "psycopg[binary]>=3.2.0",
  "python-jose[cryptography]>=3.3.0",
```

Keep existing dependencies unchanged.

- [ ] **Step 2: Create failing model tests**

Create `tests/test_auth.py`:

```python
from sqlmodel import Session, select

from noviscope.models.user import InviteCode, InviteStatus, User, UserRole


def test_user_and_invite_persist(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hashed-password",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(
        code="LAB-2026-0001",
        created_by_user_id=admin.id,
        max_uses=1,
    )
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    saved_user = db_session.exec(select(User)).one()
    saved_invite = db_session.exec(select(InviteCode)).one()

    assert saved_user.email == "admin@example.com"
    assert saved_user.role == UserRole.ADMIN
    assert saved_invite.status == InviteStatus.ACTIVE
    assert saved_invite.used_count == 0
```

- [ ] **Step 3: Run the failing model test**

Run:

```bash
pytest tests/test_auth.py::test_user_and_invite_persist -q
```

Expected: FAIL with an import error for `noviscope.models.user`.

- [ ] **Step 4: Implement user and invite models**

Create `src/noviscope/models/user.py`:

```python
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from noviscope.models.common import new_id, utc_now


class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"


class InviteStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    EXHAUSTED = "exhausted"


class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("user"), primary_key=True)
    email: str = Field(index=True, unique=True)
    display_name: str
    password_hash: str
    role: UserRole = Field(
        default=UserRole.MEMBER,
        sa_type=SAEnum(UserRole, values_callable=lambda enum: [item.value for item in enum]),
    )
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())


class InviteCode(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("invite"), primary_key=True)
    code: str = Field(index=True, unique=True)
    status: InviteStatus = Field(
        default=InviteStatus.ACTIVE,
        sa_type=SAEnum(InviteStatus, values_callable=lambda enum: [item.value for item in enum]),
    )
    created_by_user_id: str | None = Field(default=None, foreign_key="user.id")
    max_uses: int = 1
    used_count: int = 0
    expires_at: str | None = None
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())
    updated_at: str = Field(default_factory=lambda: utc_now().isoformat())
```

- [ ] **Step 5: Register models in schema imports**

Modify `src/noviscope/db/session.py` imports:

```python
from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401
from noviscope.models.user import InviteCode, User  # noqa: F401
```

Modify `tests/conftest.py` imports:

```python
from noviscope.models.agent import AgentAssignment  # noqa: F401
from noviscope.models.provider import ModelProvider  # noqa: F401
from noviscope.models.quest import Quest, StageCard  # noqa: F401
from noviscope.models.user import InviteCode, User  # noqa: F401
```

- [ ] **Step 6: Run model test**

Run:

```bash
pytest tests/test_auth.py::test_user_and_invite_persist -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml src/noviscope/models/user.py src/noviscope/db/session.py tests/conftest.py tests/test_auth.py
git commit -m "feat: add user and invite models"
```

## Task 2: Add Passwords and Auth Service

**Files:**
- Create: `src/noviscope/auth/__init__.py`
- Create: `src/noviscope/auth/passwords.py`
- Create: `src/noviscope/auth/service.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Add failing password and registration tests**

Append to `tests/test_auth.py`:

```python
import pytest

from noviscope.auth.passwords import hash_password, verify_password
from noviscope.auth.service import AuthService


def test_password_hash_verification():
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False


def test_register_member_consumes_invite(db_session: Session):
    admin = User(
        email="admin@example.com",
        display_name="Admin",
        password_hash="hash",
        role=UserRole.ADMIN,
    )
    invite = InviteCode(code="LAB-INVITE", created_by_user_id=admin.id)
    db_session.add(admin)
    db_session.add(invite)
    db_session.commit()

    service = AuthService(db_session)
    user = service.register_member(
        invite_code="LAB-INVITE",
        email="student@example.com",
        display_name="Student",
        password="student-password",
    )
    saved_invite = db_session.get(InviteCode, invite.id)

    assert user.email == "student@example.com"
    assert user.role == UserRole.MEMBER
    assert verify_password("student-password", user.password_hash) is True
    assert saved_invite is not None
    assert saved_invite.used_count == 1
    assert saved_invite.status == InviteStatus.EXHAUSTED


def test_register_member_rejects_invalid_invite(db_session: Session):
    service = AuthService(db_session)

    with pytest.raises(ValueError, match="Invalid invite code"):
        service.register_member(
            invite_code="MISSING",
            email="student@example.com",
            display_name="Student",
            password="student-password",
        )
```

- [ ] **Step 2: Run failing auth service tests**

Run:

```bash
pytest tests/test_auth.py::test_password_hash_verification tests/test_auth.py::test_register_member_consumes_invite tests/test_auth.py::test_register_member_rejects_invalid_invite -q
```

Expected: FAIL because `noviscope.auth` modules do not exist.

- [ ] **Step 3: Add auth package marker**

Create `src/noviscope/auth/__init__.py`:

```python
__all__ = []
```

- [ ] **Step 4: Implement password helpers**

Create `src/noviscope/auth/passwords.py`:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)
```

- [ ] **Step 5: Implement auth service**

Create `src/noviscope/auth/service.py`:

```python
from sqlmodel import Session, select

from noviscope.auth.passwords import hash_password, verify_password
from noviscope.models.common import utc_now
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_invite(
        self,
        *,
        code: str,
        created_by_user_id: str | None,
        max_uses: int = 1,
        expires_at: str | None = None,
    ) -> InviteCode:
        invite = InviteCode(
            code=code,
            created_by_user_id=created_by_user_id,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        self.session.add(invite)
        self.session.commit()
        self.session.refresh(invite)
        return invite

    def register_member(
        self,
        *,
        invite_code: str,
        email: str,
        display_name: str,
        password: str,
    ) -> User:
        invite = self._get_active_invite(invite_code)
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(password),
            role=UserRole.MEMBER,
        )
        invite.used_count += 1
        if invite.used_count >= invite.max_uses:
            invite.status = InviteStatus.EXHAUSTED
        invite.updated_at = utc_now().isoformat()
        self.session.add(user)
        self.session.add(invite)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.session.exec(select(User).where(User.email == email)).first()
        if user is None or not user.is_active:
            raise ValueError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        return user

    def _get_active_invite(self, code: str) -> InviteCode:
        invite = self.session.exec(select(InviteCode).where(InviteCode.code == code)).first()
        if invite is None or invite.status != InviteStatus.ACTIVE:
            raise ValueError("Invalid invite code")
        if invite.used_count >= invite.max_uses:
            raise ValueError("Invalid invite code")
        return invite
```

- [ ] **Step 6: Run auth service tests**

Run:

```bash
pytest tests/test_auth.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/noviscope/auth tests/test_auth.py
git commit -m "feat: add auth service"
```

## Task 3: Add Session Auth Dependencies and API Routes

**Files:**
- Modify: `src/noviscope/core/config.py`
- Create: `src/noviscope/api/dependencies.py`
- Create: `src/noviscope/auth/dependencies.py`
- Modify: `src/noviscope/api/routes.py`
- Modify: `src/noviscope/main.py`
- Test: `tests/test_api.py`
- Test: `tests/test_auth.py`

- [ ] **Step 1: Add failing API tests**

Append to `tests/test_api.py`:

```python
def test_invite_registration_login_and_me_flow():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        invite_response = client.post(
            "/admin/invites",
            json={"code": "LAB-INVITE", "max_uses": 1},
            headers={"X-NoviScope-Dev-Admin": "true"},
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


def test_protected_quest_create_requires_login():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        response = client.post(
            "/quests",
            json={"title": "Badminton", "initial_direction": "AI+体育"},
        )

        assert response.status_code == 401
```

- [ ] **Step 2: Run failing API auth tests**

Run:

```bash
pytest tests/test_api.py::test_invite_registration_login_and_me_flow tests/test_api.py::test_protected_quest_create_requires_login -q
```

Expected: FAIL because auth routes and route protection do not exist.

- [ ] **Step 3: Add session settings**

Modify `src/noviscope/core/config.py`:

```python
class Settings(BaseSettings):
    app_name: str = "NoviScope"
    database_url: str = Field(default="sqlite:///./noviscope.db")
    allow_external_private_uploads: bool = Field(default=False)
    provider_secret_key: str = Field(default="noviscope-dev-secret-key-change-me")
    session_secret_key: str = Field(default="noviscope-session-dev-secret-change-me")
    session_cookie_name: str = Field(default="noviscope_session")
    dev_admin_header_enabled: bool = Field(default=True)
    artifact_root: str = Field(default=".noviscope/artifacts")

    model_config = SettingsConfigDict(env_prefix="NOVISCOPE_", env_file=".env")
```

- [ ] **Step 4: Implement auth dependencies**

Create `src/noviscope/api/dependencies.py`:

```python
from sqlmodel import Session


def get_session() -> Session:
    raise RuntimeError("session dependency must be overridden by create_app")
```

Modify `src/noviscope/main.py` import:

```python
from noviscope.api.dependencies import get_session
from noviscope.api.routes import router
```

Remove `get_session` from the `from noviscope.api.routes import ...` import.

Create `src/noviscope/auth/dependencies.py`:

```python
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from jose import JWTError, jwt
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.core.config import get_settings
from noviscope.models.user import User, UserRole

SESSION_ALGORITHM = "HS256"
SESSION_TTL_HOURS = 24


def create_session_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(hours=SESSION_TTL_HOURS)
    payload = {"sub": user.id, "exp": expires_at}
    return jwt.encode(payload, settings.session_secret_key, algorithm=SESSION_ALGORITHM)


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        httponly=True,
        samesite="lax",
        secure=False,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(get_settings().session_cookie_name)


def get_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias="noviscope_session")] = None,
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(token, get_settings().session_secret_key, algorithms=[SESSION_ALGORITHM])
        user_id = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")
    return user


def get_optional_current_user(
    session: Annotated[Session, Depends(get_session)],
    token: Annotated[str | None, Cookie(alias="noviscope_session")] = None,
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(token, get_settings().session_secret_key, algorithms=[SESSION_ALGORITHM])
        user_id = payload.get("sub")
    except JWTError:
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_admin_or_dev_header(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    value: Annotated[str | None, Header(alias="X-NoviScope-Dev-Admin")] = None,
) -> User | None:
    settings = get_settings()
    if settings.dev_admin_header_enabled and value == "true":
        return None
    if current_user is None or current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
```

- [ ] **Step 5: Add auth schemas and routes**

Modify `src/noviscope/api/routes.py` imports:

```python
from fastapi import APIRouter, Depends, HTTPException, Response, status
```

Add imports:

```python
from noviscope.api.dependencies import get_session
from noviscope.auth.dependencies import (
    clear_session_cookie,
    create_session_token,
    get_admin_or_dev_header,
    get_current_user,
    set_session_cookie,
)
from noviscope.auth.service import AuthService
from noviscope.models.user import InviteCode, InviteStatus, User, UserRole
```

Add response/request models near existing models:

```python
class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: str
    updated_at: str


class RegisterRequest(BaseModel):
    invite_code: str
    email: str
    display_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class InviteCreateRequest(BaseModel):
    code: str
    max_uses: int = 1
    expires_at: str | None = None


class InviteResponse(BaseModel):
    id: str
    code: str
    status: InviteStatus
    max_uses: int
    used_count: int
    expires_at: str | None
    created_at: str
    updated_at: str


class InvitesResponse(BaseModel):
    invites: list[InviteResponse]
```

Add helper:

```python
def user_response(user: User) -> UserResponse:
    return UserResponse.model_validate(user, from_attributes=True)


def invite_response(invite: InviteCode) -> InviteResponse:
    return InviteResponse.model_validate(invite, from_attributes=True)
```

Add routes before provider routes:

```python
@router.post("/auth/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(
    request: RegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    service = AuthService(session)
    try:
        user = service.register_member(
            invite_code=request.invite_code,
            email=request.email,
            display_name=request.display_name,
            password=request.password,
        )
        return user_response(user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/auth/login", response_model=UserResponse)
def login_user(
    request: LoginRequest,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
) -> UserResponse:
    service = AuthService(session)
    try:
        user = service.authenticate(email=request.email, password=request.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    set_session_cookie(response, create_session_token(user))
    return user_response(user)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_user(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return user_response(current_user)


@router.post("/admin/invites", status_code=status.HTTP_201_CREATED, response_model=InviteResponse)
def create_invite(
    request: InviteCreateRequest,
    session: Annotated[Session, Depends(get_session)],
    current_admin: Annotated[User | None, Depends(get_admin_or_dev_header)],
) -> InviteResponse:
    admin_id = current_admin.id if current_admin is not None else None
    invite = AuthService(session).create_invite(
        code=request.code,
        created_by_user_id=admin_id,
        max_uses=request.max_uses,
        expires_at=request.expires_at,
    )
    return invite_response(invite)
```

In this task, keep the dev admin header path only for tests and bootstrap. Authenticated admins use the same endpoint without the dev header.

- [ ] **Step 6: Protect existing quest routes**

Modify `create_quest`, `list_quest_stages`, and `update_stage` signatures to depend on current user:

```python
current_user: Annotated[User, Depends(get_current_user)],
```

Do not use `current_user` for ownership yet; Task 4 adds that behavior.

Update existing quest API tests in `tests/test_api.py` to register and log in before calling protected quest and stage endpoints:

```python
def register_and_login(client: TestClient, invite_code: str, email: str):
    client.post(
        "/admin/invites",
        json={"code": invite_code, "max_uses": 1},
        headers={"X-NoviScope-Dev-Admin": "true"},
    )
    client.post(
        "/auth/register",
        json={
            "invite_code": invite_code,
            "email": email,
            "display_name": email.split("@")[0],
            "password": "password",
        },
    )
    response = client.post("/auth/login", json={"email": email, "password": "password"})
    assert response.status_code == 200
```

Call this helper at the start of:

- `test_create_quest_endpoint`
- `test_stage_flow_endpoints_record_review_payloads`
- `test_stage_endpoint_rejects_invalid_transition`

- [ ] **Step 7: Run API auth tests**

Run:

```bash
pytest tests/test_api.py::test_invite_registration_login_and_me_flow tests/test_api.py::test_protected_quest_create_requires_login -q
```

Expected: PASS.

- [ ] **Step 8: Run full backend tests**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add src/noviscope/core/config.py src/noviscope/api/dependencies.py src/noviscope/auth/dependencies.py src/noviscope/api/routes.py src/noviscope/main.py tests/test_api.py tests/test_auth.py
git commit -m "feat: add invitation auth api"
```

## Task 4: Add Quest Ownership and Quest List APIs

**Files:**
- Modify: `src/noviscope/models/quest.py`
- Modify: `src/noviscope/quests/service.py`
- Modify: `src/noviscope/api/routes.py`
- Test: `tests/test_quest_ownership.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Add failing quest ownership service tests**

Create `tests/test_quest_ownership.py`:

```python
from sqlmodel import Session

from noviscope.models.user import User, UserRole
from noviscope.quests.service import QuestService


def make_user(email: str, role: UserRole = UserRole.MEMBER) -> User:
    return User(
        email=email,
        display_name=email.split("@")[0],
        password_hash="hash",
        role=role,
    )


def test_member_lists_only_owned_quests(db_session: Session):
    member = make_user("member@example.com")
    other = make_user("other@example.com")
    db_session.add(member)
    db_session.add(other)
    db_session.commit()

    service = QuestService(db_session)
    owned = service.create_quest(
        title="Owned",
        initial_direction="AI+体育",
        owner_user_id=member.id,
    )
    service.create_quest(
        title="Other",
        initial_direction="手写文本擦除",
        owner_user_id=other.id,
    )

    quests = service.list_quests_for_user(member)

    assert [quest.id for quest in quests] == [owned.id]


def test_admin_lists_all_quests(db_session: Session):
    admin = make_user("admin@example.com", UserRole.ADMIN)
    member = make_user("member@example.com")
    db_session.add(admin)
    db_session.add(member)
    db_session.commit()

    service = QuestService(db_session)
    service.create_quest(title="One", initial_direction="AI+体育", owner_user_id=member.id)
    service.create_quest(title="Two", initial_direction="手写文本擦除", owner_user_id=member.id)

    assert len(service.list_quests_for_user(admin)) == 2
```

- [ ] **Step 2: Run failing quest ownership tests**

Run:

```bash
pytest tests/test_quest_ownership.py -q
```

Expected: FAIL because `Quest.owner_user_id` and service methods do not exist.

- [ ] **Step 3: Add owner field**

Modify `src/noviscope/models/quest.py` `Quest`:

```python
class Quest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: new_id("quest"), primary_key=True)
    owner_user_id: str | None = Field(default=None, foreign_key="user.id", index=True)
    title: str
    initial_direction: str
```

- [ ] **Step 4: Update QuestService**

Modify `src/noviscope/quests/service.py` imports:

```python
from noviscope.models.user import User, UserRole
```

Change `create_quest` signature and body:

```python
def create_quest(self, *, title: str, initial_direction: str, owner_user_id: str | None = None) -> Quest:
    quest = Quest(title=title, initial_direction=initial_direction, owner_user_id=owner_user_id)
```

Add methods:

```python
def list_quests_for_user(self, user: User) -> list[Quest]:
    statement = select(Quest)
    if user.role != UserRole.ADMIN:
        statement = statement.where(Quest.owner_user_id == user.id)
    statement = statement.order_by(Quest.updated_at)
    return list(self.session.exec(statement).all())


def get_quest_for_user(self, quest_id: str, user: User) -> Quest:
    quest = self.session.get(Quest, quest_id)
    if quest is None:
        raise LookupError(f"Quest {quest_id} not found")
    if user.role != UserRole.ADMIN and quest.owner_user_id != user.id:
        raise PermissionError(f"Quest {quest_id} is not accessible")
    return quest


def get_stage_card_for_user(self, stage_id: str, user: User) -> StageCard:
    stage = self.get_stage_card(stage_id)
    self.get_quest_for_user(stage.quest_id, user)
    return stage
```

- [ ] **Step 5: Run quest ownership service tests**

Run:

```bash
pytest tests/test_quest_ownership.py -q
```

Expected: PASS.

- [ ] **Step 6: Add quest list/detail API tests**

Reuse the `register_and_login` helper introduced in Task 3. Append to `tests/test_api.py`:

```python
def test_quest_list_returns_only_current_user_quests():
    with TestClient(create_app(database_url="sqlite:///:memory:")) as client:
        register_and_login(client, "INVITE-ONE", "one@example.com")
        first = client.post(
            "/quests",
            json={"title": "One", "initial_direction": "AI+体育"},
        ).json()
        client.post("/auth/logout")

        register_and_login(client, "INVITE-TWO", "two@example.com")
        client.post(
            "/quests",
            json={"title": "Two", "initial_direction": "手写文本擦除"},
        )

        response = client.get("/quests")

        assert response.status_code == 200
        quests = response.json()["quests"]
        assert [quest["title"] for quest in quests] == ["Two"]
        assert first["id"] not in [quest["id"] for quest in quests]
```

- [ ] **Step 7: Add quest response schemas and routes**

Modify `src/noviscope/api/routes.py`:

```python
class QuestResponse(BaseModel):
    id: str
    owner_user_id: str | None
    title: str
    initial_direction: str
    status: QuestStatus
    created_at: str
    updated_at: str


class QuestsResponse(BaseModel):
    quests: list[QuestResponse]
```

Add helper:

```python
def quest_response(quest: Quest) -> QuestResponse:
    return QuestResponse.model_validate(quest, from_attributes=True)
```

Update `QuestCreateResponse` to include `owner_user_id: str | None`.

Modify `create_quest` to pass `owner_user_id=current_user.id`.

Add routes:

```python
@router.get("/quests", response_model=QuestsResponse)
def list_quests(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestsResponse:
    service = QuestService(session)
    return QuestsResponse(quests=[quest_response(quest) for quest in service.list_quests_for_user(current_user)])


@router.get("/quests/{quest_id}", response_model=QuestResponse)
def get_quest(
    quest_id: str,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> QuestResponse:
    service = QuestService(session)
    try:
        return quest_response(service.get_quest_for_user(quest_id, current_user))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
```

Modify `list_quest_stages` to verify quest access before returning stages:

```python
try:
    service.get_quest_for_user(quest_id, current_user)
except LookupError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
except PermissionError as exc:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
```

Modify `update_stage` to verify the stage belongs to a quest the current user can access before calling `update_stage_card`:

```python
try:
    service.get_stage_card_for_user(stage_id, current_user)
    stage = service.update_stage_card(...)
except LookupError as exc:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
except PermissionError as exc:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
```

- [ ] **Step 8: Run quest API tests**

Run:

```bash
pytest tests/test_quest_ownership.py tests/test_api.py::test_quest_list_returns_only_current_user_quests -q
```

Expected: PASS.

- [ ] **Step 9: Run full backend tests**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/noviscope/models/quest.py src/noviscope/quests/service.py src/noviscope/api/routes.py tests/test_quest_ownership.py tests/test_api.py
git commit -m "feat: add quest ownership"
```

## Task 5: Add Provider Scope and Visibility

**Files:**
- Modify: `src/noviscope/models/provider.py`
- Modify: `src/noviscope/providers/service.py`
- Modify: `src/noviscope/api/routes.py`
- Test: `tests/test_provider_scope.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Add failing provider scope tests**

Create `tests/test_provider_scope.py`:

```python
from sqlmodel import Session

from noviscope.core.crypto import SecretBox
from noviscope.models.provider import ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole
from noviscope.providers.service import ProviderService


def make_user(email: str, role: UserRole = UserRole.MEMBER) -> User:
    return User(email=email, display_name=email.split("@")[0], password_hash="hash", role=role)


def test_member_sees_shared_and_own_personal_providers(db_session: Session):
    admin = make_user("admin@example.com", UserRole.ADMIN)
    member = make_user("member@example.com")
    other = make_user("other@example.com")
    db_session.add(admin)
    db_session.add(member)
    db_session.add(other)
    db_session.commit()

    service = ProviderService(db_session, SecretBox("test-secret"))
    shared = service.create_provider(
        name="shared-openai",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.openai.com/v1",
        default_model="gpt-4.1",
        api_key="shared-key",
        scope=ProviderScope.SHARED,
        owner_user_id=None,
    )
    own = service.create_provider(
        name="member-deepseek",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.deepseek.com",
        default_model="deepseek-chat",
        api_key="member-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=member.id,
    )
    service.create_provider(
        name="other-kimi",
        kind=ProviderKind.OPENAI_COMPATIBLE,
        base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2",
        api_key="other-key",
        scope=ProviderScope.PERSONAL,
        owner_user_id=other.id,
    )

    providers = service.list_providers_for_user(member)

    assert {provider.id for provider in providers} == {shared.id, own.id}
```

- [ ] **Step 2: Run failing provider scope tests**

Run:

```bash
pytest tests/test_provider_scope.py -q
```

Expected: FAIL because `ProviderScope` and service arguments do not exist.

- [ ] **Step 3: Add provider scope model fields**

Modify `src/noviscope/models/provider.py`:

```python
class ProviderScope(StrEnum):
    SHARED = "shared"
    PERSONAL = "personal"
```

Modify `ModelProvider`:

```python
name: str = Field(index=True)
scope: ProviderScope = Field(
    default=ProviderScope.PERSONAL,
    sa_type=SAEnum(ProviderScope, values_callable=lambda enum: [item.value for item in enum]),
)
owner_user_id: str | None = Field(default=None, foreign_key="user.id", index=True)
created_by_user_id: str | None = Field(default=None, foreign_key="user.id")
```

Remove the old `unique=True` constraint from `name`. In group usage, two members must be able to use the same provider display name in their personal scope. Database-level scoped uniqueness can be added later with migrations; do not keep a global unique name constraint.

- [ ] **Step 4: Update ProviderService**

Modify `src/noviscope/providers/service.py` imports:

```python
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
from noviscope.models.user import User, UserRole
```

Update `create_provider` signature and body:

```python
def create_provider(
    self,
    *,
    name: str,
    kind: ProviderKind,
    base_url: str,
    default_model: str,
    api_key: str,
    scope: ProviderScope = ProviderScope.PERSONAL,
    owner_user_id: str | None = None,
    created_by_user_id: str | None = None,
) -> ModelProvider:
    provider = ModelProvider(
        name=name,
        kind=kind,
        base_url=base_url,
        default_model=default_model,
        api_key_ciphertext=self.secret_box.encrypt(api_key),
        scope=scope,
        owner_user_id=owner_user_id,
        created_by_user_id=created_by_user_id,
    )
```

Add:

```python
def list_providers_for_user(self, user: User) -> list[ModelProvider]:
    statement = select(ModelProvider)
    if user.role != UserRole.ADMIN:
        statement = statement.where(
            (ModelProvider.scope == ProviderScope.SHARED)
            | (ModelProvider.owner_user_id == user.id)
        )
    return list(self.session.exec(statement).all())


def get_provider_for_user(self, provider_id: str, user: User) -> ModelProvider:
    provider = self.get_provider(provider_id)
    if user.role == UserRole.ADMIN:
        return provider
    if provider.scope == ProviderScope.SHARED or provider.owner_user_id == user.id:
        return provider
    raise PermissionError(f"Provider {provider_id} is not accessible")


def update_provider_for_user(
    self,
    provider_id: str,
    user: User,
    **updates: object,
) -> ModelProvider:
    provider = self.get_provider_for_user(provider_id, user)
    if provider.scope == ProviderScope.SHARED and user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required")
    return self.update_provider(provider_id, **updates)


def delete_provider_for_user(self, provider_id: str, user: User) -> None:
    provider = self.get_provider_for_user(provider_id, user)
    if provider.scope == ProviderScope.SHARED and user.role != UserRole.ADMIN:
        raise PermissionError("Admin access required")
    self.delete_provider(provider_id)
```

- [ ] **Step 5: Run provider service tests**

Run:

```bash
pytest tests/test_provider_scope.py -q
```

Expected: PASS.

- [ ] **Step 6: Update provider API schemas**

Modify `src/noviscope/api/routes.py` imports:

```python
from noviscope.models.provider import ModelProvider, ProviderKind, ProviderScope
```

Update `ProviderCreateRequest`:

```python
class ProviderCreateRequest(BaseModel):
    name: str
    kind: ProviderKind
    base_url: str
    default_model: str
    api_key: SecretStr = Field(repr=False)
    scope: ProviderScope = ProviderScope.PERSONAL
```

Update `ProviderResponse`:

```python
class ProviderResponse(BaseModel):
    id: str
    name: str
    kind: ProviderKind
    scope: ProviderScope
    owner_user_id: str | None
    base_url: str
    default_model: str
    is_active: bool
    created_at: str
    updated_at: str
```

Modify `create_provider`:

```python
scope = request.scope
if scope == ProviderScope.SHARED and current_user.role != UserRole.ADMIN:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
provider = service.create_provider(
    name=request.name,
    kind=request.kind,
    base_url=request.base_url,
    default_model=request.default_model,
    api_key=request.api_key.get_secret_value(),
    scope=scope,
    owner_user_id=None if scope == ProviderScope.SHARED else current_user.id,
    created_by_user_id=current_user.id,
)
```

Modify `list_providers` to use `service.list_providers_for_user(current_user)`.

Modify provider route signatures to depend on the current user:

```python
current_user: Annotated[User, Depends(get_current_user)],
```

Use `service.get_provider_for_user(provider_id, current_user)`, `service.update_provider_for_user(...)`, and `service.delete_provider_for_user(...)` in the get/update/delete provider routes. Convert `PermissionError` to `403` and `LookupError` to `404`.

- [ ] **Step 7: Add API visibility tests**

Update the existing `test_provider_crud_endpoints_do_not_return_api_key` to call `register_and_login(client, "INVITE-PROVIDER", "provider@example.com")` before provider CRUD requests.

Append to `tests/test_api.py`:

```python
def test_provider_visibility_shared_and_personal():
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
```

- [ ] **Step 8: Run provider API tests**

Run:

```bash
pytest tests/test_provider_scope.py tests/test_api.py::test_provider_visibility_shared_and_personal -q
```

Expected: PASS.

- [ ] **Step 9: Run full backend tests**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add src/noviscope/models/provider.py src/noviscope/providers/service.py src/noviscope/api/routes.py tests/test_provider_scope.py tests/test_api.py
git commit -m "feat: add provider visibility scopes"
```

## Task 6: Scaffold Web MVP

**Files:**
- Create all `web/` files listed in File Structure

- [ ] **Step 1: Create Vite package files**

Create `web/package.json`:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.1"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "typescript": "^5.7.2",
    "vite": "^6.0.0"
  }
}
```

Create `web/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>NoviScope</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
```

Create `web/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
```

Create `web/tailwind.config.js`:

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

Create `web/postcss.config.js`:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 2: Add minimal React app**

Create `web/src/main.tsx`, `web/src/app.tsx`, and `web/src/styles/globals.css` with a login/register/quest shell. Keep all API calls through `/api`.

`web/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./app";
import "./styles/globals.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

`web/src/app.tsx`:

```tsx
import { Link, Route, Routes } from "react-router-dom";
import { CreateQuestPage } from "./pages/create-quest";
import { LoginPage } from "./pages/login";
import { ProviderSettingsPage } from "./pages/provider-settings";
import { QuestListPage } from "./pages/quest-list";
import { RegisterPage } from "./pages/register";
import { StageDetailPage } from "./pages/stage-detail";

export function App() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/">NoviScope</Link>
        <nav>
          <Link to="/quests/new">New Quest</Link>
          <Link to="/providers">Providers</Link>
        </nav>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<QuestListPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/quests/new" element={<CreateQuestPage />} />
          <Route path="/providers" element={<ProviderSettingsPage />} />
          <Route path="/stages/:stageId" element={<StageDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

`web/src/styles/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f7f8fa;
  color: #172033;
}

.app-shell {
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
}

.topbar nav {
  display: flex;
  gap: 16px;
}

main {
  max-width: 1120px;
  margin: 0 auto;
  padding: 24px;
}
```

- [ ] **Step 3: Add API client and pages**

Create lightweight API functions and page components that call auth, provider, quest, and stage endpoints. Use simple forms and tables; do not add shadcn/ui.

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd web && npm install && npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web
git commit -m "feat: add web mvp shell"
```

## Task 7: Add Deployment Configuration and Docs

**Files:**
- Create: `.env.example`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Add environment example**

Create `.env.example`:

```env
NOVISCOPE_DATABASE_URL=postgresql+psycopg://noviscope:noviscope-password@127.0.0.1:5432/noviscope
NOVISCOPE_PROVIDER_SECRET_KEY=replace-with-a-long-random-secret
NOVISCOPE_SESSION_SECRET_KEY=replace-with-a-different-long-random-secret
NOVISCOPE_DEV_ADMIN_HEADER_ENABLED=false
NOVISCOPE_ARTIFACT_ROOT=.noviscope/artifacts
```

- [ ] **Step 2: Add deployment docs**

Update README files with:

````markdown
## Admin-Managed Lab Alpha

NoviScope is intended to be deployed once by a server administrator. Group members use the web app through the lab URL and register with invitation codes.

Development still supports SQLite:

```bash
NOVISCOPE_DATABASE_URL=sqlite:///./noviscope-dev.db uvicorn noviscope.main:app --reload
```

Lab deployment should use PostgreSQL:

```bash
cp .env.example .env
uvicorn noviscope.main:app --host 127.0.0.1 --port 8000
```

Build the web app and serve `web/dist` through Nginx/Caddy on the lab URL. Proxy `/api/` to the FastAPI backend:

```nginx
location /api/ {
  proxy_pass http://127.0.0.1:8000/;
}

location / {
  root /srv/noviscope/web/dist;
  try_files $uri /index.html;
}
```
````

- [ ] **Step 3: Run documentation sanity check**

Run:

```bash
rg -n "SSH tunnel MVP|SQLite.*group deployment|Database: SQLite|TODO|TBD" README.md README.zh-CN.md docs/superpowers/specs docs/superpowers/plans --glob '!2026-07-05-admin-managed-lab-alpha.md'
```

Expected: no matches for stale deployment claims. Mentions that SQLite is supported only for development/tests are acceptable and should not be removed.

- [ ] **Step 4: Commit**

```bash
git add .env.example README.md README.zh-CN.md
git commit -m "docs: add lab alpha deployment guide"
```

## Task 8: Final Verification

**Files:**
- No new files

- [ ] **Step 1: Run lint**

Run:

```bash
ruff check .
```

Expected: PASS.

- [ ] **Step 2: Run backend tests**

Run:

```bash
pytest -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd web && npm run build
```

Expected: PASS.

- [ ] **Step 4: Manual API smoke**

Run server:

```bash
uvicorn noviscope.main:app --host 127.0.0.1 --port 8000
```

In another shell, create an invite, register, login, create a quest, and list stages:

```bash
curl -s -X POST http://127.0.0.1:8000/admin/invites \
  -H "Content-Type: application/json" \
  -H "X-NoviScope-Dev-Admin: true" \
  -d '{"code":"SMOKE-INVITE","max_uses":1}'

curl -i -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"invite_code":"SMOKE-INVITE","email":"smoke@example.com","display_name":"Smoke","password":"password"}'

curl -i -c /tmp/noviscope-cookies.txt -s -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@example.com","password":"password"}'

curl -s -b /tmp/noviscope-cookies.txt -X POST http://127.0.0.1:8000/quests \
  -H "Content-Type: application/json" \
  -d '{"title":"Smoke Quest","initial_direction":"AI+体育"}'
```

Expected: login response sets `noviscope_session`; quest creation returns `201` and a `demand_validator` first stage.

- [ ] **Step 5: Commit final fixes if needed**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "fix: stabilize lab alpha shell"
```

If no fixes were needed, do not create an empty commit.
