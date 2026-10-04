import re
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

SAFE_GIF_NAME = re.compile(r"^[A-Za-z0-9_-]+(?:\.(?:gif|png|webp|jpg|jpeg))?$")


def gif_dir() -> Path:
    path = Path(get_settings().media_root) / "gifs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def gif_path(file_key: str) -> Path:
    return gif_dir() / f"{file_key}.gif"


def thumb_path(file_key: str) -> Path:
    return gif_dir() / f"{file_key}.png"


def public_gif_url(file_key: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/media/gifs/{file_key}.gif"


def is_legacy_remote_gif(url: str | None) -> bool:
    """True for deprecated third-party GIF hosts we no longer use."""
    if not url or not url.strip():
        return False
    lowered = url.strip().lower()
    return "workoutxapp.com" in lowered or "api.workoutx" in lowered


def save_gif_and_thumb(file_key: str, content: bytes) -> str:
    dest = gif_path(file_key)
    dest.write_bytes(content)
    try:
        with Image.open(dest) as image:
            image.seek(0)
            image.convert("RGB").save(thumb_path(file_key), "PNG")
    except Exception:
        pass
    return public_gif_url(file_key)


def normalize_gif_id(filename: str) -> str | None:
    if not SAFE_GIF_NAME.fullmatch(filename):
        return None
    for suffix in (".gif", ".png", ".webp", ".jpg", ".jpeg"):
        if filename.lower().endswith(suffix):
            return filename[: -len(suffix)]
    return filename


def resolve_local_gif(file_key: str) -> Path | None:
    dest = gif_path(file_key)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    return None


def media_key_for_exercise(exercise) -> str | None:
    if exercise.external_id:
        return str(exercise.external_id)
    return str(exercise.id)


def exercise_public_gif_url(exercise) -> str | None:
    if exercise.gif_url:
        return exercise.gif_url
    key = media_key_for_exercise(exercise)
    if key and resolve_local_gif(key):
        return public_gif_url(key)
    return None
