from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlmodel import Session

from noviscope.api.dependencies import get_session
from noviscope.api.literature_paper_csv import (
    build_literature_paper_csv,
    literature_paper_csv_filename,
)
from noviscope.api.literature_paper_detail import (
    LiteraturePaperDetailResponse,
    LiteraturePaperNotFoundError,
    build_literature_paper_detail,
)
from noviscope.api.literature_paper_table import (
    LiteraturePaperReliabilityLevel,
    LiteraturePaperSort,
    LiteraturePaperTableFilters,
    LiteraturePaperTableOptions,
    LiteraturePaperTableResponse,
    build_literature_paper_table,
)
from noviscope.auth.dependencies import get_current_user
from noviscope.models.user import User
from noviscope.quests.service import QuestService

router = APIRouter()


@dataclass(frozen=True, slots=True)
class LiteraturePaperTableRouteContext:
    session: Session
    current_user: User


def get_literature_paper_table_route_context(
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiteraturePaperTableRouteContext:
    return LiteraturePaperTableRouteContext(current_user=current_user, session=session)


def get_literature_paper_table_options(
    reliability_level: Annotated[
        LiteraturePaperReliabilityLevel | None,
        Query(),
    ] = None,
    sort: LiteraturePaperSort = LiteraturePaperSort.RELEVANCE_DESC,
) -> LiteraturePaperTableOptions:
    filters = LiteraturePaperTableFilters(reliability_level=reliability_level)
    return LiteraturePaperTableOptions(filters=filters, sort_mode=sort)


def read_literature_paper_table(
    stage_id: str,
    context: LiteraturePaperTableRouteContext,
    options: LiteraturePaperTableOptions,
) -> LiteraturePaperTableResponse:
    service = QuestService(context.session)
    stage = service.get_stage_card_for_user(stage_id, context.current_user)
    return build_literature_paper_table(stage, options)


def read_literature_paper_detail(
    stage_id: str,
    context: LiteraturePaperTableRouteContext,
    paper_ref: str,
) -> LiteraturePaperDetailResponse:
    service = QuestService(context.session)
    stage = service.get_stage_card_for_user(stage_id, context.current_user)
    return build_literature_paper_detail(stage, paper_ref)


@router.get("/stages/{stage_id}/literature-papers", response_model=LiteraturePaperTableResponse)
def list_literature_papers(
    stage_id: str,
    context: Annotated[
        LiteraturePaperTableRouteContext,
        Depends(get_literature_paper_table_route_context),
    ],
    options: Annotated[
        LiteraturePaperTableOptions,
        Depends(get_literature_paper_table_options),
    ],
) -> LiteraturePaperTableResponse:
    try:
        return read_literature_paper_table(stage_id, context, options)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/stages/{stage_id}/literature-papers/download.csv")
def download_literature_papers_csv(
    stage_id: str,
    context: Annotated[
        LiteraturePaperTableRouteContext,
        Depends(get_literature_paper_table_route_context),
    ],
    options: Annotated[
        LiteraturePaperTableOptions,
        Depends(get_literature_paper_table_options),
    ],
) -> Response:
    try:
        table = read_literature_paper_table(stage_id, context, options)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return Response(
        content=build_literature_paper_csv(table),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{literature_paper_csv_filename(stage_id)}"'
            ),
        },
        media_type="text/csv; charset=utf-8",
    )


@router.get(
    "/stages/{stage_id}/literature-papers/detail",
    response_model=LiteraturePaperDetailResponse,
)
def get_literature_paper_detail(
    stage_id: str,
    context: Annotated[
        LiteraturePaperTableRouteContext,
        Depends(get_literature_paper_table_route_context),
    ],
    paper_ref: Annotated[str, Query(min_length=1)],
) -> LiteraturePaperDetailResponse:
    try:
        return read_literature_paper_detail(stage_id, context, paper_ref)
    except LiteraturePaperNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
