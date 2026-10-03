import React from 'react';
import {
  Layers,
  DollarSign,
  AlertTriangle,
  ShieldCheck,
  Calendar,
  ExternalLink,
  Download
} from 'lucide-react';
import EmptyState from '../components/EmptyState';

export default function OverviewDashboard({
  data,
  onLoadSample,
  onGoToUpload,
  loadingAction
}) {
  if (!data || !data.has_data) {
    return (
      <EmptyState
        title="Overview Dashboard — Ready for Ingestion"
        description="No commodity derivatives market data detected. Load the authentic MCX gold contracts dataset to view live relative pricing matrices, normalized valuations, and cross-contract spread differentials."
        onLoadSample={onLoadSample}
        onGoToUpload={onGoToUpload}
        loadingAction={loadingAction}
        showSpecs={true}
        specs={data?.contracts || []}
      />
    );
  }

  const quotes = data.quotes || [];
  const matrix = data.spread_matrix || [];
  const contracts = data.contracts || [];

  // Summary Metrics
  const goldmQuote = quotes.find(q => q.symbol === 'GOLDM') || quotes[0];
  const benchmark10g = goldmQuote ? goldmQuote.normalized_close_10g : 0;
  const petalQuote = quotes.find(q => q.symbol === 'GOLDPETAL');
  const retailSpread = (petalQuote && goldmQuote) ? (petalQuote.normalized_close_10g - goldmQuote.normalized_close_10g) : 0;
  const totalVolume = quotes.reduce((acc, q) => acc + (q.volume || 0), 0);
  const totalOI = quotes.reduce((acc, q) => acc + (q.open_interest || 0), 0);

  return (
    <div>
      {/* Institutional Metadata & Verification Banner */}
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
              MCX Official Market Intelligence Feed Active
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Standard Reference Basis: <strong>INR per 10.0g @ 999.0 Fine Gold Equivalent</strong> • Original Exchange Settlement Marks Strictly Preserved
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <span className="badge badge-gold mono">
            <Calendar size={11} style={{ marginRight: '0.25rem' }} />
            Data Date: {data.latest_trade_date}
          </span>
          <span className="badge badge-neutral">
            Source: <a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer" style={{ color: 'inherit', textDecoration: 'underline', marginLeft: '0.25rem' }}>
              mcxindia.com <ExternalLink size={9} style={{ display: 'inline' }} />
            </a>
          </span>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid-4" style={{ marginBottom: '1.25rem' }}>
        <div className="stat-tile">
          <div className="stat-label">
            <span>Benchmark (GOLDM 10g)</span>
            <DollarSign size={14} style={{ color: 'var(--gold-600)' }} />
          </div>
          <div className="stat-value mono">
            ₹{benchmark10g.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className="stat-sub">
            <span className="badge badge-neutral mono">{data.latest_trade_date}</span>
            <span>Near-Month Expiry</span>
          </div>
        </div>

        <div className="stat-tile">
          <div className="stat-label">
            <span>Mini-Petal Basis Spread</span>
            <Layers size={14} style={{ color: 'var(--info-blue)' }} />
          </div>
          <div className="stat-value mono">
            {retailSpread >= 0 ? `+₹${retailSpread.toFixed(2)}` : `-₹${Math.abs(retailSpread).toFixed(2)}`}
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}> /10g</span>
          </div>
          <div className="stat-sub">
            <span className={retailSpread >= 0 ? "badge badge-gold" : "badge badge-blue"}>
              {retailSpread >= 0 ? 'Petal Retail Premium' : 'Mini Premium'}
            </span>
          </div>
        </div>

        <div className="stat-tile">
          <div className="stat-label">
            <span>Total Day Volume</span>
            <span className="badge badge-neutral mono">Lots</span>
          </div>
          <div className="stat-value mono">
            {totalVolume.toLocaleString('en-IN')}
          </div>
          <div className="stat-sub">
            <span>Across 4 Active Contracts</span>
          </div>
        </div>

        <div className="stat-tile">
          <div className="stat-label">
            <span>Aggregate Open Interest</span>
            <span className="badge badge-neutral mono">Contracts</span>
          </div>
          <div className="stat-value mono">
            {totalOI.toLocaleString('en-IN')}
          </div>
          <div className="stat-sub">
            <span>Market Positioning Exposure</span>
          </div>
        </div>
      </div>

      {/* Contract Specification and Live Quotation Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <ShieldCheck size={16} style={{ color: 'var(--gold-600)' }} />
              MCX Gold Derivatives: Normalized Relative Valuation
            </div>
            <div className="card-desc">
              Standardized comparison to ₹ per 10 grams quotation unit and 999 fine purity equivalent
            </div>
          </div>
          <span className="badge badge-neutral mono">Report Date: {data.latest_trade_date}</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-wrapper">
            <table className="fin-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Contract Name</th>
                  <th>Trading Unit</th>
                  <th>Quoted As</th>
                  <th>Raw Close</th>
                  <th>Norm. 10g Base</th>
                  <th>999 Purity Equiv</th>
                  <th>DTE</th>
                  <th>Day Volume</th>
                  <th>Open Interest</th>
                  <th>Expiry Date</th>
                </tr>
              </thead>
              <tbody>
                {quotes.map((q) => {
                  const spec = contracts.find(c => c.symbol === q.symbol) || {};
                  return (
                    <tr key={q.symbol}>
                      <td>
                        <strong>{q.symbol}</strong>
                      </td>
                      <td>{spec.name || q.symbol}</td>
                      <td className="mono">{spec.trading_unit_grams}g</td>
                      <td className="mono" style={{ color: 'var(--text-muted)' }}>
                        per {spec.quote_unit_grams}g
                      </td>
                      <td className="mono" style={{ fontWeight: 600 }}>
                        ₹{q.close.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="mono">
                        <span className="badge badge-gold" style={{ fontSize: '0.825rem' }}>
                          ₹{q.normalized_close_10g.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </span>
                      </td>
                      <td className="mono" style={{ color: 'var(--info-blue)', fontWeight: 600 }}>
                        ₹{q.purity_adjusted_10g.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td className="mono">
                        <span className="badge badge-neutral">{q.dte} days</span>
                      </td>
                      <td className="mono">{q.volume.toLocaleString('en-IN')}</td>
                      <td className="mono">{q.open_interest.toLocaleString('en-IN')}</td>
                      <td className="mono" style={{ color: 'var(--text-muted)' }}>{q.expiry_date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Relative Pricing Spread Matrix and Microstructure */}
      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <Layers size={16} style={{ color: 'var(--info-blue)' }} />
                Pairwise Relative Spread Matrix (₹ / 10g)
              </div>
              <div className="card-desc">
                Row contract minus Column contract normalized price differential
              </div>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrapper">
              <table className="fin-table">
                <thead>
                  <tr>
                    <th>Leg A \ Leg B</th>
                    {quotes.map(q => <th key={q.symbol}>{q.symbol}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {matrix.map((row) => (
                    <tr key={row.symbol}>
                      <td><strong>{row.symbol}</strong></td>
                      {quotes.map((col) => {
                        const val = row[col.symbol];
                        if (val === null || val === undefined) return <td key={col.symbol}>-</td>;
                        const isZero = Math.abs(val) < 0.001;
                        const isPositive = val > 0;
                        return (
                          <td key={col.symbol} className="mono">
                            {isZero ? (
                              <span style={{ color: 'var(--text-dim)' }}>₹0.00</span>
                            ) : (
                              <span className={isPositive ? 'badge badge-green' : 'badge badge-red'}>
                                {isPositive ? `+₹${val.toFixed(2)}` : `-₹${Math.abs(val).toFixed(2)}`}
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Microstructure & Arbitrage Dynamics Guide */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <AlertTriangle size={16} style={{ color: 'var(--gold-600)' }} />
              MCX Relative Pricing Microstructure & Statutory Friction
            </div>
          </div>
          <div className="card-body" style={{ fontSize: '0.825rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            <p style={{ marginBottom: '0.75rem' }}>
              <strong>Underlying Purity Basis:</strong> GOLDM references <strong>995 purity</strong>, while GOLDPETAL references <strong>999 fine gold</strong>. Official MCX GOLDGUINEA deliverable specification is <strong>995 fineness</strong> (coin standard), whereas Problem Statement #03 listed it as 999. The theoretical conversion premium for 995 to 999 is <span className="mono">999/995 ≈ +0.402%</span> (~₹300/10g).
            </p>
            <p style={{ marginBottom: '0.75rem' }}>
              <strong>Retail Packaging & Fabrication Frictions:</strong> GOLDPETAL trades in sealed tamper-proof blister cards (1 gram), commanding a structural fabrication premium over wholesale 100g Mini lots.
            </p>
            <div style={{ background: 'var(--bg-muted)', padding: '0.65rem 0.85rem', borderRadius: '6px', border: '1px solid var(--border-subtle)', marginTop: '0.5rem' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.35rem' }}>
                MCX Statutory Transaction Cost Structure Modeled:
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.15rem', fontSize: '0.75rem', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.25rem' }}>
                <li>Exchange Turnover: <strong>0.0015%</strong></li>
                <li>CTT (Sell Side): <strong>0.01%</strong></li>
                <li>Stamp Duty (Buy Side): <strong>0.002%</strong></li>
                <li>Institutional Brokerage: <strong>0.005%</strong></li>
                <li>GST on Fees: <strong>18.0%</strong></li>
                <li>Slippage Buffer: <strong>0.5 Ticks</strong></li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* Contract Normalization Engine Assumptions & Multiplier Audit Panel */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <ShieldCheck size={16} style={{ color: 'var(--gold-600)' }} />
              Contract Normalization Engine: Multiplier Matrix & Assumptions Audit
            </div>
            <div className="card-desc">
              Standard Reference: INR per 10 grams of 999.0 Fine Gold Equivalent. Separate Trading Unit vs Quote Unit.
            </div>
          </div>
          <a
            href="/api/normalization/report"
            download="aurumiq_normalization_audit_report.csv"
            className="btn btn-secondary btn-sm"
            style={{ textDecoration: 'none' }}
          >
            <Download size={13} />
            Download Assumptions Report (CSV)
          </a>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-wrapper">
            <table className="fin-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Contract Name</th>
                  <th>Trading Unit</th>
                  <th>Quotation Unit</th>
                  <th>Contract Purity</th>
                  <th>Expiry Rule</th>
                  <th>Quotation Mult.</th>
                  <th>Purity Mult.</th>
                  <th>Composite Mult.</th>
                  <th>Notional Mult.</th>
                </tr>
              </thead>
              <tbody>
                {data.normalization_assumptions?.contract_factors?.map((f) => (
                  <tr key={f.symbol}>
                    <td><strong>{f.symbol}</strong></td>
                    <td>{f.name}</td>
                    <td className="mono">{f.trading_unit_grams}g</td>
                    <td className="mono">per {f.quote_unit_grams}g</td>
                    <td className="mono">
                      <span className="badge badge-neutral mono">{f.contract_purity} Fineness</span>
                      {f.is_flagged_assumption && (
                        <span className="badge badge-gold mono" style={{ fontSize: '0.65rem', marginLeft: '4px' }} title="Official MCX is 995; PS#03 assumed 999">
                          Audit Flag
                        </span>
                      )}
                    </td>
                    <td className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {f.expiry_rule?.includes('5th day') ? '5th of Month' : 'Month-End'}
                    </td>
                    <td className="mono" style={{ fontWeight: 600 }}>{f.quotation_multiplier}x</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{f.purity_multiplier.toFixed(6)}x</td>
                    <td className="mono">
                      <span className="badge badge-gold mono">{f.composite_multiplier.toFixed(4)}x</span>
                    </td>
                    <td className="mono" style={{ fontWeight: 600 }}>{f.notional_multiplier}x</td>
                  </tr>
                )) || contracts.map((c) => (
                  <tr key={c.symbol}>
                    <td><strong>{c.symbol}</strong></td>
                    <td>{c.name}</td>
                    <td className="mono">{c.trading_unit_grams}g</td>
                    <td className="mono">per {c.quote_unit_grams}g</td>
                    <td className="mono">{c.purity} Fineness</td>
                    <td className="mono" style={{ fontSize: '0.75rem' }}>{c.symbol === 'GOLDM' ? '5th of Month' : 'Month-End'}</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{(10.0 / c.quote_unit_grams).toFixed(1)}x</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{(999.0 / c.purity).toFixed(6)}x</td>
                    <td className="mono"><span className="badge badge-gold mono">{((10.0 / c.quote_unit_grams) * (999.0 / c.purity)).toFixed(4)}x</span></td>
                    <td className="mono" style={{ fontWeight: 600 }}>{(c.trading_unit_grams / c.quote_unit_grams).toFixed(1)}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ padding: '0.85rem 1.25rem', backgroundColor: '#fafbfc', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            <div style={{ marginBottom: '0.35rem' }}>
              <strong>Official MCX Specification Audit (Verified 2026-10-04):</strong> Sourced from official MCX product specifications (<a href="https://www.mcxindia.com/products/bullion/gold" target="_blank" rel="noreferrer" style={{ color: 'var(--info-blue)', textDecoration: 'underline' }}>mcxindia.com/products/bullion/gold</a>) and MCX Circular MCX/TRD/714/2024.
            </div>
            <div style={{ marginBottom: '0.35rem' }}>
              <strong>Flagged Audit Discrepancy:</strong> Official MCX Gold Guinea deliverable specification is <strong>995 fineness</strong> coin, whereas Hack in Hills Problem Statement #03 listed it as 999. AurumIQ provides configurable convention support (<code style={{ backgroundColor: '#f1f5f9', padding: '1px 4px', borderRadius: 3 }}>OFFICIAL_MCX</code> vs <code style={{ backgroundColor: '#f1f5f9', padding: '1px 4px', borderRadius: 3 }}>PROBLEM_STATEMENT_03</code>) and flags this transparently.
            </div>
            <div>
              <strong>Expiry Rules & Lifecycle:</strong> GOLDM expires on the 5th of the month; GOLDTEN, GOLDGUINEA, and GOLDPETAL expire at month-end. Tender periods span the final 3 trading days of each contract, during which non-delivery spread trading is blocked.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
