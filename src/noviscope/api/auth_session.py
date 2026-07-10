from typing import Annotated

from fastapi import APIRouter, Depends

from noviscope.api.routes import UserResponse, user_response
from noviscope.auth.dependencies import get_optional_current_user
from noviscope.models.user import User

router = APIRouter()


@router.get("/auth/session", response_model=UserResponse | None)
def get_optional_session(
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> UserResponse | None:
    if current_user is None:
        return None
    return user_response(current_user)
