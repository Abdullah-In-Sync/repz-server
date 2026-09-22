import asyncio
import re
from pathlib import Path

from PIL import Image

from app.core.config import get_settings

_gif_fetch_lock = asyncio.Semaphore(2)

SAFE_GIF_NAME = re.compile(r"^[A-Za-z0-9_-]+(?:\.(?:gif|png))?$")


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


def normalize_gif_id(filename: str) -> str | None:
    if not SAFE_GIF_NAME.fullmatch(filename):
        return None
    return filename.removesuffix(".gif").removesuffix(".png")


async def ensure_local_gif(external_id: str) -> Path | None:
    dest = gif_path(external_id)
    if dest.exists() and dest.stat().st_size > 0:
        return dest

    settings = get_settings()
    if not settings.workoutx_api_key:
        return None

    import httpx

    headers = {"X-WorkoutX-Key": settings.workoutx_api_key}
    base = settings.workoutx_base_url.rstrip("/")
    async with _gif_fetch_lock:
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        async with httpx.AsyncClient(timeout=10.0) as client:
            for url in (f"{base}/v1/gifs/{external_id}.gif", f"{base}/v1/gifs/{external_id}"):
                try:
                    response = await client.get(url, headers=headers)
                except httpx.HTTPError:
                    continue
                if response.status_code == 200 and response.content:
                    await asyncio.to_thread(save_gif_and_thumb, external_id, response.content)
                    return dest if dest.exists() else None
    return None
