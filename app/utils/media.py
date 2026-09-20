from pathlib import Path

from PIL import Image

from app.core.config import get_settings


def gif_dir() -> Path:
    path = Path(get_settings().media_root) / "gifs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def gif_path(external_id: str) -> Path:
    return gif_dir() / f"{external_id}.gif"


def thumb_path(external_id: str) -> Path:
    return gif_dir() / f"{external_id}.png"


def public_gif_url(external_id: str) -> str:
    return f"{get_settings().public_base_url.rstrip('/')}/media/gifs/{external_id}.gif"


def save_gif_and_thumb(external_id: str, content: bytes) -> str:
    dest = gif_path(external_id)
    dest.write_bytes(content)
    try:
        with Image.open(dest) as image:
            image.seek(0)
            image.convert("RGB").save(thumb_path(external_id), "PNG")
    except Exception:
        pass
    return public_gif_url(external_id)
