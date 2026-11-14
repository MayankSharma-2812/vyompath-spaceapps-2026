#!/usr/bin/env python3
"""scripts/fetch_data.py - Manifest-driven DTM and asset fetcher with resumption and verification.

Supports:
- Manifest parsing (data/layers.json, data/manifest.json)
- Resumable HTTP downloads (Range header support)
- SHA-256 verification of downloaded or existing assets
- Safe atomic promotions via .part files
- Dry-run mode for manifest verification without network side effects
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_data")

CHUNK_SIZE = 64 * 1024  # 64 KiB buffer for downloads and hashing


def compute_sha256(filepath: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()


def parse_content_range_start(content_range_hdr: Optional[str]) -> Optional[int]:
    """Parse the start byte offset from an HTTP Content-Range header.

    Example: 'bytes 100-199/200' -> 100
    """
    if not content_range_hdr:
        return None
    try:
        unit, rest = content_range_hdr.strip().split(" ", 1)
        if unit.lower() != "bytes":
            return None
        range_spec = rest.split("/")[0].strip()
        start_str = range_spec.split("-")[0].strip()
        return int(start_str)
    except (ValueError, IndexError):
        return None


def verify_file(filepath: Path, expected_sha256: Optional[str]) -> Tuple[bool, str]:
    """Verify file existence and optional SHA-256 checksum."""
    if not filepath.exists():
        return False, "File does not exist"
    if not expected_sha256:
        return True, "File exists (no checksum specified)"
    actual_sha = compute_sha256(filepath)
    if actual_sha.lower() == expected_sha256.lower():
        return True, f"SHA-256 match: {actual_sha}"
    return False, f"Checksum mismatch: expected {expected_sha256}, got {actual_sha}"


def download_file_resumable(
    url: str,
    dest_path: Path,
    expected_sha256: Optional[str] = None,
    dry_run: bool = False,
) -> bool:
    """Download a file with HTTP Range resume support and atomic .part promotion.

    If destination already exists and matches expected_sha256, download is skipped.
    If destination exists with wrong checksum, it will be re-downloaded.
    """
    if dry_run:
        logger.info("[DRY-RUN] Would fetch: %s -> %s", url, dest_path)
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Check if complete target already matches checksum
    if dest_path.exists() and expected_sha256:
        ok, msg = verify_file(dest_path, expected_sha256)
        if ok:
            logger.info("Destination %s already exists and checksum is valid. Skipping.", dest_path.name)
            return True
        logger.warning("Destination %s exists but failed checksum (%s). Re-fetching.", dest_path.name, msg)

    part_path = dest_path.with_suffix(dest_path.suffix + ".part")
    existing_bytes = part_path.stat().st_size if part_path.exists() else 0

    req = urllib.request.Request(url)
    if existing_bytes > 0:
        req.headers["Range"] = f"bytes={existing_bytes}-"
        logger.info("Resuming %s from byte offset %d", dest_path.name, existing_bytes)
    else:
        logger.info("Starting fresh download for %s", dest_path.name)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status = getattr(response, "status", 200)

            if status not in (200, 206):
                logger.error("Unexpected HTTP status code %d for %s", status, url)
                return False

            # Check if server honored Range request
            if existing_bytes > 0 and status == 206:
                content_range = response.headers.get("Content-Range")
                range_start = parse_content_range_start(content_range)
                if range_start is None or range_start != existing_bytes:
                    logger.error(
                        "Server returned HTTP 206 with invalid Content-Range: requested start %d, received '%s'",
                        existing_bytes,
                        content_range,
                    )
                    return False
                mode = "ab"
                logger.info("Server accepted Range request (HTTP 206 Partial Content: %s).", content_range)
            else:
                mode = "wb"
                if existing_bytes > 0 and status == 200:
                    logger.warning("Server responded with HTTP 200 (no Range support); restarting from 0.")
                    existing_bytes = 0

            with open(part_path, mode) as out_f:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    out_f.write(chunk)

    except urllib.error.HTTPError as e:
        if e.code == 416:  # Requested Range Not Satisfiable
            logger.warning("HTTP 416 (Range Not Satisfiable). Checking if .part file is already complete...")
            if part_path.exists() and expected_sha256 and compute_sha256(part_path).lower() == expected_sha256.lower():
                pass
            elif part_path.exists():
                logger.warning("Invalid .part file. Removing and retrying fresh.")
                part_path.unlink(missing_ok=True)
                return download_file_resumable(url, dest_path, expected_sha256, dry_run=False)
            else:
                logger.error("HTTP 416 returned on fresh request (server rejected Range or offset invalid): %s", url)
                return False
        else:
            logger.error("HTTP error downloading %s: %s", url, e)
            return False
    except Exception as e:
        logger.error("Download failed for %s: %s", url, e)
        return False

    # 2. Checksum validation on the completed .part file before promotion
    if expected_sha256:
        actual_sha = compute_sha256(part_path)
        if actual_sha.lower() != expected_sha256.lower():
            logger.error(
                "Checksum verification FAILED for %s!\n  Expected: %s\n  Actual:   %s",
                part_path.name,
                expected_sha256,
                actual_sha,
            )
            part_path.unlink(missing_ok=True)
            return False
        logger.info("Checksum verified successfully for %s (%s)", part_path.name, actual_sha)

    # 3. Safe atomic replace
    part_path.replace(dest_path)
    logger.info("Successfully fetched and verified: %s", dest_path)
    return True


def inspect_manifests(repo_root: Path) -> List[Dict[str, Any]]:
    """Inspect data manifests for downloadable resources."""
    targets = []

    layers_path = repo_root / "data" / "layers.json"
    if layers_path.exists():
        try:
            with open(layers_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for layer in data.get("layers", []):
                    # Check for direct download or source URLs
                    url = layer.get("url") or layer.get("source_url")
                    path_rel = layer.get("local_path") or layer.get("path")
                    if url and path_rel:
                        targets.append({
                            "id": layer.get("id"),
                            "url": url,
                            "dest": repo_root / path_rel,
                            "sha256": layer.get("sha256"),
                            "source": "layers.json",
                        })
        except Exception as e:
            logger.error("Failed to parse %s: %s", layers_path, e)

    manifest_path = repo_root / "data" / "manifest.json"
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("assets", []):
                    url = item.get("url")
                    path_rel = item.get("path")
                    if url and path_rel:
                        targets.append({
                            "id": item.get("id"),
                            "url": url,
                            "dest": repo_root / path_rel,
                            "sha256": item.get("sha256"),
                            "source": "manifest.json",
                        })
        except Exception as e:
            logger.error("Failed to parse %s: %s", manifest_path, e)

    return targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch DTMs and spatial assets with resumption and checksum validation.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect manifests and report actions without downloading.")
    parser.add_argument("--verify-only", action="store_true", help="Verify checksums of existing assets without downloading.")
    parser.add_argument("--target-dir", type=str, default="data", help="Target base directory (default: data).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    base_dir = repo_root / args.target_dir

    logger.info("--- VyomPath Data Fetcher & Verification Utility ---")
    logger.info("Base target directory: %s", base_dir)
    logger.info("Dry-run mode: %s | Verify-only mode: %s", args.dry_run, args.verify_only)

    # Ensure required directory structure exists
    subdirs = ["raw", "processed", "dtm", "tiles"]
    for sub in subdirs:
        d = base_dir / sub
        if not d.exists() and not args.dry_run:
            d.mkdir(parents=True, exist_ok=True)
            logger.info("Created directory: %s", d)

    targets = inspect_manifests(repo_root)
    if not targets:
        logger.info("No remote downloadable assets currently registered in data manifests.")
        logger.info("Manifests checked: data/layers.json, data/manifest.json")
        return 0

    logger.info("Found %d registered asset(s) in manifests.", len(targets))
    failures = 0

    for item in targets:
        target_dest = item["dest"]
        url = item["url"]
        expected_sha = item.get("sha256")

        logger.info("Asset [%s] -> %s", item["id"], target_dest)

        if args.verify_only:
            if not target_dest.exists():
                logger.warning("  MISSING: %s", target_dest)
                failures += 1
            else:
                ok, msg = verify_file(target_dest, expected_sha)
                if ok:
                    logger.info("  OK: %s", msg)
                else:
                    logger.error("  FAILED: %s", msg)
                    failures += 1
            continue

        success = download_file_resumable(
            url=url,
            dest_path=target_dest,
            expected_sha256=expected_sha,
            dry_run=args.dry_run,
        )
        if not success:
            failures += 1

    if failures > 0:
        logger.error("Encountered %d failure(s) during data fetch/verification.", failures)
        return 1

    logger.info("All operations completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
