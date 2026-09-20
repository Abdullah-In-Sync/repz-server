TIME_BASED_NAMES = {
    "plank",
    "side plank",
    "hollow hold",
    "wall sit",
    "dead hang",
}

DISTANCE_EQUIPMENT = {
    "treadmill",
    "elliptical machine",
    "stationary bike",
    "skierg machine",
    "stepmill machine",
    "bike",
    "elliptical",
}

TIME_AND_DISTANCE_EQUIPMENT = {
    "treadmill",
    "elliptical machine",
    "stationary bike",
    "skierg machine",
    "stepmill machine",
}


def classify_exercise(name: str, equipment: str | None) -> tuple[bool, bool]:
    lowered_name = (name or "").strip().lower()
    lowered_eq = (equipment or "").strip().lower()
    is_time = lowered_name in TIME_BASED_NAMES or lowered_eq in TIME_AND_DISTANCE_EQUIPMENT
    is_distance = lowered_eq in DISTANCE_EQUIPMENT or lowered_eq in TIME_AND_DISTANCE_EQUIPMENT
    if lowered_name == "plank":
        is_distance = False
        is_time = True
    return is_time, is_distance


def epley_1rm(weight_kg: float, reps: int) -> float:
    if reps <= 1:
        return weight_kg
    return round(weight_kg * (1 + reps / 30.0), 2)


def set_volume(weight_kg: float | None, reps: int | None, is_warmup: bool) -> float:
    if is_warmup or not weight_kg or not reps:
        return 0.0
    return float(weight_kg) * int(reps)


def parse_range(range_value: str) -> int:
    mapping = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
    if range_value not in mapping:
        raise ValueError("range must be one of 7d, 30d, 90d, 1y")
    return mapping[range_value]
