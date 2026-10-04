from app.models.exercise import ExerciseSource
from app.services.exercise_seed import map_json_exercise


def test_map_json_exercise_reps_weight() -> None:
    raw = {
        "id": "0999",
        "name": "Dumbbell Bench Press",
        "bodyPart": "Chest",
        "target": "Pectorals",
        "equipment": "Dumbbell",
        "is_time_based": False,
        "is_distance_based": False,
        "is_load_based": True,
        "tracking_mode": "reps_weight",
    }
    mapped = map_json_exercise(raw)
    assert mapped["source"] == ExerciseSource.CATALOG
    assert mapped["external_id"] == "0999"
    assert mapped["is_load_based"] is True
    assert mapped["is_reps_based"] is True
    assert mapped["gif_url"] is None


def test_map_json_exercise_bodyweight_reps() -> None:
    raw = {
        "id": "0003",
        "name": "Push-up",
        "equipment": "Body Weight",
        "is_time_based": False,
        "is_distance_based": False,
        "is_load_based": False,
        "tracking_mode": "reps",
    }
    mapped = map_json_exercise(raw)
    assert mapped["is_load_based"] is False
    assert mapped["is_reps_based"] is True
