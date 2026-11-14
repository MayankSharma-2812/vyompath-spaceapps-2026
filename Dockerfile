# ──────────────────────────────────────────────────────────────
# VyomPath Backend — Production Container Image
# ──────────────────────────────────────────────────────────────
# Multi-container orchestrated via docker-compose.yml
# Standalone run: docker run -p 8000:8000 vyompath-backend
#
# Configuration via environment variables:
#   CORS_ORIGINS      — comma-separated allowed origins
#   PORT              — listening port (default 8000)
#   VYOMPATH_DEM_PATH — path to real HiRISE DTM GeoTIFF
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install runtime libraries required by rasterio and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libexpat1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Dependencies (cached layer) ──────────────────────────────
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# ── Application code & default metadata ──────────────────────
COPY backend/ /app/backend/
COPY data/ /app/data/
COPY scripts/ /app/scripts/

# Create non-root user and set permissions
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health probe
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT:-8000}/api/health || exit 1

EXPOSE 8000

# Run with 2 workers for production concurrency
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"]
