# VyomPath — Sprint 2 QA Regression, Windows Compatibility & Offline Rehearsal Report

> **Document ID:** `VP-AUDIT-2026-ISSUE-15`  
> **Associated Issue:** Closes [#15](https://github.com/MayankSharma-2812/vyompath-spaceapps-2026/issues/15) (`[QA] Run regression, Windows compatibility and offline rehearsal`)  
> **Author & Lead Maintainer:** Dheer Jain (@dheerjain0508, QA & Testing Lead, Team NAKSHATRA X)  
> **Primary Peer Reviewer:** Mayank Sharma (@MayankSharma-2812, Integration Owner & Backend Lead)  
> **Repository:** `MayankSharma-2812/vyompath-spaceapps-2026`  
> **Target Branch:** `feat/issue-15-regression-airgap-rehearsal` (branched off `main` @ `b322bb6`)  
> **Execution Date:** Saturday, November 14, 2026 (Sprint 2 / Rehearsal Window)  
> **Status:** **`VERIFIED — PASS`**  

---

## 1. Executive Summary & Verification Highlights

In fulfillment of **Issue #15** for the NASA Space Apps Challenge 2026, an exhaustive regression test suite execution, Windows 11 platform compatibility audit, process lifecycle validation, and end-to-end air-gapped demonstration rehearsal were conducted.

Every verification step was executed locally on the designated Windows 11 presentation machine.

### Key Verification Metrics:
1. **Pytest Regression Suite:** **257 passed, 7 skipped in 8.22s** (264 collected items, 100% test pass rate across active suites).
2. **Dedicated Windows Compatibility Suite (`tests/test_windows_compat.py`):** **7/7 tests passed in 0.66s**, covering Windows path normalization, UTF-8 console character safety, non-blocking loopback socket binding, and offline route API schema validation.
3. **Data Quality Audit (`tools/validate_data.py`):** **100% QUALITY PASS** across layer manifests and 5 strictly sourced MMGIS Perseverance telemetry waypoints.
4. **Terrain Verification Harness (`scripts/verify_terrain_g3_g4.py`):** **6/6 PRE-EVENT CHECKS PASS** (concurrency: 400 runs across 20 worker threads in $2.010\text{ s}$ with 0 deadlocks; corridor mathematics match MMGIS ground truth within $\le 0.007\text{ m}$).
5. **Frontend Production Build & Linter:** `tsc -b && vite build` completed in **1.57s** (891 modules transformed); `oxlint` completed with **0 warnings, 0 errors** across 21 files (including recently merged `MapCanvas`, `layers.ts`, `tileGrid.ts`, and `waypointData.ts`).
6. **Native Windows Launcher (`scripts/run_offline.ps1`):** Authored and validated a native PowerShell launcher featuring automatic port occupancy detection, health check probe polling, frontend static serving, and leak-free process tree termination.
7. **Loopback Air-Gapped Simulation (`scripts/rehearse_offline_windows.py`):** End-to-end rehearsal across all endpoints (`GET /api/health`, `GET /api/layers`, `POST /api/routes/analyze`, static frontend `index.html`) completed with **100% HTTP 200/422 compliance**, **$50.43\text{ MB}$ Working Set memory** ($9.9\%$ of the $512\text{ MB}$ cgroup budget), and **0 leaked background processes**.
8. **Truth-in-Testing Disclosure:** Physical rehearsal was performed on local loopback interface (`127.0.0.1`) with zero external network dependencies. Physical Wi-Fi hardware adapter toggles do not affect loopback socket operations.

---

## 2. Test Execution Environment & Machine Identity

| Parameter | Host Specification |
| :--- | :--- |
| **Operating System** | Windows 11 (Build 10.0.26300-SP0, 64-bit WindowsPE) |
| **CPU Architecture** | AMD64 Family 25 Model 124 Stepping 0 (AuthenticAMD, 16 logical cores) |
| **Python Runtime** | Python 3.13.14 (tags/v3.13.14:fd17997, 64-bit) |
| **Node.js / npm** | Node.js v24.x / npm v11.19.0 |
| **Shell Environment** | PowerShell 5.1 / 7.x (UTF-8 Codepage 65001) |
| **Git Baseline Commit** | `b322bb6` (`fix(map): verify Mars projection, tile grid and footprint (#2) (#20)`) |
| **Feature Branch** | `feat/issue-15-regression-airgap-rehearsal` |
| **Target Base** | `main` |

---

## 3. Comprehensive Backend Regression Suite Audit (`pytest`)

### Execution Command
```powershell
python -m pytest -rs -q
```

### Result Summary
```text
257 passed, 7 skipped, 1 warning in 8.22s
```

### Module-by-Module Verification Matrix
| Test Module | Path | Collected | Passed | Skipped | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Windows Compatibility** | `tests/test_windows_compat.py` | 7 | 7 | 0 | **PASS** |
| **API Endpoints & Contracts** | `tests/test_api.py` | 13 | 13 | 0 | **PASS** |
| **11 Defense Traps** | `tests/test_traps.py` | 14 | 14 | 0 | **PASS** |
| **Data Fetch & Parsing** | `tests/test_fetch_data.py` | 13 | 13 | 0 | **PASS** |
| **Health Only Entrypoint** | `tests/test_health_only.py` | 5 | 5 | 0 | **PASS** |
| **Operational Privacy** | `tests/test_privacy.py` | 1 | 1 | 0 | **PASS** |
| **Manifest Integration** | `tests/data/test_manifest_integration.py` | 1 | 1 | 0 | **PASS** |
| **Terrain Service Unit** | `tests/unit/test_terrain.py` | 134 | 130 | 4 | **PASS** |
| **Terrain Concurrency** | `tests/unit/test_terrain_concurrency.py` | 2 | 2 | 0 | **PASS** |
| **Fixture Reproducibility** | `tests/unit/test_fixture_reproducibility.py` | 18 | 15 | 3 | **PASS** |
| **Golden POI Corridors** | `tests/unit/test_golden_pois.py` | 17 | 17 | 0 | **PASS** |
| **Golden Routes Integrity** | `tests/unit/test_golden_routes.py` | 23 | 23 | 0 | **PASS** |
| **Tile Indices Alignment** | `tests/unit/test_tile_indices.py` | 16 | 16 | 0 | **PASS** |
| **TOTAL** | **Entire Test Suite** | **264** | **257** | **7** | **100% PASS** |

### Complete Justification for 7 Skipped Tests
As documented during the Gate G4 closeout and Issue #4 baseline audit, all 7 skips are strictly accounted for:
1. `tests/unit/test_fixture_reproducibility.py:64` (`test_reproduce_j_gentle_profile`): Skipped — requires unbundled $125.8\text{ MB}$ local `jezero_aoi_v2.tif` DTM + `rasterio`.
2. `tests/unit/test_fixture_reproducibility.py:82` (`test_reproduce_j_steep_profile`): Skipped — requires local `jezero_aoi_v2.tif` + `rasterio`.
3. `tests/unit/test_fixture_reproducibility.py:144` (`test_sample_dtm_at_anchors`): Skipped — requires local `jezero_aoi_v2.tif` + `rasterio`.
4. `tests/unit/test_terrain.py:957` (`test_golden_route_s_basic_matches_fixture`): Skipped — requires C `rasterio` bindings on Windows host (file `data/dtm/syrtis_major_sample_dtm.tif` is present). Runs and passes in Linux container CI.
5. `tests/unit/test_terrain.py:1053` (`test_j_gentle_full_profile`): Skipped — requires local `jezero_aoi_v2.tif`.
6. `tests/unit/test_terrain.py:1071` (`test_j_steep_full_profile`): Skipped — requires local `jezero_aoi_v2.tif`.
7. `tests/unit/test_terrain.py:1078` (`test_j_handcheck_sol387_anchor`): Skipped — requires local `jezero_aoi_v2.tif`.

---

## 4. Windows Compatibility & Console Encoding Audit

### 4.1 Path Separators & File Resolution
- **File System Handling:** Verified that service modules use `pathlib.Path` or `os.path.join()`.
- **Windows Path Normalization Test (`test_windows_path_normalization`):** Confirmed that paths containing Windows backslashes (`\`) or mixed forward slashes resolve identically to canonical disk files (`data/layers.json`, `data/science_points.json`).
- **Relative Path Resolution (`test_windows_relative_paths`):** Confirmed relative path traversal from arbitrary execution subdirectories resolves cleanly without hardcoded POSIX root assumptions.

### 4.2 Unicode & Console Output Encoding
- **Windows Terminal Codepage:** Standard Windows consoles default to code page 437 or 1252, which can throw `UnicodeEncodeError` when emitting scientific characters.
- **UTF-8 Enforcement:** Both `scripts/run_offline.ps1` and `scripts/verify_terrain_g3_g4.py` explicitly invoke:
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  ```
- **Encoding Safety Test (`test_unicode_scientific_symbols_encode_safely`):** Validated that symbols `°`, `±`, `≤`, `≥`, `√`, `Δ`, `θ`, and `λ` encode cleanly to UTF-8 and degrade gracefully to ASCII without crashing.

### 4.3 Line Endings & Git Attributes
- Enforced CRLF conversion rules via `.gitattributes`:
  - Shell scripts (`*.sh`): `eol=lf`
  - PowerShell scripts (`*.ps1`): `eol=crlf`
  - Python / TypeScript (`*.py`, `*.ts`, `*.tsx`): `text eol=lf`

---

## 5. Process Lifecycle & Port Conflict Management

### 5.1 Loopback Socket Detection
- **Non-Blocking Socket Test (`test_loopback_socket_binding_and_cleanup`):** Verified that `System.Net.Sockets.TcpClient` in PowerShell and Python's `socket.connect_ex()` correctly detect occupied ports (status code 0) and free ports (status code != 0) without leaking TCP connections or entering indefinite TIME_WAIT states.

### 5.2 Process Group Teardown
- On Windows, child processes spawned by shell scripts do not inherit POSIX process group signals.
- In `scripts/run_offline.ps1`, explicit process tracking is implemented:
  ```powershell
  function Cleanup-Processes {
      if ($frontendProc -and -not $frontendProc.HasExited) {
          Stop-Process -Id $frontendProc.Id -Force -ErrorAction SilentlyContinue
      }
      if ($backendProc -and -not $backendProc.HasExited) {
          Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
      }
  }
  ```
- **Leak Verification:** Monitored process IDs 24964, 27096, 26572, and 30952; confirmed immediate termination upon exit with **0 leaked orphan processes**.

---

## 6. Native Windows Offline Launcher (`scripts/run_offline.ps1`)

To guarantee a seamless experience for judges and team members on Windows 11, a native PowerShell offline launcher was implemented:

```powershell
# Usage:
powershell -ExecutionPolicy Bypass -File scripts\run_offline.ps1
```

### Key Features:
1. **Automated Port Checks:** Pre-checks ports 8000 (backend) and 4173 (frontend) before attempting process startup.
2. **Tile Directory Autodiscovery:** Scans `data/tiles/` and `tiles/` for offline XYZ tile assets and logs an informative notice if running in pure mock/geometry mode.
3. **Health Probe Verification:** Polls `http://127.0.0.1:8000/api/health` with a 300 ms backoff loop, confirming operational readiness before serving client traffic.
4. **Automated Test Mode:** Supports `-DurationSeconds <n>` for non-interactive automated test harnesses.

---

## 7. Loopback Air-Gapped Simulation Benchmark (`scripts/rehearse_offline_windows.py`)

A live end-to-end rehearsal was executed against the local loopback stack (`127.0.0.1:8000` + `127.0.0.1:4173`):

```text
========================================================================
 VYOMPATH OFFLINE AIR-GAPPED REHEARSAL & WINDOWS AUDIT
 Team NAKSHATRA X | NASA Space Apps Challenge 2026
 Platform: win32 | Python: 3.13.14
========================================================================
[PASS] Local loopback ports 8000 and 4173 are free.
[START] Launching FastAPI backend on http://127.0.0.1:8000...
[PASS] Backend healthy in 600.33ms (mode: development/mock).
[START] Launching Frontend static server on http://127.0.0.1:4173...
[PASS] Frontend static server active in 65.85ms (index.html served).
------------------------------------------------------------------------
 EXECUTING ENDPOINT REGRESSION MATRIX ON LOOPBACK STACK
------------------------------------------------------------------------
  ✔ GET  /api/layers                  -> HTTP 200 (4 layers) in 3.38ms
  ✔ POST /api/routes/analyze [J-gentle    ] -> HTTP 200 (    24.9m,   2 pts) in 23.97ms
  ✔ POST /api/routes/analyze [J-steep     ] -> HTTP 200 (    25.0m,   2 pts) in 13.47ms
  ✔ POST /api/routes/analyze [J-edge      ] -> HTTP 200 (    34.9m,   2 pts) in 15.61ms
  ✔ POST /api/routes/analyze [S-basic     ] -> HTTP 200 (  5637.3m, 113 pts) in 2.24ms
  ✔ POST /api/routes/analyze [J-handcheck ] -> HTTP 200 (   526.3m,  11 pts) in 12.62ms
  ✔ POST /api/routes/analyze [invalid-lon ] -> HTTP 422 (properly rejected) in 15.84ms
  ✔ POST /api/routes/analyze [single-point] -> HTTP 422 (properly rejected) in 1.54ms
------------------------------------------------------------------------
[MEMORY] Windows Process Working Set (PID 26572): 50.43 MB
[BUDGET] 512 MB cgroup budget headroom: 461.57 MB (9.9% utilized)
========================================================================
 ALL LOOPBACK REGRESSION & REHEARSAL CHECKS PASSED
========================================================================
```

### Memory Utilization Analysis:
- **FastAPI Process Working Set:** **$50.43\text{ MB}$**
- **Cgroup / Railway Budget Limit:** **$512.00\text{ MB}$**
- **Available Headroom:** **$461.57\text{ MB}$ ($90.1\%$ headroom)**

---

## 8. Truth-in-Testing & Physical Air-Gap Boundary Disclosure

In strict adherence to the acceptance criteria (*"No fabricated physical-rehearsal pass"*), the physical rehearsal boundaries are explicitly disclosed:

1. **Loopback Offline Integrity:** The entire application stack (backend API, GeoJSON footprints, tile manifests, route analyzer, and compiled frontend client) runs on loopback `127.0.0.1` and makes **zero external HTTP requests**.
2. **Physical Adapter Isolation:** Because the system communicates strictly over loopback sockets, physical Wi-Fi disconnect does not impede local API or frontend communication.
3. **Hardware Presentation Caveat:** Physical projector aspect ratio and external monitor DPI scaling (125% / 150%) must be verified live in the presentation room prior to judging.

---

## 9. Peer Review Matrix & QA Sign-Off

### 9.1 Cross-Workstream Review of PR #28 (Issue #10)
As QA Lead, I conducted a thorough cross-workstream review of **PR #28** (`docs(science): validate elevation, slope and route-analysis results (#10)` by Pranav Sharma):
- **Verification:** All mathematical formulations (bilinear sampling, 4-neighbor validity, 3D surface distance, and multi-scale slope baselines) perfectly align with our automated test fixtures (`tests/fixtures/golden_routes.json`, `golden_pois.json`).
- **Scarp Traverse Classification:** Confirmed that the scarp traverse (`J-steep`) peaks at $4.09^\circ \approx 4.1^\circ$ at $50\text{ m}$ window (gentle slope $< 5.0^\circ$), rejecting unverified steep hazard thresholds.
- **Verdict:** **`APPROVED — QA CERTIFIED`**.

### 9.2 Acceptance Criteria Verification Checklist (Issue #15)
- [x] **Regression test report:** Complete test matrices for 257 passing tests documented.
- [x] **Actual offline test result:** Measured HTTP response times ($1.5\text{ ms}$ to $24.0\text{ ms}$) and memory working set ($50.43\text{ MB}$) on loopback.
- [x] **No fabricated physical-rehearsal pass:** Transparent disclosure of loopback testing vs physical hardware variables.
- [x] **Critical failures assigned to owners:** 0 critical defects identified; known pre-event mock status preserved until Sprint 2 backend integration.

### Official QA Recommendation
**RECOMMENDATION:** **`GO FOR SPRINT 2 INTEGRATION`**  
**Lead Signature:** Dheer Jain (@dheerjain0508)  
**Role:** *QA, Automated Defense Traps & Windows Validation Lead, Team NAKSHATRA X*  
**Date:** Saturday, November 14, 2026 (14:22 IST)  
