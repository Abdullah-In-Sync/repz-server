from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import BodyMetric
from app.models.user import User
from app.schemas.metrics import BodyMetricCreate
from app.utils.training import parse_range


async def list_body_metrics(
    db: AsyncSession, user: User, limit: int, offset: int
) -> tuple[list[BodyMetric], int]:
    from sqlalchemy import func

    total = int(
        (
            await db.execute(
                select(func.count()).select_from(BodyMetric).where(BodyMetric.user_id == user.id)
            )
        ).scalar_one()
    )
    result = await db.execute(
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id)
        .order_by(BodyMetric.date.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all()), total


async def create_body_metric(
    db: AsyncSession, user: User, payload: BodyMetricCreate
) -> BodyMetric:
    metric = BodyMetric(user_id=user.id, **payload.model_dump())
    db.add(metric)
    await db.commit()
    await db.refresh(metric)
    return metric


async def body_metric_graph(db: AsyncSession, user: User, range_value: str) -> list[dict]:
    days = parse_range(range_value)
    start = date.today() - timedelta(days=days - 1)
    result = await db.execute(
        select(BodyMetric)
        .where(BodyMetric.user_id == user.id, BodyMetric.date >= start)
        .order_by(BodyMetric.date.asc())
    )
    return [{"date": row.date.isoformat(), "value": row.weight_kg} for row in result.scalars().all()]
