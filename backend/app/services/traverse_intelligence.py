"""VyomPath — Mission-Aware Traverse Intelligence Service.

This service evaluates alternative rover traverse paths against specific
planetary surface mission objectives:
  1. Slope-conscious traverse (hazard mitigation, mechanical tilt margins)
  2. Energy-efficient traverse (power conservation, cumulative vertical climb)
  3. Data-confidence-first traverse (DTM coverage integrity, NoData minimization)

All calculations rely strictly on verified analytical metrics from the route
analysis pipeline (distance, profile slopes, elevation gain/loss, DTM coverage).
No artificial scores, fabricated waypoints, or unverified safety guarantees.

Scientific context: Planning decision-support prototype. Not flight-certified.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, Field

MissionObjective = Literal["slope_conscious", "energy_efficient", "data_confidence"]

# ---------------------------------------------------------------------------
# Mission Objective Weight Profiles
# ---------------------------------------------------------------------------
OBJECTIVE_WEIGHTS: Dict[MissionObjective, Dict[str, float]] = {
    "slope_conscious": {
        "slope": 0.60,
        "energy": 0.20,
        "confidence": 0.20,
    },
    "energy_efficient": {
        "slope": 0.20,
        "energy": 0.60,
        "confidence": 0.20,
    },
    "data_confidence": {
        "slope": 0.15,
        "energy": 0.15,
        "confidence": 0.70,
    },
}

OBJECTIVE_TITLES: Dict[MissionObjective, str] = {
    "slope_conscious": "Slope-Conscious Traverse",
    "energy_efficient": "Energy-Efficient Traverse",
    "data_confidence": "Data-Confidence-First Traverse",
}

OBJECTIVE_DESCRIPTIONS: Dict[MissionObjective, str] = {
    "slope_conscious": "Prioritizes minimal mechanical tilt, lower maximum slope, and avoidance of steep scarps (>15°).",
    "energy_efficient": "Prioritizes minimal distance, lower cumulative climb against Martian gravity, and lower mechanical work.",
    "data_confidence": "Prioritizes valid HiRISE stereo DTM coverage, minimizing unmapped NoData terrain and out-of-bounds drives.",
}

# Mars gravity and rover physical constants for mechanical energy proxy
MARS_G_M_S2: float = 3.721
ROVER_MASS_KG: float = 1025.0  # Mars 2020 Perseverance class baseline
ROLLING_RESISTANCE_COEFF: float = 0.05  # Regolith rolling friction proxy


# ---------------------------------------------------------------------------
# Pydantic Schemas for Intelligence Output
# ---------------------------------------------------------------------------

class MetricScoreBreakdown(BaseModel):
    slope_score: float = Field(..., ge=0.0, le=100.0, description="Normalized slope control score (0-100).")
    energy_score: float = Field(..., ge=0.0, le=100.0, description="Normalized energy economy score (0-100).")
    confidence_score: float = Field(..., ge=0.0, le=100.0, description="Normalized data confidence score (0-100).")


class RouteIntelligenceMetrics(BaseModel):
    total_distance_m: float
    total_gain_m: float
    total_loss_m: float
    max_slope_deg: float
    average_slope_deg: float
    steep_segments_ratio: float
    steep_segments_count: int
    total_segments_count: int
    valid_points_count: int
    total_points_count: int
    coverage_ratio: float
    coverage_status: str
    estimated_work_kj: float
    dtm_source: str
    is_mock: bool


class RouteEvaluation(BaseModel):
    route_id: str
    label: str
    overall_score: float = Field(..., ge=0.0, le=100.0)
    score_breakdown: MetricScoreBreakdown
    metrics: RouteIntelligenceMetrics
    advantages: List[str]
    disadvantages: List[str]


class TraverseIntelligenceResult(BaseModel):
    objective: MissionObjective
    objective_title: str
    objective_description: str
    recommendation: Literal["route_a", "route_b", "tie", "single_route"]
    summary_verdict: str
    evidence_explanation: str
    route_a: Optional[RouteEvaluation] = None
    route_b: Optional[RouteEvaluation] = None
    score_delta_b_minus_a: Optional[float] = None
    scientific_disclaimers: List[str]


# ---------------------------------------------------------------------------
# Core Analytical Metric Extraction
# ---------------------------------------------------------------------------

def extract_route_metrics(route: Union[Dict[str, Any], Any]) -> RouteIntelligenceMetrics:
    """Extract and derive genuine physical and terrain metrics from route analysis data.
    
    Handles missing DTM data honestly: NoData samples are not treated as 0 elevation.
    """
    if hasattr(route, "model_dump"):
        data = route.model_dump()
    elif hasattr(route, "dict"):
        data = route.dict()
    elif isinstance(route, dict):
        data = route
    else:
        data = dict(route)

    dist_m = float(data.get("total_distance_m", 0.0) or 0.0)
    gain_m = float(data.get("total_gain_m", 0.0) or 0.0)
    loss_m = float(data.get("total_loss_m", 0.0) or 0.0)
    max_slope = float(data.get("max_slope_deg", 0.0) or 0.0)
    cov_status = str(data.get("coverage_status", "not_applicable"))
    dtm_source = str(data.get("dtm_source", "unknown"))
    is_mock = bool(data.get("is_mock", False))

    profile = data.get("elevation_profile", []) or []
    total_pts = len(profile)

    # Inspect valid elevations (null or NaN represents NoData/uncovered terrain)
    valid_pts = 0
    valid_elevations: List[Tuple[float, float]] = []

    for pt in profile:
        if isinstance(pt, dict):
            d = pt.get("distance_m", 0.0)
            z = pt.get("elevation_m")
        else:
            d = getattr(pt, "distance_m", 0.0)
            z = getattr(pt, "elevation_m", None)

        if z is not None and not (isinstance(z, float) and math.isnan(z)):
            valid_pts += 1
            valid_elevations.append((float(d), float(z)))

    cov_ratio = (valid_pts / total_pts) if total_pts > 0 else 0.0

    # Calculate along-track slopes between consecutive valid elevation points
    segment_slopes: List[float] = []
    steep_count = 0

    for i in range(len(valid_elevations) - 1):
        d0, z0 = valid_elevations[i]
        d1, z1 = valid_elevations[i + 1]
        step = d1 - d0
        if step > 0.0:
            dz = abs(z1 - z0)
            slope_deg = math.degrees(math.atan2(dz, step))
            segment_slopes.append(slope_deg)
            if slope_deg >= 15.0:  # standard 15° rover engineering tilt threshold
                steep_count += 1

    total_segments = len(segment_slopes)
    avg_slope = (sum(segment_slopes) / total_segments) if total_segments > 0 else (max_slope * 0.5)
    steep_ratio = (steep_count / total_segments) if total_segments > 0 else 0.0

    # Physical energy work proxy in kJ: Work against gravity climb + rolling resistance
    # W = m * g * gain + C_rr * m * g * distance
    work_kj = ((ROVER_MASS_KG * MARS_G_M_S2 * gain_m) + 
               (ROLLING_RESISTANCE_COEFF * ROVER_MASS_KG * MARS_G_M_S2 * dist_m)) / 1000.0

    return RouteIntelligenceMetrics(
        total_distance_m=round(dist_m, 2),
        total_gain_m=round(gain_m, 2),
        total_loss_m=round(loss_m, 2),
        max_slope_deg=round(max_slope, 2),
        average_slope_deg=round(avg_slope, 2),
        steep_segments_ratio=round(steep_ratio, 4),
        steep_segments_count=steep_count,
        total_segments_count=total_segments,
        valid_points_count=valid_pts,
        total_points_count=total_pts,
        coverage_ratio=round(cov_ratio, 4),
        coverage_status=cov_status,
        estimated_work_kj=round(work_kj, 2),
        dtm_source=dtm_source,
        is_mock=is_mock,
    )


# ---------------------------------------------------------------------------
# Normalization & Sub-Scoring Engine
# ---------------------------------------------------------------------------

def compute_subscores(metrics: RouteIntelligenceMetrics) -> MetricScoreBreakdown:
    """Normalize incomparable units into bounded [0, 100] sub-scores.
    
    100 = optimal planetary performance for that dimension.
    0 = severe hazard, extreme penalty, or complete data void.
    """
    # 1. Slope Score: penalizes max slope, steep segment exposure (>15°), and average slope
    # Max slope threshold: 30° is critical tilt limit for rover stability
    pen_max_slope = min(100.0, (metrics.max_slope_deg / 30.0) * 100.0)
    pen_steep_exposure = min(100.0, metrics.steep_segments_ratio * 200.0)  # 50% steep = 100 penalty
    pen_avg_slope = min(100.0, (metrics.average_slope_deg / 15.0) * 100.0)

    raw_slope_score = 100.0 - (0.45 * pen_max_slope + 0.35 * pen_steep_exposure + 0.20 * pen_avg_slope)
    slope_score = max(0.0, min(100.0, raw_slope_score))

    # 2. Energy Score: penalizes route length, vertical climb (gain), and total work proxy
    pen_dist = min(100.0, (metrics.total_distance_m / 4000.0) * 100.0)
    pen_gain = min(100.0, (metrics.total_gain_m / 200.0) * 100.0)
    pen_work = min(100.0, (metrics.estimated_work_kj / 1500.0) * 100.0)

    raw_energy_score = 100.0 - (0.40 * pen_dist + 0.40 * pen_gain + 0.20 * pen_work)
    energy_score = max(0.0, min(100.0, raw_energy_score))

    # 3. Data Confidence Score: evaluates true stereo DTM integrity and NoData exposure
    if metrics.coverage_status == "complete":
        base_confidence = 100.0
    elif metrics.coverage_status == "partial_gap":
        base_confidence = 100.0 * metrics.coverage_ratio
    elif metrics.coverage_status == "out_of_bounds":
        base_confidence = 0.0
    else:  # not_applicable (synthetic/mock mode)
        base_confidence = 40.0

    nodata_penalty = (1.0 - metrics.coverage_ratio) * 100.0
    confidence_score = max(0.0, min(100.0, base_confidence - (0.5 * nodata_penalty)))

    # If completely out of bounds, slope and energy are unknown and must be heavily penalized
    if metrics.coverage_status == "out_of_bounds":
        slope_score = 0.0
        energy_score = min(energy_score, 20.0)

    return MetricScoreBreakdown(
        slope_score=round(slope_score, 1),
        energy_score=round(energy_score, 1),
        confidence_score=round(confidence_score, 1),
    )


def compute_route_evaluation(
    route: Union[Dict[str, Any], Any],
    label: str,
    objective: MissionObjective,
) -> RouteEvaluation:
    """Evaluate a single route against a mission objective."""
    metrics = extract_route_metrics(route)
    breakdown = compute_subscores(metrics)
    weights = OBJECTIVE_WEIGHTS[objective]

    overall = (
        weights["slope"] * breakdown.slope_score
        + weights["energy"] * breakdown.energy_score
        + weights["confidence"] * breakdown.confidence_score
    )

    # Derive concrete advantages and disadvantages from measurements
    advantages: List[str] = []
    disadvantages: List[str] = []

    # Slope attributes
    if metrics.max_slope_deg <= 10.0:
        advantages.append(f"Gentle maximum slope ({metrics.max_slope_deg:.1f}° ≤ 10° threshold)")
    elif metrics.max_slope_deg >= 18.0:
        disadvantages.append(f"Steep max slope ({metrics.max_slope_deg:.1f}°) approaching rover tilt limits")

    if metrics.steep_segments_ratio == 0.0:
        advantages.append("Zero terrain segments exceeding 15° tilt threshold")
    elif metrics.steep_segments_ratio > 0.05:
        pct = metrics.steep_segments_ratio * 100.0
        disadvantages.append(f"{pct:.1f}% of traverse traverses steep slopes (>15°)")

    # Energy attributes
    if metrics.total_gain_m <= 15.0:
        advantages.append(f"Low vertical climb ({metrics.total_gain_m:.1f} m cumulative gain)")
    elif metrics.total_gain_m >= 60.0:
        disadvantages.append(f"High cumulative climb ({metrics.total_gain_m:.1f} m gain increases battery draw)")

    if metrics.total_distance_m <= 1200.0:
        advantages.append(f"Compact path length ({metrics.total_distance_m:.1f} m)")
    elif metrics.total_distance_m >= 3000.0:
        disadvantages.append(f"Extended path length ({(metrics.total_distance_m / 1000.0):.2f} km)")

    # Data confidence attributes
    if metrics.coverage_status == "complete":
        advantages.append("100% verified HiRISE stereo DTM coverage")
    elif metrics.coverage_status == "partial_gap":
        disadvantages.append(f"Contains NoData gaps ({metrics.valid_points_count}/{metrics.total_points_count} valid samples)")
    elif metrics.coverage_status == "out_of_bounds":
        disadvantages.append("Route lies entirely outside the calibrated HiRISE stereo DTM footprint")
    elif metrics.is_mock:
        disadvantages.append("Evaluated on synthetic mock elevation data (unverified)")

    if not advantages:
        advantages.append("Nominal traverse profile without critical single-metric standouts")
    if not disadvantages:
        disadvantages.append("No critical hazard or operational red flags detected")

    route_id = str(getattr(route, "route_id", "") or (route.get("route_id") if isinstance(route, dict) else "") or label)

    return RouteEvaluation(
        route_id=route_id,
        label=label,
        overall_score=round(overall, 1),
        score_breakdown=breakdown,
        metrics=metrics,
        advantages=advantages,
        disadvantages=disadvantages,
    )


# ---------------------------------------------------------------------------
# Decision & Comparative Intelligence Engine
# ---------------------------------------------------------------------------

def evaluate_traverse_intelligence(
    route_a: Optional[Union[Dict[str, Any], Any]],
    route_b: Optional[Union[Dict[str, Any], Any]],
    objective: MissionObjective = "slope_conscious",
) -> TraverseIntelligenceResult:
    """Evaluate Route A and Route B, providing transparent comparative intelligence.
    
    If only Route A is provided, returns single-route assessment without pretending to compare.
    """
    obj_title = OBJECTIVE_TITLES.get(objective, "Slope-Conscious Traverse")
    obj_desc = OBJECTIVE_DESCRIPTIONS.get(objective, "")

    disclaimers: List[str] = [
        "DECISION-SUPPORT PROTOTYPE: Not flight-certified rover autonomy. Metric scores are research models referencing HiRISE/MOLA data.",
        "TERRAIN INVARIANTS: Slopes are evaluated along 50m baseline windows. Micro-hazards (<1m rocks, sand ripples) require in-situ rover hazard avoidance cameras.",
    ]

    # Handle insufficient data (no Route A)
    if not route_a:
        return TraverseIntelligenceResult(
            objective=objective,
            objective_title=obj_title,
            objective_description=obj_desc,
            recommendation="single_route",
            summary_verdict="No route available for evaluation.",
            evidence_explanation="Please draw a route on the Martian Surface Explorer or select a Jezero Crater corridor to compute mission-aware intelligence.",
            scientific_disclaimers=disclaimers,
        )

    eval_a = compute_route_evaluation(route_a, label="Route A", objective=objective)

    if eval_a.metrics.is_mock:
        disclaimers.insert(
            0,
            "DEMONSTRATION MODE NOTICE: Evaluated on synthetic mock data. Elevation and slope metrics are illustrative and do not reflect real Martian terrain.",
        )

    # Single route assessment (Route B not provided)
    if not route_b:
        summary = (
            f"Route A scores {eval_a.overall_score:.1f}/100 under the {obj_title} profile. "
            f"Max slope: {eval_a.metrics.max_slope_deg:.1f}°, Distance: {eval_a.metrics.total_distance_m:.1f} m."
        )
        evidence = (
            f"Single-route evaluation complete. To generate comparative traverse intelligence, "
            f"pin an alternative route or load the Jezero Delta Scarp preset as Route B."
        )
        return TraverseIntelligenceResult(
            objective=objective,
            objective_title=obj_title,
            objective_description=obj_desc,
            recommendation="single_route",
            summary_verdict=summary,
            evidence_explanation=evidence,
            route_a=eval_a,
            route_b=None,
            score_delta_b_minus_a=None,
            scientific_disclaimers=disclaimers,
        )

    # Dual route comparative intelligence
    eval_b = compute_route_evaluation(route_b, label="Route B", objective=objective)
    delta = round(eval_b.overall_score - eval_a.overall_score, 1)

    mA = eval_a.metrics
    mB = eval_b.metrics

    # Check for near parity (|delta| < 2.0)
    if abs(delta) < 2.0:
        recommendation: Literal["route_a", "route_b", "tie", "single_route"] = "tie"
        verdict = f"Routes exhibit near-parity under the {obj_title} objective (Route A: {eval_a.overall_score:.1f}, Route B: {eval_b.overall_score:.1f}, Δ = {delta:+.1f})."
        evidence = (
            f"Neither route demonstrates a decisive operational advantage under current weights (score margin < 2.0 points). "
            f"Route A spans {mA.total_distance_m:.1f} m (max slope {mA.max_slope_deg:.1f}°, climb {mA.total_gain_m:.1f} m) "
            f"versus Route B at {mB.total_distance_m:.1f} m (max slope {mB.max_slope_deg:.1f}°, climb {mB.total_gain_m:.1f} m). "
            f"Operational selection should depend on tactical ground obstacles or science targets."
        )
    elif delta > 0:
        recommendation = "route_b"
        verdict = f"Route B is recommended for {obj_title} (Score: {eval_b.overall_score:.1f}/100, +{delta:.1f} vs Route A)."
        evidence = _generate_comparative_evidence("Route B", eval_b, "Route A", eval_a, objective)
    else:
        recommendation = "route_a"
        verdict = f"Route A is recommended for {obj_title} (Score: {eval_a.overall_score:.1f}/100, +{abs(delta):.1f} vs Route B)."
        evidence = _generate_comparative_evidence("Route A", eval_a, "Route B", eval_b, objective)

    return TraverseIntelligenceResult(
        objective=objective,
        objective_title=obj_title,
        objective_description=obj_desc,
        recommendation=recommendation,
        summary_verdict=verdict,
        evidence_explanation=evidence,
        route_a=eval_a,
        route_b=eval_b,
        score_delta_b_minus_a=delta,
        scientific_disclaimers=disclaimers,
    )


def _generate_comparative_evidence(
    winner_label: str,
    winner: RouteEvaluation,
    alt_label: str,
    alt: RouteEvaluation,
    objective: MissionObjective,
) -> str:
    """Generate deterministic, measurement-anchored reasoning for why the winner scored higher."""
    mW = winner.metrics
    mA = alt.metrics

    reasons: List[str] = []

    # Coverage status check
    if mW.coverage_status == "complete" and mA.coverage_status in ("partial_gap", "out_of_bounds"):
        reasons.append(f"{winner_label} maintains 100% verified DTM coverage whereas {alt_label} suffers from {mA.coverage_status.replace('_', ' ')}")

    # Objective-specific rationale
    if objective == "slope_conscious":
        if mW.max_slope_deg < mA.max_slope_deg:
            reasons.append(f"lower maximum slope ({mW.max_slope_deg:.1f}° vs {mA.max_slope_deg:.1f}°)")
        if mW.steep_segments_ratio < mA.steep_segments_ratio:
            reasons.append(f"fewer steep segments >15° ({(mW.steep_segments_ratio * 100):.1f}% vs {(mA.steep_segments_ratio * 100):.1f}%)")
        if mW.average_slope_deg < mA.average_slope_deg:
            reasons.append(f"smoother mean gradient ({mW.average_slope_deg:.1f}° vs {mA.average_slope_deg:.1f}°)")

    elif objective == "energy_efficient":
        if mW.total_distance_m < mA.total_distance_m:
            diff_d = mA.total_distance_m - mW.total_distance_m
            reasons.append(f"{diff_d:.1f} m shorter traverse distance ({mW.total_distance_m:.1f} m vs {mA.total_distance_m:.1f} m)")
        if mW.total_gain_m < mA.total_gain_m:
            diff_g = mA.total_gain_m - mW.total_gain_m
            reasons.append(f"{diff_g:.1f} m less cumulative elevation gain against Mars gravity")
        if mW.estimated_work_kj < mA.estimated_work_kj:
            reasons.append(f"lower estimated mechanical work ({mW.estimated_work_kj:.1f} kJ vs {mA.estimated_work_kj:.1f} kJ)")

    elif objective == "data_confidence":
        if mW.coverage_ratio > mA.coverage_ratio:
            reasons.append(f"higher valid elevation sample ratio ({(mW.coverage_ratio * 100):.1f}% vs {(mA.coverage_ratio * 100):.1f}%)")
        if mW.coverage_status == "complete":
            reasons.append("complete stereo photogrammetry posting without NoData gaps")

    if not reasons:
        reasons.append("a balanced combination of slope moderation, path efficiency, and data integrity")

    # Counter-trade-off acknowledgment
    tradeoffs: List[str] = []
    if mW.total_distance_m > mA.total_distance_m:
        diff_d = mW.total_distance_m - mA.total_distance_m
        tradeoffs.append(f"requires {diff_d:.1f} m of additional traverse length")
    if mW.total_gain_m > mA.total_gain_m:
        diff_g = mW.total_gain_m - mA.total_gain_m
        tradeoffs.append(f"encounters {diff_g:.1f} m more elevation gain")
    if mW.max_slope_deg > mA.max_slope_deg:
        diff_s = mW.max_slope_deg - mA.max_slope_deg
        tradeoffs.append(f"has a slightly higher local peak slope (+{diff_s:.1f}°)")

    explanation = f"{winner_label} is preferred for this objective primarily due to " + ", ".join(reasons) + "."
    if tradeoffs:
        explanation += f" Operational trade-off: {winner_label} " + ", but ".join(tradeoffs) + "."

    return explanation
