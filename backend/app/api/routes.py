"""Route-analysis endpoint.

POST /api/routes/analyze — accepts a list of waypoints and returns
terrain / POI analysis for the route.

IMPORTANT — service boundaries:
  • Terrain sampling  → Pranav's terrain service (stubbed here).
  • Science-POI search → Dheer's science service (stubbed here).
  • Map rendering      → Arya's frontend feature (not touched here).
  • Route dashboard    → Kumkum's frontend feature (not touched here).

Mock orchestration (synthetic elevation, illustrative metrics) lives in
this module.  It is owned by Mayank and will be replaced when Pranav's
terrain service and Dheer's science service are integrated.
"""

from __future__ import annotations

import math

from fastapi import APIRouter

from backend.app.schemas import (
    Coordinate,
    ElevationPoint,
    RouteAnalysisRequest,
    RouteAnalysisResponse,
)

router = APIRouter(tags=["routes"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MARS_RADIUS_M: float = 3_389_500.0  # IAU 2015 mean radius


# ---------------------------------------------------------------------------
# Pure-geometry helpers (no external service calls)
# ---------------------------------------------------------------------------

def _haversine_m(a: Coordinate, b: Coordinate) -> float:
    """Great-circle distance on Mars between two coordinates, in metres."""
    lon1, lat1 = math.radians(a.lon), math.radians(a.lat)
    lon2, lat2 = math.radians(b.lon), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * _MARS_RADIUS_M * math.asin(math.sqrt(h))


def _segment_distances(coords: list[Coordinate]) -> list[float]:
    """Return the haversine length of each consecutive segment."""
    return [
        _haversine_m(coords[i], coords[i + 1])
        for i in range(len(coords) - 1)
    ]


def _total_distance(coords: list[Coordinate]) -> float:
    """Sum of consecutive haversine segments."""
    return sum(_segment_distances(coords))


# ---------------------------------------------------------------------------
# Deterministic synthetic elevation generator
# ---------------------------------------------------------------------------
# This produces a repeatable, smooth sine-wave profile so the frontend
# can render a plausible elevation chart.  The wave parameters are derived
# from the route's total distance — NOT from randomness — so the same
# input always yields the same output.
#
# The amplitude and wavelength are chosen to be visually plausible for
# Martian terrain without claiming to represent any real surface.
# ---------------------------------------------------------------------------

_SAMPLE_SPACING_M: float = 50.0    # target spacing between profile samples
_MAX_SAMPLES: int = 500            # cap to keep payloads reasonable
_BASE_ELEVATION_M: float = -4000.0  # roughly Martian datum (MOLA geoid)
_WAVE_AMPLITUDE_M: float = 120.0    # half-height of the synthetic wave
_WAVELENGTH_FACTOR: float = 6.0     # number of full sine cycles across route


def _synthetic_elevation_profile(
    total_distance_m: float,
) -> list[ElevationPoint]:
    """Generate a deterministic synthetic elevation profile.

    The profile is a sum of two sine waves (fundamental + harmonic) to
    produce a mildly interesting shape that is still fully deterministic.

    Returns at least 2 sample points, even for very short routes.
    """
    if total_distance_m <= 0:
        return [
            ElevationPoint(distance_m=0.0, elevation_m=_BASE_ELEVATION_M),
        ]

    n = max(2, min(int(total_distance_m / _SAMPLE_SPACING_M) + 1, _MAX_SAMPLES))
    step = total_distance_m / (n - 1)

    # Two sine components for a richer shape.
    omega1 = 2.0 * math.pi * _WAVELENGTH_FACTOR / total_distance_m
    omega2 = omega1 * 2.3  # incommensurate harmonic

    profile: list[ElevationPoint] = []
    for i in range(n):
        d = i * step
        elev = (
            _BASE_ELEVATION_M
            + _WAVE_AMPLITUDE_M * math.sin(omega1 * d)
            + (_WAVE_AMPLITUDE_M * 0.35) * math.sin(omega2 * d)
        )
        profile.append(
            ElevationPoint(
                distance_m=round(d, 2),
                elevation_m=round(elev, 2),
            )
        )

    return profile


# ---------------------------------------------------------------------------
# Deterministic metric derivation (internally consistent with profile)
# ---------------------------------------------------------------------------

def _derive_metrics(
    profile: list[ElevationPoint],
    slope_window_m: float,
) -> dict:
    """Compute gain, loss, and max slope from the synthetic profile.

    All values are derived directly from the profile so they are
    guaranteed to be internally consistent.
    """
    total_gain = 0.0
    total_loss = 0.0
    max_slope_deg = 0.0

    for i in range(1, len(profile)):
        delta_d = profile[i].distance_m - profile[i - 1].distance_m
        delta_e = profile[i].elevation_m - profile[i - 1].elevation_m

        if delta_e > 0:
            total_gain += delta_e
        else:
            total_loss += abs(delta_e)

        if delta_d > 0:
            slope_rad = math.atan2(abs(delta_e), delta_d)
            slope_deg = math.degrees(slope_rad)
            if slope_deg > max_slope_deg:
                max_slope_deg = slope_deg

    return {
        "total_gain_m": round(total_gain, 2),
        "total_loss_m": round(total_loss, 2),
        "max_slope_deg": round(max_slope_deg, 2),
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/routes/analyze",
    summary="Analyse a Martian route",
    response_model=RouteAnalysisResponse,
    response_description="Terrain and POI analysis for the submitted route.",
)
async def analyze_route(body: RouteAnalysisRequest) -> RouteAnalysisResponse:
    """Accept waypoints and return route analysis.

    **Current behaviour (development / mock mode):**

    - Great-circle distance is computed correctly using the haversine
      formula with the IAU 2015 Mars mean radius (3 389 500 m).
    - The elevation profile is a deterministic synthetic sine-wave.
      No real HiRISE or MOLA raster sampling takes place.
    - Gain, loss and slope metrics are derived from the synthetic
      profile and are internally consistent with it, but do NOT
      represent real Martian terrain.
    - No science POIs are returned.  The science-POI service is owned
      by Dheer; no fake "verified" points are fabricated.
    - The ``limitations`` field explicitly lists every caveat.

    **Validation rules (enforced by Pydantic):**

    - ``coordinates`` must contain ≥ 2 points (a line needs two ends).
    - Each ``lon`` ∈ [-180, 180], ``lat`` ∈ [-90, 90].
    - ``buffer_distance_m`` ∈ [50, 2000].

    The response ``coverage_status`` is always ``"complete"`` in mock
    mode because the synthetic generator always covers the full route.
    Only the three documented values (``complete``, ``partial_gap``,
    ``out_of_bounds``) are ever returned.
    """
    total_dist = _total_distance(body.coordinates)

    slope_window_m = 50.0
    profile = _synthetic_elevation_profile(total_dist)
    metrics = _derive_metrics(profile, slope_window_m)

    limitations: list[str] = [
        (
            "MOCK DATA: Elevation profile is a deterministic synthetic "
            "sine-wave, not sampled from real DTM rasters.  No HiRISE "
            "or MOLA data was accessed."
        ),
        (
            "MOCK DATA: Gain, loss and slope metrics are derived from "
            "the synthetic profile.  They are internally consistent but "
            "do not represent actual Martian terrain."
        ),
        (
            "MOCK DATA: Nearby POIs are empty.  The science-POI service "
            "(owner: Dheer) is not yet integrated.  No fabricated science "
            "points are returned."
        ),
        (
            "MOCK DATA: Terrain service (owner: Pranav) is not yet "
            "integrated.  DTM source and posting are placeholders."
        ),
        (
            "This analysis is NOT scientifically validated and MUST NOT "
            "be used for mission-critical route planning."
        ),
    ]

    return RouteAnalysisResponse(
        route_id=body.route_id,
        total_distance_m=round(total_dist, 2),
        elevation_profile=profile,
        total_gain_m=metrics["total_gain_m"],
        total_loss_m=metrics["total_loss_m"],
        max_slope_deg=metrics["max_slope_deg"],
        slope_window_m=slope_window_m,
        dtm_source="synthetic/mock — no real DTM loaded",
        dtm_posting_m=0.0,
        coverage_status="complete",
        nearby_pois=[],
        limitations=limitations,
    )
