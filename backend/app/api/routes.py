"""Route-analysis endpoint.

POST /api/routes/analyze — accepts a list of waypoints and returns
terrain / POI analysis for the route.

When a real DTM is available via $VYOMPATH_DEM_PATH, real HiRISE Float32
elevation sampling, gap analysis, and multi-scale slope metrics are returned.
If the DTM is unavailable or unreadable, the endpoint cleanly falls back to
deterministic mock generation with explicit transparency caveats.
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
from backend.app.services.coords import MARS_RADIUS_M
from backend.app.services.terrain import route_distance_m, sample_route_dtm

router = APIRouter(tags=["routes"])


# ---------------------------------------------------------------------------
# Deterministic synthetic elevation generator (Mock Fallback Mode)
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
        if profile[i].elevation_m is None or profile[i - 1].elevation_m is None:
            continue
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

    When $VYOMPATH_DEM_PATH points to a valid GeoTIFF DTM raster, real Float32
    elevations are sampled using 4-neighbor bilinear interpolation, multi-scale
    along-track slopes (20m, 50m, 100m) are calculated, and true coverage status
    (complete, partial_gap, out_of_bounds) is returned.

    If $VYOMPATH_DEM_PATH is unset or unreadable, the endpoint safely falls back
    to deterministic synthetic mock curves with explicit caveat disclosures.
    """
    total_dist = route_distance_m(body.coordinates)
    slope_window_m = 50.0

    # 1. Attempt real DTM raster sampling
    real_terrain = sample_route_dtm(
        body.coordinates,
        step_m=5.0,
        slope_window_m=slope_window_m,
    )

    if real_terrain is not None:
        return RouteAnalysisResponse(
            route_id=body.route_id,
            total_distance_m=round(total_dist, 2),
            elevation_profile=real_terrain["elevation_profile"],
            total_gain_m=real_terrain["total_gain_m"],
            total_loss_m=real_terrain["total_loss_m"],
            max_slope_deg=real_terrain["max_slope_deg"],
            slope_window_m=real_terrain["slope_window_m"],
            dtm_source=real_terrain["dtm_source"],
            dtm_posting_m=real_terrain["dtm_posting_m"],
            coverage_status=real_terrain["coverage_status"],
            nearby_pois=[],
            limitations=real_terrain["limitations"],
            analysis_mode="real_dtm",
            is_mock=False,
        )

    # 2. Truthful Mock Fallback Mode
    profile = _synthetic_elevation_profile(total_dist)
    metrics = _derive_metrics(profile, slope_window_m)

    limitations: list[str] = [
        (
            "DEMONSTRATION MODE: Elevation and slope values shown are generated synthetic examples. "
            "They are not measurements from real Martian terrain and must not be used for mission planning."
        ),
        (
            "MOCK DATA: Elevation profile is a deterministic synthetic "
            "sine-wave, not sampled from real DTM rasters. No HiRISE "
            "or MOLA data was accessed."
        ),
        (
            "MOCK DATA: Gain, loss and slope metrics are derived from "
            "the synthetic profile. They are illustrative only and "
            "do not represent actual Martian terrain."
        ),
        (
            "COVERAGE: Not applicable in synthetic/mock mode. No geographic "
            "coverage calculation can be performed without a real terrain raster."
        ),
        (
            "MOCK DATA: Nearby POIs are empty. The science-POI service "
            "is not integrated in mock mode. No fabricated science points are returned."
        ),
        (
            "MOCK DATA: Terrain service is running in fallback mode "
            "because VYOMPATH_DEM_PATH is not configured, unreadable, or missing."
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
        coverage_status="not_applicable",
        nearby_pois=[],
        limitations=limitations,
        analysis_mode="mock",
        is_mock=True,
    )
