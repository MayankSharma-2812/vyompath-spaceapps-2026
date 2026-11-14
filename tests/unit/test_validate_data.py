from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.validate_data import POINTS_FILE, _extract_points, validate_science_points

SAMPLE_POINT = {
    "id": "POI-TEST-001",
    "name": "Test Point Alpha",
    "coordinates": [77.45, 18.44],
    "mission": "Mars 2020 (Perseverance)",
    "significance": "Test sample outcrop location.",
    "source_url": "https://mars.nasa.gov/test",
    "citation": "Test Citation 2026.",
}


def test_validate_flat_list_of_valid_points(tmp_path: Path):
    path = tmp_path / "science_points.json"
    path.write_text(json.dumps([SAMPLE_POINT]), encoding="utf-8")
    errors = validate_science_points(path)
    assert errors == []


def test_validate_dict_with_points_list(tmp_path: Path):
    path = tmp_path / "science_points.json"
    path.write_text(json.dumps({"points": [SAMPLE_POINT]}), encoding="utf-8")
    errors = validate_science_points(path)
    assert errors == []


@pytest.mark.parametrize("invalid_data", ['"just a string"', "42", "true", "null"])
def test_validate_top_level_non_container(tmp_path: Path, invalid_data: str):
    path = tmp_path / "science_points.json"
    path.write_text(invalid_data, encoding="utf-8")
    errors = validate_science_points(path)
    assert len(errors) == 1
    assert "must contain a 'points' array" in errors[0]


def test_validate_dict_without_points(tmp_path: Path):
    path = tmp_path / "science_points.json"
    path.write_text(json.dumps({"version": "1.0.0", "items": []}), encoding="utf-8")
    errors = validate_science_points(path)
    assert len(errors) == 1
    assert "must contain a 'points' array" in errors[0]


def test_validate_real_science_points_file():
    assert POINTS_FILE.is_file()
    errors = validate_science_points(POINTS_FILE)
    assert errors == []


def test_extract_points_helper_direct():
    assert _extract_points([SAMPLE_POINT]) == [SAMPLE_POINT]
    assert _extract_points({"points": [SAMPLE_POINT]}) == [SAMPLE_POINT]
    with pytest.raises(ValueError, match="Science catalogue must contain a 'points' array"):
        _extract_points({"invalid": []})
    with pytest.raises(ValueError, match="Science catalogue must contain a 'points' array"):
        _extract_points("not a container")
