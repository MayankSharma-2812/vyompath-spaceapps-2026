# VyomPath — Sprint 1 QA Baseline Test Suite Audit & Environment Discrepancy Report

> **Document ID:** `VP-AUDIT-2026-ISSUE-4`  
> **Associated Issue:** Closes [#4](https://github.com/MayankSharma-2812/vyompath-spaceapps-2026/issues/4)  
> **Author & Lead Maintainer:** Dheer Jain (@dheerjain0508, QA & Testing Lead, Team NAKSHATRA X)  
> **Primary Peer Reviewer:** Mayank Sharma (@MayankSharma-2812, Integration Owner)  
> **Repository:** `MayankSharma-2812/vyompath-spaceapps-2026`  
> **Target Branch:** `feat/issue-4-baseline-test-suites` (rebased on `main` @ `fef7508`)  
> **Execution Date:** Saturday, November 14, 2026 (Kickoff / Sprint 1)  
> **Status:** **`VERIFIED — PASS`**

---

## 1. Executive Summary

In fulfillment of **Issue #4** for the NASA Space Apps Challenge 2026 kickoff, this report establishes the official, reproducible baseline test verification across all backend, frontend, geodesy, and terrain suites on the Windows presentation machine.

Every test, data validator, fixture check, and build task was executed locally in an air-gapped simulation without active cloud dependencies.

### Key Verification Metrics
1. **Pytest Regression Suite:** **250 passed, 7 skipped in 15.26s** (257 collected items, 100% test pass rate).
2. **Environment Skip Disambiguation:** 6 skips represent the expected local `jezero_aoi_v2.tif` DTM tests (identical to Linux CI); 1 skip (`tests/unit/test_terrain.py:957`) is uniquely accounted for by the absence of C-geospatial bindings (`rasterio`) on the Windows host Python environment while `syrtis_major_sample_dtm.tif` is physically present.
3. **Data Quality Audit:** `python tools/validate_data.py` completes with **100% QUALITY PASS** across all layer manifests and 5 strictly sourced MMGIS Perseverance telemetry waypoints.
4. **Terrain Verification Harness:** `python scripts/verify_terrain_g3_g4.py` completes with **6/6 PRE-EVENT CHECKS PASS** (concurrency: 400 runs across 20 threads in 2.691s with 0 deadlocks; corridor math matches MMGIS ground truth within $\le 0.007\text{ m}$).
5. **Privacy & Security Gate:** `python -m pytest tests/test_privacy.py` completes with **1 passed in 0.39s** (guaranteeing zero tracked decision logs, secrets, or untracked credentials).
6. **Frontend Production Build & Linter:** `tsc -b && vite build` completed in **19.95s** (825 modules transformed); `oxlint` completed with **0 warnings, 0 errors** across 17 files.
7. **Offline Process Lifecycles:** Verified clean local loopback execution (`backend.app.main:app` on port 8000 and `frontend/dist` on port 4173) with **0 leaked background worker processes** upon teardown.

---

## 2. Test Execution Environment & Machine Identity

```text
Host Platform:       Windows 11 (Build 10.0.26300-SP0, 64-bit WindowsPE)
CPU Architecture:    AMD64 Family 25 Model 124 Stepping 0 (AuthenticAMD, 16 logical cores)
Python Runtime:      Python 3.13.14 (tags/v3.13.14:fd17997, 64-bit)
Node.js / npm:       Node.js v24.x / npm v11.19.0
Git HEAD Commit:     fef7508528c43935d4b14318ea76287f4005e97d
Active Branch:       feat/issue-4-baseline-test-suites
Target Base:         main
```

---

## 3. Comprehensive Backend Test Suite Audit (`pytest`)

### Exact Execution Command
```powershell
python -m pytest -rs -q
```

### Overall Result
```text
250 passed, 7 skipped, 1 warning in 15.26s
```

### Module-by-Module Verification Breakdown
| Test Module | Path | Collected | Passed | Skipped | Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Manifest Integration** | `tests/data/test_manifest_integration.py` | 1 | 1 | 0 | **PASS** |
| **API Endpoints & Validation** | `tests/test_api.py` | 16 | 16 | 0 | **PASS** |
| **Data Fetch & Resilience** | `tests/test_fetch_data.py` | 17 | 17 | 0 | **PASS** |
| **Health-Only Isolation** | `tests/test_health_only.py` | 9 | 9 | 0 | **PASS** |
| **Privacy & Security** | `tests/test_privacy.py` | 1 | 1 | 0 | **PASS** |
| **Planetary Geodesy Traps** | `tests/test_traps.py` | 14 | 14 | 0 | **PASS** |
| **Mars Coordinates & Math** | `tests/unit/test_coords.py` | 19 | 19 | 0 | **PASS** |
| **Data Schema Validation** | `tests/unit/test_data_validation.py` | 7 | 7 | 0 | **PASS** |
| **Fixture Reproducibility** | `tests/unit/test_fixture_reproducibility.py` | 5 | 2 | 3 | **PASS (3 expected skips)** |
| **Golden POI Corridors** | `tests/unit/test_golden_pois.py` | 17 | 17 | 0 | **PASS** |
| **Science Telemetry** | `tests/unit/test_science.py` | 30 | 30 | 0 | **PASS** |
| **Terrain Sampling & Slopes** | `tests/unit/test_terrain.py` | 89 | 85 | 4 | **PASS (4 expected skips)** |
| **Terrain Concurrency (400 runs)** | `tests/unit/test_terrain_concurrency.py` | 2 | 2 | 0 | **PASS** |
| **Mars Tile Grid (z=0 to z=15)** | `tests/unit/test_tile_grid.py` | 20 | 20 | 0 | **PASS** |
| **Validate Data Script Unit** | `tests/unit/test_validate_data.py` | 9 | 9 | 0 | **PASS** |
| **TOTALS** | &mdash; | **257** | **250** | **7** | **100% REGRESSION PASS** |

---

## 4. Disambiguation of Skipped Tests (CI vs Windows Host)

In strict accordance with the testing and acceptance plan, all skipped tests are explicitly justified to ensure no unverified code is silently waived:

| Skipped Test ID | Source File & Line | Justification & Requirement | CI Status | Windows Host Status |
| :--- | :--- | :--- | :---: | :---: |
| `test_reproduce_j_gentle_profile` | `test_fixture_reproducibility.py:64` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM + `rasterio` | **SKIPPED** | **SKIPPED (Expected)** |
| `test_reproduce_j_steep_profile` | `test_fixture_reproducibility.py:82` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM + `rasterio` | **SKIPPED** | **SKIPPED (Expected)** |
| `test_sample_dtm_at_anchors` | `test_fixture_reproducibility.py:144` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM + `rasterio` | **SKIPPED** | **SKIPPED (Expected)** |
| `test_golden_route_s_basic_matches_fixture` | `test_terrain.py:957` | Requires `rasterio` bindings to sample `syrtis_major_sample_dtm.tif` | **PASSED** (in Linux CI) | **SKIPPED** (`rasterio` missing) |
| `test_j_gentle_full_profile` | `test_terrain.py:1053` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM | **SKIPPED** | **SKIPPED (Expected)** |
| `test_j_steep_full_profile` | `test_terrain.py:1071` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM | **SKIPPED** | **SKIPPED (Expected)** |
| `test_j_handcheck_sol387_anchor` | `test_terrain.py:1078` | Requires unbundled 125 MiB `jezero_aoi_v2.tif` DTM | **SKIPPED** | **SKIPPED (Expected)** |

> **Audit Note on `test_terrain.py:957` Discrepancy:**  
> On Linux CI, GDAL and Rasterio manylinux wheels are installed in the container, enabling test 957 to run against the in-tree test raster `data/dtm/syrtis_major_sample_dtm.tif` ($885\text{ KB}$). On the native Windows presentation machine, `rasterio` is not installed in the global Python 3.13 environment, so pytest gracefully skips this test without error. When executed in the Docker container (`vyompath-api:latest`), this test passes 100%.

---

## 5. Offline Data Quality & Scientific Sourcing Audit

### Exact Execution Command
```powershell
python tools/validate_data.py
```

### Output Summary
```text
=================================================================
  VYOMPATH DATA QUALITY AUDIT - SHYAM SHARMA
=================================================================

[1] Layer Manifest: data\layers.json
    - Structural Schema: PASS (All layers structurally sound & valid bounds)
    - Service Endpoints: PASS (Verified HTTP/HTTPS WMTS/WMS service URLs)

[2] Science POIs:   data\science_points.json
    - Structural Schema: PASS (Valid planetary coordinates in [-180, 180], [-90, 90])
    - Citation Metadata: PASS (Sourced MMGIS telemetry; terms_of_use not substituted)
    - Policy Status:     PASS (Unverified licensing status strictly preserved as null)

=================================================================
  RESULT: 100% QUALITY PASS - Structural & Citation Verified
  NOTICE: Licensing policies remain preserved as unverified.
=================================================================
```

### Verified Scientific Ground Truth:
- **Total POIs:** Exactly 5 points (`POI-M20-SOL-013`, `023`, `034`, `386`, `387`).
- **Telemetry Separation:** Confirmed 100% operational rover traverse waypoints from NASA Mars 2020 MMGIS; 0 natural geological science targets exist in the micro HiRISE stereo strip.
- **Licensing Hygiene:** Unverified MMGIS telemetry is explicitly reported as unverified rather than substituted with unproven boilerplate.

---

## 6. Tabletop Dry-Run & Terrain Concurrency Verification

### Exact Execution Command
```powershell
python scripts/verify_terrain_g3_g4.py
```

### Output Summary
```text
========================================================================
 VYOMPATH TERRAIN SERVICE TABLETOP & OFFLINE VERIFICATION (G3/G4)
 Team NAKSHATRA X | NASA Space Apps Challenge 2026
========================================================================

[VERIFY] Checking golden fixtures integrity...
  ✔ PASS: tests/fixtures/golden_routes.json (14052 bytes)
  ✔ PASS: tests/fixtures/golden_pois.json (2100 bytes)
  ✔ PASS: tests/fixtures/tile_indices.json (27480 bytes)
  ✔ PASS: tests/fixtures/unit_test_anchors.json (4529 bytes)

[VERIFY] Verifying 3D surface distance mathematics (Spec v3.1 § 4.2)...
  ✔ PASS: Flat terrain: d_3D == d_2D (100.0 m == 100.0 m)
  ✔ PASS: Incline terrain: d_3D (100.499 m) > d_2D (100.000 m)
  ✔ PASS: Pythagorean triple step (4 m horiz, 3 m vert = 5.000 m)

[VERIFY] Verifying golden route fixtures (Spec v3.1 § 4 & § 6)...
  ✔ PASS: Route 'J-gentle': 6 points, coverage=complete
  ✔ PASS: Route 'J-steep': 6 points, coverage=complete
  ✔ PASS: Route 'J-edge': 8 points, coverage=partial_gap
  ✔ PASS: Route 'S-basic': 6 points, coverage=complete
  ✔ PASS: Route 'J-handcheck': 6 points, coverage=complete
  ✔ PASS: Scarp traverse (J-steep) peaks at 4.09° at 50m (gentle slope < 5°); 20m peaks at 8.66°

[VERIFY] Verifying science POI corridor buffer math (Tolerance <= 1.0 m)...
  ✔ PASS: Corridor demo_route_sol_corridor_100m_10m -> POI-M20-SOL-386: cross error=0.7mm, along error=0.7mm
  ✔ PASS: Corridor demo_route_sol_corridor_100m_10m -> POI-M20-SOL-387: cross error=0.1mm, along error=4.2mm
  ✔ PASS: Corridor demo_route_sol_corridor_302m_boundary_250m -> POI-M20-SOL-386: cross error=2.9mm, along error=2.2mm
  ✔ PASS: Corridor demo_route_sol_corridor_302m_full_350m -> POI-M20-SOL-386: cross error=2.9mm, along error=2.2mm
  ✔ PASS: Corridor demo_route_sol_corridor_302m_full_350m -> POI-M20-SOL-387: cross error=3.0mm, along error=7.3mm

[VERIFY] Verifying 20-worker parallel read concurrency (Spec v3.1 § 5.5)...
  ✔ PASS: Executed 400 full pipeline runs across 20 threads in 2.691s (0 deadlocks)

[VERIFY] Verifying MARS:2000 tile grid indices at golden anchor (Spec v3.1 § 5.4)...
  ✔ PASS: Perseverance anchor (77.45°E, 18.44°N, z=15) -> (15, 46867, 13027) exact match

========================================================================
 ALL 6 PRE-EVENT ENGINEERING CHECKS PASSED (ZERO NETWORK REQUIRED)
 Gate G3 Tabletop Dry Run & Nov 11 Fixture Freeze Ready.
========================================================================
```

---

## 7. Frontend Production Build & Code Quality Audit

### Exact Execution Commands
```powershell
cd frontend
npm run build
npx oxlint
```

### Output Summary
- **Vite Build (`tsc -b && vite build`):** Built in **19.95s** with 825 modules transformed.
  - Production bundle: `dist/index.html` ($0.40\text{ kB}$), `dist/assets/index-*.css` ($18.32\text{ kB}$), `dist/assets/index-*.js` ($813.16\text{ kB}$).
- **Oxlint Quality Audit:** Finished in **85ms** on 17 files with 96 rules using 12 threads.
  - **Result:** **0 warnings, 0 errors**.

---

## 8. Offline Launch & Process Teardown Verification

Tested multi-process loopback execution using native PowerShell commands on ports 8000 and 4173:
- **Backend API (`uvicorn backend.app.main:app`):** Returns HTTP 200 on `GET /api/health` within **1,798.61 ms** (`mode: "development/mock"`).
- **Layer Manifest (`GET /api/layers`):** Responds within **42.78 ms** loading all 4 offline layers.
- **Route Analysis Endpoint (`POST /api/routes/analyze`):** Responds within **37.11 ms** returning mock elevation and 0 POIs.
- **Frontend Static Preview (`http.server` on port 4173):** Returns HTTP 200 within **101.86 ms**.
- **Process Memory:** Physical Windows Working Set: **50.76 MB** (Peak Working Set: **50.76 MB**), consuming $< 10\%$ of the $512\text{ MB}$ container budget.
- **Process Teardown:** Terminated cleanly with **0 leaked orphan processes**.

---

## 9. Issue #4 Acceptance Criteria Checklist

- [x] **Full test regression executed:** All 257 tests collected; 250 passed, 7 skipped (100% pass rate).
- [x] **All skipped tests documented & explained:** 6 local DTM skips + 1 Windows `rasterio` skip fully justified.
- [x] **Data validation verified:** 100% Quality Pass on schemas, coordinates, and citations.
- [x] **Terrain tabletop checks pass:** 6/6 checks pass with 0 deadlocks across 400 parallel runs.
- [x] **Frontend build & lint verified:** 0 warnings, 0 errors; production assets built in `frontend/dist`.
- [x] **Privacy & security verified:** `test_privacy.py` passes; zero decision files or credentials tracked.
- [x] **Offline startup verified:** Clean loopback launch and shutdown on Windows 11 host.
