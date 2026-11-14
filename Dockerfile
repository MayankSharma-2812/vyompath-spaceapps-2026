# ──────────────────────────────────────────────────────────────
# VyomPath Backend — Production Container Image
# ──────────────────────────────────────────────────────────────
# Build:  docker build -t vyompath-api .
# Run:    docker run -p 8000:8000 vyompath-api
#
# The application starts WITHOUT any real HiRISE / MOLA DTM.
# It operates in development/mock mode by default.
#
# Configuration via environment variables:
#   CORS_ORIGINS  — comma-separated allowed origins
#   PORT          — listening port (default 8000)
#
# No secrets or credentials are baked into this image.
# Pass runtime configuration via environment variables.
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install minimal system runtime library required by rasterio manylinux wheel
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/*

# ── Dependencies (cached layer) ──────────────────────────────
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# ── Application code ─────────────────────────────────────────
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/

# ── Data directory ───────────────────────────────────────────
# Ensure /app/data exists for layer manifests or runtime mounts.
# If no manifest is provided, the API uses its synthetic fallback.
RUN mkdir -p /app/data

# ── Runtime ──────────────────────────────────────────────────
# PORT is read by the CMD below.
# Cloud platforms (Cloud Run, Railway, Render) set PORT automatically.
ENV PORT=8000

EXPOSE ${PORT}

# Listen on 0.0.0.0 so the container is reachable from outside.
# --workers 1 is safe for Day 1; scale up for production load.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT} --workers 1"]
