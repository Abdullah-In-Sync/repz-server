from datetime import datetime

from app.models.exercise import ExerciseSource
from app.schemas.exercise import ExerciseRead


def test_local_gif_overrides_workoutx_url(monkeypatch) -> None:
    import app.schemas.exercise as exercise_schema

    monkeypatch.setattr(
        exercise_schema,
        "resolve_local_gif",
        lambda key: object(),
    )
    monkeypatch.setattr(
        exercise_schema,
        "public_gif_url",
        lambda key: f"http://localhost:8000/media/gifs/{key}.gif",
    )

    row = ExerciseRead(
        id="uuid-1",
        source=ExerciseSource.CATALOG,
        external_id="0001",
        name="Test",
        body_part=None,
        target=None,
        equipment=None,
        secondary_muscles=None,
        instructions=None,
        gif_url="https://api.workoutxapp.com/v1/gifs/0001.gif",
        category=None,
        difficulty=None,
        mechanic=None,
        force=None,
        met=None,
        calories_per_minute=None,
        is_unilateral=False,
        recommended_sets=None,
        recommended_reps=None,
        movement_tags=None,
        created_by_user_id=None,
        is_time_based=False,
        is_distance_based=False,
        is_load_based=False,
        is_reps_based=True,
        description=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert row.gif_url == "http://localhost:8000/media/gifs/0001.gif"
