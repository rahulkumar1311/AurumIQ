import React from 'react';
import { Database, AlertCircle, RefreshCw, UploadCloud, Info } from 'lucide-react';

export default function EmptyState({
  title = "No Market Data Ingested",
  description = "AurumIQ operates strictly on verified exchange data with zero fabricated prices or artificial results. Load the authentic MCX sample dataset or upload a public Bhavcopy CSV to initialize analytics.",
  onLoadSample,
  onGoToUpload,
  loadingAction = false,
  showSpecs = false,
  specs = []
}) {
  return (
    <div>
      <div className="empty-state-box">
        <Database className="empty-state-icon" />
        <h3 className="empty-state-title">{title}</h3>
        <p className="empty-state-desc">{description}</p>
        
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
          {onLoadSample && (
            <button
              className="btn btn-gold"
              onClick={onLoadSample}
              disabled={loadingAction}
            >
              <RefreshCw size={15} className={loadingAction ? 'animate-spin' : ''} />
              {loadingAction ? 'Ingesting Dataset...' : 'Load Authentic MCX Dataset (120 Days)'}
            </button>
          )}
          {onGoToUpload && (
            <button className="btn btn-secondary" onClick={onGoToUpload}>
              <UploadCloud size={15} />
              Upload MCX Bhavcopy CSV
            </button>
          )}
        </div>

        <div style={{
          marginTop: '1.5rem',
          display: 'inline-flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          background: 'var(--bg-muted)',
          padding: '0.35rem 0.75rem',
          borderRadius: '4px'
        }}>
          <Info size={13} style={{ color: 'var(--gold-600)' }} />
          Zero fictitious prices, simulated guarantees, or artificial signals. Full mathematical rigor.
        </div>
      </div>

      {showSpecs && specs && specs.length > 0 && (
        <div className="card" style={{ marginTop: '1.5rem' }}>
          <div className="card-header">
            <div>
              <div className="card-title">
                <AlertCircle size={16} style={{ color: 'var(--gold-600)' }} />
                Standard MCX Gold Derivatives Contract Specifications
              </div>
              <div className="card-desc">
                Normalization rules and official Multi Commodity Exchange (MCX) contract parameters
              </div>
            </div>
          </div>
          <div className="card-body" style={{ padding: 0 }}>
            <div className="table-wrapper">
              <table className="fin-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Contract Name</th>
                    <th>Trading Unit</th>
                    <th>Quotation Base</th>
                    <th>10g Multiplier</th>
                    <th>Purity</th>
                    <th>Tick Size</th>
                    <th>Delivery Lot</th>
                  </tr>
                </thead>
                <tbody>
                  {specs.map((s) => (
                    <tr key={s.symbol}>
                      <td><strong>{s.symbol}</strong></td>
                      <td>{s.name}</td>
                      <td className="mono">{s.trading_unit_grams}g</td>
                      <td className="mono">₹ per {s.quote_unit_grams}g</td>
                      <td>
                        <span className="badge badge-gold mono">x{s.multiplier_to_10g}</span>
                      </td>
                      <td>
                        <span className={`badge ${s.purity === 999 ? 'badge-blue' : 'badge-neutral'} mono`}>
                          {s.purity} Fineness
                        </span>
                      </td>
                      <td className="mono">₹{s.tick_size}</td>
                      <td style={{ color: 'var(--text-muted)' }}>{s.lot_size_description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
