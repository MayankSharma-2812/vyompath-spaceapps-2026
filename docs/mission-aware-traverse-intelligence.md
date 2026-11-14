# Mission-Aware Traverse Intelligence

**VyomPath — Interplanetary Survival Guide: Martian Map**  
*Team NAKSHATRA X | NASA Space Apps Challenge 2026*

---

## 1. Executive Summary & Problem Statement

Conventional planetary GIS viewers display raw topographic maps, contours, or static elevation profiles. While valuable for visualizing terrain, they leave tactical operational decisions entirely to human intuition:
- Which traverse route minimizes mechanical stress and rover tilt risk?
- Which path conserves mission battery power against Martian gravity?
- How does partial stereo photogrammetry or unmapped NoData terrain influence risk?

In actual tactical rover operations (e.g. NASA's Mars 2020 *Perseverance* or Mars Science Laboratory *Curiosity*), traverse planning balances three competing operational regimes:
1. **Kinematic & Slope Safety:** Minimizing pitch/roll angles, avoiding steep scarps ($>15^\circ$), and preventing excessive wheel slip on sandy bedrock slopes.
2. **Energy Budget:** Minimizing battery watt-hour expenditure driven by cumulative vertical climb ($\Delta z_{\text{gain}}$) against Martian gravity ($g = 3.721\text{ m/s}^2$) and rolling resistance over regolith.
3. **Epistemic Risk & Data Confidence:** Preventing blind rover drives through unmapped terrain or photogrammetric voids where hazard detection sensors have no prior DTM baseline.

**Mission-Aware Traverse Intelligence** is VyomPath's core Unique Selling Proposition (USP). It bridges planetary GIS visualization and tactical rover operations by formalizing multi-objective trade-off scoring with bounded mathematical normalization, explainable deterministic evidence, and zero fabricated safety claims.

---

## 2. Why It Differentiates VyomPath

| Feature Dimension | Conventional Mars Web Viewers | VyomPath Mission-Aware Traverse Intelligence |
| :--- | :--- | :--- |
| **Route Evaluation** | Visual inspection of 2D line profiles | Multi-criteria operational scoring across 3 distinct mission priorities |
| **Slope Analysis** | Single point elevation lookups | Multi-scale along-track slope gradients, max slope, and steep segment ($>15^\circ$) ratios |
| **Energy Proxy** | None / manual distance calculation | Physical mechanical work proxy ($W \approx m g \Delta z + C_{rr} m g d$) based on Mars gravity and rover mass |
| **Data Gaps (NoData)** | Flat interpolation or crash | Truthful NoData accounting; missing elevation is penalized and never coerced to 0 m |
| **Explainability** | Black-box or absent | Transparent, measurement-grounded natural language explanation citing exact metric deltas |
| **Operational Honesty** | Generic "Safe Route" badges | Truth-in-labeling: strictly decision-support; distinguishes real HiRISE DTM from mock demonstration data |

---

## 3. Mathematical Scoring Methodology & Weights

To avoid the pitfall of adding incomparable physical units directly (metres, degrees, kilojoules, percentages), all metrics are normalized into bounded sub-scores $S \in [0, 100]$:

### 3.1 Sub-Score Formulations

1. **Slope Hazard Mitigation Score ($S_{\text{slope}} \in [0, 100]$):**
   $$\text{pen}_{\max} = \min\left(100, \frac{\theta_{\max}}{30.0^\circ} \times 100\right)$$
   $$\text{pen}_{\text{steep}} = \min(100, F_{\text{steep}} \times 200)$$
   $$\text{pen}_{\text{avg}} = \min\left(100, \frac{\bar{\theta}}{15.0^\circ} \times 100\right)$$
   $$S_{\text{slope}} = \max\left(0, 100 - (0.45 \cdot \text{pen}_{\max} + 0.35 \cdot \text{pen}_{\text{steep}} + 0.20 \cdot \text{pen}_{\text{avg}})\right)$$
   *Where $\theta_{\max}$ is the 50 m baseline max slope, $F_{\text{steep}}$ is the fraction of traverse with slope $\ge 15.0^\circ$, and $\bar{\theta}$ is average along-track slope.*

2. **Energy Economy Score ($S_{\text{energy}} \in [0, 100]$):**
   $$\text{pen}_{\text{dist}} = \min\left(100, \frac{d}{4000\text{ m}} \times 100\right)$$
   $$\text{pen}_{\text{gain}} = \min\left(100, \frac{G}{200\text{ m}} \times 100\right)$$
   $$\text{pen}_{\text{work}} = \min\left(100, \frac{W_{\text{est}}}{1500\text{ kJ}} \times 100\right)$$
   $$S_{\text{energy}} = \max\left(0, 100 - (0.40 \cdot \text{pen}_{\text{dist}} + 0.40 \cdot \text{pen}_{\text{gain}} + 0.20 \cdot \text{pen}_{\text{work}})\right)$$
   *Where mechanical work $W_{\text{est}} = \frac{m \cdot g \cdot G + C_{rr} \cdot m \cdot g \cdot d}{1000}$ kJ ($m = 1025\text{ kg}$, $g = 3.721\text{ m/s}^2$, $C_{rr} = 0.05$).*

3. **Data Confidence Score ($S_{\text{confidence}} \in [0, 100]$):**
   $$\text{base} = \begin{cases} 100.0 & \text{if coverage is complete} \\ 100.0 \times C_{\text{ratio}} & \text{if coverage is partial\_gap} \\ 0.0 & \text{if out\_of\_bounds} \\ 40.0 & \text{if synthetic/mock mode} \end{cases}$$
   $$\text{pen}_{\text{nodata}} = (1.0 - C_{\text{ratio}}) \times 100$$
   $$S_{\text{confidence}} = \max(0, \text{base} - 0.5 \cdot \text{pen}_{\text{nodata}})$$

### 3.2 Objective Weight Profiles

$$\text{Composite Score } S_{\text{mission}} = w_{\text{slope}} S_{\text{slope}} + w_{\text{energy}} S_{\text{energy}} + w_{\text{confidence}} S_{\text{confidence}}$$

| Mission Objective | $w_{\text{slope}}$ | $w_{\text{energy}}$ | $w_{\text{confidence}}$ | Operational Target |
| :--- | :---: | :---: | :---: | :--- |
| **1. Slope-Conscious Traverse** | **0.60** | 0.20 | 0.20 | Minimizing rover tilt margins, steep scarps ($>15^\circ$), and wheel slippage. |
| **2. Energy-Efficient Traverse** | 0.20 | **0.60** | 0.20 | Power conservation, shortest path, and minimizing climb against gravity. |
| **3. Data-Confidence-First Traverse** | 0.15 | 0.15 | **0.70** | Minimizing unmapped NoData terrain, void crossings, and out-of-bounds drives. |

---

## 4. Explainable Decision Engine & Near-Parity Handling

When comparing Route A and Route B:
- **Score Delta:** $\Delta S = S_{\text{mission}}(B) - S_{\text{mission}}(A)$.
- **Near-Parity Condition ($|\Delta S| < 2.0$ points):**
  If two alternative routes score within 2 points of each other, the engine declares a **Tie / Near-Parity** state. It explicitly avoids exaggerating trivial differences, advising operators that tactical ground obstacles or scientific targets should govern selection.
- **Definitive Recommendation ($|\Delta S| \ge 2.0$ points):**
  The engine synthesizes a transparent natural language rationale citing exact measured differences:
  > *"Route A is recommended for Slope-Conscious Traverse (Score: 89.4/100, +18.2 vs Route B). Route A is preferred primarily due to lower maximum slope (2.8° vs 22.4°), fewer steep segments >15° (0.0% vs 28.6%), and smoother mean gradient (1.4° vs 8.7%). Operational trade-off: Route A requires 120.0 m of additional traverse length."*

---

## 5. Honest Scientific Behaviour & NoData Handling

1. **No "Flight-Certified" or "Safe" Claims:** Planetary mobility involves sand dunes, sub-pixel boulder fields, and sink hazards undetectable in 1 m/px orbital DTMs. The feature is explicitly labeled as a **Planning Decision-Support Prototype**.
2. **Missing Data is Never Flattened:** Uncovered raster points retain `null` elevation values. Slopes are calculated strictly between consecutive valid samples, preventing false 2500 m cliffs.
3. **Out-of-Bounds Drives:** Traverses falling outside the DTM boundary receive $S_{\text{confidence}} = 0$ and $S_{\text{slope}} = 0$, reflecting epistemic blindness.
4. **Mock vs Real DTM Mode:** In mock demonstration mode, results are explicitly flagged with `DEMONSTRATION MODE NOTICE: Synthetic elevation data — not real Martian terrain`.

---

## 6. Verification & Test Coverage

The feature is verified with unit and end-to-end tests across backend and frontend:

- **Backend Pytest (`tests/unit/test_traverse_intelligence.py` & `tests/test_api.py`):**
  - `test_route_a_wins_slope_conscious`: Confirms Route A with gentle slopes beats steep Route B.
  - `test_route_b_wins_energy_efficient`: Confirms shorter Route B with minimal climb beats longer Route A on energy.
  - `test_objective_switch_flips_winner`: Confirms that changing mission objective changes the winning route.
  - `test_missing_dtm_coverage_penalizes_data_confidence`: Confirms partial gaps and out-of-bounds paths score lower on data confidence.
  - `test_nodata_not_interpreted_as_zero_elevation`: Verifies null samples never produce artificial steep cliffs.
  - `test_mock_data_explicitly_flagged`: Verifies mock mode warnings.
  - `test_near_equal_routes_report_tie`: Confirms near-parity routes ($|\Delta| < 2.0$) report a tie.
  - `test_evaluate_intelligence_api_endpoint`: End-to-end API verification of `POST /api/routes/evaluate-intelligence`.
  - **Result: 293 passed, 6 skipped.**

- **Frontend Playwright E2E (`frontend/e2e/traverse-intelligence.spec.ts`):**
  - `TI-1`: Renders section heading and objective selectors.
  - `TI-2`: Switching objectives updates profile descriptions and weights.
  - `TI-3`: Displays single-route assessment without fake comparison.
  - `TI-4`: Recommends Route A over steep Route B under slope-conscious profile.
  - `TI-5`: Displays scientific constraints and physical constants.
  - **Result: 32 passed, 3 skipped.**

---

## 7. NASA Space Apps Presentation Blurb

> *"While other Martian maps only let you look at the terrain, VyomPath thinks like a rover mission planner. Our **Mission-Aware Traverse Intelligence** evaluates alternative paths across Jezero Crater using true HiRISE stereo slopes, cumulative gravitational climb, and photogrammetric confidence. By selecting your mission priority—whether mitigating steep scarp hazards, conserving battery Wh, or avoiding unmapped NoData terrain—VyomPath delivers transparent, explainable recommendations backed by real Martian measurements."*

---

## 8. 30-Second Video Demonstration Script

- **[0:00 – 0:08] The Problem & Corridors:**  
  *Visual:* On the Martian Surface Explorer, show the Jezero Crater AOI. Click `Floor Corridor (Sol 386–387)`.  
  *Voiceover:* "When planning rover traverses across Mars, choosing between paths isn't just about distance—it's about survival."

- **[0:08 – 0:16] Pinning Alternative Route:**  
  *Visual:* Scroll to Route Comparison, click `⚡ Compare with Delta Scarp` as Route B.  
  *Voiceover:* "We pin the rapid crater floor against the steep Jezero Delta Scarp."

- **[0:16 – 0:24] Mission-Aware Intelligence in Action:**  
  *Visual:* Scroll to **Mission-Aware Traverse Intelligence**. Show Route A winning with 89/100 under *Slope-Conscious*. Click *Energy-Efficient*—watch the scores and trade-off evidence dynamically update.  
  *Voiceover:* "Under Slope-Conscious mode, Route A wins by avoiding dangerous 22° scarps. Switch to Energy-Efficient, and VyomPath computes real mechanical work against Mars gravity."

- **[0:24 – 0:30] Scientific Rigor:**  
  *Visual:* Highlight the transparent evidence explanation and DTM confidence badges.  
  *Voiceover:* "No black-box guesses. Just transparent, measurement-driven planetary navigation. That is VyomPath."
