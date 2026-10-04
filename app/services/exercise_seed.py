"""Load the local exercises.json catalog into PostgreSQL."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.exercise import Exercise, ExerciseSource
from app.schemas.exercise import as_str_list
from app.utils.media import resolve_local_gif, save_gif_and_thumb

logger = get_logger(__name__)


def _reps_flag(raw: dict) -> bool:
    if "is_reps_based" in raw:
        return bool(raw["is_reps_based"])
    mode = raw.get("tracking_mode") or ""
    return mode in {"reps", "reps_weight"}


def map_json_exercise(raw: dict) -> dict:
    external_id = str(raw["id"])

    return {
        "source": ExerciseSource.CATALOG,
        "external_id": external_id,
        "name": raw.get("name") or "",
        "body_part": raw.get("bodyPart"),
        "target": raw.get("target"),
        "equipment": raw.get("equipment"),
        "secondary_muscles": as_str_list(raw.get("secondaryMuscles")),
        "instructions": as_str_list(raw.get("instructions")),
        "gif_url": None,
        "category": raw.get("category"),
        "difficulty": raw.get("difficulty"),
        "mechanic": raw.get("mechanic"),
        "force": raw.get("force"),
        "met": raw.get("met"),
        "calories_per_minute": raw.get("caloriesPerMinute"),
        "is_unilateral": bool(raw.get("isUnilateral") or False),
        "recommended_sets": _str_or_none(raw.get("recommendedSets")),
        "recommended_reps": _str_or_none(raw.get("recommendedReps")),
        "movement_tags": as_str_list(raw.get("movement_tags") or raw.get("movementTags")),
        "description": raw.get("description"),
        "is_time_based": bool(raw.get("is_time_based") or False),
        "is_distance_based": bool(raw.get("is_distance_based") or False),
        "is_load_based": bool(raw.get("is_load_based") or False),
        "is_reps_based": _reps_flag(raw),
    }


def _preserve_gif_url(exercise: Exercise, external_id: str) -> bool:
    if exercise.gif_url and exercise.gif_url.strip():
        return True
    return resolve_local_gif(external_id) is not None


def _str_or_none(value) -> str | None:
    if value is None:
        return None
    return str(value)


async def _maybe_download_gif(external_id: str, remote_url: str | None) -> None:
    if not remote_url or not remote_url.startswith("http"):
        return
    from app.utils.media import gif_path

    dest = gif_path(external_id)
    if dest.exists() and dest.stat().st_size > 0:
        return
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(remote_url)
            if response.status_code == 200 and response.content:
                save_gif_and_thumb(external_id, response.content)
    except httpx.HTTPError as exc:
        logger.warning("gif_download_failed", external_id=external_id, error=str(exc))


async def seed_exercises_from_file(
    db: AsyncSession,
    path: Path,
    *,
    download_gifs: bool = False,
) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("data")
    if not isinstance(items, list):
        raise ValueError("exercises file must contain a top-level 'data' array")

    upserted = 0
    for raw in items:
        if not isinstance(raw, dict) or raw.get("id") is None:
            continue
        mapped = map_json_exercise(raw)
        external_id = mapped["external_id"]
        if download_gifs:
            await _maybe_download_gif(external_id, raw.get("gifUrl"))

        result = await db.execute(
            select(Exercise).where(Exercise.external_id == external_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for key, value in mapped.items():
                if key == "gif_url" and _preserve_gif_url(existing, external_id):
                    continue
                setattr(existing, key, value)
        else:
            db.add(Exercise(**mapped))
        upserted += 1

    await db.commit()
    logger.info("exercise_seed_complete", upserted=upserted, total=len(items))
    return {"upserted": upserted, "total": len(items)}
