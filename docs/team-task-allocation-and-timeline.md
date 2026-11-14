# VyomPath — Team Task Allocation & Execution Timeline

> **Document ID:** `VP-TIME-2026-EVENT`  
> **Challenge:** Interplanetary Survival Guide: Martian Map · NASA Space Apps Challenge 2026 (Jaipur, India)  
> **Team:** NAKSHATRA X  
> **Date:** Saturday, 14 November 2026 (All Times IST)  
> **Day-End Target:** Fully integrated, tested, and honestly documented project ready to submit by 9:00 PM IST (Saturday target; Sunday fallback window if release gates fail).  
> **Last Updated:** November 14, 2026  

---

## 1. Workspaces & Integration Rules

1. **Central Integration Machine:** Mayank's Lenovo IdeaPad (Ryzen 7, 16 GB RAM) hosts the canonical checkout, local backend + frontend, regional tile bundles, final rehearsal, and submission operations.
2. **Individual Development:** All six members work on assigned feature branches or personal workspaces. Never overwrite another member's files or push directly to `main`.
3. **Integration Gate:** PRs are reviewed and merged onto the central integration machine only after diff inspection and running the relevant automated checks.
4. **Four Synchronous Checkpoints:**
   - **12:30 PM IST:** Contract Freeze Checkpoint (API schema, `{lon, lat}`, $R=3,396,190.0\text{ m}$, footprint).
   - **04:30 PM IST:** Feature Freeze (zero new features, compile P0/P1 blocker list).
   - **06:30 PM IST:** Clean Launch & Air-Gapped Rehearsal on central laptop.
   - **08:45 PM IST:** Final Release Decision (Submit or hold for Sunday).

---

## 2. Shared Master Timeline (Saturday, 14 November 2026)

| Time (IST) | Phase Focus | Key Tasks & Required Outputs |
|---|---|---|
| **08:00–09:00** | **Setup / Eligibility** | All 6 leads join event channels. Mayank queries Local Lead on pre-existing prototype eligibility rules. Zero code implementation before official start. |
| **09:00–09:30** | **Kickoff & Scope** | Attend Jaipur orientation. Confirm challenge requirements, rules, judging criteria, and submission portal details. |
| **09:30–12:30** | **Sprint 1 (Parallel Work)** | Parallel engineering across backend/terrain, map canvas, dashboard, scientific validation, data provenance, and QA baselines. |
| **12:30–01:00** | **Contract Checkpoint** | Synchronous team sync. Freeze API payload, coordinate convention, Mars radius, and footprint boundaries. Record blockers. |
| **01:00–01:45** | **Lunch Break** | Team lunch. Leave async status notes if long-running tests or data builds are active. |
| **01:45–04:30** | **Sprint 2 / Integration** | Integrate reviewed changes on central laptop. Connect map, API, DTM data, dashboard, and truthful real-vs-mock status. |
| **04:30–05:00** | **Feature Freeze** | Hard freeze on all new feature requests. Publish integration status; compile P0/P1 defects; assign one owner per fix. |
| **05:00–07:30** | **QA / Bug Bash / Rehearsal** | Dheer leads QA bug bash; Pranav validates scientific claims; execute physical air-gapped rehearsal with Wi-Fi disabled. |
| **07:30–08:45** | **Submission Prep & Review** | Assemble README, summary, source licenses, screenshots, 30-sec demo video / 7 slides. All six members review. |
| **08:45–09:00** | **Submit or Hold** | Mayank submits as team owner only if all 9 release gates pass. Capture confirmation. Otherwise continue fixes Sunday. |

---

## 3. Individual Member Timetables & Deliverables

### 3.1 Mayank Sharma — Backend & Cloud Lead / Integration Owner
- **Day-End Objective:** Own the central integrated build, connect the backend to verified terrain processing, enforce contracts, and submit the project only after all gates pass.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Owner / Kickoff | Check portal and team channel. Obtain Local Lead written guidance on prototype eligibility. Confirm official start. |
| **09:30–10:15** | Repo Baseline | On Lenovo, verify clean status, preserve stash/history, and create working integration branch. Do not reset or clean. |
| **10:15–12:30** | Backend Sprint | Inspect service boundaries. Wire real Float32 DTM once CRS and fixtures are confirmed. Validate schemas and NoData. |
| **12:30–01:00** | Contract Freeze | Agree with Arya and Pranav on `{lon, lat}`, radius, footprint, and response fields. Record unresolved assumptions. |
| **01:45–04:30** | Integration / API QA | Bring in reviewed map/frontend changes. Run both apps; test health, layers, routes, invalid inputs, and empty POIs. |
| **04:30–05:00** | Feature Freeze | Publish integration status and blocker list. Assign one owner per blocker; reject new feature requests. |
| **05:00–06:30** | Fix / Coordinate | Resolve backend blockers with Arya and Pranav. Keep local/offline fallback. Do not provision cloud unless permitted. |
| **06:30–07:30** | Clean Launch | Restart cleanly on Lenovo; verify frontend, API, tiles, logs, zero secrets, zero orphan processes, and shutdown. |
| **07:30–08:45** | Submission Package | Own README, project summary, demo links, data references, third-party license list, and coordinate all-six review. |
| **08:45–09:00** | Submit / Hold | Submit as team owner only after all 9 gates pass; capture confirmation. Otherwise do not submit misleading claims. |

---

### 3.2 Arya Tiwari — Map Engineering Lead
- **Day-End Objective:** Ensure the Mars map renders the correct projection, regional XYZ tiles, and coordinate conversion, providing a reliable interaction path to the API.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Join / Kickoff | Join team call and event orientation. Confirm map deliverables and schedule. |
| **09:30–10:30** | Projection Check | Verify MARS:2000 Equirectangular projection, extent, and radius convention with Pranav. Confirm east-positive units. |
| **10:30–12:30** | Map Integration | Connect `MapCanvas` to canonical tile URLs. Verify tile-grid alignment and zoom range against actual frozen data bundle. |
| **12:30–01:00** | Contract Checkpoint | Confirm outgoing route requests use `{lon, lat}` in degrees (lon first). Record transformation and edge cases. |
| **01:45–03:15** | Route Interaction | Wire traverse drawing tools to API contract. Ensure map canvas metres are transformed to geographic degrees before POST. |
| **03:15–04:30** | Map QA | Check tile coverage, footprint boundary, zoom levels, missing tile behavior, marker locations, and route overlay alignment. |
| **04:30–05:00** | Feature Freeze | Send map status, changed files list, known issues, and one-line verification evidence to Mayank. |
| **05:00–06:30** | Integration Fixes | Resolve coordinate, CORS, tile URL, or rendering issues with Mayank. Keep screenshot proof of correct map alignment. |
| **06:30–07:30** | Clean Launch Check | Verify map on central laptop and test offline tile loading with network cut. |
| **07:30–08:45** | Submission Evidence | Provide final map screenshots and concise description of projection, datasets, and map layers for submission. |

---

### 3.3 Kumkum Kushwah — UI/UX Dashboard Lead
- **Day-End Objective:** Deliver a clear, responsive dashboard communicating map traverse profiles, slope/elevation metrics, science POIs, coverage gaps, and truthful mock/real status.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Join / Kickoff | Join team call and orientation. Confirm API contract owner and required dashboard states. |
| **09:30–10:30** | UI Scope | Confirm core screen and user journey. Prioritize map, route input, analysis results, and limitations over decorative additions. |
| **10:30–12:30** | Dashboard Build | Implement route selection, profile charts (Recharts), loading/error states, and responsive layout using agreed response schema. |
| **12:30–01:00** | Contract Checkpoint | Confirm exact fields with Mayank. Do not invent response properties; request sample payloads for each state. |
| **01:45–03:15** | API Wiring | Connect dashboard to real backend responses. Handle HTTP errors, invalid requests, empty POIs, and partial coverage gracefully. |
| **03:15–04:30** | Truthful States | Display `DEVELOPMENT / MOCK` when API mode is mock. Distinguish rover waypoints from geological features. Never label a route "safe". |
| **04:30–05:00** | Feature Freeze | Send build status, completed screens, known UI defects, and remaining blockers to Mayank. |
| **05:00–06:30** | Integration QA | Fix API/UI mismatches, axis labels, units, state synchronization with map, and overflow issues. |
| **06:30–07:30** | Demo Polish | Prepare a clean demo path: open map, choose route, view analysis, inspect caveats/POIs, and demonstrate fallback states. |
| **07:30–08:45** | Submission Assets | Capture clean dashboard screenshots and deliver a concise, accurate user-facing feature summary to Mayank. |

---

### 3.4 Pranav Sharma — Terrain and Scientific Analysis Lead
- **Day-End Objective:** Validate scientific assumptions, confirm coordinate/radius conventions, verify terrain outputs against known ground-truth samples, and approve only evidence-backed claims.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Join / Kickoff | Join team call and orientation. Confirm scientific acceptance criteria with Mayank and Arya. |
| **09:30–10:30** | Coordinate Sign-Off | Confirm CRS, coordinate ordering, east-positive convention, units, radius ($R=3,396,190.0\text{ m}$), and valid-data footprint. |
| **10:30–12:30** | Terrain Validation | Verify reference DTM sample coordinates, elevation discrepancies, and NoData behavior. Confirm authoritative fixtures before use. |
| **12:30–01:00** | Contract Checkpoint | Issue written scientific decisions: radius, projection, valid footprint, sample anchor/tolerance, and unresolved uncertainties. |
| **01:45–03:15** | Analysis Verification | Inspect route elevation profiles, slope outputs, and sampling behavior against DTM. Check edge-of-coverage and missing-data behavior. |
| **03:15–04:30** | Method Review | Confirm route length/spacing and slope methodology against agreed requirements. Flag any threshold lacking scientific approval. |
| **04:30–05:00** | Feature Freeze | Provide Mayank with concise sign-off: verified, conditionally verified, and not verified items. |
| **05:00–06:30** | Scientific QA | Re-test integrated outputs with Dheer. Check units, chart interpretations, claims, and limitations. |
| **06:30–07:30** | Demo Review | Watch final presentation demo and approve wording for terrain interpretations and scientific limitations. |
| **07:30–08:45** | Submission Content | Provide concise methodology paragraph, validated data references, and physical limitations for project description. |

---

### 3.5 Shyam Sharma — Data and GIS Lead
- **Day-End Objective:** Freeze the correct regional data bundle, verify contents and footprint, confirm dataset citations, and eliminate data-source and license ambiguity.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Join / Kickoff | Join team call and orientation. Confirm final data bundle and source list. |
| **09:30–10:30** | Bundle Identity | Confirm exact tile archive filename, byte size, SHA-256, and extraction layout. Do not use legacy v1.4 as final v1.6. |
| **10:30–12:30** | Data Integrity | Verify archive extraction, tile counts, zoom ranges, and canonical metadata. Confirm tile URLs match extracted structure. |
| **12:30–01:00** | Data Checkpoint | Send Mayank verified bundle identity, integrity results, footprint path, layer inventory, and unresolved discrepancies. |
| **01:45–03:15** | Footprint / Provenance | Validate canonical valid-data footprint and identify which datasets contribute to active map and analysis layers. |
| **03:15–04:30** | Citation / License Audit | Prepare source citations, dataset identifiers, providers, and licenses. Investigate MMGIS feed terms; do not treat citation as permission. |
| **04:30–05:00** | Feature Freeze | Declare which datasets are cleared for inclusion and which are blocked pending license confirmation. |
| **05:00–06:30** | Data QA | Check map data against footprint, verify 5 rover waypoints are not labeled geological features, and confirm empty geological state. |
| **06:30–07:30** | Offline Data Check | Verify extracted tiles and DTM data exist on central laptop. Confirm offline map request paths. |
| **07:30–08:45** | Submission References | Deliver final data-source and license list for NASA submission; flag any material that must be removed or replaced. |

---

### 3.6 Dheer Jain — QA and Testing Lead
- **Day-End Objective:** Provide empirical evidence that the integrated application functions, detect release blockers, verify clean/offline launch, and validate submission completeness.

| Time (IST) | Focus | Task / Required Output |
|---|---|---|
| **08:00–09:30** | Join / Kickoff | Join team call and orientation. Confirm QA target OS and available test laptops. |
| **09:30–12:30** | Plan / Baseline Tests | Prepare acceptance checklist. Run backend/frontend test suites. Record commands, pass/fail counts, and environment gaps. |
| **01:45–04:30** | Integration / Windows QA | Smoke-test startup, map/layers, route API, invalid coordinates, and partial results. Test Windows paths, encodings, and shutdown. |
| **04:30–05:00** | Feature Freeze | Publish prioritized defects: P0 blocks submission, P1 affects demo, P2 cosmetic. Assign owners with Mayank. |
| **05:00–06:30** | Regression / Bug Bash | Re-test P0/P1 fixes. Check logs, secrets, accidental local paths, and broken API calls. |
| **06:30–07:30** | Clean / Offline Rehearsal | On central laptop, verify clean startup and offline data paths with Wi-Fi cut. |
| **07:30–08:15** | Release Checklist | Verify README, public repository visibility, demo-link permissions, assets, and absence of secrets or unintended large files. |
| **08:15–08:45** | Final Acceptance | Deliver formal written GO / NO-GO recommendation to Mayank with evidence and known limitations. |
