"""VyomPath — Martian Map API entry point.

Run locally with:
    uvicorn backend.app.main:app --reload --port 8000

OpenAPI docs available at http://localhost:8000/docs
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import health, layers, routes

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VyomPath API",
    summary="Martian route-planning and map-layer service for NAKSHATRA X.",
    version="0.1.0-day1",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS Configuration
# ---------------------------------------------------------------------------
# CORS_ORIGINS: comma-separated list of allowed origin URLs.
# Default includes the local Vite development servers.
# Rejects or safely handles empty values, trims whitespace, and ensures
# wildcard origins ('*') are never combined with allow_credentials=True.
DEFAULT_CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _resolve_cors_origins(raw: str | None) -> tuple[list[str], bool]:
    """Parse and sanitize CORS_ORIGINS environment variable.

    Returns:
        tuple[list[str], bool]: (sanitized_origins, allow_credentials)
    """
    if not raw or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS), True

    parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if not parsed:
        return list(DEFAULT_CORS_ORIGINS), True

    # Security rule: Wildcard origins ('*') must never be paired with allow_credentials=True
    has_wildcard = "*" in parsed
    allow_credentials = not has_wildcard
    return parsed, allow_credentials


_cors_origins, _cors_allow_credentials = _resolve_cors_origins(
    os.getenv("CORS_ORIGINS")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — all mounted under /api
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api")
app.include_router(layers.router, prefix="/api")
app.include_router(routes.router, prefix="/api")
