import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  AreaChart,
  Area,
  ReferenceLine
} from 'recharts';
import {
  Play,
  TrendingUp,
  ShieldAlert,
  Award,
  FileText,
  Download,
  Calendar,
  Sliders,
  AlertTriangle,
  ShieldCheck,
  ExternalLink,
  Scale,
  Upload,
  RefreshCw
} from 'lucide-react';
import EmptyState from '../components/EmptyState';
import { getApiUrl } from '../config';

const CONTRACTS = ['GOLDM', 'GOLDTEN', 'GOLDGUINEA', 'GOLDPETAL'];

export default function BacktestingLab({
  hasData,
  health,
  onLoadSample,
  onGoToUpload,
  loadingAction
}) {
  const [pairA, setPairA] = useState('GOLDM');
  const [pairB, setPairB] = useState('GOLDPETAL');
  const [entryZ, setEntryZ] = useState(1.5);
  const [exitZ, setExitZ] = useState(0.2);
  const [stopLossZ, setStopLossZ] = useState(3.0);
  const [lookback, setLookback] = useState(20);
  const [capital, setCapital] = useState(500000);
  const [includeFriction, setIncludeFriction] = useState(true);
  const [autoCalibrate, setAutoCalibrate] = useState(false);
  const [expiryBufferDays, setExpiryBufferDays] = useState(3);

  const [loading, setLoading] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [backtestResult, setBacktestResult] = useState(null);

  useEffect(() => {
    if (!hasData) {
      setBacktestResult(null);
    }
  }, [hasData]);

  const handleRunBacktest = async (e) => {
    if (e) e.preventDefault();
    if (!hasData) return;
    setLoading(true);
    try {
      const res = await fetch(getApiUrl('/api/backtest/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair_a: pairA,
          pair_b: pairB,
          entry_z: Number(entryZ),
          exit_z: Number(exitZ),
          stop_loss_z: Number(stopLossZ),
          lookback: Number(lookback),
          initial_capital: Number(capital),
          use_purity_adjusted: false,
          include_friction: includeFriction,
          auto_calibrate: autoCalibrate,
          expiry_buffer_days: Number(expiryBufferDays),
          dev_ratio: 0.50,
          val_ratio: 0.25,
          test_ratio: 0.25
        })
      });
      const data = await res.json();
      setBacktestResult(data);
    } catch (err) {
      console.error('Failed to execute backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSampleAndRun = async () => {
    if (!onLoadSample) return;
    setLoading(true);
    try {
      await onLoadSample();
      // Execute walk-forward backtest immediately after 120-day dataset ingestion
      const res = await fetch(getApiUrl('/api/backtest/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair_a: pairA,
          pair_b: pairB,
          entry_z: Number(entryZ),
          exit_z: Number(exitZ),
          stop_loss_z: Number(stopLossZ),
          lookback: Number(lookback),
          initial_capital: Number(capital),
          use_purity_adjusted: false,
          include_friction: includeFriction,
          auto_calibrate: autoCalibrate,
          expiry_buffer_days: Number(expiryBufferDays),
          dev_ratio: 0.50,
          val_ratio: 0.25,
          test_ratio: 0.25
        })
      });
      const data = await res.json();
      setBacktestResult(data);
    } catch (err) {
      console.error('Failed to load sample and execute backtest:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadReport = async () => {
    setDownloadingReport(true);
    try {
      const res = await fetch(getApiUrl('/api/backtest/report'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pair_a: pairA,
          pair_b: pairB,
          entry_z: Number(entryZ),
          exit_z: Number(exitZ),
          stop_loss_z: Number(stopLossZ),
          lookback: Number(lookback),
          initial_capital: Number(capital),
          use_purity_adjusted: false,
          include_friction: includeFriction,
          auto_calibrate: autoCalibrate,
          expiry_buffer_days: Number(expiryBufferDays),
          dev_ratio: 0.50,
          val_ratio: 0.25,
          test_ratio: 0.25
        })
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `aurumiq_walk_forward_backtest_${pairA}_${pairB}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Failed to download backtest report:', err);
    } finally {
      setDownloadingReport(false);
    }
  };

  if (!hasData) {
    return (
      <EmptyState
        title="Walk-Forward Backtesting Lab — Ingestion Required"
        description="Load MCX futures data to evaluate statistical spread arbitrage strategies using chronological walk-forward partitions, frozen in-sample parameters, contract rolls, and benchmark alpha comparisons."
        onLoadSample={onLoadSample}
        onGoToUpload={onGoToUpload}
        loadingAction={loadingAction}
      />
    );
  }

  const metrics = backtestResult?.metrics;
  const splits = backtestResult?.walk_forward_splits;
  const benchmark = backtestResult?.benchmark_comparison;
  const trades = backtestResult?.trades || [];
  const equityCurve = backtestResult?.equity_curve || [];
  const isInsufficient = backtestResult && backtestResult.success === false;

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
          <ShieldCheck size={18} style={{ color: 'var(--bull-green)' }} />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
              Walk-Forward Backtesting Laboratory • Zero Look-Ahead Bias
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Chronological Partitioning: <strong>50% Development (In-Sample)</strong> • <strong>25% Validation</strong> • <strong>25% Final Unseen Test (Out-of-Sample)</strong>
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span className="badge badge-gold mono">
            Pair: {pairA} / {pairB}
          </span>
          <span className="badge badge-neutral">
            Source: <a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'underline', marginLeft: '0.25rem' }}>
              mcxindia.com <ExternalLink size={9} style={{ display: 'inline' }} />
            </a>
          </span>
        </div>
      </div>

      {/* Proactive Sample Size Advisory */}
      {health?.total_trading_days && health.total_trading_days < 30 && (
        <div style={{
          background: '#fffbeb',
          border: '1px solid #fde68a',
          borderLeft: '4px solid #f59e0b',
          borderRadius: '6px',
          padding: '0.85rem 1.25rem',
          fontSize: '0.8rem',
          color: '#92400e',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.75rem',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
            <AlertTriangle size={18} style={{ color: '#d97706', flexShrink: 0 }} />
            <div>
              <strong style={{ color: '#78350f' }}>Single-Date Bhavcopy Loaded: </strong>
              The database currently contains {health.total_trading_days} session ({health?.date_range?.start || '1 day'}). Walk-forward backtesting requires ≥ 30 overlapping sessions for zero look-ahead parameter freezing.
            </div>
          </div>
          <button
            className="btn btn-gold btn-sm"
            onClick={handleLoadSampleAndRun}
            disabled={loading || loadingAction}
            style={{ fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
          >
            <RefreshCw size={13} className={loading || loadingAction ? 'animate-spin' : ''} />
            {loading || loadingAction ? 'Ingesting Feed...' : '⚡ Load 120d MCX History'}
          </button>
        </div>
      )}

      {/* Parameter Form Card */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Sliders size={17} style={{ color: 'var(--gold-600)' }} />
            Defensible Walk-Forward Backtesting Configuration
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Strict chronological partition: 50% Dev / 25% Val / 25% Unseen Test
          </span>
        </div>
        <div className="card-body">
          <form onSubmit={handleRunBacktest}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem', alignItems: 'flex-end', marginBottom: '1rem' }}>
              <div className="form-group">
                <label className="form-label">Leg A (Benchmark)</label>
                <select className="form-select" value={pairA} onChange={(e) => setPairA(e.target.value)}>
                  {CONTRACTS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Leg B (Relative)</label>
                <select className="form-select" value={pairB} onChange={(e) => setPairB(e.target.value)}>
                  {CONTRACTS.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Entry Z-Score (±σ)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.5"
                  max="4.0"
                  className="form-input mono"
                  value={entryZ}
                  onChange={(e) => setEntryZ(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Exit Z-Score (±σ)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.0"
                  max="2.0"
                  className="form-input mono"
                  value={exitZ}
                  onChange={(e) => setExitZ(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Stop-Loss Z (±σ)</label>
                <input
                  type="number"
                  step="0.5"
                  min="2.0"
                  max="6.0"
                  className="form-input mono"
                  value={stopLossZ}
                  onChange={(e) => setStopLossZ(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Lookback (Days)</label>
                <input
                  type="number"
                  min="5"
                  max="60"
                  className="form-input mono"
                  value={lookback}
                  onChange={(e) => setLookback(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Initial Capital (₹)</label>
                <input
                  type="number"
                  step="50000"
                  min="100000"
                  className="form-input mono"
                  value={capital}
                  onChange={(e) => setCapital(e.target.value)}
                />
              </div>
            </div>

            {/* Microstructure & Lifecycle Controls */}
            <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center', background: '#f8fafc', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <label className="toggle-label" style={{ fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeFriction}
                  onChange={(e) => setIncludeFriction(e.target.checked)}
                />
                <span style={{ fontWeight: 500 }}>MCX Statutory Fees + Slippage</span>
              </label>

              <label className="toggle-label" style={{ fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={autoCalibrate}
                  onChange={(e) => setAutoCalibrate(e.target.checked)}
                />
                <span style={{ fontWeight: 500 }}>Auto-Calibrate on Development Window</span>
              </label>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Expiry Tender Roll Buffer:</span>
                <select
                  className="form-select"
                  style={{ width: '90px', padding: '0.2rem 0.5rem', fontSize: '0.775rem' }}
                  value={expiryBufferDays}
                  onChange={(e) => setExpiryBufferDays(Number(e.target.value))}
                >
                  <option value={2}>2 Days</option>
                  <option value={3}>3 Days</option>
                  <option value={5}>5 Days</option>
                </select>
              </div>

              <div className="backtest-submit-container" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button
                  type="submit"
                  className="btn btn-gold"
                  disabled={loading}
                  style={{ height: '36px' }}
                >
                  <Play size={14} />
                  {loading ? 'Simulating...' : 'Execute Walk-Forward Backtest'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>

      {/* Model Assumptions & Statutory Friction Panel */}
      <div className="grid-2">
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header" style={{ padding: '0.75rem 1rem' }}>
            <div className="card-title" style={{ fontSize: '0.85rem' }}>
              <Scale size={15} style={{ color: 'var(--gold-600)' }} />
              Normalization & Partition Assumptions
            </div>
          </div>
          <div className="card-body" style={{ padding: '0.85rem 1rem', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
            <ul style={{ margin: 0, paddingLeft: '1.15rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              <li><strong>Reference Standard:</strong> INR per 10 grams of 999.0 Fine Gold Equivalent.</li>
              <li><strong>Chronological Splits:</strong> Development (50%), Validation (25%), Unseen Test (25%).</li>
              <li><strong>Zero Look-Ahead:</strong> In-sample parameters strictly frozen before stepping forward.</li>
              <li><strong>Roll Mechanism:</strong> Mandatory contract rollover {expiryBufferDays} days prior to maturity to prevent delivery default.</li>
            </ul>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header" style={{ padding: '0.75rem 1rem' }}>
            <div className="card-title" style={{ fontSize: '0.85rem' }}>
              <FileText size={15} style={{ color: 'var(--info-blue)' }} />
              Statutory Transaction-Cost Assumptions
            </div>
          </div>
          <div className="card-body" style={{ padding: '0.85rem 1rem', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>
            <ul className="two-col-list" style={{ margin: 0, paddingLeft: '1.15rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.25rem' }}>
              <li>Turnover Fee: <strong>0.0015%</strong></li>
              <li>CTT (Sell Side): <strong>0.01%</strong></li>
              <li>Stamp Duty (Buy): <strong>0.002%</strong></li>
              <li>Brokerage: <strong>0.005%</strong></li>
              <li>GST on Charges: <strong>18.0%</strong></li>
              <li>Execution Slippage: <strong>0.5 ticks</strong></li>
            </ul>
            <div style={{ marginTop: '0.45rem', fontSize: '0.725rem', color: 'var(--text-dim)' }}>
              *Illiquidity penalty applied dynamically to retail contracts (volume &lt; 10 lots).
            </div>
          </div>
        </div>
      </div>

      {/* Settlement Price Limitation Banner */}
      <div style={{
        background: '#fffbeb',
        border: '1px solid #fde68a',
        borderLeft: '4px solid #d97706',
        borderRadius: '6px',
        padding: '0.75rem 1.25rem',
        fontSize: '0.775rem',
        color: '#92400e',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        <AlertTriangle size={18} style={{ color: '#d97706', flexShrink: 0 }} />
        <div>
          <strong style={{ color: '#78350f' }}>SETTLEMENT PRICE LIMITATION & ILLIQUIDITY DISCLOSURE: </strong>
          Settlement prices represent official exchange daily clearing marks, not guaranteed trade fill prices. Fill prices are subject to order book depth and bid-ask spreads. For thin retail contracts (GOLDGUINEA, GOLDPETAL), illiquidity surcharges are applied when volume &lt; 10 lots.
        </div>
      </div>

      {/* Insufficient Data State with Actionable 1-Click Resolution */}
      {isInsufficient && (
        <div className="card" style={{ padding: '2rem 1.5rem', textAlign: 'center', border: '1px solid #fecaca', background: '#fef2f2' }}>
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '54px',
            height: '54px',
            borderRadius: '50%',
            background: '#fee2e2',
            margin: '0 auto 0.75rem'
          }}>
            <ShieldAlert size={32} style={{ color: '#dc2626' }} />
          </div>
          <h4 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#991b1b', marginBottom: '0.4rem' }}>
            Insufficient Data for Reliable Validation
          </h4>
          <p style={{ fontSize: '0.85rem', color: '#b91c1c', maxWidth: 620, margin: '0 auto 0.75rem', lineHeight: 1.5 }}>
            {backtestResult.message}
          </p>

          <div style={{
            maxWidth: 620,
            margin: '0.85rem auto 1.25rem',
            padding: '0.85rem 1.15rem',
            background: '#ffffff',
            border: '1px solid #fca5a5',
            borderRadius: '6px',
            textAlign: 'left',
            fontSize: '0.785rem',
            color: '#7f1d1d',
            lineHeight: 1.55
          }}>
            <strong>Why is this requirement strictly enforced?</strong>
            <ul style={{ margin: '0.35rem 0 0', paddingLeft: '1.15rem' }}>
              <li>Daily Bhavcopies provide clearing settlement prices for a <strong>single trading date</strong>.</li>
              <li>AurumIQ's walk-forward engine strictly partitions data into <strong>Development (50%)</strong>, <strong>Validation (25%)</strong>, and <strong>Unseen Test (25%)</strong> with in-sample parameter freezing to prevent look-ahead bias and data-snooping.</li>
              <li>A minimum of <strong>30 overlapping trading sessions</strong> is mandatory to calculate rolling lookbacks (lookback = {lookback}d) and out-of-sample statistics without inventing fictitious performance.</li>
            </ul>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              className="btn btn-gold"
              onClick={handleLoadSampleAndRun}
              disabled={loading || loadingAction}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.55rem',
                padding: '0.65rem 1.4rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                boxShadow: '0 4px 6px -1px rgba(217, 119, 6, 0.25)'
              }}
            >
              <RefreshCw size={15} className={loading || loadingAction ? 'animate-spin' : ''} />
              {loading || loadingAction ? 'Ingesting 120-Day MCX Dataset & Simulating...' : '⚡ Load 120-Day Benchmark Dataset & Run Backtest'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={onGoToUpload}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.45rem', padding: '0.65rem 1.2rem', fontSize: '0.825rem' }}
            >
              <Upload size={14} />
              Import Additional Bhavcopies
            </button>
          </div>
        </div>
      )}

      {/* Initial Empty State before Run */}
      {!backtestResult && (
        <div className="card" style={{ padding: '2.5rem', textAlign: 'center' }}>
          <Play size={36} style={{ color: 'var(--gold-600)', margin: '0 auto 1rem' }} />
          <h4 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.4rem' }}>
            Walk-Forward Quantitative Simulation Engine Ready
          </h4>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 580, margin: '0 auto 1.25rem' }}>
            Configure your parameters above and click <strong>"Execute Walk-Forward Backtest"</strong>. The engine will split available historical data chronologically into Development, Validation, and Final Unseen Test periods, freeze parameters on the training window, model physical contract rolls, and compare returns against the MCX Gold benchmark.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={handleRunBacktest} disabled={loading}>
              Execute Initial Walk-Forward Simulation
            </button>
            {(!health?.total_trading_days || health.total_trading_days < 30) && (
              <button
                className="btn btn-gold"
                onClick={handleLoadSampleAndRun}
                disabled={loading || loadingAction}
                style={{ fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '0.45rem' }}
              >
                <RefreshCw size={14} className={loading || loadingAction ? 'animate-spin' : ''} />
                {loading || loadingAction ? 'Ingesting...' : '⚡ Load 120d MCX History & Run'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Backtest Results Section */}
      {metrics && splits && (
        <div>
          {/* Header Action Bar */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
              <span className="badge badge-gold" style={{ fontSize: '0.85rem', padding: '0.25rem 0.65rem' }}>
                {backtestResult.strategy_name}
              </span>
              <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Run ID: {backtestResult.run_id} | Frozen Params: Lookback {metrics.lookback}d, Entry ±{metrics.entry_z}σ, Exit ±{metrics.exit_z}σ
              </span>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={handleDownloadReport}
              disabled={downloadingReport}
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
            >
              <Download size={14} />
              {downloadingReport ? 'Exporting...' : 'Download Audit Report (CSV)'}
            </button>
          </div>

          {/* Out-of-Sample Performance Highlight Card */}
          {splits.unseen_test && (
            <div className="card" style={{ border: '2px solid var(--bull-green-border)', background: 'linear-gradient(to right, #ecfdf5, #ffffff)', marginBottom: '1.25rem' }}>
              <div className="card-header" style={{ background: 'transparent', borderBottom: '1px solid var(--bull-green-border)' }}>
                <div className="card-title" style={{ color: 'var(--bull-green)' }}>
                  <Award size={18} />
                  Out-of-Sample Performance (Final Unseen Test Partition)
                </div>
                <span className="badge badge-green mono">
                  {splits.unseen_test.start_date} to {splits.unseen_test.end_date} ({splits.unseen_test.trading_days} Days)
                </span>
              </div>
              <div className="card-body">
                <div className="grid-4" style={{ gap: '0.75rem' }}>
                  <div style={{ background: '#ffffff', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>OOS Net PnL</div>
                    <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: splits.unseen_test.metrics?.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                      {splits.unseen_test.metrics?.total_net_pnl >= 0 ? `+₹${splits.unseen_test.metrics?.total_net_pnl?.toLocaleString('en-IN')}` : `-₹${Math.abs(splits.unseen_test.metrics?.total_net_pnl)?.toLocaleString('en-IN')}`}
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                      Return: <strong>{splits.unseen_test.metrics?.total_return_pct}%</strong>
                    </div>
                  </div>

                  <div style={{ background: '#ffffff', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>OOS Benchmark Alpha</div>
                    <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 700, color: splits.unseen_test.metrics?.alpha_pct >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                      {splits.unseen_test.metrics?.alpha_pct >= 0 ? `+${splits.unseen_test.metrics?.alpha_pct}%` : `${splits.unseen_test.metrics?.alpha_pct}%`}
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                      Gold Bench: <strong>{splits.unseen_test.metrics?.benchmark_return_pct}%</strong>
                    </div>
                  </div>

                  <div style={{ background: '#ffffff', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>OOS Sharpe & Max DD</div>
                    <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      Sharpe: {splits.unseen_test.metrics?.sharpe_ratio}
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--bear-red)' }}>
                      Max Drawdown: -{splits.unseen_test.metrics?.max_drawdown_pct}%
                    </div>
                  </div>

                  <div style={{ background: '#ffffff', padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>OOS Trades & Costs</div>
                    <div className="mono" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                      {splits.unseen_test.trade_count} Trades ({splits.unseen_test.metrics?.win_rate_pct}% Win)
                    </div>
                    <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>
                      Friction: ₹{splits.unseen_test.metrics?.total_statutory_costs?.toFixed(2)}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Full Simulation Performance KPI Tiles */}
          <div className="grid-4" style={{ marginBottom: '1.25rem' }}>
            <div className="stat-tile">
              <div className="stat-label">
                <span>Net Portfolio PnL</span>
                <TrendingUp size={14} style={{ color: metrics.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }} />
              </div>
              <div className="stat-value mono">
                <span style={{ color: metrics.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                  {metrics.total_net_pnl >= 0 ? `+₹${metrics.total_net_pnl.toLocaleString('en-IN')}` : `-₹${Math.abs(metrics.total_net_pnl).toLocaleString('en-IN')}`}
                </span>
              </div>
              <div className="stat-sub">
                <span className={metrics.total_return_pct >= 0 ? 'badge badge-green mono' : 'badge badge-red mono'}>
                  {metrics.total_return_pct >= 0 ? `+${metrics.total_return_pct}%` : `${metrics.total_return_pct}%`} Return
                </span>
                <span>Gross: ₹{metrics.total_gross_pnl.toLocaleString('en-IN')}</span>
              </div>
            </div>

            <div className="stat-tile">
              <div className="stat-label">
                <span>Benchmark Alpha & Beta</span>
                <Award size={14} style={{ color: 'var(--gold-600)' }} />
              </div>
              <div className="stat-value mono">
                <span style={{ color: benchmark?.alpha_pct >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                  {benchmark?.alpha_pct >= 0 ? `+${benchmark?.alpha_pct}%` : `${benchmark?.alpha_pct}%`}
                </span>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}> Alpha</span>
              </div>
              <div className="stat-sub">
                <span>Gold Return: {benchmark?.benchmark_return_pct}% | Beta: {benchmark?.beta}</span>
              </div>
            </div>

            <div className="stat-tile">
              <div className="stat-label">
                <span>Risk & Drawdown</span>
                <ShieldAlert size={14} style={{ color: 'var(--bear-red)' }} />
              </div>
              <div className="stat-value mono">
                Sharpe: {metrics.sharpe_ratio}
              </div>
              <div className="stat-sub">
                <span className="badge badge-red mono">Max DD: -{metrics.max_drawdown_pct}%</span>
                <span>IR: {benchmark?.information_ratio}</span>
              </div>
            </div>

            <div className="stat-tile">
              <div className="stat-label">
                <span>Execution Friction</span>
                <FileText size={14} style={{ color: 'var(--text-muted)' }} />
              </div>
              <div className="stat-value mono">
                ₹{metrics.total_statutory_costs.toLocaleString('en-IN')}
              </div>
              <div className="stat-sub">
                <span>Turnover: ₹{(metrics.total_turnover / 100000).toFixed(1)}L ({metrics.total_trades} trades)</span>
              </div>
            </div>
          </div>

          {/* Walk-Forward Multi-Period Breakdown Table */}
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="card-header">
              <div className="card-title">
                <Calendar size={16} style={{ color: 'var(--gold-600)' }} />
                Walk-Forward Multi-Period Breakdown (Chronological Isolation, Zero Shuffling)
              </div>
              <span className="badge badge-neutral mono">Parameters Frozen on Development</span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-wrapper">
                <table className="fin-table">
                  <thead>
                    <tr>
                      <th>Partition Window</th>
                      <th>Trading Period</th>
                      <th>Days</th>
                      <th>Trades</th>
                      <th>Net PnL (₹)</th>
                      <th>Return %</th>
                      <th>Gold Bench %</th>
                      <th>Alpha %</th>
                      <th>Sharpe</th>
                      <th>Max DD %</th>
                      <th>Win Rate</th>
                      <th>Friction (₹)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Development Row */}
                    <tr>
                      <td><span className="badge badge-gold">1. Development (In-Sample)</span></td>
                      <td className="mono">{splits.development?.start_date} to {splits.development?.end_date}</td>
                      <td className="mono">{splits.development?.trading_days}d</td>
                      <td className="mono">{splits.development?.trade_count}</td>
                      <td className="mono" style={{ fontWeight: 600, color: splits.development?.metrics?.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.development?.metrics?.total_net_pnl >= 0 ? `+₹${splits.development?.metrics?.total_net_pnl?.toFixed(2)}` : `-₹${Math.abs(splits.development?.metrics?.total_net_pnl)?.toFixed(2)}`}
                      </td>
                      <td className="mono">{splits.development?.metrics?.total_return_pct}%</td>
                      <td className="mono">{splits.development?.metrics?.benchmark_return_pct}%</td>
                      <td className="mono" style={{ fontWeight: 600, color: splits.development?.metrics?.alpha_pct >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.development?.metrics?.alpha_pct >= 0 ? `+${splits.development?.metrics?.alpha_pct}%` : `${splits.development?.metrics?.alpha_pct}%`}
                      </td>
                      <td className="mono">{splits.development?.metrics?.sharpe_ratio}</td>
                      <td className="mono" style={{ color: 'var(--bear-red)' }}>-{splits.development?.metrics?.max_drawdown_pct}%</td>
                      <td className="mono">{splits.development?.metrics?.win_rate_pct}%</td>
                      <td className="mono">₹{splits.development?.metrics?.total_statutory_costs?.toFixed(2)}</td>
                    </tr>

                    {/* Validation Row */}
                    <tr>
                      <td><span className="badge badge-neutral">2. Validation (Holdout 1)</span></td>
                      <td className="mono">{splits.validation?.start_date} to {splits.validation?.end_date}</td>
                      <td className="mono">{splits.validation?.trading_days}d</td>
                      <td className="mono">{splits.validation?.trade_count}</td>
                      <td className="mono" style={{ fontWeight: 600, color: splits.validation?.metrics?.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.validation?.metrics?.total_net_pnl >= 0 ? `+₹${splits.validation?.metrics?.total_net_pnl?.toFixed(2)}` : `-₹${Math.abs(splits.validation?.metrics?.total_net_pnl)?.toFixed(2)}`}
                      </td>
                      <td className="mono">{splits.validation?.metrics?.total_return_pct}%</td>
                      <td className="mono">{splits.validation?.metrics?.benchmark_return_pct}%</td>
                      <td className="mono" style={{ fontWeight: 600, color: splits.validation?.metrics?.alpha_pct >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.validation?.metrics?.alpha_pct >= 0 ? `+${splits.validation?.metrics?.alpha_pct}%` : `${splits.validation?.metrics?.alpha_pct}%`}
                      </td>
                      <td className="mono">{splits.validation?.metrics?.sharpe_ratio}</td>
                      <td className="mono" style={{ color: 'var(--bear-red)' }}>-{splits.validation?.metrics?.max_drawdown_pct}%</td>
                      <td className="mono">{splits.validation?.metrics?.win_rate_pct}%</td>
                      <td className="mono">₹{splits.validation?.metrics?.total_statutory_costs?.toFixed(2)}</td>
                    </tr>

                    {/* Unseen Test Row */}
                    <tr style={{ background: '#f0fdf4' }}>
                      <td><span className="badge badge-green">3. Final Unseen Test (Out-of-Sample)</span></td>
                      <td className="mono">{splits.unseen_test?.start_date} to {splits.unseen_test?.end_date}</td>
                      <td className="mono">{splits.unseen_test?.trading_days}d</td>
                      <td className="mono">{splits.unseen_test?.trade_count}</td>
                      <td className="mono" style={{ fontWeight: 700, color: splits.unseen_test?.metrics?.total_net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.unseen_test?.metrics?.total_net_pnl >= 0 ? `+₹${splits.unseen_test?.metrics?.total_net_pnl?.toFixed(2)}` : `-₹${Math.abs(splits.unseen_test?.metrics?.total_net_pnl)?.toFixed(2)}`}
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>{splits.unseen_test?.metrics?.total_return_pct}%</td>
                      <td className="mono">{splits.unseen_test?.metrics?.benchmark_return_pct}%</td>
                      <td className="mono" style={{ fontWeight: 700, color: splits.unseen_test?.metrics?.alpha_pct >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                        {splits.unseen_test?.metrics?.alpha_pct >= 0 ? `+${splits.unseen_test?.metrics?.alpha_pct}%` : `${splits.unseen_test?.metrics?.alpha_pct}%`}
                      </td>
                      <td className="mono">{splits.unseen_test?.metrics?.sharpe_ratio}</td>
                      <td className="mono" style={{ color: 'var(--bear-red)' }}>-{splits.unseen_test?.metrics?.max_drawdown_pct}%</td>
                      <td className="mono">{splits.unseen_test?.metrics?.win_rate_pct}%</td>
                      <td className="mono">₹{splits.unseen_test?.metrics?.total_statutory_costs?.toFixed(2)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Equity Curve & Walk-Forward Partition Visualization */}
          <div className="card" style={{ marginBottom: '1.25rem' }}>
            <div className="card-header">
              <div className="card-title">
                <TrendingUp size={16} style={{ color: 'var(--gold-600)' }} />
                Walk-Forward Portfolio Equity Curve (₹) Across Development, Validation & Unseen Test
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <span className="badge badge-gold mono">Dev: {splits.development?.start_date?.slice(5)}</span>
                <span className="badge badge-neutral mono">Val: {splits.validation?.start_date?.slice(5)}</span>
                <span className="badge badge-green mono">Test: {splits.unseen_test?.start_date?.slice(5)}</span>
              </div>
            </div>
            <div className="card-body">
              <div style={{ width: '100%', height: 320 }}>
                <ResponsiveContainer>
                  <AreaChart data={equityCurve} margin={{ top: 10, right: 30, left: 20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#d97706" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#d97706" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="trade_date" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(val) => val.slice(5)} />
                    <YAxis domain={['dataMin - 1000', 'dataMax + 1000']} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', fontSize: '12px' }}
                      formatter={(val) => [`₹${Number(val).toLocaleString('en-IN')}`, 'Portfolio Capital']}
                    />
                    {splits.validation?.start_date && (
                      <ReferenceLine x={splits.validation.start_date} stroke="#64748b" strokeDasharray="3 3" label={{ value: 'Validation Split', fill: '#64748b', fontSize: 10 }} />
                    )}
                    {splits.unseen_test?.start_date && (
                      <ReferenceLine x={splits.unseen_test.start_date} stroke="#059669" strokeDasharray="3 3" label={{ value: 'Unseen Test Split', fill: '#059669', fontSize: 10 }} />
                    )}
                    <Area type="monotone" dataKey="capital" stroke="#d97706" strokeWidth={2.5} fillOpacity={1} fill="url(#equityGradient)" name="Portfolio Capital" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Trade Execution Log Table with Specific Contract Expiries & Rolls */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <FileText size={16} style={{ color: 'var(--info-blue)' }} />
                Chronological Trade Execution & Contract Roll Log
              </div>
              <span className="badge badge-neutral mono">{trades.length} Closed / Rolled Executions</span>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-wrapper">
                <table className="fin-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Direction</th>
                      <th>Contract A & Expiry</th>
                      <th>Contract B & Expiry</th>
                      <th>Entry Date</th>
                      <th>Exit Date</th>
                      <th>Hold</th>
                      <th>Entry Spread</th>
                      <th>Exit Spread</th>
                      <th>Entry Z</th>
                      <th>Exit Z</th>
                      <th>Gross PnL</th>
                      <th>MCX Friction</th>
                      <th>Net PnL</th>
                      <th>Return %</th>
                      <th>Exit / Roll Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((t) => (
                      <tr key={t.trade_id} style={{ background: t.was_rolled ? '#fffbeb' : undefined }}>
                        <td className="mono">{t.trade_id}</td>
                        <td>
                          <span className={t.direction === 'Long Spread' ? 'badge badge-green' : 'badge badge-gold'}>
                            {t.direction}
                          </span>
                        </td>
                        <td className="mono" style={{ fontSize: '0.75rem' }}>
                          <strong>{t.contract_a}</strong> ({t.expiry_a})
                        </td>
                        <td className="mono" style={{ fontSize: '0.75rem' }}>
                          <strong>{t.contract_b}</strong> ({t.expiry_b})
                        </td>
                        <td className="mono">{t.entry_date}</td>
                        <td className="mono">{t.exit_date}</td>
                        <td className="mono">{t.holding_days}d</td>
                        <td className="mono">₹{t.entry_spread}</td>
                        <td className="mono">₹{t.exit_spread}</td>
                        <td className="mono">{t.entry_z}σ</td>
                        <td className="mono">{t.exit_z}σ</td>
                        <td className="mono">₹{t.gross_pnl.toFixed(2)}</td>
                        <td className="mono" style={{ color: 'var(--bear-red)' }}>
                          -₹{t.transaction_costs.toFixed(2)}
                        </td>
                        <td className="mono" style={{ fontWeight: 600 }}>
                          <span style={{ color: t.net_pnl >= 0 ? 'var(--bull-green)' : 'var(--bear-red)' }}>
                            {t.net_pnl >= 0 ? `+₹${t.net_pnl.toFixed(2)}` : `-₹${Math.abs(t.net_pnl).toFixed(2)}`}
                          </span>
                        </td>
                        <td className="mono">
                          <span className={t.return_pct >= 0 ? 'badge badge-green' : 'badge badge-red'}>
                            {t.return_pct >= 0 ? `+${t.return_pct}%` : `${t.return_pct}%`}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.75rem', color: t.was_rolled ? '#92400e' : 'var(--text-muted)' }}>
                          {t.exit_reason}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
