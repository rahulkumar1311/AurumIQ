import React, { useState, useEffect, useCallback } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import {
  Sliders,
  Activity,
  Zap,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  RefreshCw,
  Calendar,
  TrendingUp,
  Scale,
  ShieldAlert,
  Info,
  Layers,
  TrendingDown
} from 'lucide-react';
import EmptyState from '../components/EmptyState';

const CONTRACTS = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];

export default function HistoricalSpreadAnalysis({
  hasData,
  onLoadSample,
  onGoToUpload,
  loadingAction
}) {
  // Selection State
  const [pairA, setPairA] = useState('GOLDM');
  const [expiryA, setExpiryA] = useState('');
  const [pairB, setPairB] = useState('GOLDPETAL');
  const [expiryB, setExpiryB] = useState('');

  // Configuration Parameters
  const [lookback, setLookback] = useState(20);
  const [zThreshold, setZThreshold] = useState(2.0);
  const [exitThreshold, setExitThreshold] = useState(0.5);
  const [minObservations, setMinObservations] = useState(10);
  const [purityAdjusted, setPurityAdjusted] = useState(false);

  // UI state
  const [activeChartTab, setActiveChartTab] = useState('all');
  const [availableExpiries, setAvailableExpiries] = useState({});
  const [spreadData, setSpreadData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Fetch available contract expiries
  useEffect(() => {
    if (!hasData) {
      setAvailableExpiries({});
      setSpreadData(null);
      return;
    }
    const fetchExpiries = async () => {
      try {
        const res = await fetch('/api/expiries');
        if (res.ok) {
          const json = await res.json();
          setAvailableExpiries(json.expiries || {});
        }
      } catch (err) {
        console.error('Failed to fetch contract expiries:', err);
      }
    };
    fetchExpiries();
  }, [hasData]);

  // Fetch relative-value spread analytics
  const fetchSpreads = useCallback(async () => {
    if (!hasData) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const params = new URLSearchParams({
        pair_a: pairA,
        pair_b: pairB,
        lookback: String(lookback),
        purity_adjusted: String(purityAdjusted),
        z_threshold: String(zThreshold),
        exit_threshold: String(exitThreshold),
        min_observations: String(minObservations)
      });
      if (expiryA) params.append('expiry_a', expiryA);
      if (expiryB) params.append('expiry_b', expiryB);

      const res = await fetch(`/api/spreads?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const json = await res.json();
      setSpreadData(json);
    } catch (err) {
      console.error('Failed to fetch spread analytics:', err);
      setErrorMsg('Failed to fetch relative-value analytics. Please check backend connection.');
    } finally {
      setLoading(false);
    }
  }, [
    hasData,
    pairA,
    expiryA,
    pairB,
    expiryB,
    lookback,
    purityAdjusted,
    zThreshold,
    exitThreshold,
    minObservations
  ]);

  useEffect(() => {
    fetchSpreads();
  }, [fetchSpreads]);

  // Apply Presets
  const applyPreset = (lb, z, ex) => {
    setLookback(lb);
    setZThreshold(z);
    setExitThreshold(ex);
  };

  if (!hasData) {
    return (
      <EmptyState
        title="Cross-Contract Relative-Value Analytics — Awaiting Market Data"
        description="Select eligible contracts and specific expiries to analyze normalized settlement prices, rolling z-scores, transaction friction barriers, and point-in-time mean-reversion signals."
        onLoadSample={onLoadSample}
        onGoToUpload={onGoToUpload}
        loadingAction={loadingAction}
      />
    );
  }

  const series = spreadData?.series || [];
  const stats = spreadData?.statistics;
  const signal = spreadData?.signal;
  const warnings = spreadData?.data_quality_warnings || [];
  const expiriesA = availableExpiries[pairA] || [];
  const expiriesB = availableExpiries[pairB] || [];

  // Determine signal badge color styling
  const isActionable = signal?.is_actionable;
  const signalType = signal?.signal_type || 'NO_SIGNAL';
  let signalBadgeClass = 'badge badge-neutral';
  if (isActionable) {
    signalBadgeClass = signalType === 'LONG_SPREAD' ? 'badge badge-green' : 'badge badge-red';
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Institutional Metadata & Verification Bar */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.75rem 1.25rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        boxShadow: 'var(--shadow-sm)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <ShieldAlert size={18} style={{ color: 'var(--gold-600)' }} />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Statistical Relative Spread Engine • Zero Look-Ahead Bias
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Active Pair: <strong>{pairA}</strong> ({expiryA || 'Near-Month'}) vs <strong>{pairB}</strong> ({expiryB || 'Near-Month'}) • Rolling Window: {lookback}d
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span className="badge badge-gold mono">
            <Calendar size={11} style={{ marginRight: '0.25rem' }} />
            Session Date: {signal?.timestamp?.slice(0, 10) || 'Active'}
          </span>
          <span className="badge badge-neutral">
            Source: <a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'underline', marginLeft: '0.25rem' }}>
              mcxindia.com
            </a>
          </span>
        </div>
      </div>

      {errorMsg && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          padding: '0.75rem 1rem',
          color: '#991b1b',
          fontSize: '0.825rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Parameter Controls Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Sliders size={17} style={{ color: 'var(--gold-600)' }} />
            Contract Selection & Relative-Value Model Calibration
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Presets:</span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => applyPreset(20, 2.0, 0.5)}
              title="20-day lookback, ±2.0σ entry"
            >
              Standard (20d, ±2.0σ)
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => applyPreset(10, 1.5, 0.3)}
              title="10-day lookback, ±1.5σ entry"
            >
              High-Sensitivity (10d, ±1.5σ)
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => applyPreset(30, 2.5, 0.5)}
              title="30-day lookback, ±2.5σ entry"
            >
              Conservative (30d, ±2.5σ)
            </button>
            {loading && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', color: 'var(--gold-700)' }}>
                <RefreshCw size={13} className="spin" /> Calculating...
              </span>
            )}
          </div>
        </div>

        <div className="card-body">
          {/* Row 1: Contract & Expiry Selection */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Scale size={13} style={{ color: 'var(--gold-600)' }} />
                Leg A (Benchmark Contract)
              </label>
              <select
                className="form-select"
                value={pairA}
                onChange={(e) => {
                  setPairA(e.target.value);
                  setExpiryA(''); // Reset to near-month on contract change
                }}
              >
                {CONTRACTS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Calendar size={13} style={{ color: 'var(--gold-600)' }} />
                Leg A Expiry Date
              </label>
              <select
                className="form-select"
                value={expiryA}
                onChange={(e) => setExpiryA(e.target.value)}
              >
                <option value="">Near-Month (Dynamic Min DTE)</option>
                {expiriesA.map((exp) => (
                  <option key={exp} value={exp}>{exp}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Scale size={13} style={{ color: 'var(--info-blue)' }} />
                Leg B (Relative Contract)
              </label>
              <select
                className="form-select"
                value={pairB}
                onChange={(e) => {
                  setPairB(e.target.value);
                  setExpiryB(''); // Reset to near-month on contract change
                }}
              >
                {CONTRACTS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Calendar size={13} style={{ color: 'var(--info-blue)' }} />
                Leg B Expiry Date
              </label>
              <select
                className="form-select"
                value={expiryB}
                onChange={(e) => setExpiryB(e.target.value)}
              >
                <option value="">Near-Month (Dynamic Min DTE)</option>
                {expiriesB.map((exp) => (
                  <option key={exp} value={exp}>{exp}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Row 2: Configurable Quantitative Parameters */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1.25rem', alignItems: 'center', background: '#f8fafc', padding: '1rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                <span>Rolling Lookback Window</span>
                <span className="mono" style={{ color: 'var(--gold-700)' }}>{lookback} Days</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                step="5"
                value={lookback}
                onChange={(e) => setLookback(Number(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                <span>Signal Entry Threshold (Z)</span>
                <span className="mono" style={{ color: '#dc2626' }}>±{zThreshold.toFixed(1)}σ</span>
              </div>
              <input
                type="range"
                min="1.0"
                max="3.5"
                step="0.1"
                value={zThreshold}
                onChange={(e) => setZThreshold(Number(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                <span>Signal Exit Threshold (Z)</span>
                <span className="mono" style={{ color: '#2563eb' }}>±{exitThreshold.toFixed(1)}σ</span>
              </div>
              <input
                type="range"
                min="0.1"
                max="1.5"
                step="0.1"
                value={exitThreshold}
                onChange={(e) => setExitThreshold(Number(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.775rem', fontWeight: 600, marginBottom: '0.3rem' }}>
                <span>Min Valid Observations</span>
                <span className="mono">{minObservations} Bars</span>
              </div>
              <input
                type="range"
                min="5"
                max="30"
                step="1"
                value={minObservations}
                onChange={(e) => setMinObservations(Number(e.target.value))}
                style={{ width: '100%', cursor: 'pointer' }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'center' }}>
              <label className="toggle-label" style={{ fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={purityAdjusted}
                  onChange={(e) => setPurityAdjusted(e.target.checked)}
                />
                <span style={{ fontWeight: 500 }}>Purity-Adjusted (999 Fine)</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Institutional Compliance Disclaimer Banner */}
      <div style={{
        background: '#f8fafc',
        border: '1px solid #cbd5e1',
        borderLeft: '4px solid #d97706',
        borderRadius: '6px',
        padding: '0.75rem 1.25rem',
        fontSize: '0.775rem',
        color: '#334155',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        <ShieldAlert size={20} style={{ color: '#d97706', flexShrink: 0 }} />
        <div>
          <strong style={{ color: '#0f172a' }}>ANALYTICAL INFORMATION ONLY — NOT A GUARANTEED TRADE RECOMMENDATION: </strong>
          Statistical mispricing indicators and rolling z-scores do not guarantee price convergence or risk-free arbitrage. Realized basis can diverge further due to physical delivery frictions, margin variation, liquidity shocks, and financing carry rate shifts.
        </div>
      </div>

      {/* Diagnostic Signal & Reference Prices Panel */}
      {signal && (
        <div className="card" style={{ borderTop: `3px solid ${isActionable ? (signalType === 'LONG_SPREAD' ? 'var(--bull-green)' : 'var(--bear-red)') : '#94a3b8'}` }}>
          <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <Zap size={18} style={{ color: isActionable ? (signalType === 'LONG_SPREAD' ? 'var(--bull-green)' : 'var(--bear-red)') : '#64748b' }} />
              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Relative-Value Analytical Output
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.15rem' }}>
                  <span className={signalBadgeClass} style={{ fontSize: '0.95rem', padding: '0.25rem 0.65rem' }}>
                    {signal.signal_label}
                  </span>
                  <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Session Timestamp: {signal.timestamp}
                  </span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className={`badge ${signal.spread_metrics?.is_executable_opportunity ? 'badge-green' : 'badge-neutral'}`} style={{ fontSize: '0.75rem' }}>
                {signal.spread_metrics?.is_executable_opportunity
                  ? `Executable Edge: +₹${signal.spread_metrics?.net_executable_spread?.toFixed(2)}/10g`
                  : 'Observed Pricing Difference Only (Non-Executable)'}
              </span>
            </div>
          </div>

          <div className="card-body">
            {/* Reference Prices Table */}
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.45rem' }}>
                Underlying Reference Settlement Prices & Contract Liquidity
              </div>
              <div className="table-wrapper">
                <table className="fin-table">
                  <thead>
                    <tr>
                      <th>Leg Role</th>
                      <th>Contract</th>
                      <th>Maturity Expiry</th>
                      <th>DTE</th>
                      <th>Raw MCX Close</th>
                      <th>Normalized Price (₹/10g)</th>
                      <th>Trading Volume</th>
                      <th>Open Interest</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><span className="badge badge-gold">Leg A (Benchmark)</span></td>
                      <td style={{ fontWeight: 600 }}>{signal.reference_prices?.symbol_a?.symbol}</td>
                      <td className="mono">{signal.reference_prices?.symbol_a?.expiry}</td>
                      <td className="mono">{signal.reference_prices?.symbol_a?.dte}d</td>
                      <td className="mono">₹{signal.reference_prices?.symbol_a?.raw_close?.toFixed(2)}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>₹{signal.reference_prices?.symbol_a?.normalized_price_10g?.toFixed(2)}</td>
                      <td className="mono">{signal.reference_prices?.symbol_a?.volume?.toLocaleString()} lots</td>
                      <td className="mono">{signal.reference_prices?.symbol_a?.open_interest?.toLocaleString()}</td>
                    </tr>
                    <tr>
                      <td><span className="badge badge-neutral">Leg B (Relative)</span></td>
                      <td style={{ fontWeight: 600 }}>{signal.reference_prices?.symbol_b?.symbol}</td>
                      <td className="mono">{signal.reference_prices?.symbol_b?.expiry}</td>
                      <td className="mono">{signal.reference_prices?.symbol_b?.dte}d</td>
                      <td className="mono">₹{signal.reference_prices?.symbol_b?.raw_close?.toFixed(2)}</td>
                      <td className="mono" style={{ fontWeight: 600 }}>₹{signal.reference_prices?.symbol_b?.normalized_price_10g?.toFixed(2)}</td>
                      <td className="mono">{signal.reference_prices?.symbol_b?.volume?.toLocaleString()} lots</td>
                      <td className="mono">{signal.reference_prices?.symbol_b?.open_interest?.toLocaleString()}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Microstructure Breakdown: Observed vs Executable Opportunity */}
            <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
              {/* Left Column: Mathematical Spread Decomposition */}
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Layers size={14} style={{ color: 'var(--gold-600)' }} />
                  Observed Spread vs. Executable Friction Accounting
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem', fontSize: '0.825rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed #f1f5f9', paddingBottom: '0.3rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Observed Gross Spread (A - B):</span>
                    <span className="mono" style={{ fontWeight: 600 }}>
                      {signal.spread_metrics?.gross_spread >= 0 ? `+₹${signal.spread_metrics?.gross_spread?.toFixed(2)}` : `-₹${Math.abs(signal.spread_metrics?.gross_spread).toFixed(2)}`} / 10g
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400, marginLeft: '0.35rem' }}>
                        ({signal.spread_metrics?.pct_spread > 0 ? `+${signal.spread_metrics?.pct_spread}` : signal.spread_metrics?.pct_spread}%)
                      </span>
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed #f1f5f9', paddingBottom: '0.3rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Theoretical Calendar Carry Drag (6.5% p.a.):</span>
                    <span className="mono">₹{signal.spread_metrics?.calendar_carry_drag?.toFixed(2)} / 10g</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed #f1f5f9', paddingBottom: '0.3rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Maturity-Adjusted Residual Spread:</span>
                    <span className="mono" style={{ fontWeight: 600 }}>₹{signal.spread_metrics?.maturity_adjusted_spread?.toFixed(2)} / 10g</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px dashed #f1f5f9', paddingBottom: '0.3rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Estimated Round-Trip Friction (Turnover + CTT + Stamp + Slippage):</span>
                    <span className="mono" style={{ color: '#dc2626' }}>₹{signal.spread_metrics?.estimated_friction?.toFixed(2)} / 10g</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.3rem', fontSize: '0.9rem', fontWeight: 700 }}>
                    <span>Estimated Net Executable Edge:</span>
                    <span className="mono" style={{ color: signal.spread_metrics?.net_executable_spread > 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                      {signal.spread_metrics?.net_executable_spread > 0 ? `+₹${signal.spread_metrics?.net_executable_spread?.toFixed(2)}` : `₹${signal.spread_metrics?.net_executable_spread?.toFixed(2)}`} / 10g
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Diagnostic Reasoning */}
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '6px', padding: '1rem' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '0.65rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Info size={14} style={{ color: 'var(--info-blue)' }} />
                  Point-in-Time Diagnostic Reasoning
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '0.8rem', color: '#1e293b', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                  {signal.reasons?.map((reason, idx) => (
                    <li key={idx} style={{ lineHeight: 1.45 }}>{reason}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Data-Quality Warnings Section */}
            {warnings.length > 0 && (
              <div style={{
                background: '#fffbeb',
                border: '1px solid #fde68a',
                borderRadius: '6px',
                padding: '0.85rem 1.15rem',
                fontSize: '0.8rem',
                color: '#92400e'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem', fontWeight: 600, marginBottom: '0.35rem' }}>
                  <AlertTriangle size={15} style={{ color: '#d97706' }} />
                  Data Quality & Microstructure Pipeline Warnings ({warnings.length})
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                  {warnings.map((w, idx) => (
                    <li key={idx}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Statistical KPIs Grid */}
      {!stats && series.length > 0 && (
        <div className="card" style={{ padding: '1.25rem 1.5rem', background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, marginBottom: '0.35rem', fontSize: '0.9rem' }}>
            <AlertTriangle size={18} style={{ color: '#d97706' }} />
            Insufficient Historical Observations for Statistical Parameter Estimation
          </div>
          <p style={{ fontSize: '0.8rem', lineHeight: 1.5, margin: 0 }}>
            Only <strong>{series.length}</strong> overlapping trading session(s) detected for {pairA} vs {pairB}. A minimum of <strong>{minObservations}</strong> concurrent trading sessions is strictly required to calculate rolling mean (&mu;), standard deviation (&sigma;), and Z-scores. AurumIQ adheres to zero fabrication principles: rolling indicators and signals remain blocked until sufficient real observations exist.
          </p>
        </div>
      )}

      {stats && (
        <div className="grid-4">
          <div className="stat-tile">
            <div className="stat-label">
              <span>Current Normalized Spread</span>
              <Activity size={14} style={{ color: 'var(--gold-600)' }} />
            </div>
            <div className="stat-value mono">
              {stats.current_spread >= 0 ? `+₹${stats.current_spread.toFixed(2)}` : `-₹${Math.abs(stats.current_spread).toFixed(2)}`}
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}> /10g</span>
            </div>
            <div className="stat-sub">
              <span>Hist. Mean: ₹{stats.mean_spread?.toFixed(2)} (±₹{stats.std_spread?.toFixed(2)})</span>
            </div>
          </div>

          <div className="stat-tile">
            <div className="stat-label">
              <span>Point-in-Time Z-Score</span>
              <Zap size={14} style={{ color: 'var(--info-blue)' }} />
            </div>
            <div className="stat-value mono">
              <span className={Math.abs(stats.current_z_score) >= zThreshold ? (stats.current_z_score > 0 ? 'badge badge-red' : 'badge badge-green') : 'badge badge-neutral'} style={{ fontSize: '1.2rem' }}>
                {stats.current_z_score > 0 ? `+${stats.current_z_score.toFixed(2)}σ` : `${stats.current_z_score.toFixed(2)}σ`}
              </span>
            </div>
            <div className="stat-sub">
              <span>Percentile Rank: <strong>{stats.percentile_rank}%</strong></span>
            </div>
          </div>

          <div className="stat-tile">
            <div className="stat-label">
              <span>O-U Half-Life Speed</span>
              <CheckCircle2 size={14} style={{ color: 'var(--bull-green)' }} />
            </div>
            <div className="stat-value mono">
              {stats.half_life_days !== null ? `${stats.half_life_days} Days` : 'N/A'}
            </div>
            <div className="stat-sub">
              <span>Ornstein-Uhlenbeck Reversion Rate</span>
            </div>
          </div>

          <div className="stat-tile">
            <div className="stat-label">
              <span>ADF Cointegration Test</span>
              <AlertCircle size={14} style={{ color: stats.is_stationary_5pct ? 'var(--bull-green)' : 'var(--bear-red)' }} />
            </div>
            <div className="stat-value mono">
              <span className={stats.is_stationary_5pct ? 'badge badge-green' : 'badge badge-red'}>
                t = {stats.adf_t_statistic}
              </span>
            </div>
            <div className="stat-sub">
              <span>{stats.is_stationary_5pct ? 'Stationary at 5% (< -2.89)' : 'Non-Stationary Unit Root'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Visual Analytics Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '0.25rem' }}>
        <button
          className={`btn btn-sm ${activeChartTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveChartTab('all')}
        >
          All Relative-Value Analytics
        </button>
        <button
          className={`btn btn-sm ${activeChartTab === 'prices' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveChartTab('prices')}
        >
          Normalized Settlement Prices
        </button>
        <button
          className={`btn btn-sm ${activeChartTab === 'spread' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveChartTab('spread')}
        >
          Spread & Bollinger Bands
        </button>
        <button
          className={`btn btn-sm ${activeChartTab === 'zscore' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveChartTab('zscore')}
        >
          Standardized Z-Score Oscillator
        </button>
        <button
          className={`btn btn-sm ${activeChartTab === 'pct' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveChartTab('pct')}
        >
          Percentage Premium / Discount
        </button>
      </div>

      {/* Empty State when series has no overlapping trading dates */}
      {series.length === 0 && !loading && (
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <AlertTriangle size={36} style={{ color: 'var(--gold-600)', margin: '0 auto 0.75rem' }} />
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.4rem' }}>
            No Overlapping Trading Dates Available
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 540, margin: '0 auto 0.75rem' }}>
            The selected expiry combination ({pairA} {expiryA || 'Near-Month'} and {pairB} {expiryB || 'Near-Month'}) does not share sufficient concurrent trading sessions in the local database.
          </p>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Try selecting a different contract expiry or using default Near-Month contracts to analyze relative value.
          </span>
        </div>
      )}

      {/* Chart 1: Normalized Settlement Prices of Contract A vs Contract B */}
      {series.length > 0 && (activeChartTab === 'all' || activeChartTab === 'prices') && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <TrendingUp size={16} style={{ color: 'var(--gold-600)' }} />
              Normalized Settlement Prices Over Time ({pairA} vs {pairB} in ₹ per 10 grams)
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Uniform 10g Base {purityAdjusted ? '(999 Fine Equivalent)' : '(Official MCX Quotation)'}
            </span>
          </div>
          <div className="card-body">
            <div style={{ width: '100%', height: 320 }}>
              <ResponsiveContainer>
                <LineChart data={series} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => val.slice(5)} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `₹${v.toLocaleString()}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', fontSize: '12px', borderRadius: '6px' }}
                    formatter={(val, name) => [`₹${Number(val).toFixed(2)} / 10g`, name]}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Line type="monotone" dataKey="price_a" stroke="#d97706" strokeWidth={2.2} dot={false} name={`${pairA} Normalized`} />
                  <Line type="monotone" dataKey="price_b" stroke="#2563eb" strokeWidth={2.2} dot={false} name={`${pairB} Normalized`} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Chart 2: Relative Spread & Bollinger Volatility Bands */}
      {series.length > 0 && (activeChartTab === 'all' || activeChartTab === 'spread') && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Activity size={16} style={{ color: 'var(--gold-600)' }} />
              Relative Spread Series & Rolling Bollinger Volatility Bands ({pairA} minus {pairB})
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span className="badge badge-neutral mono">Lookback: {lookback}d</span>
              <span className="badge badge-neutral mono">Bands: ±{zThreshold.toFixed(1)}σ</span>
            </div>
          </div>
          <div className="card-body">
            <div style={{ width: '100%', height: 330 }}>
              <ResponsiveContainer>
                <LineChart data={series} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => val.slice(5)} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `₹${v.toFixed(0)}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', fontSize: '12px', borderRadius: '6px' }}
                    formatter={(val, name) => [`₹${Number(val).toFixed(2)} / 10g`, name]}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Line type="monotone" dataKey="spread" stroke="#0f172a" strokeWidth={2.4} dot={false} name="Spread (A - B)" />
                  <Line type="monotone" dataKey="rolling_mean" stroke="#d97706" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="Rolling Mean (μ)" />
                  <Line type="monotone" dataKey="upper_band" stroke="#ef4444" strokeWidth={1.3} strokeDasharray="3 3" dot={false} name={`Upper Band (+${zThreshold.toFixed(1)}σ)`} />
                  <Line type="monotone" dataKey="lower_band" stroke="#10b981" strokeWidth={1.3} strokeDasharray="3 3" dot={false} name={`Lower Band (-${zThreshold.toFixed(1)}σ)`} />
                  <Line type="monotone" dataKey="upper_1s" stroke="#fca5a5" strokeWidth={0.9} strokeDasharray="1 1" dot={false} name="Upper (+1σ)" />
                  <Line type="monotone" dataKey="lower_1s" stroke="#6ee7b7" strokeWidth={0.9} strokeDasharray="1 1" dot={false} name="Lower (-1σ)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Chart 3: Standardized Rolling Z-Score Oscillator */}
      {series.length > 0 && (activeChartTab === 'all' || activeChartTab === 'zscore') && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Zap size={16} style={{ color: 'var(--info-blue)' }} />
              Standardized Rolling Z-Score Mean-Reversion Oscillator (Point-in-Time, Zero Look-Ahead)
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Entry: ±{zThreshold.toFixed(1)}σ | Exit: ±{exitThreshold.toFixed(1)}σ
            </span>
          </div>
          <div className="card-body">
            <div style={{ width: '100%', height: 230 }}>
              <ResponsiveContainer>
                <LineChart data={series} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => val.slice(5)} />
                  <YAxis domain={[-4.0, 4.0]} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', fontSize: '12px', borderRadius: '6px' }}
                    formatter={(val) => [`${Number(val).toFixed(2)}σ`, 'Z-Score']}
                  />
                  <ReferenceLine y={zThreshold} stroke="#dc2626" strokeDasharray="3 3" label={{ value: `+${zThreshold.toFixed(1)}σ Sell Spread`, fill: '#dc2626', fontSize: 10 }} />
                  <ReferenceLine y={exitThreshold} stroke="#f59e0b" strokeDasharray="2 2" />
                  <ReferenceLine y={0.0} stroke="#64748b" strokeWidth={1} />
                  <ReferenceLine y={-exitThreshold} stroke="#f59e0b" strokeDasharray="2 2" />
                  <ReferenceLine y={-zThreshold} stroke="#059669" strokeDasharray="3 3" label={{ value: `-${zThreshold.toFixed(1)}σ Buy Spread`, fill: '#059669', fontSize: 10 }} />
                  <Line type="monotone" dataKey="z_score" stroke="#2563eb" strokeWidth={2.2} dot={false} name="Z-Score" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Chart 4: Percentage Premium / Discount Curve */}
      {series.length > 0 && (activeChartTab === 'all' || activeChartTab === 'pct') && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <TrendingDown size={16} style={{ color: 'var(--gold-600)' }} />
              Relative Percentage Premium / Discount Curve ({pairA} relative to {pairB})
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Formula: ((Price_A - Price_B) / Price_B) × 100%
            </span>
          </div>
          <div className="card-body">
            <div style={{ width: '100%', height: 210 }}>
              <ResponsiveContainer>
                <LineChart data={series} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="trade_date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => val.slice(5)} />
                  <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `${v.toFixed(2)}%`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', fontSize: '12px', borderRadius: '6px' }}
                    formatter={(val) => [`${Number(val).toFixed(3)}%`, 'Premium / Discount']}
                  />
                  <ReferenceLine y={0.0} stroke="#94a3b8" strokeWidth={1} />
                  <Line type="monotone" dataKey="pct_spread" stroke="#7c3aed" strokeWidth={2} dot={false} name="Relative Premium/Discount (%)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
