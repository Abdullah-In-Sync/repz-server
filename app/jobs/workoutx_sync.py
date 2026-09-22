from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import json_cache_set
from app.models.exercise import Exercise, ExerciseSource
from app.schemas.exercise import as_str_list
from app.utils.media import public_gif_url
from app.utils.training import classify_exercise

logger = get_logger(__name__)

FILTERS_TTL = 60 * 60 * 24


def map_workoutx_exercise(raw: dict, gif_url: str | None) -> dict:
    name = raw.get("name") or ""
    equipment = raw.get("equipment")
    is_time, is_distance = classify_exercise(name, equipment)
    recommended_sets = raw.get("recommendedSets")
    recommended_reps = raw.get("recommendedReps")
    return {
        "source": ExerciseSource.WORKOUTX,
        "external_id": str(raw["id"]),
        "name": name,
        "body_part": raw.get("bodyPart"),
        "target": raw.get("target"),
        "equipment": equipment,
        "secondary_muscles": as_str_list(raw.get("secondaryMuscles")),
        "instructions": as_str_list(raw.get("instructions")),
        "gif_url": gif_url,
        "category": raw.get("category"),
        "difficulty": raw.get("difficulty"),
        "mechanic": raw.get("mechanic"),
        "force": raw.get("force"),
        "met": raw.get("met"),
        "calories_per_minute": raw.get("caloriesPerMinute"),
        "is_unilateral": bool(raw.get("isUnilateral") or False),
        "recommended_sets": str(recommended_sets) if recommended_sets is not None else None,
        "recommended_reps": str(recommended_reps) if recommended_reps is not None else None,
        "movement_tags": as_str_list(raw.get("movement_tags") or raw.get("movementTags")),
        "description": raw.get("description"),
        "is_time_based": is_time,
        "is_distance_based": is_distance,
    }


def _items_from_payload(payload: object) -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("items") or []
    return []


async def sync_exercises(db: AsyncSession) -> dict:
    settings = get_settings()
    if not settings.workoutx_api_key:
        raise RuntimeError("WORKOUTX_API_KEY is not configured")

    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential

    headers = {"X-WorkoutX-Key": settings.workoutx_api_key}

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=30))
    async def fetch_catalog(client: httpx.AsyncClient) -> list:
        response = await client.get(
            f"{settings.workoutx_base_url.rstrip('/')}/v1/exercises",
            headers=headers,
            timeout=120.0,
        )
        response.raise_for_status()
        return _items_from_payload(response.json())

    upserted = 0
    async with httpx.AsyncClient() as client:
        items = await fetch_catalog(client)
        for raw in items:
            if not raw.get("id"):
                continue
            mapped = map_workoutx_exercise(raw, public_gif_url(str(raw["id"])))
            result = await db.execute(
                select(Exercise).where(Exercise.external_id == mapped["external_id"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                for key, value in mapped.items():
                    setattr(existing, key, value)
            else:
                db.add(Exercise(**mapped))
            upserted += 1
        await db.commit()

    from app.services.exercise_service import distinct_filters

    filters = await distinct_filters(db)
    await json_cache_set("exercises:filters", filters, FILTERS_TTL)
    logger.info("workoutx_sync_complete", upserted=upserted, total=len(items))
    return {"upserted": upserted, "total": len(items)}
