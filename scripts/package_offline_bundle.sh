#!/usr/bin/env bash
# =============================================================================
# VyomPath — Offline Distribution & USB Bundle Packager
# Team NAKSHATRA X | NASA Space Apps Challenge 2026
#
# Packages application source, regional tile assets, config templates, offline
# launch scripts, container descriptors, and cryptographic checksums for
# air-gapped evaluation and offline cross-machine handoff.
#
# Governed by Decision D1 (Strict Pre-Event Preparation Mode).
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Defaults
BUNDLE_VERSION="1.4.0"
OUTPUT_DIR="${REPO_ROOT}/dist/offline_bundle"
DEFAULT_TILE_SRC="/home/mayank-sharma/Hackathon/NASA/data/vyompath-demo-bundle-v1.4"
TILES_DIR=""
INCLUDE_TILES=0
INCLUDE_DOCKER=0
CREATE_ARCHIVE=1

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Options:
  -o, --output <DIR>       Destination directory for the offline bundle
                           (default: dist/offline_bundle)
  -v, --version <VER>      Bundle version string (default: 1.4.0)
  --tiles-dir <DIR>        Path to regional tile bundle source directory
                           (default checks: data/tiles or ${DEFAULT_TILE_SRC})
  --include-tiles          Include regional raster XYZ tiles in the bundle
  --include-docker         Export Docker container image archive (vyompath-api:latest)
  --no-archive             Skip generating .tar.gz bundle archive
  -h, --help               Display this help text and exit
EOF
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    -v|--version)
      BUNDLE_VERSION="$2"
      shift 2
      ;;
    --tiles-dir)
      TILES_DIR="$2"
      INCLUDE_TILES=1
      shift 2
      ;;
    --include-tiles)
      INCLUDE_TILES=1
      shift
      ;;
    --include-docker)
      INCLUDE_DOCKER=1
      shift
      ;;
    --no-archive)
      CREATE_ARCHIVE=0
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "ERROR: Unknown option '$1'" >&2
      usage
      ;;
  esac
done

echo "================================================================="
echo "  VYOMPATH OFFLINE BUNDLE PACKAGER (v${BUNDLE_VERSION})"
echo "================================================================="
echo "Repository Root: $REPO_ROOT"
echo "Target Output:   $OUTPUT_DIR"

# Ensure output directory is clean
STAGE_DIR="${OUTPUT_DIR}/vyompath-offline-v${BUNDLE_VERSION}"
rm -rf "$STAGE_DIR"
mkdir -p "$STAGE_DIR"

# 1. Create Git bundle for full versioned history and air-gapped checkout
echo "[1/7] Generating Git bundle (vyompath-repo.bundle)..."
git bundle create "${STAGE_DIR}/vyompath-repo.bundle" --all

# 2. Export clean working-tree source (excluding git metadata, untracked, secrets)
echo "[2/7] Exporting clean standalone source tree..."
mkdir -p "${STAGE_DIR}/source"
git archive HEAD | tar -x -C "${STAGE_DIR}/source"

# Copy pre-compiled frontend distribution if available
if [ -d "${REPO_ROOT}/frontend/dist" ]; then
  echo "      Attaching pre-compiled frontend production build..."
  mkdir -p "${STAGE_DIR}/source/frontend/dist"
  cp -R "${REPO_ROOT}/frontend/dist/." "${STAGE_DIR}/source/frontend/dist/"
fi

# Ensure launchers have execution permissions
chmod +x "${STAGE_DIR}/source/scripts/run_offline.sh" 2>/dev/null || true
chmod +x "${STAGE_DIR}/source/scripts/verify_terrain_g3_g4.py" 2>/dev/null || true
chmod +x "${STAGE_DIR}/source/tools/validate_data.py" 2>/dev/null || true

# 3. Package offline configuration templates
echo "[3/7] Copying environment templates and deployment descriptors..."
mkdir -p "${STAGE_DIR}/config"
cp "${REPO_ROOT}/.env.example" "${STAGE_DIR}/config/"
cp "${REPO_ROOT}/Dockerfile" "${STAGE_DIR}/config/"
cp "${REPO_ROOT}/.dockerignore" "${STAGE_DIR}/config/"
if [ -f "${REPO_ROOT}/docker-compose.yml" ]; then
  cp "${REPO_ROOT}/docker-compose.yml" "${STAGE_DIR}/config/"
fi

# 4. Handle regional map tiles
if [ "$INCLUDE_TILES" -eq 1 ]; then
  if [ -z "$TILES_DIR" ]; then
    if [ -d "${REPO_ROOT}/data/tiles" ] && [ "$(ls -A "${REPO_ROOT}/data/tiles" 2>/dev/null)" ]; then
      TILES_DIR="${REPO_ROOT}/data/tiles"
    elif [ -d "$DEFAULT_TILE_SRC" ]; then
      TILES_DIR="$DEFAULT_TILE_SRC"
    fi
  fi

  if [ -n "$TILES_DIR" ] && [ -d "$TILES_DIR" ]; then
    echo "[4/7] Packaging regional XYZ tiles from $TILES_DIR..."
    mkdir -p "${STAGE_DIR}/tiles"
    # Copy tiles_aoi and tiles_hillshade if present, or raw tiles
    if [ -d "${TILES_DIR}/tiles_aoi" ]; then
      echo "      Copying tiles_aoi and tiles_hillshade directories..."
      cp -R "${TILES_DIR}/tiles_aoi" "${STAGE_DIR}/tiles/"
      [ -d "${TILES_DIR}/tiles_hillshade" ] && cp -R "${TILES_DIR}/tiles_hillshade" "${STAGE_DIR}/tiles/"
      # Link into source tree so run_offline.sh and Vite preview immediately see them
      mkdir -p "${STAGE_DIR}/source/data"
      ln -sfn "../../tiles" "${STAGE_DIR}/source/data/tiles"
      if [ -d "${STAGE_DIR}/source/frontend/dist" ]; then
        ln -sfn "../../../tiles/tiles_aoi" "${STAGE_DIR}/source/frontend/dist/tiles"
      fi
    else
      cp -R "${TILES_DIR}/." "${STAGE_DIR}/tiles/"
      mkdir -p "${STAGE_DIR}/source/data"
      ln -sfn "../../tiles" "${STAGE_DIR}/source/data/tiles"
      if [ -d "${STAGE_DIR}/source/frontend/dist" ]; then
        ln -sfn "../../../tiles" "${STAGE_DIR}/source/frontend/dist/tiles"
      fi
    fi
  else
    echo "[4/7] WARNING: Tile directory '$TILES_DIR' not found; skipping tile packaging."
  fi
else
  echo "[4/7] Skipping raster tile packaging (use --include-tiles to bundle)."
fi

# 5. Handle Docker container image archive
if [ "$INCLUDE_DOCKER" -eq 1 ]; then
  if command -v docker >/dev/null 2>&1; then
    echo "[5/7] Exporting Docker image archive (vyompath-api-docker.tar.gz)..."
    if ! docker image inspect vyompath-api:latest >/dev/null 2>&1; then
      echo "      Building vyompath-api:latest container..."
      docker build -t vyompath-api:latest "$REPO_ROOT"
    fi
    docker save vyompath-api:latest | gzip > "${STAGE_DIR}/vyompath-api-docker.tar.gz"
  else
    echo "[5/7] WARNING: docker command not available; skipping container export."
  fi
else
  echo "[5/7] Skipping Docker image export (use --include-docker to bundle)."
fi

# 6. Generate comprehensive offline README
echo "[6/7] Writing offline demonstration guide (README.md)..."
cat <<'README_EOF' > "${STAGE_DIR}/README.md"
# VyomPath — Offline Evaluation & Demonstration Package
**Team NAKSHATRA X | NASA Space Apps Challenge 2026**

This self-contained bundle provides all application code, pre-compiled frontend assets, test fixtures, and scripts required to run and evaluate VyomPath in an air-gapped, offline environment.

---

## 1. Package Inventory
- `vyompath-repo.bundle`: Complete Git repository bundle for offline cloning.
- `source/`: Clean standalone application source tree with pre-compiled `frontend/dist/`.
- `config/`: Configuration templates (`.env.example`, `Dockerfile`, `.dockerignore`).
- `tiles/`: Regional pre-rendered XYZ slippy tiles (if packaged).
- `SHA256SUMS`: Cryptographic checksums of all bundled assets.

---

## 2. Quick Start: Native Execution (Recommended)
Prerequisites: Python 3.10+ and Node.js 18+ (if rebuilding frontend).

```bash
# 1. Enter the extracted source directory
cd source

# 2. Launch the unified offline stack
./scripts/run_offline.sh

# 3. Access the application:
#    Frontend UI:  http://127.0.0.1:4173
#    Backend Docs: http://127.0.0.1:8000/docs
#    Health Probe: http://127.0.0.1:8000/api/health
```
Press `Ctrl+C` in the terminal to terminate both frontend and backend processes cleanly.

---

## 3. Alternative: Unpack Full Git Repository
To restore the complete git repository with commit history:
```bash
git clone vyompath-repo.bundle vyompath-restored
cd vyompath-restored
```

---

## 4. Containerized Execution (Optional)
If `vyompath-api-docker.tar.gz` is present:
```bash
docker load < vyompath-api-docker.tar.gz
docker run --rm -d --name vyompath -p 8000:8000 vyompath-api:latest
curl -s http://127.0.0.1:8000/api/health
```

---

## 5. Verification Commands
```bash
cd source
pytest tests/
python3 scripts/verify_terrain_g3_g4.py
python3 tools/validate_data.py
```
README_EOF

# 7. Generate cryptographic checksums
echo "[7/7] Generating SHA256SUMS..."
(
  cd "$STAGE_DIR"
  find . -type f ! -name "SHA256SUMS" | sort | xargs sha256sum > SHA256SUMS
)

# Optional tarball archive creation
if [ "$CREATE_ARCHIVE" -eq 1 ]; then
  ARCHIVE_NAME="vyompath-offline-v${BUNDLE_VERSION}.tar.gz"
  echo "Compressing bundle into ${OUTPUT_DIR}/${ARCHIVE_NAME}..."
  tar -czf "${OUTPUT_DIR}/${ARCHIVE_NAME}" -C "$OUTPUT_DIR" "vyompath-offline-v${BUNDLE_VERSION}"
  (
    cd "$OUTPUT_DIR"
    sha256sum "$ARCHIVE_NAME" > "${ARCHIVE_NAME}.sha256"
  )
  echo "Created archive: ${OUTPUT_DIR}/${ARCHIVE_NAME}"
fi

echo "================================================================="
echo "  OFFLINE BUNDLE CREATION COMPLETE"
echo "  Staging Directory: ${STAGE_DIR}"
[ "$CREATE_ARCHIVE" -eq 1 ] && echo "  Archive:           ${OUTPUT_DIR}/vyompath-offline-v${BUNDLE_VERSION}.tar.gz"
echo "================================================================="
