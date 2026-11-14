# VyomPath — QA & Testing Acceptance Checklist

> **Document ID:** `VP-QA-2026-CHECKLIST`  
> **Challenge:** Interplanetary Survival Guide: Martian Map · NASA Space Apps Challenge 2026 (Jaipur, India)  
> **Team:** NAKSHATRA X  
> **QA & Testing Lead:** Dheer Jain  
> **Integration Owner:** Mayank Sharma  
> **Canonical Path:** `docs/qa-and-testing-checklist.md`  
> **Last Updated:** November 14, 2026  

---

## 1. QA Objective & Governance

The objective of the QA subsystem is to provide **empirical proof** that VyomPath operates reliably, offline, and accurately before release.

### Defect Classification Matrix
- **P0 (Blocker):** Application crashes on startup, map canvas fails to render, route API unhandled 500 error, or secrets committed to repository. **Blocks submission.**
- **P1 (Critical Demo Defect):** Visual glitch during standard demo flow, chart axis mislabeling, or broken button on presentation device. Must be resolved or scripted around for judges.
- **P2 (Minor / Cosmetic):** Minor styling alignment, non-blocking warning in console, or slow asset load that completes successfully. Documented as known limitation.

---

## 2. Automated Test Suite Execution Matrix

### 2.1 Backend Automated Tests (Pytest)
```bash
# Standard CI Run (251 passed, 6 skipped pending local DTM)
pytest tests/ -v

# Full Local Regression Run (257 passed, 0 skipped with local DTM mounted)
VYOMPATH_DEM_PATH=/path/to/jezero_aoi_v2.tif pytest tests/ -v
```
- [x] `tests/unit/test_coords.py`: Spherical Great-Circle 2D distance math ($R=3,396,190.0\text{ m}$) — **PASS**
- [x] `tests/unit/test_terrain.py`: Float32 sampling, bilinear interpolation, multi-scale slope ($20\text{m}, 50\text{m}, 100\text{m}$) — **PASS**
- [x] `tests/unit/test_science.py`: Corridor buffering and telemetry waypoint extraction — **PASS**
- [x] `tests/unit/test_terrain_concurrency.py`: 20 simultaneous workers with zero deadlocks — **PASS**
- [x] `tests/unit/test_tile_grid.py`: MARS:2000 tile indices cross-validation ($z=15 \to 46867, 13027$) — **PASS**
- [x] `tests/test_health_only.py` & `tests/test_api.py`: FastAPI endpoints and error handling — **PASS**

---

### 2.2 Tabletop Engineering Dry Run (Zero Network)
```bash
python3 scripts/verify_terrain_g3_g4.py
```
- [x] **Check 1:** Golden fixtures integrity (`golden_routes.json`, `golden_pois.json`, `tile_indices.json`) — **PASS**
- [x] **Check 2:** 3D surface distance mathematics ($\Delta s_{3\text{D}} = \sqrt{\Delta d^2 + \Delta z^2}$) — **PASS**
- [x] **Check 3:** Golden route traversals (`J-gentle`, `J-steep`, `J-edge`, `S-basic`) — **PASS**
- [x] **Check 4:** Science POI corridor buffering ($<1.0\text{ mm}$ along/cross error) — **PASS**
- [x] **Check 5:** 20-worker parallel read concurrency (400 runs in 0.84s, 0 deadlocks) — **PASS**
- [x] **Check 6:** MARS:2000 tile grid indices at golden anchor — **PASS**

---

### 2.3 Science Data & Layer Quality Audit
```bash
python3 tools/validate_data.py
```
- [x] `data/layers.json`: Valid GeoJSON bounding boxes and layer manifests — **PASS**
- [x] `data/science_points.json`: Valid coordinates within $[-180, 180]$ and $[-90, 90]$ — **PASS**
- [x] Citation & Licensing Status: Unverified MMGIS status preserved as `null` — **PASS**

---

### 2.4 Frontend Linter, Typecheck & E2E Journeys
```bash
cd frontend
npm run lint
npm run build
npx playwright test
```
- [x] **Linter (`oxlint`):** 0 errors, 0 warnings across 17 source files.
- [x] **Build (`tsc -b && vite build`):** Clean compilation in $1.38\text{ s}$ (`dist/index.html` $0.40\text{ kB}$, `assets/index.js` $813.16\text{ kB}$).
- [x] **Playwright E2E Tests:**
  - Journey 1: User loads map workspace and sees initial controls — **PASS**
  - Journey 4: Route comparison panel renders comparison cards — **PASS**
  - Journey 6: Dashboard displays elevation analysis section and status badge — **PASS**
  - Journeys 2, 3, 5, 7: Live DTM and remote fallback journeys — **SKIPPED (Reserved for event-day live DTM wiring)**

---

## 3. Windows 11 Physical Compatibility Checklist

To verify the application on native Windows 11 hardware without bash dependencies:

- [ ] **PowerShell Launch:** Execute native PowerShell commands from Operational Runbook § 7.2.
- [ ] **Path Handling:** Ensure backend correctly resolves paths containing backslashes (`\`).
- [ ] **Console Encoding:** Verify console handles UTF-8 characters without `UnicodeEncodeError` (fallback to cp1252/cp437 active in scripts).
- [ ] **Port Availability:** Verify backend binds to port 8000 and frontend preview binds to port 4173 without conflict.
- [ ] **Browser Display:** Confirm OpenLayers canvas and dashboard charts render cleanly at 1080p presentation display scaling.

---

## 4. Air-Gapped Offline Demonstration Checklist

- [ ] **Network Disconnect:** Physically turn off Wi-Fi and unplug Ethernet cables.
- [ ] **Cold Start:** Launch application using `./scripts/run_offline.sh` or Windows PowerShell.
- [ ] **Browser Verification:** Open `http://localhost:4173` in a fresh browser session (or incognito window).
- [ ] **Tile Rendering:** Pan and zoom across Jezero Crater ($z=12\text{--}15$); confirm tiles render locally without network 404s.
- [ ] **API Smoke Test:** Verify `/api/health` returns `status: "ok"` on loopback `127.0.0.1`.
- [ ] **Clean Shutdown:** Terminate processes (Ctrl+C / SIGTERM); execute `pgrep -fa uvicorn` and `pgrep -fa vite` to confirm zero orphan processes remain.

---

## 5. Security & Privacy Audit

- [ ] **Zero Real Secrets:** Confirm `.env` files contain only local placeholder variables (`PORT=8000`).
- [ ] **No Large Rasters in Git:** Confirm `jezero_aoi_v2.tif` ($>100\text{ MB}$) is excluded via `.gitignore`.
- [ ] **No Absolute Local Paths:** Verify all committed code uses relative repository paths (`data/`, `tiles/`).
- [ ] **License Consistency:** Verify all source files and assets adhere to Apache 2.0 or open science attributions.

---

## 6. Release GO / NO-GO Sign-Off Template

**Evaluation Timestamp:** `_______________________`  
**QA Lead:** Dheer Jain  
**Central Machine:** Lenovo IdeaPad (Ryzen 7, 16 GB RAM)  
**Overall Recommendation:** `[  ] GO     [  ] CONDITIONAL GO     [  ] NO-GO`

**Sign-Off Criteria:**
1. All automated test suites report PASS.
2. Zero open P0 blockers.
3. Air-gapped offline launch verified on presentation machine.
4. All 9 NASA Space Apps release gates verified or honestly disclosed.
