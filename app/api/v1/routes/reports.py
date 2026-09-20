from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.api.v1.deps import CurrentUser, DbDep
from app.schemas.report import (
    AchievementRead,
    CalendarDay,
    DailyReport,
    MuscleShare,
    PersonalRecordRead,
    RangeReport,
    VolumePoint,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/daily", response_model=DailyReport)
async def daily(db: DbDep, user: CurrentUser, date_value: date = Query(alias="date")) -> DailyReport:
    return DailyReport(**await report_service.daily_report(db, user, date_value))


@router.get("/weekly", response_model=RangeReport)
async def weekly(db: DbDep, user: CurrentUser, week: str = Query(..., examples=["2026-W12"])) -> RangeReport:
    try:
        start, end = report_service.week_bounds(week)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="week must be YYYY-Www") from exc
    return RangeReport(**await report_service.range_report(db, user, start, end, f"weekly:{week}"))


@router.get("/monthly", response_model=RangeReport)
async def monthly(db: DbDep, user: CurrentUser, month: str = Query(..., examples=["2026-09"])) -> RangeReport:
    try:
        start, end = report_service.month_bounds(month)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM") from exc
    return RangeReport(**await report_service.range_report(db, user, start, end, f"monthly:{month}"))


@router.get("/calendar", response_model=list[CalendarDay])
async def calendar(db: DbDep, user: CurrentUser, month: str) -> list[CalendarDay]:
    try:
        rows = await report_service.calendar_report(db, user, month)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="month must be YYYY-MM") from exc
    return [CalendarDay(**row) for row in rows]


@router.get("/volume-graph", response_model=list[VolumePoint])
async def volume_graph(db: DbDep, user: CurrentUser, range: str = Query(default="30d")) -> list[VolumePoint]:
    try:
        rows = await report_service.volume_graph(db, user, range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [VolumePoint(**row) for row in rows]


@router.get("/muscle-distribution", response_model=list[MuscleShare])
async def muscle(db: DbDep, user: CurrentUser, range: str = Query(default="30d")) -> list[MuscleShare]:
    try:
        rows = await report_service.muscle_distribution(db, user, range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [MuscleShare(**row) for row in rows]


@router.get("/achievements", response_model=list[AchievementRead])
async def achievements(db: DbDep, user: CurrentUser) -> list[AchievementRead]:
    items = await report_service.list_achievements(db, user)
    return [
        AchievementRead(
            id=item.id,
            type=item.type,
            metadata=item.metadata_json,
            unlocked_at=item.unlocked_at,
        )
        for item in items
    ]


@router.get("/personal-records", response_model=list[PersonalRecordRead])
async def personal_records(db: DbDep, user: CurrentUser) -> list[PersonalRecordRead]:
    items = await report_service.list_personal_records(db, user)
    return [
        PersonalRecordRead(
            id=item.id,
            exercise_id=item.exercise_id,
            exercise_name=item.exercise.name if item.exercise else None,
            record_type=item.record_type,
            value=item.value,
            achieved_at=item.achieved_at,
        )
        for item in items
    ]
