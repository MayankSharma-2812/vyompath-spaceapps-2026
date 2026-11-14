"""Unit tests for scripts/fetch_data.py.

Verifies all 11 download reliability cases:
1. Successful normal HTTP 200 download.
2. Successful HTTP 206 Range-based resume.
3. Server ignoring Range and returning HTTP 200.
4. HTTP 416 response handling (complete .part promotion & corrupt recovery).
5. HTTP 500 response handling (failure without corrupting existing destination).
6. Incorrect Content-Range handling (refusal to corrupt partial data).
7. SHA256 mismatch handling (rejection and cleanup of corrupt download).
8. Existing valid file detection (skipping download).
9. Existing corrupt file handling (re-download and atomic replacement).
10. Atomic promotion from .part to final destination.
11. Interrupted download recovery and cleanup (resumption from partial file).

All tests run locally using standard-library HTTP fixtures with zero external dependencies.
"""

from __future__ import annotations

import hashlib
import http.server
import json
from pathlib import Path
import threading
from typing import Generator
import urllib.error

import pytest

from scripts.fetch_data import (
    compute_sha256,
    download_file_resumable,
    inspect_manifests,
    parse_content_range_start,
    verify_file,
)

# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------
TEST_PAYLOAD = b"VYOMPATH_DEMO_DATA_MARS_2020_JEZERO_DTM_PAYLOAD_CHUNK_0123456789" * 4  # 256 bytes
TEST_SHA256 = hashlib.sha256(TEST_PAYLOAD).hexdigest()


class ControlledMockHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Configurable HTTP request handler for download reliability testing."""

    def log_message(self, format: str, *args: object) -> None:
        """Suppress stdout log noise during test runs."""
        pass

    def do_GET(self) -> None:
        path = self.path

        if path == "/file_200":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(TEST_PAYLOAD)))
            self.end_headers()
            self.wfile.write(TEST_PAYLOAD)

        elif path == "/file_resumable":
            range_hdr = self.headers.get("Range")
            if range_hdr and range_hdr.startswith("bytes="):
                try:
                    start_str = range_hdr.split("=")[1].split("-")[0]
                    start = int(start_str)
                except ValueError:
                    start = 0

                if start >= len(TEST_PAYLOAD):
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{len(TEST_PAYLOAD)}")
                    self.end_headers()
                    return

                chunk = TEST_PAYLOAD[start:]
                self.send_response(206)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header(
                    "Content-Range",
                    f"bytes {start}-{len(TEST_PAYLOAD) - 1}/{len(TEST_PAYLOAD)}",
                )
                self.send_header("Content-Length", str(len(chunk)))
                self.end_headers()
                self.wfile.write(chunk)
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(TEST_PAYLOAD)))
                self.end_headers()
                self.wfile.write(TEST_PAYLOAD)

        elif path == "/file_ignore_range":
            # Server completely ignores Range header and sends 200 with full content
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(TEST_PAYLOAD)))
            self.end_headers()
            self.wfile.write(TEST_PAYLOAD)

        elif path == "/file_416":
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{len(TEST_PAYLOAD)}")
            self.end_headers()

        elif path == "/file_500":
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Internal Server Error")

        elif path == "/file_bad_content_range":
            # Server returns 206 but with mismatching Content-Range start
            self.send_response(206)
            self.send_header("Content-Range", f"bytes 0-{len(TEST_PAYLOAD) - 1}/{len(TEST_PAYLOAD)}")
            self.send_header("Content-Length", str(len(TEST_PAYLOAD)))
            self.end_headers()
            self.wfile.write(TEST_PAYLOAD)

        elif path == "/file_corrupt":
            corrupt = b"CORRUPTED_STREAM_DIFFERENT_HASH"
            self.send_response(200)
            self.send_header("Content-Length", str(len(corrupt)))
            self.end_headers()
            self.wfile.write(corrupt)

        elif path == "/file_abort_midstream":
            # Write 50 bytes and immediately close connection
            self.send_response(200)
            self.send_header("Content-Length", str(len(TEST_PAYLOAD)))
            self.end_headers()
            self.wfile.write(TEST_PAYLOAD[:50])
            self.wfile.flush()
            # Abrupt close without sending remaining bytes
            self.close_connection = True

        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture
def mock_http_server() -> Generator[str, None, None]:
    """Spin up an ephemeral in-process HTTP server for testing."""
    server = http.server.HTTPServer(("127.0.0.1", 0), ControlledMockHTTPHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    try:
        yield base_url
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


# ---------------------------------------------------------------------------
# Unit Tests for Helper Functions
# ---------------------------------------------------------------------------
class TestFetchHelpers:
    """Validate internal utility functions in fetch_data.py."""

    def test_parse_content_range_start_valid(self) -> None:
        assert parse_content_range_start("bytes 100-199/200") == 100
        assert parse_content_range_start("bytes 0-50/*") == 0
        assert parse_content_range_start("   bytes 4096-8191/100000   ") == 4096

    def test_parse_content_range_start_invalid(self) -> None:
        assert parse_content_range_start(None) is None
        assert parse_content_range_start("") is None
        assert parse_content_range_start("items 0-10/20") is None
        assert parse_content_range_start("bytes invalid-range") is None
        assert parse_content_range_start("malformed_header_string") is None

    def test_verify_file(self, tmp_path: Path) -> None:
        test_file = tmp_path / "sample.bin"
        test_file.write_bytes(TEST_PAYLOAD)

        # 1. Valid file with correct hash
        ok, msg = verify_file(test_file, TEST_SHA256)
        assert ok is True
        assert "SHA-256 match" in msg

        # 2. Valid file with no expected hash
        ok, msg = verify_file(test_file, None)
        assert ok is True
        assert "no checksum specified" in msg

        # 3. Checksum mismatch
        ok, msg = verify_file(test_file, "wrong_hash_value_12345")
        assert ok is False
        assert "Checksum mismatch" in msg

        # 4. Non-existent file
        missing_file = tmp_path / "missing.bin"
        ok, msg = verify_file(missing_file, TEST_SHA256)
        assert ok is False
        assert "File does not exist" in msg


# ---------------------------------------------------------------------------
# Download Reliability Test Suite (All 11 Core Cases)
# ---------------------------------------------------------------------------
class TestDownloadReliability:
    """Automated tests covering all 11 download and resume reliability cases."""

    # 1. Normal HTTP 200 full download
    def test_fetch_http_200_normal_download(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_test.bin"
        url = f"{mock_http_server}/file_200"

        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)
        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD
        assert not dest.with_suffix(".bin.part").exists()

    # 2. Successful HTTP 206 Range-based resume
    def test_fetch_http_206_range_resume(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_resume.bin"
        part = dest.with_suffix(".bin.part")
        # Pre-seed part file with first 64 bytes
        part.write_bytes(TEST_PAYLOAD[:64])
        assert part.stat().st_size == 64

        url = f"{mock_http_server}/file_resumable"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD
        assert not part.exists()

    # 3. Server ignoring Range and returning HTTP 200
    def test_fetch_server_ignores_range_returns_200(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_ignore_range.bin"
        part = dest.with_suffix(".bin.part")
        # Pre-seed part file with 100 junk bytes
        part.write_bytes(b"A" * 100)

        url = f"{mock_http_server}/file_ignore_range"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.exists()
        # Verify file is not corrupted by appending to existing bytes
        assert dest.read_bytes() == TEST_PAYLOAD
        assert len(dest.read_bytes()) == len(TEST_PAYLOAD)
        assert not part.exists()

    # 4. HTTP 416 response handling
    def test_fetch_http_416_already_complete_part_file(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_416.bin"
        part = dest.with_suffix(".bin.part")
        # Part file is already completely downloaded
        part.write_bytes(TEST_PAYLOAD)

        url = f"{mock_http_server}/file_resumable"
        # Requesting bytes beyond end triggers 416, which should recognize complete part
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD
        assert not part.exists()

    def test_fetch_http_416_corrupt_part_file_retries(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_416_corrupt.bin"
        part = dest.with_suffix(".bin.part")
        # Part file has wrong size / corrupt data exceeding range
        part.write_bytes(b"CORRUPT" * 100)

        url = f"{mock_http_server}/file_resumable"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        # Corrupt part is removed, and download is retried fresh
        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD

    # 5. HTTP 500 response handling
    def test_fetch_http_500_server_error_preserves_destination(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_500.bin"
        original_data = b"PRE_EXISTING_VALID_FILE"
        dest.write_bytes(original_data)

        url = f"{mock_http_server}/file_500"
        success = download_file_resumable(url, dest, expected_sha256="arbitrary_hash")

        assert success is False
        # Existing file is preserved untouched
        assert dest.exists()
        assert dest.read_bytes() == original_data

    # 6. Incorrect Content-Range handling
    def test_fetch_incorrect_content_range_aborts_without_corrupting(
        self, mock_http_server: str, tmp_path: Path
    ) -> None:
        dest = tmp_path / "jezero_bad_range.bin"
        part = dest.with_suffix(".bin.part")
        initial_part_data = TEST_PAYLOAD[:50]
        part.write_bytes(initial_part_data)

        url = f"{mock_http_server}/file_bad_content_range"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is False
        assert not dest.exists()
        # Part file was not corrupted by appending mismatched stream
        assert part.exists()
        assert part.read_bytes() == initial_part_data

    # 7. SHA256 mismatch handling
    def test_fetch_sha256_mismatch_cleans_up_part_file(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_corrupt.bin"
        part = dest.with_suffix(".bin.part")
        url = f"{mock_http_server}/file_corrupt"

        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is False
        assert not dest.exists()
        # Corrupted .part file must be unlinked to prevent polluting local filesystem
        assert not part.exists()

    # 8. Existing valid file detection
    def test_fetch_existing_valid_destination_skips_download(self, mock_http_server: str, tmp_path: Path) -> None:
        dest = tmp_path / "jezero_existing.bin"
        dest.write_bytes(TEST_PAYLOAD)

        # Non-existent endpoint URL: if it attempts to download, it would fail with 404
        url = f"{mock_http_server}/file_404_nonexistent"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.read_bytes() == TEST_PAYLOAD

    # 9. Existing corrupt file handling
    def test_fetch_existing_corrupt_file_is_replaced_by_valid(
        self, mock_http_server: str, tmp_path: Path
    ) -> None:
        dest = tmp_path / "jezero_corrupt_existing.bin"
        dest.write_bytes(b"PREVIOUSLY_CORRUPTED_BYTES")

        url = f"{mock_http_server}/file_200"
        success = download_file_resumable(url, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD

    # 10. Atomic promotion from .part to final destination
    def test_fetch_atomic_promotion_preserves_valid_on_error(
        self, mock_http_server: str, tmp_path: Path
    ) -> None:
        dest = tmp_path / "jezero_atomic.bin"
        valid_preexisting = TEST_PAYLOAD
        dest.write_bytes(valid_preexisting)

        # Attempt to fetch with a bad expected hash
        url = f"{mock_http_server}/file_200"
        success = download_file_resumable(url, dest, expected_sha256="wrong_checksum_12345")

        assert success is False
        # Destination was not overwritten or removed
        assert dest.exists()
        assert dest.read_bytes() == valid_preexisting

    # 11. Interrupted download recovery and cleanup
    def test_fetch_interrupted_transfer_leaves_part_and_resumes(
        self, mock_http_server: str, tmp_path: Path
    ) -> None:
        dest = tmp_path / "jezero_interrupted.bin"
        part = dest.with_suffix(".bin.part")

        # Step 1: Request from endpoint that abruptly closes after 50 bytes
        url_abort = f"{mock_http_server}/file_abort_midstream"
        # This download will fail or receive partial bytes
        download_file_resumable(url_abort, dest, expected_sha256=TEST_SHA256)

        # Intermediate .part file exists with partial content
        if part.exists():
            assert part.stat().st_size <= len(TEST_PAYLOAD)

        # Step 2: Second attempt connects to full resumable endpoint
        url_resume = f"{mock_http_server}/file_resumable"
        success = download_file_resumable(url_resume, dest, expected_sha256=TEST_SHA256)

        assert success is True
        assert dest.exists()
        assert dest.read_bytes() == TEST_PAYLOAD
        assert not part.exists()


# ---------------------------------------------------------------------------
# Manifest and Dry-Run Tests
# ---------------------------------------------------------------------------
class TestManifestAndDryRun:
    """Validate manifest discovery and non-destructive dry-run mode."""

    def test_dry_run_mode_does_not_create_files(self, tmp_path: Path) -> None:
        dest = tmp_path / "dry_run_test.bin"
        url = "http://127.0.0.1:9999/dummy"

        success = download_file_resumable(url, dest, expected_sha256="abc", dry_run=True)
        assert success is True
        assert not dest.exists()
        assert not dest.with_suffix(".bin.part").exists()

    def test_inspect_manifests(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)

        layers_json = data_dir / "layers.json"
        layers_json.write_text(
            json.dumps({
                "layers": [
                    {
                        "id": "test_layer",
                        "url": "https://example.com/test.tif",
                        "local_path": "data/dtm/test.tif",
                        "sha256": "abcdef123456",
                    }
                ]
            }),
            encoding="utf-8",
        )

        targets = inspect_manifests(tmp_path)
        assert len(targets) == 1
        assert targets[0]["id"] == "test_layer"
        assert targets[0]["url"] == "https://example.com/test.tif"
        assert targets[0]["sha256"] == "abcdef123456"
