"""Unit tests for tools.validate_data and citation / licensing semantics.

Validates:
- resolve_citation follows strict precedence: citation > source_title > source_url.
- terms_of_use and policy strings CANNOT substitute for missing citations.
- unverified policy strings cannot be reported as verified license metadata.
- data/science_points.json and backend/data/science_points.json remain bit-for-bit synchronized.

NASA Space Apps Challenge 2026 | Team NAKSHATRA X
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from tools.validate_data import (
    resolve_citation,
    validate_science_points,
    validate_layers,
    POINTS_FILE,
    LAYERS_FILE,
    REPO_ROOT,
)


def _make_valid_point(**overrides) -> dict:
    pt = {
        "id": "POI-TEST-001",
        "name": "Test Science POI",
        "coordinates": [77.46, 18.46],
        "mission": "Mars 2020 (Perseverance)",
        "significance": "Test localization waypoint",
        "source_url": "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json",
        "citation": "NASA MMGIS Mars 2020 Waypoints Layer",
        "source_title": "NASA MMGIS Mars 2020 Waypoints Layer",
        "source_note": "End-of-drive localization",
        "terms_of_use": None,
        "source_policy_reference": None,
        "terms_of_use_status": "unverified",
        "source_policy_status": "unverified",
    }
    pt.update(overrides)
    return pt


class TestCitationAndLicensingSemantics:
    """Validate strict separation between citation metadata and licensing/policy status."""

    def test_resolve_citation_precedence(self):
        # 1. Explicit citation is prioritized
        rec1 = {
            "citation": "Primary Explicit Citation",
            "source_title": "Fallback Title",
            "source_url": "https://example.com/data",
        }
        assert resolve_citation(rec1) == "Primary Explicit Citation"

        # 2. Falls back to source_title when citation is missing or empty
        rec2 = {
            "citation": "",
            "source_title": "Fallback Title",
            "source_url": "https://example.com/data",
        }
        assert resolve_citation(rec2) == "Fallback Title"

        # 3. Falls back to source_url when citation and title are missing
        rec3 = {
            "citation": None,
            "source_title": None,
            "source_url": "https://example.com/data",
        }
        assert resolve_citation(rec3) == "https://example.com/data"

    def test_terms_of_use_cannot_satisfy_missing_citation(self):
        # Policy / license string must NEVER satisfy a citation requirement
        rec = {
            "citation": None,
            "source_title": None,
            "source_url": None,
            "terms_of_use": "NASA Open Data Policy (Public Domain)",
            "source_policy_reference": "https://science.nasa.gov/open-science/",
        }
        assert resolve_citation(rec) is None

    def test_terms_of_use_smuggled_as_citation_rejected(self):
        # If citation is set to the same string as terms_of_use / policy reference, it is rejected
        rec = {
            "citation": "NASA Open Data Policy",
            "terms_of_use": "NASA Open Data Policy",
        }
        assert resolve_citation(rec) is None

        rec_pol = {
            "citation": "https://science.nasa.gov/policy",
            "source_policy_reference": "https://science.nasa.gov/policy",
        }
        assert resolve_citation(rec_pol) is None

    def test_unverified_policy_status_rejects_non_null_terms_of_use(self, tmp_path: Path):
        # Point with source_policy_status="unverified" but non-null terms_of_use must fail validation
        bad_point = _make_valid_point(
            terms_of_use="NASA Open Data Policy (Unverified Claim)",
            source_policy_status="unverified",
        )
        cat_file = tmp_path / "science_points.json"
        cat_file.write_text(json.dumps([bad_point]), encoding="utf-8")

        errors = validate_science_points(cat_file)
        assert any("unverified policy status cannot report non-null terms_of_use" in err for err in errors)

    def test_unverified_policy_status_rejects_non_null_policy_reference(self, tmp_path: Path):
        # Point with source_policy_status="unverified" but non-null source_policy_reference must fail
        bad_point = _make_valid_point(
            source_policy_reference="https://science.nasa.gov/open-science/",
            source_policy_status="unverified",
        )
        cat_file = tmp_path / "science_points.json"
        cat_file.write_text(json.dumps([bad_point]), encoding="utf-8")

        errors = validate_science_points(cat_file)
        assert any("unverified policy status cannot report non-null source_policy_reference" in err for err in errors)

    def test_missing_citation_fails_validation(self, tmp_path: Path):
        # Point with no citation, source_title, or source_url fails validation
        bad_point = _make_valid_point(
            citation=None,
            source_title=None,
            source_url="not-a-url",
            terms_of_use="NASA Open Data Policy",
        )
        cat_file = tmp_path / "science_points.json"
        cat_file.write_text(json.dumps([bad_point]), encoding="utf-8")

        errors = validate_science_points(cat_file)
        assert any("missing valid citation" in err for err in errors)

    def test_live_catalogues_synchronized_and_conformant(self):
        repo_points = REPO_ROOT / "data" / "science_points.json"
        backend_points = REPO_ROOT / "backend" / "data" / "science_points.json"

        assert repo_points.exists()
        assert backend_points.exists()

        # Bit-for-bit synchronization
        assert repo_points.read_bytes() == backend_points.read_bytes(), (
            "data/science_points.json and backend/data/science_points.json must be identical!"
        )

        # Validate structure and unverified policy representation
        errors = validate_science_points(repo_points)
        assert errors == [], f"Validation errors in live science points: {errors}"

        with open(repo_points, "r", encoding="utf-8") as f:
            pts = json.load(f)

        assert len(pts) == 5
        for p in pts:
            assert p["terms_of_use"] is None
            assert p["source_policy_reference"] is None
            assert p["source_policy_status"] == "unverified"
            assert p["terms_of_use_status"] == "unverified"
            assert p["citation"]
            assert p["source_url"].startswith("https://")
            assert p["source_note"]
