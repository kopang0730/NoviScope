from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from noviscope.auth.dependencies import get_current_admin
from noviscope.core.config import get_settings
from noviscope.models.user import User
from noviscope.versioning import VersionStatus, deployed_version, version_status

router = APIRouter()


class PublicVersionResponse(BaseModel):
    app_version: str


@router.get("/version", response_model=PublicVersionResponse)
def get_version() -> PublicVersionResponse:
    return PublicVersionResponse(app_version=deployed_version(get_settings()))


@router.get("/admin/version", response_model=VersionStatus)
def get_admin_version(
    _: Annotated[User, Depends(get_current_admin)],
) -> VersionStatus:
    return version_status(get_settings())
