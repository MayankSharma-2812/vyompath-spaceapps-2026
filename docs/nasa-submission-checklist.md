# VyomPath — NASA Space Apps Challenge Submission Checklist

> **Document ID:** `VP-SUBMIT-2026-GATE`  
> **Challenge:** Interplanetary Survival Guide: Martian Map · NASA Space Apps Challenge 2026 (Jaipur, India)  
> **Team:** NAKSHATRA X  
> **Team Owner & Submission Operator:** Mayank Sharma  
> **Canonical Path:** `docs/nasa-submission-checklist.md`  
> **Last Updated:** November 14, 2026  

---

## 1. Project Registration & Metadata

- **Project Title:** VyomPath — Interplanetary Survival Guide: Martian Map
- **Challenge:** Interplanetary Survival Guide: Martian Map
- **Local Event:** Jaipur, India
- **Event Window:** Saturday, November 14, 2026 – Sunday, November 15, 2026 (IST)
- **Primary Public Repository:** `https://github.com/MayankSharma-2812/nakshatra-vyompath`
- **License:** Apache License 2.0 (`LICENSE`)
- **Submission Operator:** Mayank Sharma (as Team Owner)

---

## 2. The 9 Release Gates (Every Item Must Pass or Be Disclosed)

| Gate | Category | Pass Condition & Evidence | Status |
|---|---|---|---|
| **Gate 1** | **Eligibility** | Local Lead guidance obtained on how pre-existing prototype may be used; no false claim that earlier work was built during the event. | Ready for Check |
| **Gate 2** | **Core Demo** | A new user or judge can launch the project on loopback and complete the map-to-traverse analysis flow without critical failure. | Verified |
| **Gate 3** | **Backend Truth** | Real Float32 DTM analysis is connected and validated, OR every mock result is clearly labeled as mock. No false scientific claims. | Verified |
| **Gate 4** | **Scientific Correctness** | MARS:2000 Equirectangular CRS, $R=3,396,190.0\text{ m}$, `{lon, lat}` coordinate order, and valid-data footprint agreed. Units and golden samples verified. | Verified |
| **Gate 5** | **Map & Data** | Tile URLs match actual local bundle structure. Coverage gaps are handled. Five rover waypoints are not presented as geological features. | Verified |
| **Gate 6** | **Sources & Licenses** | Every dataset/source cited. Third-party licenses verified. Unverified raw MMGIS telemetry licensing status disclosed. | Verified |
| **Gate 7** | **QA** | Dheer reports no open P0 blockers; P1/P2 issues and demo limitations documented. Clean startup and shutdown tested. | Verified |
| **Gate 8** | **Submission Assets** | Public repository clean, README complete, accessible demo link, project summary, detailed description, references, and AI tool disclosures ready. | Verified |
| **Gate 9** | **Team Approval** | All six members (Mayank, Arya, Kumkum, Pranav, Shyam, Dheer) review the final demo and submission text before final submission. | Scheduled |

---

## 3. Submission Package Checklist

- [ ] **Public GitHub Repository URL:** Accessible without authentication; working tree clean; no committed secrets or $>100\text{ MB}$ binary rasters.
- [ ] **Working Demo URL / Video:**
  - Demo video: Maximum duration **30 seconds**.
  - Alternate presentation: Maximum **7 slides**.
  - Tested access in a private / incognito browser window to ensure no permission gating.
- [ ] **Project Summary (Short Description):** High-impact 2–3 sentence overview of VyomPath for the public portal gallery.
- [ ] **Detailed Project Description:**
  - **Problem Statement:** Operational navigation hazards on Mars; absence of air-gapped terrain analysis tools.
  - **Approach & Solution:** Two-Path Architecture combining offline XYZ map visualization with Float32 DTM physical analysis.
  - **Space Agency Datasets Used:** HiRISE Stereo DTM, MGS MOLA Altimetry, CTX Global Mosaic, Viking MDIM 2.1, and Mars 2020 Perseverance Telemetry.
  - **Hardware & Software Tools:** Python 3.12+, FastAPI, Rasterio, NumPy, Shapely, OpenLayers, React 19, Tailwind CSS, Vite.
  - **Known Limitations:** Advisory risk indicators only; remote sensing cannot resolve sub-pixel boulder fields or regolith shear strength.
- [ ] **AI & Software Tools Disclosure:** Transparently report AI assistants used for code scaffolding, documentation audits, and test generation.
- [ ] **Team Members Roster:**
  - Mayank Sharma (Backend & Cloud)
  - Arya Tiwari (Map Engineering)
  - Kumkum Kushwah (UI/UX Dashboard)
  - Pranav Sharma (Terrain and Scientific Analysis)
  - Shyam Sharma (Data and GIS)
  - Dheer Jain (QA and Testing)

---

## 4. Decision Rule

> **DECISION RULE:**  
> Saturday, November 14, 2026, 9:00 PM IST is the target submission time, **not** an excuse to submit unverified work. If eligibility, third-party licensing, core demo, or scientific claims are unresolved, do not conceal the issue. Disclose or fix it.  
> **Sunday, November 15, 2026 is the authorized fallback window.**
