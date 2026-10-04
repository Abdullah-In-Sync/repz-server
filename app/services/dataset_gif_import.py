"""Import animation GIFs from hasaneyldrm/exercises-dataset into MEDIA_ROOT/gifs."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings
from app.utils.media import gif_path, is_legacy_remote_gif, public_gif_url, save_gif_and_thumb

# Known ID collision: same id, unrelated names in Repz vs dataset.
MANUAL_SKIP_IDS = frozenset({"3533"})

MIN_NAME_SIMILARITY = 0.25


def normalize_name(name: str) -> str:
    text = (name or "").lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def name_similarity(repz_name: str, dataset_name: str) -> float:
    repz_tokens = set(normalize_name(repz_name).split())
    dataset_tokens = set(normalize_name(dataset_name).split())
    if not repz_tokens or not dataset_tokens:
        return 0.0
    return len(repz_tokens & dataset_tokens) / len(dataset_tokens | repz_tokens)


def load_repz_catalog(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Repz exercises file must contain a data array")
    return {str(raw["id"]): raw for raw in items if raw.get("id") is not None}


def load_dataset_index(dataset_root: Path) -> dict[str, dict]:
    data_path = dataset_root / "data" / "exercises.json"
    if not data_path.is_file():
        raise FileNotFoundError(f"dataset not found: {data_path}")
    items = json.loads(data_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("dataset exercises.json must be a JSON array")
    return {str(raw["id"]): raw for raw in items if raw.get("id") is not None}


def resolve_dataset_gif(dataset_root: Path, row: dict) -> Path | None:
    rel = row.get("gif_url")
    if isinstance(rel, str) and rel.strip():
        candidate = dataset_root / rel.strip()
        if candidate.is_file():
            return candidate
    exercise_id = str(row.get("id", ""))
    videos = dataset_root / "videos"
    if exercise_id and videos.is_dir():
        matches = sorted(videos.glob(f"{exercise_id}-*.gif"))
        if matches:
            return matches[0]
    return None


@dataclass
class ImportStats:
    copied: int = 0
    skipped_existing: int = 0
    skipped_no_dataset: int = 0
    skipped_name_mismatch: int = 0
    skipped_manual: int = 0
    skipped_missing_file: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def import_gifs_from_dataset(
    *,
    dataset_root: Path,
    repz_catalog_path: Path,
    skip_existing: bool = True,
    dry_run: bool = False,
    min_similarity: float = MIN_NAME_SIMILARITY,
) -> ImportStats:
    stats = ImportStats()
    repz = load_repz_catalog(repz_catalog_path)
    dataset = load_dataset_index(dataset_root)

    for external_id, repz_row in repz.items():
        if external_id in MANUAL_SKIP_IDS:
            stats.skipped_manual += 1
            stats.warnings.append(
                f"{external_id}: manual skip ({repz_row.get('name')!r})"
            )
            continue

        ds_row = dataset.get(external_id)
        if not ds_row:
            stats.skipped_no_dataset += 1
            continue

        similarity = name_similarity(
            str(repz_row.get("name") or ""),
            str(ds_row.get("name") or ""),
        )
        if similarity < min_similarity:
            stats.skipped_name_mismatch += 1
            stats.warnings.append(
                f"{external_id}: name mismatch "
                f"(sim={similarity:.2f}) repz={repz_row.get('name')!r} "
                f"ds={ds_row.get('name')!r}"
            )
            continue

        dest = gif_path(external_id)
        if skip_existing and dest.exists() and dest.stat().st_size > 0:
            stats.skipped_existing += 1
            continue

        src = resolve_dataset_gif(dataset_root, ds_row)
        if not src:
            stats.skipped_missing_file += 1
            stats.errors.append(f"{external_id}: GIF file missing in dataset")
            continue

        if dry_run:
            stats.copied += 1
            continue

        try:
            content = src.read_bytes()
            save_gif_and_thumb(external_id, content)
            stats.copied += 1
        except OSError as exc:
            stats.errors.append(f"{external_id}: {exc}")

    return stats


async def rewrite_legacy_remote_gif_urls(db) -> int:
    """Replace WorkoutX (etc.) gif_url values with local URLs or null."""
    from sqlalchemy import select

    from app.models.exercise import Exercise

    result = await db.execute(select(Exercise))
    updated = 0
    for exercise in result.scalars().all():
        if not is_legacy_remote_gif(exercise.gif_url):
            continue
        key = exercise.external_id or exercise.id
        if key and gif_path(str(key)).exists() and gif_path(str(key)).stat().st_size > 0:
            exercise.gif_url = public_gif_url(str(key))
        else:
            exercise.gif_url = None
        updated += 1
    if updated:
        await db.commit()
    return updated


async def update_db_gif_urls_for_external_ids(
    db,
    external_ids: set[str],
) -> int:
    """Set gif_url for catalog rows that now have on-disk GIFs."""
    from sqlalchemy import select

    from app.models.exercise import Exercise, ExerciseSource

    if not external_ids:
        return 0
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    updated = 0
    for external_id in external_ids:
        dest = gif_path(external_id)
        if not dest.exists() or dest.stat().st_size == 0:
            continue
        result = await db.execute(
            select(Exercise).where(
                Exercise.external_id == external_id,
                Exercise.source == ExerciseSource.CATALOG,
            )
        )
        exercise = result.scalar_one_or_none()
        if not exercise:
            continue
        url = public_gif_url(external_id)
        if exercise.gif_url != url:
            exercise.gif_url = url
            updated += 1
    if updated:
        await db.commit()
    return updated


def copy_attribution_notice(dataset_root: Path, media_root: Path | None = None) -> Path:
    """Copy dataset NOTICE into media root for deployment attribution."""
    root = media_root or Path(get_settings().media_root)
    src = dataset_root / "NOTICE.md"
    dest = root / "GYM_VISUAL_NOTICE.md"
    if src.is_file() and not dest.exists():
        shutil.copy2(src, dest)
    return dest
