from app.services.dataset_gif_import import (
    MANUAL_SKIP_IDS,
    name_similarity,
    normalize_name,
)


def test_normalize_name_strips_gender_suffix() -> None:
    assert "side lying" in normalize_name("Side Lying (male)")


def test_name_similarity_pallof() -> None:
    sim = name_similarity(
        "Band Horizontal Pallof Press",
        "band horizontal pallof press",
    )
    assert sim >= 0.9


def test_name_similarity_mismatch_3533() -> None:
    sim = name_similarity("Bulgarian Split Squat", "quads")
    assert sim < 0.25


def test_manual_skip_includes_3533() -> None:
    assert "3533" in MANUAL_SKIP_IDS
