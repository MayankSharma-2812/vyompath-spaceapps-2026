/**
 * TraverseIntelligence.tsx — Mission-Aware Traverse Intelligence Dashboard Section.
 *
 * Provides multi-criteria decision support for rover traverses across 3 mission objectives:
 *   1. Slope-Conscious Traverse (mechanical tilt & scarp mitigation)
 *   2. Energy-Efficient Traverse (distance, vertical climb & work proxy)
 *   3. Data-Confidence-First Traverse (HiRISE stereo DTM coverage integrity)
 *
 * Implements transparent, explainable recommendations derived from actual measurements.
 */

import { useState, useMemo } from 'react';
import type { RouteAnalysisData } from '../map/types';
import {
  type MissionObjective,
  OBJECTIVE_PROFILES,
  evaluateTraverseIntelligenceLocal,
} from './traverseIntelligence';

interface TraverseIntelligenceProps {
  analysis: RouteAnalysisData | null;
  routeBAnalysis: RouteAnalysisData | null;
  isLoading?: boolean;
  onSetAsRouteB?: () => void;
  onLoadPresetAsRouteB?: (presetKey: string) => void;
}

export function TraverseIntelligence({
  analysis,
  routeBAnalysis,
  isLoading: _isLoading = false,
  onSetAsRouteB,
  onLoadPresetAsRouteB,
}: TraverseIntelligenceProps) {
  const [selectedObjective, setSelectedObjective] = useState<MissionObjective>('slope_conscious');

  // Compute multi-criteria evaluation instantly from measured route profiles
  const result = useMemo(() => {
    return evaluateTraverseIntelligenceLocal(analysis, routeBAnalysis, selectedObjective);
  }, [analysis, routeBAnalysis, selectedObjective]);

  const activeProfile = OBJECTIVE_PROFILES[selectedObjective];

  const getScoreColor = (score: number) => {
    if (score >= 80) return '#10b981'; // Green
    if (score >= 60) return '#f59e0b'; // Amber
    if (score >= 40) return '#ea580c'; // Orange
    return '#ef4444'; // Red
  };

  return (
    <section
      className="panel traverse-intelligence-panel"
      id="traverse-intelligence-section"
      aria-labelledby="traverse-intel-title"
      style={{
        marginTop: '16px',
        border: '1px solid #cbd5e1',
        borderRadius: '8px',
        background: '#ffffff',
      }}
    >
      {/* Header */}
      <div className="panel-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <span className="eyebrow" style={{ color: '#0284c7', fontWeight: 700, fontSize: '11px', letterSpacing: '0.06em' }}>
            MISSION DECISION SUPPORT · USP
          </span>
          <h2 id="traverse-intel-title" style={{ margin: '4px 0 0', fontSize: '16px', fontWeight: 700, color: '#0f172a' }}>
            Mission-Aware Traverse Intelligence
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#64748b', maxWidth: '680px', lineHeight: 1.4 }}>
            Evaluates alternative rover traverses against operational mission priorities using verified HiRISE DTM slopes, cumulative vertical climb, and photogrammetric coverage integrity.
          </p>
        </div>

        {/* Status Mode Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              padding: '4px 10px',
              borderRadius: '16px',
              fontSize: '11px',
              fontWeight: 600,
              background: result.route_a?.metrics.is_mock ? '#fef3c7' : '#ecfdf5',
              color: result.route_a?.metrics.is_mock ? '#92400e' : '#065f46',
              border: `1px solid ${result.route_a?.metrics.is_mock ? '#fcd34d' : '#a7f3d0'}`,
            }}
          >
            {result.route_a?.metrics.is_mock ? '⚠️ Synthetic / Demo Model' : '🛰️ HiRISE Raster Model'}
          </span>
        </div>
      </div>

      {/* Objective Selector Tabs */}
      <div
        role="tablist"
        aria-label="Mission Priorities"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '8px',
          margin: '14px 0',
        }}
      >
        {(Object.keys(OBJECTIVE_PROFILES) as MissionObjective[]).map((objKey) => {
          const prof = OBJECTIVE_PROFILES[objKey];
          const isSelected = selectedObjective === objKey;
          return (
            <button
              key={objKey}
              type="button"
              role="tab"
              aria-selected={isSelected}
              onClick={() => setSelectedObjective(objKey)}
              style={{
                padding: '10px 14px',
                textAlign: 'left',
                borderRadius: '6px',
                border: isSelected ? '2px solid #0284c7' : '1px solid #cbd5e1',
                background: isSelected ? '#f0f9ff' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.15s ease-in-out',
                display: 'flex',
                flexDirection: 'column',
                gap: '3px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 700, fontSize: '13px', color: isSelected ? '#0369a1' : '#1e293b' }}>
                  {prof.icon} {prof.title}
                </span>
                {isSelected && (
                  <span style={{ fontSize: '10px', fontWeight: 700, color: '#0284c7', background: '#e0f2fe', padding: '2px 6px', borderRadius: '4px' }}>
                    ACTIVE
                  </span>
                )}
              </div>
              <span style={{ fontSize: '11px', color: isSelected ? '#0284c7' : '#64748b' }}>
                {prof.tagline}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active Objective Summary Banner */}
      <div
        style={{
          padding: '10px 14px',
          background: '#f8fafc',
          borderLeft: '4px solid #0284c7',
          borderRadius: '4px',
          marginBottom: '16px',
          fontSize: '12px',
          color: '#334155',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ flex: '1 1 360px' }}>
          <strong>Objective Focus: </strong> {activeProfile.description}
        </div>
        <div style={{ fontSize: '11px', color: '#475569', display: 'flex', gap: '8px', fontFamily: 'monospace' }}>
          <span>Weights: Slope {(activeProfile.weights.slope * 100).toFixed(0)}%</span>
          <span>· Energy {(activeProfile.weights.energy * 100).toFixed(0)}%</span>
          <span>· Data {(activeProfile.weights.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>

      {/* Primary Recommendation Banner */}
      <div
        role="alert"
        aria-label="Traverse Recommendation"
        style={{
          padding: '14px 18px',
          borderRadius: '8px',
          border: '1px solid',
          marginBottom: '16px',
          background:
            result.recommendation === 'route_b'
              ? 'rgba(216, 138, 45, 0.08)'
              : result.recommendation === 'route_a'
                ? 'rgba(2, 132, 199, 0.08)'
                : '#f8fafc',
          borderColor:
            result.recommendation === 'route_b'
              ? '#d88a2d'
              : result.recommendation === 'route_a'
                ? '#0284c7'
                : '#cbd5e1',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
          <span style={{ fontSize: '18px' }}>
            {result.recommendation === 'route_a' || result.recommendation === 'route_b'
              ? '🏆'
              : result.recommendation === 'tie'
                ? '⚖️'
                : '📍'}
          </span>
          <h3
            style={{
              margin: 0,
              fontSize: '14px',
              fontWeight: 700,
              color:
                result.recommendation === 'route_b'
                  ? '#b45309'
                  : result.recommendation === 'route_a'
                    ? '#0369a1'
                    : '#0f172a',
            }}
          >
            {result.summary_verdict}
          </h3>
        </div>
        <p style={{ margin: 0, fontSize: '12.5px', lineHeight: 1.5, color: '#334155' }}>
          <strong>Analytical Evidence: </strong> {result.evidence_explanation}
        </p>
      </div>

      {/* Route Evaluation Cards (Route A vs Route B) */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '14px',
          marginBottom: '16px',
        }}
      >
        {/* Route A Card */}
        {result.route_a ? (
          <article
            style={{
              padding: '14px',
              border: `2px solid ${result.recommendation === 'route_a' ? '#0284c7' : '#e2e8f0'}`,
              borderRadius: '8px',
              background: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#0284c7', textTransform: 'uppercase' }}>
                  PRIMARY TRAVERSE
                </span>
                <h4 style={{ margin: '2px 0 0', fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
                  Route A ({result.route_a.route_id})
                </h4>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '22px', fontWeight: 800, color: getScoreColor(result.route_a.overall_score) }}>
                  {result.route_a.overall_score.toFixed(1)}
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#64748b' }}>/100</span>
                </div>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>MISSION-FIT SCORE</span>
              </div>
            </div>

            {/* Sub-Score Progress Bars */}
            <div style={{ display: 'grid', gap: '6px', margin: '12px 0', padding: '10px', background: '#f8fafc', borderRadius: '6px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Slope Hazard Mitigation ({Math.round(activeProfile.weights.slope * 100)}%)</span>
                  <strong>{result.route_a.score_breakdown.slope_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_a.score_breakdown.slope_score}%`, height: '100%', background: '#0284c7' }} />
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Energy Economy ({Math.round(activeProfile.weights.energy * 100)}%)</span>
                  <strong>{result.route_a.score_breakdown.energy_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_a.score_breakdown.energy_score}%`, height: '100%', background: '#10b981' }} />
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Data Confidence ({Math.round(activeProfile.weights.confidence * 100)}%)</span>
                  <strong>{result.route_a.score_breakdown.confidence_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_a.score_breakdown.confidence_score}%`, height: '100%', background: '#8b5cf6' }} />
                </div>
              </div>
            </div>

            {/* Tactical Measured Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', fontSize: '11px', marginBottom: '10px' }}>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Traverse Distance</div>
                <div style={{ fontWeight: 600 }}>{result.route_a.metrics.total_distance_m.toFixed(1)} m</div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Max / Avg Slope</div>
                <div style={{ fontWeight: 600 }}>
                  {result.route_a.metrics.max_slope_deg.toFixed(1)}° / {result.route_a.metrics.average_slope_deg.toFixed(1)}°
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Climb / Work Proxy</div>
                <div style={{ fontWeight: 600 }}>
                  {result.route_a.metrics.total_gain_m.toFixed(1)}m / {result.route_a.metrics.estimated_work_kj.toFixed(1)} kJ
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Steep Segments (&gt;15°)</div>
                <div style={{ fontWeight: 600 }}>
                  {(result.route_a.metrics.steep_segments_ratio * 100).toFixed(1)}% ({result.route_a.metrics.steep_segments_count})
                </div>
              </div>
            </div>

            {/* Pros & Cons */}
            <div style={{ fontSize: '11px', display: 'grid', gap: '4px' }}>
              {result.route_a.advantages.map((adv, idx) => (
                <div key={idx} style={{ color: '#166534', display: 'flex', gap: '6px' }}>
                  <span>✓</span> <span>{adv}</span>
                </div>
              ))}
              {result.route_a.disadvantages.map((dis, idx) => (
                <div key={idx} style={{ color: '#991b1b', display: 'flex', gap: '6px' }}>
                  <span>✗</span> <span>{dis}</span>
                </div>
              ))}
            </div>
          </article>
        ) : (
          <div style={{ padding: '24px', textAlign: 'center', background: '#f8fafc', borderRadius: '8px' }}>
            No Route A loaded. Draw a route on the map or select a corridor.
          </div>
        )}

        {/* Route B Card */}
        {result.route_b ? (
          <article
            style={{
              padding: '14px',
              border: `2px solid ${result.recommendation === 'route_b' ? '#d88a2d' : '#e2e8f0'}`,
              borderRadius: '8px',
              background: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
              <div>
                <span style={{ fontSize: '11px', fontWeight: 700, color: '#d88a2d', textTransform: 'uppercase' }}>
                  COMPARISON TRAVERSE
                </span>
                <h4 style={{ margin: '2px 0 0', fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
                  Route B ({result.route_b.route_id})
                </h4>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '22px', fontWeight: 800, color: getScoreColor(result.route_b.overall_score) }}>
                  {result.route_b.overall_score.toFixed(1)}
                  <span style={{ fontSize: '12px', fontWeight: 500, color: '#64748b' }}>/100</span>
                </div>
                <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>MISSION-FIT SCORE</span>
              </div>
            </div>

            {/* Sub-Score Progress Bars */}
            <div style={{ display: 'grid', gap: '6px', margin: '12px 0', padding: '10px', background: '#f8fafc', borderRadius: '6px' }}>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Slope Hazard Mitigation ({Math.round(activeProfile.weights.slope * 100)}%)</span>
                  <strong>{result.route_b.score_breakdown.slope_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_b.score_breakdown.slope_score}%`, height: '100%', background: '#d88a2d' }} />
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Energy Economy ({Math.round(activeProfile.weights.energy * 100)}%)</span>
                  <strong>{result.route_b.score_breakdown.energy_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_b.score_breakdown.energy_score}%`, height: '100%', background: '#10b981' }} />
                </div>
              </div>
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', marginBottom: '2px' }}>
                  <span>Data Confidence ({Math.round(activeProfile.weights.confidence * 100)}%)</span>
                  <strong>{result.route_b.score_breakdown.confidence_score.toFixed(1)}/100</strong>
                </div>
                <div style={{ height: '6px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${result.route_b.score_breakdown.confidence_score}%`, height: '100%', background: '#8b5cf6' }} />
                </div>
              </div>
            </div>

            {/* Tactical Measured Metrics */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', fontSize: '11px', marginBottom: '10px' }}>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Traverse Distance</div>
                <div style={{ fontWeight: 600 }}>{result.route_b.metrics.total_distance_m.toFixed(1)} m</div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Max / Avg Slope</div>
                <div style={{ fontWeight: 600 }}>
                  {result.route_b.metrics.max_slope_deg.toFixed(1)}° / {result.route_b.metrics.average_slope_deg.toFixed(1)}°
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Climb / Work Proxy</div>
                <div style={{ fontWeight: 600 }}>
                  {result.route_b.metrics.total_gain_m.toFixed(1)}m / {result.route_b.metrics.estimated_work_kj.toFixed(1)} kJ
                </div>
              </div>
              <div style={{ padding: '6px 8px', background: '#f1f5f9', borderRadius: '4px' }}>
                <div style={{ color: '#64748b' }}>Steep Segments (&gt;15°)</div>
                <div style={{ fontWeight: 600 }}>
                  {(result.route_b.metrics.steep_segments_ratio * 100).toFixed(1)}% ({result.route_b.metrics.steep_segments_count})
                </div>
              </div>
            </div>

            {/* Pros & Cons */}
            <div style={{ fontSize: '11px', display: 'grid', gap: '4px' }}>
              {result.route_b.advantages.map((adv, idx) => (
                <div key={idx} style={{ color: '#166534', display: 'flex', gap: '6px' }}>
                  <span>✓</span> <span>{adv}</span>
                </div>
              ))}
              {result.route_b.disadvantages.map((dis, idx) => (
                <div key={idx} style={{ color: '#991b1b', display: 'flex', gap: '6px' }}>
                  <span>✗</span> <span>{dis}</span>
                </div>
              ))}
            </div>
          </article>
        ) : (
          <article
            style={{
              padding: '24px 18px',
              border: '2px dashed #cbd5e1',
              borderRadius: '8px',
              background: '#f8fafc',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '28px', marginBottom: '8px' }}>📌</div>
            <h4 style={{ margin: '0 0 6px', fontSize: '14px', fontWeight: 700, color: '#334155' }}>
              No Route B Pinned For Comparison
            </h4>
            <p style={{ margin: '0 0 14px', fontSize: '12px', color: '#64748b', maxWidth: '300px', lineHeight: 1.4 }}>
              Compare Route A against an alternative path to unlock comparative intelligence and automated trade-off evidence.
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
              {onLoadPresetAsRouteB && (
                <button
                  type="button"
                  onClick={() => onLoadPresetAsRouteB('jezeroDelta')}
                  style={{
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontWeight: 600,
                    borderRadius: '4px',
                    border: '1px solid #d88a2d',
                    background: '#fef3c7',
                    color: '#92400e',
                    cursor: 'pointer',
                  }}
                >
                  ⚡ Compare with Delta Scarp
                </button>
              )}
              {analysis && onSetAsRouteB && (
                <button
                  type="button"
                  onClick={onSetAsRouteB}
                  style={{
                    padding: '6px 12px',
                    fontSize: '11px',
                    fontWeight: 600,
                    borderRadius: '4px',
                    border: '1px solid #cbd5e1',
                    background: '#ffffff',
                    color: '#475569',
                    cursor: 'pointer',
                  }}
                >
                  📌 Pin Route A as Route B
                </button>
              )}
            </div>
          </article>
        )}
      </div>

      {/* Disclaimers & Methodology Constraints */}
      <footer
        style={{
          padding: '10px 14px',
          background: '#f1f5f9',
          border: '1px solid #e2e8f0',
          borderRadius: '6px',
          fontSize: '11px',
          color: '#475569',
        }}
      >
        <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
          Planetary Engineering Constraints & Disclaimers:
        </div>
        <ul style={{ margin: 0, paddingLeft: '16px', lineHeight: 1.5 }}>
          {result.scientific_disclaimers.map((disc, idx) => (
            <li key={idx}>{disc}</li>
          ))}
          <li>
            <strong>Physical Model Reference:</strong> Mars gravity g = 3.721 m/s², Mars 2020 Perseverance mass baseline (m = 1025 kg), rolling resistance friction proxy Crr = 0.05.
          </li>
        </ul>
      </footer>
    </section>
  );
}
