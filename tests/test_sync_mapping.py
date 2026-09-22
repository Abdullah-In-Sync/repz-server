from datetime import datetime

from app.jobs.workoutx_sync import map_workoutx_exercise
from app.models.exercise import Exercise, ExerciseSource
from app.schemas.common import PaginatedResponse
from app.schemas.exercise import ExerciseRead
from app.services.achievement_engine import VOLUME_MILESTONES


def test_map_workoutx_exercise() -> None:
    raw = {
        "id": "0001",
        "name": "3/4 Sit-up",
        "bodyPart": "Waist",
        "target": "Abs",
        "equipment": "Body Weight",
        "secondaryMuscles": ["Hip Flexors"],
        "instructions": ["Lie down"],
        "gifUrl": "https://api.workoutxapp.com/v1/gifs/0001.gif",
        "category": "strength",
        "difficulty": "beginner",
        "mechanic": "isolation",
        "force": "push",
        "met": 3.5,
        "caloriesPerMinute": 4.3,
        "isUnilateral": False,
        "recommendedSets": "3",
        "recommendedReps": "10-15",
        "movement_tags": ["beginner-friendly"],
        "description": "A sit-up variation",
    }
    mapped = map_workoutx_exercise(raw, "http://localhost:8000/media/gifs/0001.gif")
    assert mapped["external_id"] == "0001"
    assert mapped["source"] == ExerciseSource.WORKOUTX
    assert mapped["body_part"] == "Waist"
    assert mapped["calories_per_minute"] == 4.3
    assert mapped["gif_url"].endswith("/0001.gif")
    assert mapped["is_time_based"] is False
    assert mapped["secondary_muscles"] == ["Hip Flexors"]
    assert mapped["instructions"] == ["Lie down"]
    assert mapped["movement_tags"] == ["beginner-friendly"]


def test_map_workoutx_exercise_coerces_non_lists() -> None:
    raw = {
        "id": "0002",
        "name": "Plank",
        "equipment": "Body Weight",
        "secondaryMuscles": "Abs",
        "instructions": "Hold position",
        "movementTags": {"a": "core", "b": "isometric"},
    }
    mapped = map_workoutx_exercise(raw, None)
    assert mapped["secondary_muscles"] == ["Abs"]
    assert mapped["instructions"] == ["Hold position"]
    assert mapped["movement_tags"] == ["core", "isometric"]


def test_paginated_exercises_serialize_orm_rows() -> None:
    now = datetime(2026, 1, 1)
    exercise = Exercise(
        id="ex-1",
        source=ExerciseSource.WORKOUTX,
        name="Sit-up",
        is_unilateral=False,
        is_time_based=False,
        is_distance_based=False,
        created_at=now,
        updated_at=now,
    )
    payload = PaginatedResponse[ExerciseRead](items=[exercise], total=1, limit=40, offset=0)
    dumped = payload.model_dump(mode="json")
    assert dumped["items"][0]["name"] == "Sit-up"
    assert dumped["total"] == 1


def test_volume_milestones() -> None:
    assert 10_000 in VOLUME_MILESTONES
