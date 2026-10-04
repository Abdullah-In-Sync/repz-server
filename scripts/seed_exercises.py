#!/usr/bin/env python3
"""Seed PostgreSQL from exercises.json (run after migrations)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal
from app.services.exercise_seed import seed_exercises_from_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=ROOT / "exercises.json",
        help="Path to enriched exercises.json",
    )
    parser.add_argument(
        "--download-gifs",
        action="store_true",
        help="Download gifUrl assets into MEDIA_ROOT/gifs (one-time)",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if not args.file.is_file():
        raise SystemExit(f"file not found: {args.file}")

    async with SessionLocal() as db:
        stats = await seed_exercises_from_file(
            db, args.file, download_gifs=args.download_gifs
        )
    print(stats)


if __name__ == "__main__":
    asyncio.run(main())
