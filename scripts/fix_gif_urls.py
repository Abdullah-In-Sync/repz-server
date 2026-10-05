#!/usr/bin/env python3
"""Clear legacy WorkoutX gif_url values and point catalog rows at local /media/gifs."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal
from app.services.dataset_gif_import import (
    load_repz_catalog,
    rewrite_legacy_remote_gif_urls,
    update_db_gif_urls_for_external_ids,
)


async def main() -> None:
    catalog = ROOT / "exercises.json"
    ids = set(load_repz_catalog(catalog).keys()) if catalog.is_file() else set()
    async with SessionLocal() as db:
        legacy = await rewrite_legacy_remote_gif_urls(db)
        synced = await update_db_gif_urls_for_external_ids(db, ids) if ids else 0
    print({"legacy_gif_url_cleared": legacy, "db_gif_url_synced": synced})


if __name__ == "__main__":
    asyncio.run(main())
