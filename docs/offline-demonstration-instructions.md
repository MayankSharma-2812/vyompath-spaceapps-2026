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

### Method 2: Native Windows 11 (PowerShell)

On the Windows presentation laptop without bash:

**Terminal 1 (Backend API):**
```powershell
cd C:\path\to\vyompath-spaceapps-2026
$env:PORT="8000"
$env:CORS_ORIGINS="http://localhost:4173,http://127.0.0.1:4173,http://localhost:5173"
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 (Frontend Preview):**
```powershell
cd C:\path\to\vyompath-spaceapps-2026\frontend
npm run preview -- --host 127.0.0.1 --port 4173
```

---

## 4. Step-by-Step Judge Walkthrough (60 Seconds)

Open browser at: **`http://localhost:4173`** (or in an incognito window).

### Step 1: Confirm Air-Gapped Status
1. Show the presentation laptop’s system tray showing **Airplane Mode ON** or Wi-Fi disconnected.
2. Open Browser Developer Tools (`F12`), navigate to the **Network** tab.
3. Show that all tile requests and API calls resolve to `127.0.0.1` / `localhost` with zero external calls to `nasa.gov` or external CDNs.

### Step 2: Regional Tile Navigation
1. Zoom into Jezero Crater across zoom levels 12, 13, 14, and 15.
2. Toggle between **Basemap** and **Hillshade** visual layers.
3. Highlight that tiles load instantly ($<3\text{ ms}$ loopback latency).

### Step 3: Draw a Candidate Traverse
1. Click the **Draw Route** tool on the map canvas.
2. Click points along the crater floor (e.g. from Perseverance Sol 386 toward Sol 387).
3. Finish the traverse (double-click).

### Step 4: Inspect Scientific Analysis Dashboard
1. Observe the **Elevation Profile Chart** rendering elevation in metres.
2. Observe the **KPI Cards**: Minimum Elevation, Maximum Elevation, Cumulative Gain, Cumulative Loss, and Maximum Slope.
3. Inspect the **Nearby Science POIs** panel showing discovered Perseverance rover waypoints with cross-track offset distances.
4. Point out the **Authoritative Boundary Indicator** (`COMPLETE` status when inside the 63.16% valid HiRISE swath).

### Step 5: Boundary Gap Demonstration (Edge of Swath)
1. Draw a traverse that exits the western boundary of the HiRISE swath.
2. Observe the dashboard gracefully transition to **`PARTIAL GAP`** or **`OUT OF BOUNDS`** without crashing.

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
