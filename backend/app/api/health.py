"""Health-check endpoint.

GET /api/health — lightweight liveness probe.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_VERSION = "0.1.0-day1"


@router.get(
    "/health",
    summary="Health check",
    response_description="Service status with version tag and mode indicator.",
)
async def health_check() -> dict:
    """Return basic liveness information.

    Exposes the operational mode based on whether a valid HiRISE DTM raster
    is mounted via VYOMPATH_DEM_PATH. Consumers use this to distinguish
    real DTM terrain engine execution from development/mock fallback mode.
    """
    dem_path = os.environ.get("VYOMPATH_DEM_PATH")
    is_live = bool(dem_path and os.path.isfile(dem_path))
    mode = "production/live" if is_live else "development/mock"
    notes = (
        "Real Jezero HiRISE stereo DTM is mounted and active via VYOMPATH_DEM_PATH."
        if is_live
        else (
            "All route-analysis and layer data is synthetic or illustrative. "
            "No real HiRISE/MOLA raster sampling is performed in this mode."
        )
    )

    return {
        "status": "ok",
        "service": "vyompath-api",
        "version": _VERSION,
        "mode": mode,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }
