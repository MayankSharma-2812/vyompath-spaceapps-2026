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
