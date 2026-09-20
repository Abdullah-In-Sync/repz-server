from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.redis import json_cache_set
from app.models.exercise import Exercise, ExerciseSource
from app.utils.media import gif_path, public_gif_url, save_gif_and_thumb
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
        "secondary_muscles": raw.get("secondaryMuscles"),
        "instructions": raw.get("instructions"),
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
        "movement_tags": raw.get("movement_tags") or raw.get("movementTags"),
        "description": raw.get("description"),
        "is_time_based": is_time,
        "is_distance_based": is_distance,
    }


async def download_gif(client, raw: dict) -> str | None:
    external_id = str(raw["id"])
    remote = raw.get("gifUrl")
    existing = gif_path(external_id)
    if existing.exists():
        return public_gif_url(external_id)
    if not remote:
        return None
    response = await client.get(remote)
    response.raise_for_status()
    return save_gif_and_thumb(external_id, response.content)


async def sync_exercises(db: AsyncSession) -> dict:
    settings = get_settings()
    if not settings.workoutx_api_key:
        raise RuntimeError("WORKOUTX_API_KEY is not configured")

    import httpx
    from tenacity import retry, stop_after_attempt, wait_exponential

    headers = {"X-WorkoutX-Key": settings.workoutx_api_key}
    upserted = 0
    offset = 0
    limit = 100
    total = None

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=20))
    async def fetch_page(client: httpx.AsyncClient, page_offset: int) -> dict:
        response = await client.get(
            f"{settings.workoutx_base_url.rstrip('/')}/v1/exercises",
            params={"limit": limit, "offset": page_offset},
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return {"total": len(payload), "count": len(payload), "data": payload}
        return payload

    async with httpx.AsyncClient() as client:
        while True:
            page = await fetch_page(client, offset)
            items = page.get("data") or []
            total = page.get("total") if total is None else total
            if not items:
                break
            for raw in items:
                gif_url = None
                try:
                    gif_url = await download_gif(client, raw)
                except Exception as exc:
                    logger.warning("gif_download_failed", exercise_id=raw.get("id"), error=str(exc))
                    gif_url = raw.get("gifUrl")
                mapped = map_workoutx_exercise(raw, gif_url)
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
            offset += len(items)
            if total is not None and offset >= int(total):
                break
            if len(items) < limit:
                break

    from app.services.exercise_service import distinct_filters

    filters = await distinct_filters(db)
    await json_cache_set("exercises:filters", filters, FILTERS_TTL)
    logger.info("workoutx_sync_complete", upserted=upserted, total=total)
    return {"upserted": upserted, "total": total}
