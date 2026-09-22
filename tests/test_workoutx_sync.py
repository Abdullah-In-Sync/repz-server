from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.workoutx_sync import sync_exercises


class FakeResponse:
    def __init__(self, payload=None):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


@pytest.mark.asyncio
async def test_sync_fetches_full_catalog_without_pagination(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WORKOUTX_API_KEY", "wx_test")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    from app.core import config
    from app.core.config import get_settings

    get_settings.cache_clear()
    config.settings = get_settings()

    catalog = {
        "total": 3,
        "data": [
            {"id": "0001", "name": "Plank", "bodyPart": "Waist", "target": "Abs"},
            {"id": "0002", "name": "Squat", "bodyPart": "Legs", "target": "Quads"},
            {"id": "0003", "name": "Press", "bodyPart": "Chest", "target": "Pectorals"},
        ],
    }
    captured: dict = {}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None, headers=None, timeout=None):
            captured["params"] = params
            captured["url"] = url
            return FakeResponse(payload=catalog)

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
            new=AsyncMock(return_value={"body_parts": [], "targets": [], "equipment": []}),
        ),
        patch("app.jobs.workoutx_sync.json_cache_set", new=AsyncMock()),
    ):
        result = await sync_exercises(db)

    assert captured["params"] is None
    assert result["upserted"] == 3
    assert result["total"] == 3
    assert db.add.call_count == 3
    get_settings.cache_clear()
    config.settings = get_settings()
