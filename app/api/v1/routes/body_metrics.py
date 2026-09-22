from fastapi import APIRouter, Query, status

from app.api.v1.deps import CurrentUser, DbDep, PaginationDep
from app.schemas.common import PaginatedResponse
from app.schemas.metrics import BodyMetricCreate, BodyMetricRead, GraphPoint
from app.services import metrics_service

router = APIRouter(prefix="/body-metrics", tags=["body-metrics"])


@router.get("", response_model=PaginatedResponse[BodyMetricRead])
async def list_metrics(
    db: DbDep, user: CurrentUser, pagination: PaginationDep
):
    limit, offset = pagination
    items, total = await metrics_service.list_body_metrics(db, user, limit, offset)
    return PaginatedResponse[BodyMetricRead](items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=BodyMetricRead, status_code=status.HTTP_201_CREATED)
async def create_metric(
    payload: BodyMetricCreate, db: DbDep, user: CurrentUser
):
    return await metrics_service.create_body_metric(db, user, payload)


@router.get("/graph", response_model=list[GraphPoint])
async def graph(
    db: DbDep,
    user: CurrentUser,
    range: str = Query(default="30d", alias="range"),
) -> list[GraphPoint]:
    try:
        points = await metrics_service.body_metric_graph(db, user, range)
    except ValueError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [GraphPoint(**point) for point in points]
