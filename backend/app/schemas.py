"""VyomPath Pydantic v2 contracts.

These schemas define the public API contract for VyomPath route analysis.
Keep them stable — frontend and other services depend on these shapes.

Owner: Mayank (Backend & Cloud Systems Lead)
Terrain sampling:  stubbed — Pranav owns the terrain service.
Science-POI buffering: stubbed — Dheer owns the science service.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_ROUTE_DISTANCE_M: float = 25_000.0


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------

class Coordinate(BaseModel):
    """A single geographic point on Mars.

    Longitude is east-positive, latitude is planetocentric.
    """

    lon: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Longitude in degrees, east-positive.",
    )
    lat: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Latitude in planetocentric degrees.",
    )


# ---------------------------------------------------------------------------
# Route analysis request
# ---------------------------------------------------------------------------

class RouteAnalysisRequest(BaseModel):
    """Payload submitted to POST /api/routes/analyze."""

    route_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Client-assigned identifier for this route.",
    )
    coordinates: list[Coordinate] = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Ordered waypoints defining the route (2 to 500, inclusive).",
    )
    buffer_distance_m: float = Field(
        default=250.0,
        ge=50.0,
        le=2000.0,
        description="Lateral buffer in metres for nearby-POI search.",
    )

    @model_validator(mode="after")
    def validate_route_length(self) -> RouteAnalysisRequest:
        """Reject routes exceeding the maximum permitted 25,000 metre cumulative length."""
        from backend.app.services.coords import haversine_m
        coords = self.coordinates
        total_dist = 0.0
        for i in range(len(coords) - 1):
            total_dist += float(haversine_m(coords[i].lon, coords[i].lat, coords[i + 1].lon, coords[i + 1].lat))
        if total_dist > MAX_ROUTE_DISTANCE_M + 1e-3:
            raise ValueError(
                f"Cumulative route distance ({total_dist:.1f} m) exceeds maximum permitted limit of 25,000.0 metres."
            )
        return self


# ---------------------------------------------------------------------------
# Route analysis response
# ---------------------------------------------------------------------------

class ElevationPoint(BaseModel):
    """A single sample on the elevation profile."""

    distance_m: float = Field(
        ...,
        ge=0.0,
        description="Distance along route from the start, in metres.",
    )
    elevation_m: Optional[float] = Field(
        default=None,
        description="Surface elevation at this distance in metres, or null for uncovered segments.",
    )


class NearbyPOI(BaseModel):
    """A point of interest found within the route buffer."""

    id: str
    name: str
    mission: str
    cross_track_m: float = Field(
        ...,
        description="Perpendicular distance from the route centreline.",
    )
    along_route_m: float = Field(
        ...,
        description="Distance along route to the nearest point.",
    )
    source_url: str = Field(
        ...,
        description="Authoritative URL for this POI.",
    )
    significance: str = Field(
        ...,
        description="Brief description of scientific or operational significance.",
    )
    source_note: Optional[str] = Field(
        default=None,
        description="Verbatim telemetry note from source (e.g. MMGIS) preserved separately from authored descriptions.",
    )


class RouteAnalysisResponse(BaseModel):
    """Full result returned by POST /api/routes/analyze."""

    route_id: str
    total_distance_m: float = Field(
        ...,
        ge=0.0,
        description="Great-circle distance of the full route, in metres.",
    )

    # Elevation profile
    elevation_profile: list[ElevationPoint] = Field(
        default_factory=list,
        description="Sampled elevation points along the route.",
    )
    total_gain_m: float = Field(
        default=0.0,
        ge=0.0,
        description="Cumulative positive elevation change, in metres.",
    )
    total_loss_m: float = Field(
        default=0.0,
        ge=0.0,
        description="Cumulative negative elevation change (positive number), in metres.",
    )
    max_slope_deg: float = Field(
        default=0.0,
        ge=0.0,
        description="Steepest slope encountered, in degrees.",
    )
    slope_window_m: float = Field(
        default=50.0,
        gt=0.0,
        description="Window length used for slope calculation, in metres.",
    )

    # DTM metadata
    dtm_source: str = Field(
        default="stub",
        description="Identity of the DTM data source (e.g. MOLA, HRSC).",
    )
    dtm_posting_m: float = Field(
        default=0.0,
        ge=0.0,
        description="Native DTM posting / ground sample distance, in metres.",
    )
    coverage_status: Literal["complete", "partial_gap", "out_of_bounds"] = Field(
        default="complete",
        description="Whether the DTM fully covers the requested route.",
    )

    # Science POIs
    nearby_pois: list[NearbyPOI] = Field(
        default_factory=list,
        description="Points of interest within the buffer distance.",
    )

    # Transparency
    limitations: list[str] = Field(
        default_factory=list,
        description="Known caveats, data gaps, or approximations.",
    )
