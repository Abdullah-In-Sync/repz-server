#!/usr/bin/env python3
"""Copy GIFs from exercises-dataset into MEDIA_ROOT/gifs (match on exercise id)."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.dataset_gif_import import (
    import_gifs_from_dataset,
    load_repz_catalog,
    rewrite_legacy_remote_gif_urls,
    update_db_gif_urls_for_external_ids,
    copy_attribution_notice,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default_dataset = ROOT.parent / "exercises-dataset"
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=default_dataset,
        help=f"Path to exercises-dataset clone (default: {default_dataset})",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        default=ROOT / "exercises.json",
        help="Repz catalog JSON (for id + name sanity check)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite GIFs that already exist on disk",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report actions without writing files",
    )
    parser.add_argument(
        "--update-db",
        action="store_true",
        help="Set gif_url on matching catalog exercises after import",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.25,
        help="Minimum Repz/dataset name token overlap (0-1)",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    if not args.dataset_root.is_dir():
        raise SystemExit(f"dataset root not found: {args.dataset_root}")
    if not args.file.is_file():
        raise SystemExit(f"catalog not found: {args.file}")

    stats = import_gifs_from_dataset(
        dataset_root=args.dataset_root,
        repz_catalog_path=args.file,
        skip_existing=not args.force,
        dry_run=args.dry_run,
        min_similarity=args.min_similarity,
    )
    if not args.dry_run:
        copy_attribution_notice(args.dataset_root)

    print(
        {
            "copied": stats.copied,
            "skipped_existing": stats.skipped_existing,
            "skipped_no_dataset": stats.skipped_no_dataset,
            "skipped_name_mismatch": stats.skipped_name_mismatch,
            "skipped_manual": stats.skipped_manual,
            "skipped_missing_file": stats.skipped_missing_file,
            "media_root": str(Path(get_settings().media_root) / "gifs"),
            "dry_run": args.dry_run,
        }
    )
    if stats.warnings:
        print("warnings:", *stats.warnings[:20], sep="\n  ")
        if len(stats.warnings) > 20:
            print(f"  ... and {len(stats.warnings) - 20} more")
    if stats.errors:
        print("errors:", *stats.errors[:20], sep="\n  ")
        raise SystemExit(1)

    if args.update_db and not args.dry_run:
        repz = load_repz_catalog(args.file)
        async with SessionLocal() as db:
            legacy = await rewrite_legacy_remote_gif_urls(db)
            updated = await update_db_gif_urls_for_external_ids(db, set(repz.keys()))
        print({"legacy_gif_url_cleared": legacy, "db_gif_url_updated": updated})


def main() -> None:
    asyncio.run(main_async(parse_args()))


if __name__ == "__main__":
    main()
