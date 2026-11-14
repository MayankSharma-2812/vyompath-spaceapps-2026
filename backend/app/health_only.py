"""VyomPath — Minimal Isolated Health-Check Entry Point.

Pre-Event Deployment Probe:
This isolated FastAPI application exposes strictly `GET /api/health` for
infrastructure, container networking, and DNS liveness verification.

All product routers (layers, route analysis, terrain services) and API
documentation endpoints (Swagger UI, ReDoc, OpenAPI schema JSON) are
completely omitted or disabled.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router

# ---------------------------------------------------------------------------
# Application: Isolated Liveness Probe (No docs, No OpenAPI schema)
# ---------------------------------------------------------------------------
app = FastAPI(
    title="VyomPath Health Probe",
    summary="Minimal health-check probe for container and DNS verification.",
    version="0.1.0-day1",
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
_origins = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", _default_origins).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — Strictly health probe only
# ---------------------------------------------------------------------------
app.include_router(health_router, prefix="/api")
