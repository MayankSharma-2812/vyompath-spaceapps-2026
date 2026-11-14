/**
 * traverseIntelligence.ts — Mission-Aware Traverse Intelligence Engine.
 *
 * Implements multi-criteria evaluation of planetary rover traverse alternatives
 * under three operational mission profiles:
 *   1. slope_conscious: steep slope mitigation and mechanical tilt margins
 *   2. energy_efficient: path length, cumulative climb, and mechanical work proxy
 *   3. data_confidence: HiRISE stereo DTM coverage integrity and NoData minimization
 *
 * Provides both client-side deterministic evaluation for zero-latency UI reactivity
 * and remote backend evaluation fallback.
 */

import type { RouteAnalysisData } from '../map/types';

export type MissionObjective = 'slope_conscious' | 'energy_efficient' | 'data_confidence';

export interface MetricScoreBreakdown {
  slope_score: number;
  energy_score: number;
  confidence_score: number;
}

export interface RouteIntelligenceMetrics {
  total_distance_m: number;
  total_gain_m: number;
  total_loss_m: number;
  max_slope_deg: number;
  average_slope_deg: number;
  steep_segments_ratio: number;
  steep_segments_count: number;
  total_segments_count: number;
  valid_points_count: number;
  total_points_count: number;
  coverage_ratio: number;
  coverage_status: string;
  estimated_work_kj: number;
  dtm_source: string;
  is_mock: boolean;
}

export interface RouteEvaluation {
  route_id: string;
  label: string;
  overall_score: number;
  score_breakdown: MetricScoreBreakdown;
  metrics: RouteIntelligenceMetrics;
  advantages: string[];
  disadvantages: string[];
}

export interface TraverseIntelligenceResult {
  objective: MissionObjective;
  objective_title: string;
  objective_description: string;
  recommendation: 'route_a' | 'route_b' | 'tie' | 'single_route';
  summary_verdict: string;
  evidence_explanation: string;
  route_a?: RouteEvaluation | null;
  route_b?: RouteEvaluation | null;
  score_delta_b_minus_a?: number | null;
  scientific_disclaimers: string[];
}

export const OBJECTIVE_PROFILES: Record<
  MissionObjective,
  {
    title: string;
    icon: string;
    tagline: string;
    description: string;
    weights: { slope: number; energy: number; confidence: number };
  }
> = {
  slope_conscious: {
    title: 'Slope-Conscious Traverse',
    icon: '🏔️',
    tagline: 'Hazard Mitigation & Tilt Margins',
    description:
      'Prioritizes lower maximum slope, reduced average incline, and strict avoidance of steep scarps (>15°) to minimize rover slippage and mechanical wear.',
    weights: { slope: 0.6, energy: 0.2, confidence: 0.2 },
  },
  energy_efficient: {
    title: 'Energy-Efficient Traverse',
    icon: '⚡',
    tagline: 'Power Conservation & Minimum Work',
    description:
      'Prioritizes shorter path distance, minimal cumulative elevation gain against Mars gravity, and minimized total mechanical work expenditure.',
    weights: { slope: 0.2, energy: 0.6, confidence: 0.2 },
  },
  data_confidence: {
    title: 'Data-Confidence-First Traverse',
    icon: '🛰️',
    tagline: 'DTM Coverage & Blind-Drive Avoidance',
    description:
      'Prioritizes 100% verified HiRISE stereo DTM elevation coverage, penalizing NoData gaps, unmapped regions, and out-of-bounds blind rover traverses.',
    weights: { slope: 0.15, energy: 0.15, confidence: 0.7 },
  },
};

const MARS_G_M_S2 = 3.721;
const ROVER_MASS_KG = 1025.0; // Mars 2020 Perseverance class
const ROLLING_RESISTANCE_COEFF = 0.05; // Regolith rolling friction proxy

/**
 * Extracts and derives real analytical physical metrics from route analysis data.
 */
export function extractMetrics(route: RouteAnalysisData): RouteIntelligenceMetrics {
  const dist_m = Number.isFinite(route.total_distance_m) ? Math.max(0, route.total_distance_m) : 0;
  const gain_m = Number.isFinite(route.total_gain_m) ? Math.max(0, route.total_gain_m) : 0;
  const loss_m = Number.isFinite(route.total_loss_m) ? Math.max(0, route.total_loss_m) : 0;
  const max_slope = Number.isFinite(route.max_slope_deg) ? Math.max(0, route.max_slope_deg) : 0;
  const cov_status = route.coverage_status ?? 'not_applicable';
  const dtm_source = route.dtm_source ?? 'unknown';
  const is_mock = Boolean(route.is_mock || dtm_source.toLowerCase().includes('mock') || dtm_source.toLowerCase().includes('synthetic'));

  const profile = route.elevation_profile ?? [];
  const total_pts = profile.length;

  const valid_elevations: Array<[number, number]> = [];
  for (const pt of profile) {
    if (pt.elevation_m !== null && typeof pt.elevation_m === 'number' && Number.isFinite(pt.elevation_m)) {
      valid_elevations.push([pt.distance_m ?? 0, pt.elevation_m]);
    }
  }

  const valid_pts = valid_elevations.length;
  const cov_ratio = total_pts > 0 ? valid_pts / total_pts : 0;

  const segment_slopes: number[] = [];
  let steep_count = 0;

  for (let i = 0; i < valid_elevations.length - 1; i++) {
    const [d0, z0] = valid_elevations[i];
    const [d1, z1] = valid_elevations[i + 1];
    const step = d1 - d0;
    if (step > 0) {
      const dz = Math.abs(z1 - z0);
      const slope_deg = (Math.atan2(dz, step) * 180) / Math.PI;
      segment_slopes.push(slope_deg);
      if (slope_deg >= 15.0) {
        steep_count++;
      }
    }
  }

  const total_segments = segment_slopes.length;
  const avg_slope = total_segments > 0 ? segment_slopes.reduce((acc, v) => acc + v, 0) / total_segments : max_slope * 0.5;
  const steep_ratio = total_segments > 0 ? steep_count / total_segments : 0;

  // Mechanical energy proxy in kJ: Work against Martian gravity + rolling resistance
  const work_kj =
    (ROVER_MASS_KG * MARS_G_M_S2 * gain_m +
      ROLLING_RESISTANCE_COEFF * ROVER_MASS_KG * MARS_G_M_S2 * dist_m) /
    1000.0;

  return {
    total_distance_m: Number(dist_m.toFixed(2)),
    total_gain_m: Number(gain_m.toFixed(2)),
    total_loss_m: Number(loss_m.toFixed(2)),
    max_slope_deg: Number(max_slope.toFixed(2)),
    average_slope_deg: Number(avg_slope.toFixed(2)),
    steep_segments_ratio: Number(steep_ratio.toFixed(4)),
    steep_segments_count: steep_count,
    total_segments_count: total_segments,
    valid_points_count: valid_pts,
    total_points_count: total_pts,
    coverage_ratio: Number(cov_ratio.toFixed(4)),
    coverage_status: cov_status,
    estimated_work_kj: Number(work_kj.toFixed(2)),
    dtm_source,
    is_mock,
  };
}

/**
 * Normalizes incomparable metric units into bounded [0, 100] sub-scores.
 */
export function computeSubscores(metrics: RouteIntelligenceMetrics): MetricScoreBreakdown {
  // Slope score (30° max penalty threshold, 15° average threshold)
  const pen_max_slope = Math.min(100, (metrics.max_slope_deg / 30.0) * 100.0);
  const pen_steep_exposure = Math.min(100, metrics.steep_segments_ratio * 200.0);
  const pen_avg_slope = Math.min(100, (metrics.average_slope_deg / 15.0) * 100.0);

  let slope_score = Math.max(0, Math.min(100, 100.0 - (0.45 * pen_max_slope + 0.35 * pen_steep_exposure + 0.2 * pen_avg_slope)));

  // Energy score
  const pen_dist = Math.min(100, (metrics.total_distance_m / 4000.0) * 100.0);
  const pen_gain = Math.min(100, (metrics.total_gain_m / 200.0) * 100.0);
  const pen_work = Math.min(100, (metrics.estimated_work_kj / 1500.0) * 100.0);

  let energy_score = Math.max(0, Math.min(100, 100.0 - (0.4 * pen_dist + 0.4 * pen_gain + 0.2 * pen_work)));

  // Data confidence score
  let base_confidence = 100.0;
  if (metrics.coverage_status === 'complete') {
    base_confidence = 100.0;
  } else if (metrics.coverage_status === 'partial_gap') {
    base_confidence = 100.0 * metrics.coverage_ratio;
  } else if (metrics.coverage_status === 'out_of_bounds') {
    base_confidence = 0.0;
  } else {
    base_confidence = 40.0; // synthetic / mock mode baseline
  }

  const nodata_penalty = (1.0 - metrics.coverage_ratio) * 100.0;
  const confidence_score = Math.max(0, Math.min(100, base_confidence - 0.5 * nodata_penalty));

  if (metrics.coverage_status === 'out_of_bounds') {
    slope_score = 0.0;
    energy_score = Math.min(energy_score, 20.0);
  }

  return {
    slope_score: Number(slope_score.toFixed(1)),
    energy_score: Number(energy_score.toFixed(1)),
    confidence_score: Number(confidence_score.toFixed(1)),
  };
}

/**
 * Computes evaluation for a single route under a selected mission objective.
 */
export function evaluateSingleRoute(
  route: RouteAnalysisData,
  label: string,
  objective: MissionObjective,
): RouteEvaluation {
  const metrics = extractMetrics(route);
  const breakdown = computeSubscores(metrics);
  const weights = OBJECTIVE_PROFILES[objective].weights;

  const overall =
    weights.slope * breakdown.slope_score +
    weights.energy * breakdown.energy_score +
    weights.confidence * breakdown.confidence_score;

  const advantages: string[] = [];
  const disadvantages: string[] = [];

  // Slope
  if (metrics.max_slope_deg <= 10.0) {
    advantages.push(`Gentle maximum slope (${metrics.max_slope_deg.toFixed(1)}° ≤ 10° threshold)`);
  } else if (metrics.max_slope_deg >= 18.0) {
    disadvantages.push(`Steep maximum slope (${metrics.max_slope_deg.toFixed(1)}°) near tilt limits`);
  }

  if (metrics.steep_segments_ratio === 0.0) {
    advantages.push('Zero terrain segments exceeding 15° tilt threshold');
  } else if (metrics.steep_segments_ratio > 0.05) {
    disadvantages.push(`${(metrics.steep_segments_ratio * 100).toFixed(1)}% of traverse crosses steep slopes (>15°)`);
  }

  // Energy
  if (metrics.total_gain_m <= 15.0) {
    advantages.push(`Low cumulative vertical climb (${metrics.total_gain_m.toFixed(1)} m gain)`);
  } else if (metrics.total_gain_m >= 60.0) {
    disadvantages.push(`High elevation gain (${metrics.total_gain_m.toFixed(1)} m increases battery draw)`);
  }

  if (metrics.total_distance_m <= 1200.0) {
    advantages.push(`Short path length (${metrics.total_distance_m.toFixed(1)} m)`);
  } else if (metrics.total_distance_m >= 3000.0) {
    disadvantages.push(`Extended path length (${(metrics.total_distance_m / 1000).toFixed(2)} km)`);
  }

  // Coverage
  if (metrics.coverage_status === 'complete') {
    advantages.push('100% verified HiRISE stereo DTM elevation coverage');
  } else if (metrics.coverage_status === 'partial_gap') {
    disadvantages.push(`Uncovered NoData gaps present (${metrics.valid_points_count}/${metrics.total_points_count} valid samples)`);
  } else if (metrics.coverage_status === 'out_of_bounds') {
    disadvantages.push('Route lies completely outside calibrated HiRISE DTM boundary');
  } else if (metrics.is_mock) {
    disadvantages.push('Evaluated on synthetic mock elevation data (illustrative)');
  }

  if (advantages.length === 0) {
    advantages.push('Balanced traverse profile without critical single-metric standouts');
  }
  if (disadvantages.length === 0) {
    disadvantages.push('No critical hazard or operational red flags detected');
  }

  return {
    route_id: route.route_id || label,
    label,
    overall_score: Number(overall.toFixed(1)),
    score_breakdown: breakdown,
    metrics,
    advantages,
    disadvantages,
  };
}

/**
 * Generates transparent evidence reasoning based on measured metric deltas.
 */
function generateEvidence(
  winnerLabel: string,
  winner: RouteEvaluation,
  altLabel: string,
  alt: RouteEvaluation,
  objective: MissionObjective,
): string {
  const mW = winner.metrics;
  const mA = alt.metrics;
  const reasons: string[] = [];

  if (mW.coverage_status === 'complete' && (mA.coverage_status === 'partial_gap' || mA.coverage_status === 'out_of_bounds')) {
    reasons.push(`${winnerLabel} maintains 100% verified DTM coverage whereas ${altLabel} suffers from ${mA.coverage_status.replace('_', ' ')}`);
  }

  if (objective === 'slope_conscious') {
    if (mW.max_slope_deg < mA.max_slope_deg) {
      reasons.push(`lower maximum slope (${mW.max_slope_deg.toFixed(1)}° vs ${mA.max_slope_deg.toFixed(1)}°)`);
    }
    if (mW.steep_segments_ratio < mA.steep_segments_ratio) {
      reasons.push(`fewer steep segments >15° (${(mW.steep_segments_ratio * 100).toFixed(1)}% vs ${(mA.steep_segments_ratio * 100).toFixed(1)}%)`);
    }
    if (mW.average_slope_deg < mA.average_slope_deg) {
      reasons.push(`smoother mean gradient (${mW.average_slope_deg.toFixed(1)}° vs ${mA.average_slope_deg.toFixed(1)}°)`);
    }
  } else if (objective === 'energy_efficient') {
    if (mW.total_distance_m < mA.total_distance_m) {
      const diffD = mA.total_distance_m - mW.total_distance_m;
      reasons.push(`${diffD.toFixed(1)} m shorter traverse distance (${mW.total_distance_m.toFixed(1)} m vs ${mA.total_distance_m.toFixed(1)} m)`);
    }
    if (mW.total_gain_m < mA.total_gain_m) {
      const diffG = mA.total_gain_m - mW.total_gain_m;
      reasons.push(`${diffG.toFixed(1)} m less cumulative climb against Martian gravity`);
    }
    if (mW.estimated_work_kj < mA.estimated_work_kj) {
      reasons.push(`lower mechanical work proxy (${mW.estimated_work_kj.toFixed(1)} kJ vs ${mA.estimated_work_kj.toFixed(1)} kJ)`);
    }
  } else if (objective === 'data_confidence') {
    if (mW.coverage_ratio > mA.coverage_ratio) {
      reasons.push(`higher valid elevation sample ratio (${(mW.coverage_ratio * 100).toFixed(1)}% vs ${(mA.coverage_ratio * 100).toFixed(1)}%)`);
    }
    if (mW.coverage_status === 'complete') {
      reasons.push('complete stereo photogrammetry posting without NoData gaps');
    }
  }

  if (reasons.length === 0) {
    reasons.push('a balanced combination of slope moderation, path efficiency, and data integrity');
  }

  const tradeoffs: string[] = [];
  if (mW.total_distance_m > mA.total_distance_m) {
    const diffD = mW.total_distance_m - mA.total_distance_m;
    tradeoffs.push(`requires ${diffD.toFixed(1)} m of additional traverse length`);
  }
  if (mW.total_gain_m > mA.total_gain_m) {
    const diffG = mW.total_gain_m - mA.total_gain_m;
    tradeoffs.push(`encounters ${diffG.toFixed(1)} m more elevation gain`);
  }
  if (mW.max_slope_deg > mA.max_slope_deg) {
    const diffS = mW.max_slope_deg - mA.max_slope_deg;
    tradeoffs.push(`has a slightly higher local peak slope (+${diffS.toFixed(1)}°)`);
  }

  let text = `${winnerLabel} is preferred for this objective primarily due to ` + reasons.join(', ') + '.';
  if (tradeoffs.length > 0) {
    text += ` Operational trade-off: ${winnerLabel} ` + tradeoffs.join(', but ') + '.';
  }
  return text;
}

/**
 * Main evaluation orchestrator: compares Route A and Route B or provides single route assessment.
 */
export function evaluateTraverseIntelligenceLocal(
  routeA: RouteAnalysisData | null,
  routeB: RouteAnalysisData | null,
  objective: MissionObjective = 'slope_conscious',
): TraverseIntelligenceResult {
  const profile = OBJECTIVE_PROFILES[objective];
  const disclaimers: string[] = [
    'DECISION-SUPPORT PROTOTYPE: Not flight-certified rover autonomy. Metric scores are research models referencing HiRISE/MOLA data.',
    'TERRAIN INVARIANTS: Slopes are evaluated along 50m baseline windows. Micro-hazards (<1m rocks, sand ripples) require in-situ rover hazard avoidance cameras.',
  ];

  if (!routeA) {
    return {
      objective,
      objective_title: profile.title,
      objective_description: profile.description,
      recommendation: 'single_route',
      summary_verdict: 'No route available for evaluation.',
      evidence_explanation: 'Please draw a route on the Martian Surface Explorer or select a Jezero Crater corridor to compute mission-aware intelligence.',
      scientific_disclaimers: disclaimers,
    };
  }

  const evalA = evaluateSingleRoute(routeA, 'Route A', objective);

  if (evalA.metrics.is_mock) {
    disclaimers.unshift(
      'DEMONSTRATION MODE NOTICE: Evaluated on synthetic mock data. Elevation and slope metrics are illustrative and do not reflect real Martian terrain.',
    );
  }

  if (!routeB) {
    return {
      objective,
      objective_title: profile.title,
      objective_description: profile.description,
      recommendation: 'single_route',
      summary_verdict: `Route A scores ${evalA.overall_score.toFixed(1)}/100 under ${profile.title}. Max slope: ${evalA.metrics.max_slope_deg.toFixed(1)}°, Distance: ${evalA.metrics.total_distance_m.toFixed(1)} m.`,
      evidence_explanation: 'Single-route evaluation complete. To generate comparative traverse intelligence, pin an alternative route or load the Jezero Delta Scarp preset as Route B.',
      route_a: evalA,
      route_b: null,
      score_delta_b_minus_a: null,
      scientific_disclaimers: disclaimers,
    };
  }

  const evalB = evaluateSingleRoute(routeB, 'Route B', objective);
  const delta = Number((evalB.overall_score - evalA.overall_score).toFixed(1));

  let recommendation: 'route_a' | 'route_b' | 'tie' | 'single_route' = 'tie';
  let verdict = '';
  let evidence = '';

  if (Math.abs(delta) < 2.0) {
    recommendation = 'tie';
    verdict = `Routes exhibit near-parity under the ${profile.title} objective (Route A: ${evalA.overall_score.toFixed(1)}, Route B: ${evalB.overall_score.toFixed(1)}, Δ = ${delta > 0 ? `+${delta}` : delta}).`;
    evidence = `Neither route demonstrates a decisive operational advantage under current weights (score margin < 2.0 points). Route A spans ${evalA.metrics.total_distance_m.toFixed(1)} m (max slope ${evalA.metrics.max_slope_deg.toFixed(1)}°, climb ${evalA.metrics.total_gain_m.toFixed(1)} m) versus Route B at ${evalB.metrics.total_distance_m.toFixed(1)} m (max slope ${evalB.metrics.max_slope_deg.toFixed(1)}°, climb ${evalB.metrics.total_gain_m.toFixed(1)} m). Operational selection should depend on tactical ground obstacles or science targets.`;
  } else if (delta > 0) {
    recommendation = 'route_b';
    verdict = `Route B is recommended for ${profile.title} (Score: ${evalB.overall_score.toFixed(1)}/100, +${delta.toFixed(1)} vs Route A).`;
    evidence = generateEvidence('Route B', evalB, 'Route A', evalA, objective);
  } else {
    recommendation = 'route_a';
    verdict = `Route A is recommended for ${profile.title} (Score: ${evalA.overall_score.toFixed(1)}/100, +${Math.abs(delta).toFixed(1)} vs Route B).`;
    evidence = generateEvidence('Route A', evalA, 'Route B', evalB, objective);
  }

  return {
    objective,
    objective_title: profile.title,
    objective_description: profile.description,
    recommendation,
    summary_verdict: verdict,
    evidence_explanation: evidence,
    route_a: evalA,
    route_b: evalB,
    score_delta_b_minus_a: delta,
    scientific_disclaimers: disclaimers,
  };
}
