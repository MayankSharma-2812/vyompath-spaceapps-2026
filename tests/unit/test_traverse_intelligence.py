"""Unit tests for Mission-Aware Traverse Intelligence Service.

Covers:
  1. Route A wins when its metrics match objective.
  2. Route B wins when its metrics match objective.
  3. Objective switching flips the recommendation.
  4. Missing DTM coverage impacts data confidence score.
  5. NoData/None values are never treated as valid flat terrain.
  6. Mock data is flagged with prominent disclaimers and not treated as real DTM.
  7. Insufficient data produces honest single-route or empty state.
  8. Equal/nearly equal routes report tie/near parity without exaggeration.
"""

import pytest
from backend.app.services.traverse_intelligence import (
    extract_route_metrics,
    compute_subscores,
    compute_route_evaluation,
    evaluate_traverse_intelligence,
    OBJECTIVE_WEIGHTS,
)


def _make_dummy_route(
    route_id: str = "route-1",
    dist_m: float = 1000.0,
    gain_m: float = 20.0,
    loss_m: float = 15.0,
    max_slope_deg: float = 8.0,
    coverage_status: str = "complete",
    is_mock: bool = False,
    profile_elevations: list[float | None] = None,
) -> dict:
    if profile_elevations is None:
        # 10 nominal samples, slope gentle
        profile = [{"distance_m": i * (dist_m / 10), "elevation_m": -2500.0 + (i * 2.0)} for i in range(10)]
    else:
        profile = [{"distance_m": i * (dist_m / len(profile_elevations)), "elevation_m": z} for i, z in enumerate(profile_elevations)]

    return {
        "route_id": route_id,
        "total_distance_m": dist_m,
        "total_gain_m": gain_m,
        "total_loss_m": loss_m,
        "max_slope_deg": max_slope_deg,
        "coverage_status": coverage_status,
        "dtm_source": "USGS/NASA HiRISE" if not is_mock else "synthetic/mock",
        "dtm_posting_m": 1.0 if not is_mock else 0.0,
        "is_mock": is_mock,
        "elevation_profile": profile,
    }


class TestTraverseIntelligence:
    def test_route_a_wins_slope_conscious(self):
        """Route A with very gentle slopes beats Route B with steep terrain."""
        route_a = _make_dummy_route("route-a", dist_m=1200.0, gain_m=10.0, max_slope_deg=5.0)
        route_b = _make_dummy_route("route-b", dist_m=1000.0, gain_m=80.0, max_slope_deg=22.0)

        result = evaluate_traverse_intelligence(route_a, route_b, objective="slope_conscious")
        assert result.recommendation == "route_a"
        assert result.route_a.overall_score > result.route_b.overall_score
        assert "Route A is recommended" in result.summary_verdict
        assert "lower maximum slope" in result.evidence_explanation

    def test_route_b_wins_energy_efficient(self):
        """Route B with much shorter distance and minimal climb beats Route A on energy."""
        # Route A: 3500m, 120m climb, 8 deg slope
        route_a = _make_dummy_route("route-a", dist_m=3500.0, gain_m=120.0, max_slope_deg=8.0)
        # Route B: 800m, 10m climb, 12 deg slope
        route_b = _make_dummy_route("route-b", dist_m=800.0, gain_m=10.0, max_slope_deg=12.0)

        result = evaluate_traverse_intelligence(route_a, route_b, objective="energy_efficient")
        assert result.recommendation == "route_b"
        assert result.route_b.overall_score > result.route_a.overall_score
        assert "Route B is recommended" in result.summary_verdict
        assert "shorter traverse distance" in result.evidence_explanation

    def test_objective_switch_flips_winner(self):
        """A route with gentle slope but longer distance wins slope objective, while shorter route wins energy."""
        # Route A: Long & Ultra-Gentle (max slope 2.0°, 0% steep)
        route_a = _make_dummy_route(
            "route-a-gentle-long",
            dist_m=2200.0,
            gain_m=30.0,
            max_slope_deg=2.0,
            profile_elevations=[-2000.0 + i * 0.5 for i in range(20)],
        )
        # Route B: Short & Moderate Incline (500m, but 16.0° max slope)
        route_b = _make_dummy_route(
            "route-b-short-steep",
            dist_m=500.0,
            gain_m=8.0,
            max_slope_deg=16.0,
            profile_elevations=[-2000.0 + (i * 1.5 if i < 5 else -i * 1.5) for i in range(10)],
        )

        res_slope = evaluate_traverse_intelligence(route_a, route_b, objective="slope_conscious")
        assert res_slope.recommendation == "route_a"

        res_energy = evaluate_traverse_intelligence(route_a, route_b, objective="energy_efficient")
        assert res_energy.recommendation == "route_b"

    def test_missing_dtm_coverage_penalizes_data_confidence(self):
        """Route with complete coverage wins data confidence over route with partial gap or out of bounds."""
        route_complete = _make_dummy_route("complete-cov", coverage_status="complete")
        route_partial = _make_dummy_route(
            "partial-cov",
            coverage_status="partial_gap",
            profile_elevations=[-2500.0, -2501.0, None, None, None, -2502.0],
        )

        result = evaluate_traverse_intelligence(route_complete, route_partial, objective="data_confidence")
        assert result.recommendation == "route_a"
        assert result.route_a.score_breakdown.confidence_score > result.route_b.score_breakdown.confidence_score
        assert "verified DTM coverage" in result.evidence_explanation

    def test_nodata_not_interpreted_as_zero_elevation(self):
        """NoData (None) values must not cause artificial 2500m cliff jumps to 0.0 elevation."""
        elevations = [-2500.0, -2502.0, None, None, -2505.0]
        metrics = extract_route_metrics(_make_dummy_route("nodata-test", profile_elevations=elevations))

        assert metrics.valid_points_count == 3
        assert metrics.total_points_count == 5
        assert metrics.coverage_ratio == 0.6
        # If None was treated as 0.0, slope would be > 80 degrees!
        assert metrics.max_slope_deg < 45.0

    def test_mock_data_explicitly_flagged(self):
        """Mock analysis returns explicit transparency disclaimers."""
        route_mock = _make_dummy_route("mock-1", is_mock=True, coverage_status="not_applicable")
        result = evaluate_traverse_intelligence(route_mock, None, objective="slope_conscious")

        assert any("DEMONSTRATION MODE" in d for d in result.scientific_disclaimers)
        assert result.route_a.metrics.is_mock is True
        assert any("synthetic mock" in d.lower() for d in result.route_a.disadvantages)

    def test_insufficient_data_single_route(self):
        """When only Route A exists, single_route status is returned without fake comparison."""
        route_a = _make_dummy_route("single-route")
        result = evaluate_traverse_intelligence(route_a, None, objective="slope_conscious")

        assert result.recommendation == "single_route"
        assert result.route_a is not None
        assert result.route_b is None
        assert result.score_delta_b_minus_a is None
        assert "Single-route evaluation complete" in result.evidence_explanation

    def test_insufficient_data_empty(self):
        """When no routes are provided, an honest empty evaluation is returned."""
        result = evaluate_traverse_intelligence(None, None, objective="slope_conscious")
        assert result.recommendation == "single_route"
        assert "No route available" in result.summary_verdict
        assert result.route_a is None

    def test_near_equal_routes_report_tie(self):
        """Two nearly identical routes produce a tie with near-parity verdict."""
        route_a = _make_dummy_route("route-a", dist_m=1000.0, gain_m=20.0, max_slope_deg=8.0)
        route_b = _make_dummy_route("route-b", dist_m=1010.0, gain_m=20.5, max_slope_deg=8.1)

        result = evaluate_traverse_intelligence(route_a, route_b, objective="slope_conscious")
        assert result.recommendation == "tie"
        assert abs(result.score_delta_b_minus_a) < 2.0
        assert "near-parity" in result.summary_verdict
