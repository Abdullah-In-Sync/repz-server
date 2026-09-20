import pytest

from app.schemas.workout import SetCreate
from app.utils.training import classify_exercise, epley_1rm, parse_range, set_volume


def test_epley_1rm() -> None:
    assert epley_1rm(100, 1) == 100
    assert epley_1rm(100, 5) == 116.67


def test_set_volume_skips_warmup() -> None:
    assert set_volume(100, 5, True) == 0
    assert set_volume(100, 5, False) == 500
    assert set_volume(None, 5, False) == 0


def test_classify_plank_and_treadmill() -> None:
    assert classify_exercise("Plank", "Body Weight") == (True, False)
    is_time, is_distance = classify_exercise("Treadmill", "Treadmill")
    assert is_time and is_distance


def test_parse_range() -> None:
    assert parse_range("30d") == 30
    with pytest.raises(ValueError):
        parse_range("2d")


def test_rpe_validation() -> None:
    SetCreate(exercise_id="x", rpe=8.5)
    with pytest.raises(ValueError):
        SetCreate(exercise_id="x", rpe=8.25)
    with pytest.raises(ValueError):
        SetCreate(exercise_id="x", rpe=11)
