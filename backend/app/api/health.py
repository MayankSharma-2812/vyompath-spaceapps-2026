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

    This endpoint is intentionally simple and has no external dependencies
    so it can serve as a Kubernetes liveness probe.

    The ``mode`` field is always ``"development/mock"`` until real terrain
    and science services are integrated.  Consumers MUST NOT treat
    responses from other endpoints as scientifically validated while this
    flag reads ``"development/mock"``.
    """
    return {
        "status": "ok",
        "service": "vyompath-api",
        "version": _VERSION,
        "mode": "development/mock",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "All route-analysis and layer data is synthetic or illustrative. "
            "No real HiRISE/MOLA raster sampling is performed in this mode."
        ),
    }
