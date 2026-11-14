"""Health-check endpoint.

GET /api/health — lightweight liveness probe.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.services.terrain import is_dtm_available

router = APIRouter(tags=["health"])

_VERSION = "0.1.0-day1"


@router.get(
    "/health",
    summary="Health check",
    response_description="Service status with version tag and mode indicator.",
)
async def health_check() -> dict:
    """Return basic liveness information.

    Exposes the operational mode based on whether a valid, readable HiRISE DTM raster
    is accessible via VYOMPATH_DEM_PATH. Consumers use this to distinguish
    real DTM terrain engine execution from development/mock fallback mode.
    """
    dtm_accessible = is_dtm_available()
    mode = "production/live" if dtm_accessible else "development/mock"
    analysis_mode = "real_dtm" if dtm_accessible else "mock"
    notes = (
        "Real Jezero HiRISE stereo DTM is mounted, verified readable, and active via VYOMPATH_DEM_PATH."
        if dtm_accessible
        else (
            "Demonstration mode active. All route-analysis elevation and slope values "
            "are synthetic illustrative examples. No real HiRISE/MOLA raster sampling "
            "is performed in this mode."
        )
    )

    return {
        "status": "ok",
        "service": "vyompath-api",
        "version": _VERSION,
        "mode": mode,
        "analysis_mode": analysis_mode,
        "is_mock": not dtm_accessible,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": notes,
    }
