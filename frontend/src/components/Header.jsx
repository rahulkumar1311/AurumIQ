import React from 'react';
import { Database, RefreshCw, Upload, Trash2, Activity, Calendar } from 'lucide-react';

export default function Header({
  health,
  onLoadSample,
  onReset,
  loadingAction,
  onNavigateToDataQuality
}) {
  const isHealthy = health?.status === 'healthy';
  const hasData = health?.has_data;
  const totalRecords = health?.total_market_records || 0;
  const latestDate = health?.date_range?.end;

  return (
    <header className="top-header">
      <div className="header-brand">
        <div className="brand-icon">
          <Activity size={20} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span className="brand-title">AurumIQ</span>
            <span className="brand-badge">MCX Commodities</span>
          </div>
          <div className="brand-sub">
            Commodity Derivatives Intelligence & Quantitative Relative Pricing
          </div>
        </div>
      </div>

      <div className="header-actions">
        {/* Source & Date Badge */}
        {hasData && latestDate && (
          <div className="status-badge" style={{ background: '#fefce8', borderColor: '#fef08a' }}>
            <Calendar size={13} style={{ color: 'var(--gold-700)' }} />
            <span style={{ color: 'var(--gold-800)', fontSize: '0.725rem' }}>
              Data Date: <strong className="mono">{latestDate}</strong>
            </span>
            <span style={{ color: '#facc15', margin: '0 0.15rem' }}>•</span>
            <span style={{ color: 'var(--gold-700)', fontSize: '0.7rem' }}>
              Source: <strong title="Official Multi Commodity Exchange of India Ltd">MCX Bhavcopy</strong>
            </span>
          </div>
        )}

        {/* Database Health Badge */}
        <div className="status-badge">
          <div className={`status-dot ${isHealthy ? (hasData ? 'online' : 'empty') : ''}`} />
          <span style={{ color: 'var(--text-muted)' }}>Engine:</span>
          <strong>{isHealthy ? 'Connected' : 'Offline'}</strong>
          <span style={{ color: 'var(--border-strong)', margin: '0 0.2rem' }}>|</span>
          <Database size={13} style={{ color: 'var(--text-muted)' }} />
          <span className="mono">
            {totalRecords > 0 ? `${totalRecords.toLocaleString()} bars` : '0 bars'}
          </span>
        </div>

        {/* Actions */}
        {!hasData ? (
          <button
            className="btn btn-gold btn-sm"
            onClick={onLoadSample}
            disabled={loadingAction}
            title="Load authentic MCX gold contracts dataset (120 trading days)"
          >
            <RefreshCw size={13} className={loadingAction ? 'animate-spin' : ''} />
            {loadingAction ? 'Ingesting Feed...' : 'Load MCX Sample Data'}
          </button>
        ) : (
          <div style={{ display: 'flex', gap: '0.4rem' }}>
            <button
              className={`btn btn-sm ${(!health?.total_trading_days || health?.total_trading_days < 30) ? 'btn-gold' : 'btn-secondary'}`}
              onClick={onLoadSample}
              disabled={loadingAction}
              title="Load / re-seed authentic 120-day MCX benchmark dataset (required for 3-phase walk-forward testing)"
            >
              <RefreshCw size={13} className={loadingAction ? 'animate-spin' : ''} />
              {loadingAction ? 'Ingesting...' : ((!health?.total_trading_days || health?.total_trading_days < 30) ? '⚡ Load 120d History' : 'Load 120d Feed')}
            </button>
            <button
              className="btn btn-secondary btn-sm"
              onClick={onNavigateToDataQuality}
              title="Upload MCX Bhavcopy CSV or view contract calendar"
            >
              <Upload size={13} />
              Import Data
            </button>
            <button
              className="btn btn-danger btn-sm"
              onClick={onReset}
              disabled={loadingAction}
              title="Reset database to initial empty state"
            >
              <Trash2 size={13} />
              Reset State
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
