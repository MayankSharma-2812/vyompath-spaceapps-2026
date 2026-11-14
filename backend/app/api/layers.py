"""Map-layer catalogue endpoint.

GET /api/layers — returns the available base-map and overlay layers.

Layer resolution order:
  1. ``data/layers.json`` in the repository root (Shyam's manifest).
  2. Hard-coded synthetic fallback catalogue (for frontend dev).

If ``data/layers.json`` exists it is read and validated.  If it is
malformed the endpoint returns an error rather than silently falling back.
Do NOT modify Shyam's data files from this module.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["layers"])
_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Locate repository root relative to *this* source file so the path is
# independent of the process working directory.
# backend/app/api/layers.py  →  repo root is ../../../..
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAYERS_JSON = _REPO_ROOT / "data" / "layers.json"

# ---------------------------------------------------------------------------
# Synthetic fallback catalogue
# ---------------------------------------------------------------------------
# These entries are illustrative placeholders so the frontend can render
# a layer-switcher during development.  They describe real NASA/community
# datasets that *could* back these layers, but VyomPath has NOT verified
# connectivity, tile availability or provenance of any WMTS/WMS endpoint.
# ---------------------------------------------------------------------------
_SYNTHETIC_LAYERS: list[dict] = [
    {
        "id": "mola-colorhillshade",
        "name": "MOLA Colorized Hillshade",
        "type": "base",
        "source": "NASA/USGS (illustrative — not verified)",
        "description": (
            "Mars Orbiter Laser Altimeter global colorized hillshade. "
            "This entry is a synthetic placeholder; no live tile endpoint "
            "has been configured or tested."
        ),
    },
    {
        "id": "themis-daytime-ir",
        "name": "THEMIS Daytime IR",
        "type": "overlay",
        "source": "ASU/NASA (illustrative — not verified)",
        "description": (
            "Thermal Emission Imaging System daytime infrared mosaic. "
            "Synthetic placeholder for frontend development."
        ),
    },
    {
        "id": "ctx-mosaic",
        "name": "CTX Global Mosaic",
        "type": "overlay",
        "source": "Murray Lab / Caltech (illustrative — not verified)",
        "description": (
            "Context Camera ~6 m/px global mosaic. "
            "Synthetic placeholder for frontend development."
        ),
    },
]


def _load_layers_json() -> list[dict] | None:
    """Attempt to load and validate ``data/layers.json``.

    Returns the parsed list on success, or ``None`` if the file does not
    exist.  Raises :class:`HTTPException` if the file exists but is
    malformed, so we never silently ignore Shyam's work.
    """
    if not _LAYERS_JSON.is_file():
        return None

    _log.info("Loading layer manifest from %s", _LAYERS_JSON)
    try:
        raw = _LAYERS_JSON.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        _log.error("Failed to parse %s: %s", _LAYERS_JSON, exc)
        raise HTTPException(
            status_code=502,
            detail=(
                f"Layer manifest at {_LAYERS_JSON.relative_to(_REPO_ROOT)} "
                f"exists but could not be parsed: {exc}"
            ),
        ) from exc

    # Accept either a bare list or {"layers": [...]}.
    if isinstance(data, list):
        layers = data
    elif isinstance(data, dict) and "layers" in data:
        layers = data["layers"]
    else:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Layer manifest at {_LAYERS_JSON.relative_to(_REPO_ROOT)} "
                "has an unrecognised structure.  Expected a JSON array or "
                'an object with a "layers" key.'
            ),
        )

    # Minimal structural check — each entry must have at least an id.
    for idx, entry in enumerate(layers):
        if not isinstance(entry, dict) or "id" not in entry:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Layer manifest entry {idx} is missing a required "
                    '"id" field.'
                ),
            )

    return layers


@router.get(
    "/layers",
    summary="List available map layers",
    response_description="Catalogue of base-map and overlay layers.",
)
async def list_layers() -> dict:
    """Return every registered map layer.

    If ``data/layers.json`` exists (Shyam's manifest) it is used as the
    authoritative source.  Otherwise a synthetic fallback catalogue is
    returned so that the frontend can proceed with development.

    The ``source`` field in the response always indicates whether the
    data is from the manifest file or the synthetic fallback.
    """
    manifest_layers = _load_layers_json()

    if manifest_layers is not None:
        return {
            "count": len(manifest_layers),
            "layers": manifest_layers,
            "source": "data/layers.json",
        }

    return {
        "count": len(_SYNTHETIC_LAYERS),
        "layers": _SYNTHETIC_LAYERS,
        "source": "synthetic_fallback",
        "note": (
            "data/layers.json was not found.  These layers are synthetic "
            "placeholders for frontend development.  No WMTS/WMS endpoints "
            "have been verified."
        ),
    }
