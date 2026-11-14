"""Standalone Provenance-Aware Data Acquisition Script.

Designed for VyomPath to record verified HTTP response telemetry and eliminate
historical timestamp ambiguities on future data retrievals.
"""

import sys
import json
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


def acquire_telemetry_with_provenance(
    url: str,
    output_path: Path,
    dry_run: bool = True
) -> dict:
    """Acquires data from a remote URL while recording complete provenance telemetry.

    Args:
        url: The primary source URL to fetch.
        output_path: Local filesystem destination path.
        dry_run: If True, simulates acquisition without performing network I/O.

    Returns:
        Dictionary containing verified provenance metadata.
    """
    if dry_run:
        req_start = datetime.now(timezone.utc).isoformat()
        resp_recv = datetime.now(timezone.utc).isoformat()
        return {
            "mode": "DRY_RUN (No network I/O performed)",
            "source_url": url,
            "request_start_utc": req_start,
            "response_received_utc": resp_recv,
            "http_status": None,
            "response_headers": {},
            "payload_sha256": None,
            "filesystem_metadata": None,
            "provenance_class": "DRY_RUN_SPECIFICATION",
            "provenance_description": "Simulated acquisition specification; ready for authorized network execution."
        }

    # Timezone-aware UTC timestamp before request dispatch
    request_start_utc = datetime.now(timezone.utc)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "VyomPath-Telemetry-Acquisition/2.0 (Mars Rover Route Planning)"}
    )

    with urllib.request.urlopen(req, timeout=30.0) as resp:
        # Timezone-aware UTC timestamp immediately upon response arrival
        response_received_utc = datetime.now(timezone.utc)
        payload = resp.read()
        http_status = resp.status
        headers = dict(resp.headers)

    # Compute cryptographic hash of exact downloaded bytes
    payload_sha256 = hashlib.sha256(payload).hexdigest().upper()

    # Write payload to destination
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)

    # Read filesystem metadata immediately following write
    st = output_path.stat()
    fs_ctime_utc = datetime.fromtimestamp(st.st_ctime, tz=timezone.utc).isoformat()
    fs_mtime_utc = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()

    provenance_record = {
        "source_url": url,
        "request_start_utc": request_start_utc.isoformat(),
        "response_received_utc": response_received_utc.isoformat(),
        "http_status": http_status,
        "response_headers": {
            "Date": headers.get("Date"),
            "Last-Modified": headers.get("Last-Modified"),
            "ETag": headers.get("ETag"),
            "Content-Length": headers.get("Content-Length"),
            "Content-Type": headers.get("Content-Type")
        },
        "payload_sha256": payload_sha256,
        "filesystem_metadata": {
            "file_size_bytes": st.st_size,
            "st_ctime_utc": fs_ctime_utc,
            "st_mtime_utc": fs_mtime_utc
        },
        "provenance_class": "DIRECT_HTTP_SERVER_TELEMETRY",
        "provenance_description": (
            "Verified direct HTTP server network telemetry. request_start_utc and "
            "response_received_utc are recorded with timezone-aware UTC timestamps. "
            "Server Date header provides independent upstream verification."
        )
    }

    # Save sidecar provenance record
    meta_path = output_path.with_suffix(output_path.suffix + ".provenance.json")
    meta_path.write_text(json.dumps(provenance_record, indent=2), encoding="utf-8")

    return provenance_record


if __name__ == "__main__":
    test_url = "https://mars.nasa.gov/mmgis-maps/M20/Layers/json/M20_waypoints.json"
    dest = Path(__file__).resolve().parent.parent / "data" / "M20_waypoints.downloaded.json"

    print("Testing acquire_telemetry_with_provenance in DRY_RUN mode:")
    result = acquire_telemetry_with_provenance(test_url, dest, dry_run=True)
    print(json.dumps(result, indent=2))
