from app.jobs.workoutx_sync import map_workoutx_exercise
from app.models.exercise import ExerciseSource
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


def test_volume_milestones() -> None:
    assert 10_000 in VOLUME_MILESTONES
