from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status
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


def _get_user_from_request(session: Session, request: Request) -> User | None:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.session_secret_key, algorithms=[SESSION_ALGORITHM])
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not isinstance(user_id, str):
        return None
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User:
    user = _get_user_from_request(session, request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return user


def get_optional_current_user(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    return _get_user_from_request(session, request)


def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_admin_or_dev_header(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
    value: Annotated[str | None, Header(alias="X-NoviScope-Dev-Admin")] = None,
) -> User | None:
    settings = get_settings()
    if current_user is not None:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return current_user
    if settings.dev_admin_header_enabled and value == "true":
        return None
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
