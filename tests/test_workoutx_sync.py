from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.workoutx_sync import sync_exercises


@pytest.mark.asyncio
async def test_sync_pages_and_upserts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WORKOUTX_API_KEY", "wx_test")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    from app.core import config
    from app.core.config import get_settings

    get_settings.cache_clear()
    config.settings = get_settings()

    page = {
        "total": 1,
        "count": 1,
        "data": [
            {
                "id": "0001",
                "name": "Plank",
                "bodyPart": "Waist",
                "target": "Abs",
                "equipment": "Body Weight",
                "gifUrl": "https://example.com/0001.gif",
            }
        ],
    }

    class FakeResponse:
        def __init__(self, payload=None, content=b"GIF89a"):
            self._payload = payload
            self.content = content

        def raise_for_status(self) -> None:
            return None

        def json(self):
            return self._payload

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None, headers=None, timeout=None):
            if "example.com" in url:
                return FakeResponse(content=b"GIF89a")
            return FakeResponse(payload=page)

    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=db_result)
    db.commit = AsyncMock()
    db.add = MagicMock()

    with (
        patch("httpx.AsyncClient", return_value=FakeClient()),
        patch(
            "app.services.exercise_service.distinct_filters",
            new=AsyncMock(
                return_value={"body_parts": ["Waist"], "targets": ["Abs"], "equipment": []}
            ),
        ),
        patch("app.jobs.workoutx_sync.json_cache_set", new=AsyncMock()),
    ):
        result = await sync_exercises(db)

    assert result["upserted"] == 1
    assert result["total"] == 1
    db.add.assert_called()
    get_settings.cache_clear()
    config.settings = get_settings()
