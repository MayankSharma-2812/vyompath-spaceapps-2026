#!/usr/bin/env bash
# =============================================================================
# VyomPath — One-Command Offline Demonstration Launcher
# Team NAKSHATRA X | NASA Space Apps Challenge 2026
#
# Launches the Uvicorn FastAPI backend and serves the compiled frontend client
# on local loopback without requiring active internet connectivity.
# Uses isolated process-group tracking for leak-free lifecycle management.
# =============================================================================

set -euo pipefail
set -m  # Enable job control to assign dedicated process group IDs (PGID = PID)

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================="
echo "  VYOMPATH OFFLINE DEMONSTRATION LAUNCHER"
echo "================================================================="
echo "Working directory: $ROOT_DIR"

# 1. Verify environment and prerequisites
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required but not installed." >&2
  exit 1
fi

BACKEND_PORT="${BACKEND_PORT:-${PORT:-8000}}"
FRONTEND_PORT="${FRONTEND_PORT:-4173}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"

# 2. Check for port occupancy before starting
check_port() {
  local port="$1"
  if (echo > "/dev/tcp/127.0.0.1/$port") >/dev/null 2>&1; then
    return 0  # port is occupied
  fi
  # Fallback check using python socket
  python3 -c "import socket; s = socket.socket(); s.settimeout(0.2); exit(0 if s.connect_ex(('127.0.0.1', int($port))) == 0 else 1)" >/dev/null 2>&1 && return 0 || return 1
}

check_health() {
  local port="$1"
  if command -v curl >/dev/null 2>&1; then
    curl -s "http://127.0.0.1:$port/api/health" 2>/dev/null | grep -q '"status":"ok"'
  else
    python3 -c "import urllib.request, json; res = json.loads(urllib.request.urlopen('http://127.0.0.1:$port/api/health', timeout=1).read()); exit(0 if res.get('status') == 'ok' else 1)" >/dev/null 2>&1
  fi
}

if check_port "$BACKEND_PORT"; then
  echo "ERROR: Port $BACKEND_PORT is already in use by another process." >&2
  echo "Please stop any existing service on port $BACKEND_PORT before launching." >&2
  exit 1
fi

if [ -d "frontend/dist" ] && command -v npm >/dev/null 2>&1; then
  if check_port "$FRONTEND_PORT"; then
    echo "ERROR: Port $FRONTEND_PORT is already in use by another process." >&2
    echo "Please stop any existing service on port $FRONTEND_PORT before launching." >&2
    exit 1
  fi
fi

# 3. Check for curated regional tile assets
TILE_DIR_FOUND=""
if [ -d "data/tiles" ] && [ "$(ls -A data/tiles 2>/dev/null)" ]; then
  TILE_DIR_FOUND="$(pwd)/data/tiles"
elif [ -d "tiles" ] && [ "$(ls -A tiles 2>/dev/null)" ]; then
  TILE_DIR_FOUND="$(pwd)/tiles"
elif [ -d "../tiles" ] && [ "$(ls -A ../tiles 2>/dev/null)" ]; then
  TILE_DIR_FOUND="$(cd ../tiles && pwd)"
fi

if [ -n "$TILE_DIR_FOUND" ]; then
  echo "Found offline regional tile assets at: $TILE_DIR_FOUND"
  if [ -d "frontend/dist" ] && [ ! -e "frontend/dist/tiles" ]; then
    if [ -d "$TILE_DIR_FOUND/tiles_aoi" ]; then
      ln -sfn "$TILE_DIR_FOUND/tiles_aoi" frontend/dist/tiles 2>/dev/null || cp -R "$TILE_DIR_FOUND/tiles_aoi" frontend/dist/tiles
    else
      ln -sfn "$TILE_DIR_FOUND" frontend/dist/tiles 2>/dev/null || cp -R "$TILE_DIR_FOUND" frontend/dist/tiles
    fi
    echo "Linked tile assets to frontend/dist/tiles for Vite preview."
  fi
else
  echo "NOTICE [TILE ASSET AVAILABILITY]:"
  echo "  Offline tile directory ('tiles/', 'data/tiles/', or '../tiles/') not detected in working tree."
  echo "  Basemap tiles must be extracted from 'vyompath-demo-bundle-v1.4.zip' or generated"
  echo "  via 'python3 scripts/build_regional_tiles.py' to render offline regional maps."
  echo "  Proceeding with mock route-analysis and layer API endpoints."
  echo "-----------------------------------------------------------------"
fi

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  # Disable traps during teardown to avoid recursion
  trap - EXIT INT TERM

  echo ""
  echo "Shutting down VyomPath offline launcher..."

  if [ -n "$FRONTEND_PID" ]; then
    # Terminate the frontend process group (npm + spawned vite/node children)
    kill -TERM -- "-$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi

  if [ -n "$BACKEND_PID" ]; then
    # Terminate the backend process group (uvicorn)
    kill -TERM -- "-$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi

  # Clean up ephemeral tile symlink in frontend/dist if created by this script
  if [ -L "frontend/dist/tiles" ]; then
    rm -f "frontend/dist/tiles" 2>/dev/null || true
  fi

  echo "Shutdown complete. All child processes terminated."
}

trap cleanup EXIT INT TERM

# 4. Launch backend process in its own process group
echo "Starting VyomPath API on http://$BACKEND_HOST:$BACKEND_PORT..."
export PORT="$BACKEND_PORT"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:5173,http://127.0.0.1:5173,http://localhost:$FRONTEND_PORT,http://127.0.0.1:$FRONTEND_PORT}"

python3 -m uvicorn backend.app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
BACKEND_PID=$!

# 5. Wait for backend health check probe
echo "Verifying API health probe..."
HEALTHY=0
for i in {1..20}; do
  if check_health "$BACKEND_PORT"; then
    HEALTHY=1
    echo "SUCCESS: VyomPath API is healthy and operational."
    break
  fi
  sleep 0.3
done

if [ "$HEALTHY" -ne 1 ]; then
  echo "ERROR: Backend health check failed to respond on http://127.0.0.1:$BACKEND_PORT/api/health within timeout." >&2
  echo "Check uvicorn logs or verify that port $BACKEND_PORT is available." >&2
  exit 1
fi

# 6. Launch frontend server in its own process group
if [ -d "frontend/dist" ] && [ -d "frontend/node_modules" ] && command -v npm >/dev/null 2>&1; then
  echo "Launching frontend client on http://$FRONTEND_HOST:$FRONTEND_PORT (Vite Preview)..."
  echo "Press Ctrl+C to terminate both backend and frontend."
  npm --prefix frontend run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" &
  FRONTEND_PID=$!
  wait "$FRONTEND_PID" 2>/dev/null || true
elif [ -d "frontend/dist" ]; then
  echo "Launching pre-compiled frontend client via Python static server on http://$FRONTEND_HOST:$FRONTEND_PORT..."
  echo "Press Ctrl+C to terminate both backend and frontend."
  python3 -m http.server "$FRONTEND_PORT" --bind "$FRONTEND_HOST" --directory frontend/dist &
  FRONTEND_PID=$!
  wait "$FRONTEND_PID" 2>/dev/null || true
elif command -v npm >/dev/null 2>&1; then
  FRONTEND_DEV_PORT=5173
  if check_port "$FRONTEND_DEV_PORT"; then
    echo "ERROR: Port $FRONTEND_DEV_PORT is already in use by another process." >&2
    exit 1
  fi
  echo "frontend/dist not found; launching Vite development server on http://127.0.0.1:$FRONTEND_DEV_PORT..."
  echo "Press Ctrl+C to terminate both backend and frontend."
  npm --prefix frontend run dev -- --host 127.0.0.1 --port "$FRONTEND_DEV_PORT" &
  FRONTEND_PID=$!
  wait "$FRONTEND_PID" 2>/dev/null || true
else
  echo "npm not detected. Backend API is active at http://127.0.0.1:$BACKEND_PORT."
  echo "Open http://127.0.0.1:$BACKEND_PORT/docs for Swagger interactive documentation."
  wait "$BACKEND_PID" 2>/dev/null || true
fi
