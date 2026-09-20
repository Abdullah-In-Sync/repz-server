import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from datetime import date
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.deps import get_current_user
from app.db.session import get_db
from app.models.user import User


def mysql_available() -> bool:
    return os.getenv("RUN_DB_TESTS") == "1"


pytestmark = pytest.mark.skipif(not mysql_available(), reason="Set RUN_DB_TESTS=1 for MySQL tests")


@pytest.fixture
async def client():
    from app.core.config import settings
    from app.db.base import Base
    from app.main import app

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id = str(uuid4())
    async with Session() as session:
        session.add(
            User(
                id=user_id,
                firebase_uid="test-uid",
                email="test@example.com",
                display_name="Tester",
            )
        )
        await session.commit()

    async def override_db():
        async with Session() as session:
            yield session

    async def override_user():
        async with Session() as session:
            return await session.get(User, user_id)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_me_and_custom_exercise_and_workout(client) -> None:
    ac = client
    me = await ac.get("/api/v1/users/me")
    assert me.status_code == 200
    assert me.json()["firebase_uid"] == "test-uid"

    created = await ac.post(
        "/api/v1/exercises/custom",
        json={"name": "Custom Curl", "body_part": "Upper Arms", "target": "Biceps"},
    )
    assert created.status_code == 201
    exercise_id = created.json()["id"]

    workout = await ac.post("/api/v1/workouts", json={"name": "Push day"})
    assert workout.status_code == 201
    workout_id = workout.json()["id"]

    logged = await ac.post(
        f"/api/v1/workouts/{workout_id}/sets",
        json={"exercise_id": exercise_id, "weight_kg": 20, "reps": 10, "rpe": 8, "set_number": 1},
    )
    assert logged.status_code == 201

    finished = await ac.patch(f"/api/v1/workouts/{workout_id}", json={"finish": True})
    assert finished.status_code == 200
    assert finished.json()["total_volume_kg"] == 200

    prs = await ac.get("/api/v1/reports/personal-records")
    assert prs.status_code == 200
    assert len(prs.json()) >= 1

    metric = await ac.post(
        "/api/v1/body-metrics",
        json={"date": date.today().isoformat(), "weight_kg": 80},
    )
    assert metric.status_code == 201
