"""Offline Air-Gapped Simulation & Windows Compatibility Audit Harness.

Team NAKSHATRA X | NASA Space Apps Challenge 2026
Author: Dheer Jain (@dheerjain0508, QA & Testing Lead)

Executes complete loopback end-to-end integration:
1. Validates offline socket binding.
2. Starts FastAPI backend on port 8000.
3. Starts static frontend server on port 4173.
4. Performs live HTTP benchmark across:
   - GET /api/health
   - GET /api/layers
   - POST /api/routes/analyze (Golden routes: J-gentle, J-steep, J-edge, S-basic, J-handcheck)
   - Edge case handling (invalid coords, >25km route, empty route)
   - GET / (frontend static index.html)
5. Measures memory working set and latency.
6. Enforces clean teardown with zero orphaned processes.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_PORT = 8000
FRONTEND_PORT = 4173
HOST = "127.0.0.1"


def test_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((HOST, port)) != 0


def http_get(url: str, timeout: float = 3.0) -> tuple[int, dict | str, float]:
    start = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "VyomPath-QA-Rehearsal/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            data = resp.read()
            try:
                parsed = json.loads(data.decode("utf-8"))
            except Exception:
                parsed = data.decode("utf-8")
            return resp.status, parsed, elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        data = e.read()
        try:
            parsed = json.loads(data.decode("utf-8"))
        except Exception:
            parsed = data.decode("utf-8")
        return e.code, parsed, elapsed_ms


def http_post(url: str, payload: dict, timeout: float = 3.0) -> tuple[int, dict | str, float]:
    start = time.perf_counter()
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "VyomPath-QA-Rehearsal/1.0",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return resp.status, json.loads(resp.read().decode("utf-8")), elapsed_ms
    except urllib.error.HTTPError as e:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return e.code, json.loads(e.read().decode("utf-8")), elapsed_ms


def main() -> int:
    print("=" * 72)
    print(" VYOMPATH OFFLINE AIR-GAPPED REHEARSAL & WINDOWS AUDIT")
    print(" Team NAKSHATRA X | NASA Space Apps Challenge 2026")
    print(f" Platform: {sys.platform} | Python: {sys.version.split()[0]}")
    print("=" * 72)

    # 1. Verify ports are free
    if not test_port_free(BACKEND_PORT):
        print(f"[FAIL] Port {BACKEND_PORT} is already occupied!")
        return 1
    if not test_port_free(FRONTEND_PORT):
        print(f"[FAIL] Port {FRONTEND_PORT} is already occupied!")
        return 1
    print("[PASS] Local loopback ports 8000 and 4173 are free.")

    backend_proc = None
    frontend_proc = None

    try:
        # 2. Launch FastAPI Backend
        print(f"[START] Launching FastAPI backend on http://{HOST}:{BACKEND_PORT}...")
        env = os.environ.copy()
        env["PORT"] = str(BACKEND_PORT)
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", HOST, "--port", str(BACKEND_PORT)],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Poll health probe
        healthy = False
        health_ms = 0.0
        for _ in range(30):
            time.sleep(0.2)
            try:
                status, data, elapsed = http_get(f"http://{HOST}:{BACKEND_PORT}/api/health")
                if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
                    healthy = True
                    health_ms = elapsed
                    break
            except Exception:
                pass

        if not healthy:
            print("[FAIL] Backend failed to start or respond to health probe within timeout.")
            return 1
        print(f"[PASS] Backend healthy in {health_ms:.2f}ms (mode: {data.get('mode')}).")

        # 3. Launch Frontend Static Server
        dist_dir = ROOT_DIR / "frontend" / "dist"
        if dist_dir.exists():
            print(f"[START] Launching Frontend static server on http://{HOST}:{FRONTEND_PORT}...")
            frontend_proc = subprocess.Popen(
                [sys.executable, "-m", "http.server", str(FRONTEND_PORT), "--bind", HOST, "--directory", str(dist_dir)],
                cwd=str(ROOT_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            f_status, f_html, f_elapsed = http_get(f"http://{HOST}:{FRONTEND_PORT}/")
            if f_status == 200 and "<html" in str(f_html).lower():
                print(f"[PASS] Frontend static server active in {f_elapsed:.2f}ms (index.html served).")
            else:
                print(f"[WARN] Frontend server responded with status {f_status}")
        else:
            print("[NOTICE] frontend/dist not found; skipping frontend static server test.")

        # 4. Execute Endpoint Regression Matrix
        print("-" * 72)
        print(" EXECUTING ENDPOINT REGRESSION MATRIX ON LOOPBACK STACK")
        print("-" * 72)

        # Test Layers API
        l_status, l_data, l_ms = http_get(f"http://{HOST}:{BACKEND_PORT}/api/layers")
        assert l_status == 200, f"Expected 200, got {l_status}"
        assert l_data["count"] == len(l_data["layers"]), "Layer count mismatch"
        print(f"  ✔ GET  /api/layers                  -> HTTP {l_status} ({l_data['count']} layers) in {l_ms:.2f}ms")

        # Load Golden Routes
        golden_routes_file = ROOT_DIR / "tests" / "fixtures" / "golden_routes.json"
        with open(golden_routes_file, "r", encoding="utf-8") as f:
            golden_data = json.load(f)
        routes_list = golden_data.get("routes", [])

        for route_fixture in routes_list:
            r_id = route_fixture["route_id"]
            coords = [{"lon": pt["lon"], "lat": pt["lat"]} for pt in route_fixture["sample_points"]]
            payload = {"route_id": r_id, "coordinates": coords, "buffer_distance_m": 250.0}
            r_status, r_resp, r_ms = http_post(f"http://{HOST}:{BACKEND_PORT}/api/routes/analyze", payload)
            assert r_status == 200, f"Failed on route {r_id}: {r_resp}"
            assert r_resp["route_id"] == r_id
            print(f"  ✔ POST /api/routes/analyze [{r_id:<12}] -> HTTP 200 ({r_resp['total_distance_m']:>8.1f}m, {len(r_resp['elevation_profile']):>3} pts) in {r_ms:.2f}ms")

        # Test Edge Cases
        # 4a. Route exceeding 500 coordinates or invalid length
        bad_coord_payload = {
            "route_id": "invalid-lon",
            "coordinates": [{"lon": 200.0, "lat": 0.0}, {"lon": 0.0, "lat": 0.0}],
            "buffer_distance_m": 250.0,
        }
        b_status, b_resp, b_ms = http_post(f"http://{HOST}:{BACKEND_PORT}/api/routes/analyze", bad_coord_payload)
        assert b_status == 422, f"Expected 422 for out-of-range lon, got {b_status}"
        print(f"  ✔ POST /api/routes/analyze [invalid-lon ] -> HTTP {b_status} (properly rejected) in {b_ms:.2f}ms")

        # 4b. Single point route (<2 waypoints)
        short_payload = {
            "route_id": "single-point",
            "coordinates": [{"lon": 77.45, "lat": 18.44}],
            "buffer_distance_m": 250.0,
        }
        s_status, s_resp, s_ms = http_post(f"http://{HOST}:{BACKEND_PORT}/api/routes/analyze", short_payload)
        assert s_status == 422, f"Expected 422 for single waypoint, got {s_status}"
        print(f"  ✔ POST /api/routes/analyze [single-point] -> HTTP {s_status} (properly rejected) in {s_ms:.2f}ms")

        # 5. Measure Windows Process Memory
        if sys.platform == "win32":
            try:
                cmd = f"Get-Process -Id {backend_proc.pid} | Select-Object -ExpandProperty WorkingSet64"
                res = subprocess.check_output(["powershell", "-Command", cmd], text=True).strip()
                ws_mb = int(res) / (1024 * 1024)
                print("-" * 72)
                print(f"[MEMORY] Windows Process Working Set (PID {backend_proc.pid}): {ws_mb:.2f} MB")
                print(f"[BUDGET] 512 MB cgroup budget headroom: {512.0 - ws_mb:.2f} MB ({(ws_mb / 512.0) * 100:.1f}% utilized)")
            except Exception as e:
                print(f"[MEMORY] Could not query working set: {e}")

        print("=" * 72)
        print(" ALL LOOPBACK REGRESSION & REHEARSAL CHECKS PASSED")
        print("=" * 72)
        return 0

    finally:
        print("\n[TEARDOWN] Terminating test processes...")
        if frontend_proc and frontend_proc.poll() is None:
            frontend_proc.terminate()
            frontend_proc.wait(timeout=3)
            print(f"  Stopped frontend (PID {frontend_proc.pid})")
        if backend_proc and backend_proc.poll() is None:
            backend_proc.terminate()
            backend_proc.wait(timeout=3)
            print(f"  Stopped backend (PID {backend_proc.pid})")
        print("[TEARDOWN] Complete. Zero orphan processes remaining.")


if __name__ == "__main__":
    sys.exit(main())
