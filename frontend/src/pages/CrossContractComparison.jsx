import React, { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  BarChart,
  Bar
} from 'recharts';
import { TrendingUp, Percent, BarChart3, Info, Calendar, ShieldCheck, ExternalLink } from 'lucide-react';
import EmptyState from '../components/EmptyState';

export default function CrossContractComparison({
  data,
  onLoadSample,
  onGoToUpload,
  loadingAction
}) {
  const [usePurityAdjusted, setUsePurityAdjusted] = useState(false);

  if (!data || !data.has_data) {
    return (
      <EmptyState
        title="Cross-Contract Comparison — Awaiting Feed"
        description="Load MCX futures data to compare multi-tenor relative pricing, cost of carry term structures, and liquidity profiles across GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL."
        onLoadSample={onLoadSample}
        onGoToUpload={onGoToUpload}
        loadingAction={loadingAction}
      />
    );
  }

  const history = data.history || [];
  const historyPurity = data.history_purity_adjusted || history;
  const activeHistory = usePurityAdjusted ? historyPurity : history;
  const basisCurve = data.basis_curve || [];
  const liquidity = data.liquidity || [];

  const contractColors = {
    GOLDM: '#d97706',      // Gold/Amber
    GOLDTEN: '#2563eb',    // Blue
    GOLDGUINEA: '#059669', // Emerald Green
    GOLDPETAL: '#7c3aed'   // Purple
  };

  return (
    <div>
      {/* Institutional Metadata & Verification Bar */}
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.75rem 1.25rem',
        marginBottom: '1.25rem',
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
              Cross-Contract Multi-Tenor Relative Valuation
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Normalized ₹/10g Quotation Parity across Wholesale, Medium, and Retail Derivatives
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span className="badge badge-gold mono">
            <Calendar size={11} style={{ marginRight: '0.25rem' }} />
            Data Date: {data.latest_date}
          </span>
          <span className="badge badge-neutral">
            Source: <a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'underline', marginLeft: '0.25rem' }}>
              mcxindia.com <ExternalLink size={9} style={{ display: 'inline' }} />
            </a>
          </span>
        </div>
      </div>

      {/* Normalized Price Trends Chart */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <TrendingUp size={16} style={{ color: 'var(--gold-600)' }} />
              Multi-Contract Normalized Historical Price Trends
            </div>
            <div className="card-desc">
              {usePurityAdjusted
                ? 'All 4 contracts standardized to ₹ per 10 grams & adjusted to 999 fine purity equivalent'
                : 'All 4 contracts standardized to ₹ per 10 grams base'}
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={usePurityAdjusted}
                onChange={(e) => setUsePurityAdjusted(e.target.checked)}
              />
              <span>Purity-Adjusted (999 Fine Gold Equivalent)</span>
            </label>
          </div>
        </div>
        <div className="card-body">
          <div style={{ width: '100%', height: 360 }}>
            <ResponsiveContainer>
              <LineChart data={activeHistory} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis
                  dataKey="trade_date"
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(val) => val.slice(5)}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(val) => `₹${(val / 1000).toFixed(1)}k`}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '12px'
                  }}
                  formatter={(val, name) => [
                    `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })} / 10g`,
                    name
                  ]}
                />
                <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                <Line
                  type="monotone"
                  dataKey="GOLDM"
                  stroke={contractColors.GOLDM}
                  strokeWidth={2.2}
                  dot={false}
                  name="GOLDM (Mini)"
                />
                <Line
                  type="monotone"
                  dataKey="GOLDTEN"
                  stroke={contractColors.GOLDTEN}
                  strokeWidth={2}
                  dot={false}
                  name="GOLDTEN (Ten)"
                />
                <Line
                  type="monotone"
                  dataKey="GOLDGUINEA"
                  stroke={contractColors.GOLDGUINEA}
                  strokeWidth={2}
                  dot={false}
                  name="GOLDGUINEA (Guinea)"
                />
                <Line
                  type="monotone"
                  dataKey="GOLDPETAL"
                  stroke={contractColors.GOLDPETAL}
                  strokeWidth={2}
                  dot={false}
                  name="GOLDPETAL (Petal)"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        {/* Term Structure / Implied Cost of Carry */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <Percent size={16} style={{ color: 'var(--info-blue)' }} />
                Implied Cost of Carry Term Structure
              </div>
              <div className="card-desc">
                Annualized Basis Rate (% p.a.) relative to spot/near benchmark across maturities
              </div>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrapper">
              <table className="fin-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Expiry Date</th>
                    <th>DTE</th>
                    <th>Norm. Price</th>
                    <th>Implied Basis (% p.a.)</th>
                    <th>Open Interest</th>
                  </tr>
                </thead>
                <tbody>
                  {basisCurve.map((b, idx) => (
                    <tr key={`${b.symbol}-${b.expiry_date}-${idx}`}>
                      <td><strong>{b.symbol}</strong></td>
                      <td className="mono">{b.expiry_date}</td>
                      <td className="mono">
                        <span className="badge badge-neutral">{b.dte}d</span>
                      </td>
                      <td className="mono">₹{b.normalized_close_10g.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                      <td className="mono">
                        <span className={b.implied_basis_pct >= 0 ? 'badge badge-green' : 'badge badge-red'}>
                          {b.implied_basis_pct >= 0 ? `+${b.implied_basis_pct.toFixed(2)}%` : `${b.implied_basis_pct.toFixed(2)}%`}
                        </span>
                      </td>
                      <td className="mono">{b.open_interest.toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Liquidity Profile (Volume & Open Interest) */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <BarChart3 size={16} style={{ color: 'var(--bull-green)' }} />
                Contract Liquidity Breakdown
              </div>
              <div className="card-desc">
                Average Daily Volume vs Open Interest distribution
              </div>
            </div>
          </div>
          <div className="card-body">
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <BarChart data={liquidity} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="symbol" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#fff', border: '1px solid #e2e8f0', fontSize: '12px' }}
                    formatter={(val) => Number(val).toLocaleString('en-IN')}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }} />
                  <Bar dataKey="avg_daily_volume" fill="#d97706" name="Avg Daily Volume (Lots)" />
                  <Bar dataKey="avg_oi" fill="#2563eb" name="Average Open Interest" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div style={{
              marginTop: '1rem',
              fontSize: '0.75rem',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.35rem'
            }}>
              <Info size={13} style={{ color: 'var(--gold-600)' }} />
              GOLDM offers peak institutional liquidity for wholesale hedging. GOLDPETAL exhibits active retail participation.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
