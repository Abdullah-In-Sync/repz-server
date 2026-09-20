from calendar import monthrange
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import json_cache_get, json_cache_set
from app.models.achievement import Achievement
from app.models.exercise import Exercise
from app.models.metrics import DailyStat
from app.models.user import User
from app.models.workout import PersonalRecord, WorkoutSession, WorkoutSet
from app.utils.training import parse_range, set_volume

CACHE_TTL = 300


def _cache_key(user_id: str, name: str, extra: str) -> str:
    return f"reports:{user_id}:{name}:{extra}"


async def _daily_rows(db: AsyncSession, user_id: str, start: date, end: date) -> list[DailyStat]:
    result = await db.execute(
        select(DailyStat)
        .where(DailyStat.user_id == user_id, DailyStat.date >= start, DailyStat.date <= end)
        .order_by(DailyStat.date.asc())
    )
    return list(result.scalars().all())


def _sum_report(start: date, end: date, rows: list[DailyStat]) -> dict:
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "total_volume": sum(r.total_volume for r in rows),
        "total_sets": sum(r.total_sets for r in rows),
        "duration_seconds": sum(r.duration_seconds for r in rows),
        "calories_est": sum(r.calories_est for r in rows),
        "workout_days": sum(1 for r in rows if r.total_sets > 0),
        "daily": [
            {
                "date": r.date.isoformat(),
                "total_volume": r.total_volume,
                "total_sets": r.total_sets,
                "duration_seconds": r.duration_seconds,
                "calories_est": r.calories_est,
            }
            for r in rows
        ],
    }


async def daily_report(db: AsyncSession, user: User, day: date) -> dict:
    key = _cache_key(user.id, "daily", day.isoformat())
    cached = await json_cache_get(key)
    if cached:
        return cached
    rows = await _daily_rows(db, user.id, day, day)
    workouts = int(
        (
            await db.execute(
                select(func.count())
                .select_from(WorkoutSession)
                .where(WorkoutSession.user_id == user.id, func.date(WorkoutSession.started_at) == day)
            )
        ).scalar_one()
    )
    if rows:
        payload = {
            "date": day.isoformat(),
            "total_volume": rows[0].total_volume,
            "total_sets": rows[0].total_sets,
            "duration_seconds": rows[0].duration_seconds,
            "calories_est": rows[0].calories_est,
            "workout_count": workouts,
        }
    else:
        payload = {
            "date": day.isoformat(),
            "total_volume": 0,
            "total_sets": 0,
            "duration_seconds": 0,
            "calories_est": 0,
            "workout_count": workouts,
        }
    await json_cache_set(key, payload, CACHE_TTL)
    return payload


async def range_report(db: AsyncSession, user: User, start: date, end: date, name: str) -> dict:
    key = _cache_key(user.id, name, f"{start}:{end}")
    cached = await json_cache_get(key)
    if cached:
        return cached
    rows = await _daily_rows(db, user.id, start, end)
    payload = _sum_report(start, end, rows)
    await json_cache_set(key, payload, CACHE_TTL)
    return payload


def week_bounds(week: str) -> tuple[date, date]:
    year_s, week_s = week.split("-W")
    start = date.fromisocalendar(int(year_s), int(week_s), 1)
    return start, start + timedelta(days=6)


def month_bounds(month: str) -> tuple[date, date]:
    year_s, month_s = month.split("-")
    year, month_i = int(year_s), int(month_s)
    start = date(year, month_i, 1)
    end = date(year, month_i, monthrange(year, month_i)[1])
    return start, end


async def calendar_report(db: AsyncSession, user: User, month: str) -> list[dict]:
    start, end = month_bounds(month)
    rows = {r.date: r for r in await _daily_rows(db, user.id, start, end)}
    days = []
    cursor = start
    while cursor <= end:
        stat = rows.get(cursor)
        days.append(
            {
                "date": cursor.isoformat(),
                "has_workout": bool(stat and stat.total_sets > 0),
                "total_volume": stat.total_volume if stat else 0,
            }
        )
        cursor += timedelta(days=1)
    return days


async def volume_graph(db: AsyncSession, user: User, range_value: str) -> list[dict]:
    days = parse_range(range_value)
    end = date.today()
    start = end - timedelta(days=days - 1)
    rows = await _daily_rows(db, user.id, start, end)
    by_day = {r.date: r.total_volume for r in rows}
    cursor = start
    points = []
    while cursor <= end:
        points.append({"date": cursor.isoformat(), "volume": by_day.get(cursor, 0)})
        cursor += timedelta(days=1)
    return points


async def muscle_distribution(db: AsyncSession, user: User, range_value: str) -> list[dict]:
    days = parse_range(range_value)
    start_dt = datetime.combine(date.today() - timedelta(days=days - 1), datetime.min.time())
    result = await db.execute(
        select(WorkoutSet, Exercise)
        .join(Exercise, WorkoutSet.exercise_id == Exercise.id)
        .join(WorkoutSession, WorkoutSet.workout_session_id == WorkoutSession.id)
        .where(
            WorkoutSession.user_id == user.id,
            WorkoutSession.started_at >= start_dt,
            WorkoutSet.is_completed.is_(True),
        )
    )
    volumes: dict[str, float] = {}
    for workout_set, exercise in result.all():
        part = exercise.body_part or "unknown"
        volumes[part] = volumes.get(part, 0) + set_volume(
            workout_set.weight_kg, workout_set.reps, workout_set.is_warmup
        )
    total = sum(volumes.values()) or 1.0
    return [
        {"body_part": part, "volume": vol, "percent": round(100 * vol / total, 2)}
        for part, vol in sorted(volumes.items(), key=lambda item: item[1], reverse=True)
    ]


async def list_achievements(db: AsyncSession, user: User) -> list[Achievement]:
    result = await db.execute(
        select(Achievement)
        .where(Achievement.user_id == user.id)
        .order_by(Achievement.unlocked_at.desc())
    )
    return list(result.scalars().all())


async def list_personal_records(db: AsyncSession, user: User) -> list[PersonalRecord]:
    result = await db.execute(
        select(PersonalRecord)
        .options(selectinload(PersonalRecord.exercise))
        .where(PersonalRecord.user_id == user.id)
        .order_by(PersonalRecord.achieved_at.desc())
    )
    return list(result.scalars().all())
