# VyomPath — Offline Demonstration & Evaluation Guide

> **Document ID:** `VP-DEMO-2026-AIRGAP`  
> **Challenge:** Interplanetary Survival Guide: Martian Map · NASA Space Apps Challenge 2026 (Jaipur, India)  
> **Team:** NAKSHATRA X  
> **Author:** Mayank Sharma (Backend & Cloud)  
> **QA Lead:** Dheer Jain (QA and Testing)  
> **Canonical Path:** `docs/offline-demonstration-instructions.md`  
> **Last Updated:** November 14, 2026  

---

## 1. Overview & Demonstration Objective

VyomPath is engineered for **100% air-gapped evaluation**. During hackathon judging or offline field simulation, the application runs entirely on the host machine using local loopback (`127.0.0.1`), pre-rendered regional XYZ tile pyramids, and native Float32 Digital Terrain Models without sending a single network packet outside the laptop.

---

## 2. Pre-Rehearsal Setup (While Still Connected)

Before disabling Wi-Fi/Ethernet, ensure the repository dependencies are fully installed:

```bash
# 1. Backend environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# 2. Frontend environment
cd frontend
npm install
npm run build
cd ..

# 3. Verify data files exist
python3 tools/validate_data.py
```

---

## 3. Launching the Air-Gapped Stack

### Method 1: Linux / macOS / Git Bash (One Command)

```bash
# Disconnect Wi-Fi and unplug network cables
./scripts/run_offline.sh
```

*Custom Port Overrides (if default ports 8000 or 4173 are in use):*
```bash
BACKEND_PORT=8871 FRONTEND_PORT=4871 ./scripts/run_offline.sh
```

**Expected Startup Output:**
```text
========================================================================
 VYOMPATH AIR-GAPPED DEMO LAUNCHER
========================================================================
✓ Backend started (PID: 12345) on http://127.0.0.1:8000
✓ Frontend started (PID: 12346) on http://127.0.0.1:4173
Ready for offline judging evaluation!
```

---

### Method 2: Native Windows 11 (PowerShell — One Command)

On the Windows presentation laptop, launch both backend and frontend with a single command:

```powershell
.\scripts\run_offline.ps1
```

*Custom Port Overrides (if default ports 8000 or 4173 are busy):*
```powershell
.\scripts\run_offline.ps1 -BackendPort 8871 -FrontendPort 4871
```

---

### Method 3: Docker Compose (Multi-Container Production Stack)

Run the full containerized stack with Nginx reverse proxy and FastAPI backend:

```bash
docker compose up -d --build
```
Open browser at: **`http://localhost:8080`**.

---

## 4. Step-by-Step Judge Walkthrough (60 Seconds)

Open browser at: **`http://localhost:4173`** (or in an incognito window).

### Step 1: Confirm Air-Gapped Status & Operational Mode
1. Show the presentation laptop’s system tray showing **Airplane Mode ON** or Wi-Fi disconnected.
2. Open Browser Developer Tools (`F12`), navigate to the **Network** tab.
3. Show that all tile requests and API calls resolve to `127.0.0.1` / `localhost` with zero external calls to `nasa.gov` or external CDNs.
4. Note the top toolbar status badge: **`LIVE TERRAIN ENGINE`** (green) when `VYOMPATH_DEM_PATH` is mounted, or **`DEVELOPMENT / MOCK BACKEND`** (neutral) in fallback mode.

### Step 2: Regional Tile Navigation
1. Zoom into Jezero Crater across zoom levels 12, 13, 14, and 15.
2. Toggle between **MOLA Color Shaded Relief**, **CTX Visible Mosaic**, and **Viking MDIM 2.1** basemaps.
3. Highlight that regional ortho tiles load locally with sub-millisecond loopback latency.

### Step 3: Draw a Candidate Traverse (Route A)
1. Click the **Draw Route** tool on the map canvas.
2. Click points along the crater floor (e.g. from Perseverance Sol 386 toward Sol 387).
3. Finish the traverse (double-click).

### Step 4: Inspect Scientific Analysis Dashboard
1. Observe the **Elevation Profile Chart** rendering real Float32 elevations in metres without null-coercion artifacts.
2. Observe the **KPI Cards**: Minimum Elevation, Maximum Elevation, Cumulative Gain, Cumulative Loss, and Maximum Slope.
3. Point out the **Authoritative Boundary Indicator** (`COMPLETE` status when inside the 63.16% valid HiRISE swath, or `PARTIAL GAP` / `OUT OF BOUNDS` when crossing margins).

### Step 5: Route A vs Route B Comparative Analysis
1. With Route A loaded, click a corridor preset (e.g. `Jezero Floor Baseline`) or draw a second traverse to populate **Route B**.
2. Inspect the **Route Comparison Panel** displaying side-by-side KPI cards:
   - Distance Delta ($\Delta\text{m}$)
   - Elevation Gain Delta ($\Delta\text{m}$)
   - Elevation Loss Delta ($\Delta\text{m}$)
   - Max Slope Delta ($\Delta^\circ$)
3. Click **Clear Route B** to reset comparison without clearing Route A.

### Step 6: Visual Proof Reference
Visual screenshots captured during automated E2E tests are available in:
- `frontend/src/features/dashboard/__screenshots__/01_dashboard_live_dtm_overview.png`
- `frontend/src/features/dashboard/__screenshots__/02_route_comparison_deltas.png`
- `frontend/src/features/dashboard/__screenshots__/03_dashboard_mobile_view.png`

---

## 5. Clean Teardown & Process Verification

When the evaluation concludes:

1. **Press `Ctrl+C`** in the terminal running `./scripts/run_offline.sh`.
2. The launcher script traps `SIGINT`/`SIGTERM` and automatically kills the entire process group.
3. **Verify Zero Lingering Background Processes:**
   ```bash
   pgrep -fa uvicorn || echo "Clean: No lingering uvicorn processes."
   pgrep -fa vite || echo "Clean: No lingering vite processes."
   ```

---

## 6. 30-Second Video / Rapid Elevator Demo Script

| Timestamp | Screen Action | Narration Script |
|---|---|---|
| **00:00 – 00:06** | Browser opens `http://localhost:8080`, showing offline status badge and Mars Equirectangular map canvas centered on Jezero Crater. | *"VyomPath is an air-gapped Martian traverse analysis workspace for planetary rovers and astronaut crews, running 100% locally on uncompressed NASA HiRISE stereo DTMs."* |
| **00:06 – 00:14** | Cursor draws a candidate traverse across Jezero crater floor (`Draw Route` tool). Double-click to submit. | *"Planners draw candidate traverses directly on the map. VyomPath eliminates the 431-pixel northing trap and bilinearly interpolates Float32 elevations at 1.01-meter posting in real time."* |
| **00:14 – 00:22** | Screen scrolls to Elevation Profile Chart and multi-scale slope KPIs; Route B comparison is pinned. | *"The dashboard renders sub-meter elevation profiles, multi-scale wheel grades, and head-to-head Route A vs Route B comparative deltas without ever estimating over missing data."* |
| **00:22 – 00:30** | Hover over scientific limitations and dataset attribution badge; show zero fabricated safety claims. | *"Traverses are strictly labeled as advisory risk indicators with complete mathematical transparency. VyomPath: science-first navigation for the Martian frontier."* |

---

## 7. 7-Slide Judge Presentation Structure

1. **Slide 1 — Title & Hook:** *VyomPath: Interplanetary Survival Guide — Martian Map.* Team NAKSHATRA X. The Challenge: Enabling safe, autonomous traverse planning on Mars without relying on earth-bound cloud compute.
2. **Slide 2 — The Problem:** The 431-Pixel Northing Trap (PDS standard parallel shifts), uncompressed Float32 raster handling, communication delays, and dangerous "fake safety" claims in automated navigation tools.
3. **Slide 3 — The Two-Path Architecture:** Physical separation of visual display (8-bit OpenLayers XYZ pyramids) from quantitative terrain science (sub-pixel bilinear Float32 sampling on native GeoTIFFs).
4. **Slide 4 — Live Demonstration:** Real-time traverse drawing, sub-meter elevation profile generation, multi-scale slope evaluation (20m, 50m, 100m windows), and Route A vs Route B comparison deltas.
5. **Slide 5 — Scientific Truth & Data Licensing:** Rigorous provenance register: HiRISE, CTX Global Mosaic (Murray Lab), MOLA. Quarantined unverified telemetry (`terms_of_use: null`). Advisory labeling over subjective "safe route" claims.
6. **Slide 6 — Engineering Rigor & Containerization:** 283 backend tests, 11 Playwright E2E browser journeys, multi-container Docker Compose with Nginx reverse proxy, non-root execution, and 100% offline air-gapped capability.
7. **Slide 7 — Mission Impact & Roadmap:** Deployment-ready container for future Artemis/Mars missions; path to integrating Mars 2020 SPICE archives and autonomous onboard rover science.
