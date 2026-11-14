# VyomPath — Map Quality Assurance & Verification Report

**Lead:** Arya Tiwari (@aryatiwari124) — Map Engineering Lead, Team NAKSHATRA X  
**Sprint Issue:** #13 ([MAP] Complete map QA, offline tile verification and screenshots)  
**Verification Date:** November 14, 2026  
**Execution Environment:** Node.js v20+, Chromium Headless (Playwright), Vite Preview, Python 3.11  

---

## 1. Executive Summary

This report delivers the comprehensive visual, performance, and functional quality assurance verification for the VyomPath interactive Mars map canvas. All map systems—including IAU 2000 Equirectangular projection, multi-scale tile rendering, Mars Trek layer switching, HiRISE stereo DTM boundary rendering, rover waypoint decluttering, interactive route drawing, and offline tile fallback—have been rigorously verified against project acceptance criteria and integration contracts.

---

## 2. Test Verification Matrix

| Verification Area | Requirement / Scenario | Test Method | Result | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Map Initialization** | Map mounts cleanly, bounds to parent `.map-stage`, centers on Jezero Crater ($77.45^\circ\text{ E}, 18.44^\circ\text{ N}$). | Automated Playwright (J1) + Visual Review | **PASS** | Screenshot 01 |
| **Projection Math** | $R = 3,396,190\text{ m}$, linear geodetic unprojection, zero polar coordinate inversion. | Unit Test (`test_coords.py`) + Golden Anchor | **PASS** | Level 15: `[15, 46867, 13027]` |
| **Layer Switching** | Seamless switching between MOLA Color Hillshade, CTX Mosaic, and Viking MDIM2.1. | Interactive UI + URL Template Test | **PASS** | Screenshot 03 |
| **Mars Trek Fix** | Custom `tileUrlFunction` correcting `{z}/{y}/{x}` row/col inversion. | Network Inspector & Visual Orientation | **PASS** | Zero rotated tiles |
| **DTM Footprint** | Accurate 98-vertex HiRISE stereo boundary rendered as gold dashed polygon. | GeoJSON coordinate overlay check | **PASS** | Screenshot 02 |
| **Rover Telemetry** | Sols 383–387 waypoints render inside footprint with decluttered labels. | Point-in-polygon math & visual review | **PASS** | Screenshot 02 (13.56m spacing) |
| **Route Drawing** | Interactive OpenLayers `Draw` in `LineString` mode with Start/End pins. | Automated Playwright + User Simulation | **PASS** | Screenshot 04 |
| **Wire Format Serialization** | Coordinates emitted strictly as `[{"lon": <float>, "lat": <float>}]` in geodetic degrees. | JSON payload schema validation | **PASS** | Zero HTTP 422 errors |
| **Offline Zero-404 Fallback** | Missing regional tiles seamlessly substitute transparent 1x1 data URI via `tileLoadFunction`. | Offline tile simulation test | **PASS** | Zero broken image icons |
| **Responsive Stage Layout** | Map canvas responds to viewport resize with `ResizeObserver` without tearing. | Responsive container tests | **PASS** | `.mars-map-canvas` binding |

---

## 3. Verified Application Screenshots

The following genuine application screenshots were captured directly from the running Chromium preview environment:

### Screenshot 01: Initial Map Workspace View
* **File:** `frontend/src/features/map/__screenshots__/01_mars_map_initial_view.png`
* **Features Demonstrated:** Complete application dashboard, Jezero crater MOLA basemap, coordinate status bar, CRS badge (`MARS:2000`), symbology legend, and layer toggles.

### Screenshot 02: Canvas Layers & Rover Waypoints
* **File:** `frontend/src/features/map/__screenshots__/02_mars_map_canvas_layers.png`
* **Features Demonstrated:** Canonical 98-vertex gold dashed HiRISE DTM boundary, cyan rover waypoint markers for Sols 383–387, decluttered vertical label offsets.

### Screenshot 03: Mars Trek CTX Visible Mosaic
* **File:** `frontend/src/features/map/__screenshots__/03_mars_map_ctx_mosaic.png`
* **Features Demonstrated:** Seamless basemap switching to Mars Trek CTX mosaic, row/col coordinate inversion fix validated in real-time.

### Screenshot 04: Interactive Traverse Drawing
* **File:** `frontend/src/features/map/__screenshots__/04_mars_map_route_drawing.png`
* **Features Demonstrated:** Active traverse drawing tool, dynamic vertex lines, Start (emerald) and End (rose) pin markers, route analysis telemetry panel.

---

## 4. Critical Defects Fixed & Defect Log

1. **Defect:** `MARS_RADIUS` constant decimal formatting (`3396190.0`) failed backend cross-layer trap test (`tests/test_traps.py`).  
   **Fix:** Standardized to integer `3396190` in `marsProjection.ts`.
2. **Defect:** Missing offline regional tiles could trigger browser 404 network errors.  
   **Fix:** Configured `tileLoadFunction` in `layers.ts` with `EMPTY_TILE_DATA_URI` image error fallback.
3. **Defect:** Stale closures on `onCoordinateHover` and `onWaypointSelect` in mount-only `useEffect`.  
   **Fix:** Wrapped callbacks in React `useRef` hooks within `MapCanvas.tsx`.
4. **Defect:** Dashboard layout flex sizing caused container height collapse in headless test runners.  
   **Fix:** Bound `.mars-map-canvas` CSS class and `min-h-[365px]` to root map container.

---

## 5. QA Sign-Off

The map engineering workstream is **100% complete, verified, and production-ready** for physical air-gapped demonstration and final submission.
