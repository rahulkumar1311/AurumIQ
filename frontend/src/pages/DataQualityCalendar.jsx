import React, { useState } from 'react';
import {
  Calendar,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Trash2,
  FileCheck,
  Server,
  Download,
  ExternalLink,
  ShieldCheck
} from 'lucide-react';
import { getApiUrl } from '../config';

export default function DataQualityCalendar({
  data,
  onLoadSample,
  onReset,
  loadingAction,
  onRefreshData
}) {
  const [requestedDate, setRequestedDate] = useState('15/09/2026');
  const [downloading, setDownloading] = useState(false);
  const [downloadResult, setDownloadResult] = useState(null);

  const [uploadFile, setUploadFile] = useState(null);
  const [uploadRequestedDate, setUploadRequestedDate] = useState('15/09/2026');
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);

  // Direct MCX Download handler
  const handleDirectDownload = async (e) => {
    e.preventDefault();
    if (!requestedDate) return;

    setDownloading(true);
    setDownloadResult(null);

    try {
      const res = await fetch(getApiUrl('/api/bhavcopy/download'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ requested_date: requestedDate })
      });
      const json = await res.json();
      setDownloadResult(json);
      if (json.success && onRefreshData) {
        onRefreshData();
      }
    } catch (err) {
      setDownloadResult({
        success: false,
        status: 'FETCH_ERROR',
        message: `Failed to query MCX downloader: ${err.message}`
      });
    } finally {
      setDownloading(false);
    }
  };

  // CSV Fallback Upload handler
  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    if (uploadRequestedDate) {
      formData.append('requested_date', uploadRequestedDate);
    }

    try {
      const res = await fetch(getApiUrl('/api/bhavcopy/upload'), {
        method: 'POST',
        body: formData
      });
      const json = await res.json();
      setUploadResult(json);
      if (json.success && onRefreshData) {
        onRefreshData();
      }
    } catch (err) {
      setUploadResult({
        success: false,
        status: 'UPLOAD_ERROR',
        message: `Upload failed: ${err.message}`
      });
    } finally {
      setUploading(false);
    }
  };

  const hasData = data && data.has_data;
  const calendar = data?.calendar || [];
  const anomalies = data?.anomalies || [];
  const bhavcopyImports = data?.bhavcopy_imports || [];

  return (
    <div>
      {/* Top Diagnostics & Investigation Bar */}
      <div className="grid-2" style={{ marginBottom: '1.25rem' }}>
        {/* Pipeline Health & Official Source Card */}
        <div className="card">
          <div className="card-header">
            <div>
              <div className="card-title">
                <Server size={16} style={{ color: 'var(--bull-green)' }} />
                MCX Data Pipeline Health & Source Verification
              </div>
              <div className="card-desc">
                Official source: <a href="https://www.mcxindia.com/market-data/bhavcopy" target="_blank" rel="noreferrer" style={{ color: 'var(--info-blue)', textDecoration: 'underline' }}>mcxindia.com/market-data/bhavcopy <ExternalLink size={10} style={{ display: 'inline' }} /></a>
              </div>
            </div>
            <span className={`badge ${hasData ? 'badge-green' : 'badge-neutral'}`}>
              {hasData ? 'Pipeline Active' : 'Empty Database'}
            </span>
          </div>
          <div className="card-body">
            <div className="grid-2" style={{ gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ background: 'var(--bg-muted)', padding: '0.75rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Total Ingested Bars
                </div>
                <div className="mono" style={{ fontSize: '1.2rem', fontWeight: 700 }}>
                  {data?.total_records?.toLocaleString() || 0}
                </div>
              </div>

              <div style={{ background: 'var(--bg-muted)', padding: '0.75rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Date Span
                </div>
                <div className="mono" style={{ fontSize: '0.85rem', fontWeight: 600, marginTop: '0.3rem' }}>
                  {data?.date_range?.start_date ? `${data.date_range.start_date} to ${data.date_range.end_date}` : 'None'}
                </div>
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={15} style={{ color: 'var(--bull-green)' }} />
                <span>Requested Date Validation: <strong>DD/MM/YYYY Enforced</strong></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={15} style={{ color: 'var(--bull-green)' }} />
                <span>Actual Returned Date Disambiguation: <strong>MM/DD/YYYY Validated</strong></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={15} style={{ color: 'var(--bull-green)' }} />
                <span>Contract Identification: <strong>Composite (Symbol + Expiry Date)</strong></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CheckCircle size={15} style={{ color: 'var(--bull-green)' }} />
                <span>Symbol Whitespace Stripping: <strong>Active ("GOLDM   " → "GOLDM")</strong></span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={15} style={{ color: anomalies.length > 0 ? 'var(--bear-red)' : 'var(--bull-green)' }} />
                <span>
                  Price Anomalies Detected: <strong>{anomalies.length}</strong>
                </span>
              </div>
            </div>

            <div style={{ marginTop: '1.25rem', display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-gold btn-sm"
                onClick={onLoadSample}
                disabled={loadingAction}
              >
                <RefreshCw size={12} className={loadingAction ? 'animate-spin' : ''} />
                Load 120d MCX Sample
              </button>
              <button
                className="btn btn-danger btn-sm"
                onClick={onReset}
                disabled={loadingAction}
              >
                <Trash2 size={12} />
                Reset Database
              </button>
            </div>
          </div>
        </div>

        {/* MCX Bhavcopy Ingestion Engine Card (Direct Download + CSV Fallback) */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <Download size={16} style={{ color: 'var(--gold-600)' }} />
              MCX Bhavcopy Ingestion Engine
            </div>
            <span className="badge badge-neutral mono">Problem Statement #03</span>
          </div>
          <div className="card-body">
            {/* Step 1: Direct Download Attempt */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label className="form-label" style={{ marginBottom: '0.35rem', display: 'block' }}>
                1. Automated Direct Download from MCX
              </label>
              <form onSubmit={handleDirectDownload} style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="text"
                  placeholder="DD/MM/YYYY (e.g. 15/09/2026)"
                  className="form-input mono"
                  style={{ width: '190px', fontSize: '0.8rem' }}
                  value={requestedDate}
                  onChange={(e) => setRequestedDate(e.target.value)}
                />
                <button
                  type="submit"
                  className="btn btn-primary btn-sm"
                  disabled={downloading || !requestedDate}
                >
                  <Download size={13} />
                  {downloading ? 'Querying MCX...' : 'Attempt Direct Download'}
                </button>
              </form>

              {downloadResult && (
                <div
                  style={{
                    marginTop: '0.65rem',
                    padding: '0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    background: downloadResult.success ? 'var(--bull-green-bg)' : 'var(--bear-red-bg)',
                    border: `1px solid ${downloadResult.success ? 'var(--bull-green-border)' : 'var(--bear-red-border)'}`,
                    color: downloadResult.success ? 'var(--bull-green)' : 'var(--bear-red)'
                  }}
                >
                  <div>
                    <strong>Status: {downloadResult.status}</strong>
                    {downloadResult.requested_date && <span> | Requested: {downloadResult.requested_date}</span>}
                    {downloadResult.actual_data_date && <span> | Actual: {downloadResult.actual_data_date}</span>}
                  </div>
                  <div style={{ marginTop: '0.25rem', color: 'var(--text-muted)' }}>
                    {downloadResult.message}
                  </div>
                </div>
              )}
            </div>

            {/* Step 2: Reliable CSV Fallback Upload */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                <label className="form-label">
                  2. Reliable Fallback: Upload Official Bhavcopy CSV
                </label>
                <span className="badge badge-gold" style={{ fontSize: '0.65rem' }}>Guaranteed Reliable</span>
              </div>
              <p style={{ fontSize: '0.725rem', color: 'var(--text-muted)', marginBottom: '0.65rem' }}>
                When MCX bot protection prevents direct server-to-server downloads, upload the downloaded CSV file here:
              </p>
              
              <form onSubmit={handleFileUpload}>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <div style={{ flex: 1 }}>
                    <input
                      type="file"
                      accept=".csv,.txt"
                      className="form-input"
                      style={{ width: '100%', fontSize: '0.75rem' }}
                      onChange={(e) => setUploadFile(e.target.files[0])}
                    />
                  </div>
                  <div style={{ width: '140px' }}>
                    <input
                      type="text"
                      placeholder="Validate Date (DD/MM/YYYY)"
                      title="Requested Date in DD/MM/YYYY to validate against file"
                      className="form-input mono"
                      style={{ width: '100%', fontSize: '0.75rem' }}
                      value={uploadRequestedDate}
                      onChange={(e) => setUploadRequestedDate(e.target.value)}
                    />
                  </div>
                  <button
                    type="submit"
                    className="btn btn-gold btn-sm"
                    disabled={uploading || !uploadFile}
                  >
                    <FileCheck size={13} />
                    {uploading ? 'Validating...' : 'Validate & Import'}
                  </button>
                </div>
              </form>

              {uploadResult && (
                <div
                  style={{
                    marginTop: '0.65rem',
                    padding: '0.65rem',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    background: uploadResult.success ? 'var(--bull-green-bg)' : 'var(--bear-red-bg)',
                    border: `1px solid ${uploadResult.success ? 'var(--bull-green-border)' : 'var(--bear-red-border)'}`,
                    color: uploadResult.success ? 'var(--bull-green)' : 'var(--bear-red)'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>Status: {uploadResult.status}</strong>
                      {uploadResult.requested_date && <span> | Requested: {uploadResult.requested_date}</span>}
                      {uploadResult.actual_data_date && (
                        <span> | Actual Data Date: <strong>{uploadResult.actual_data_date}</strong></span>
                      )}
                    </div>
                    {uploadResult.status === 'DATE_MISMATCH' && (
                      <span className="badge badge-red">Date Mismatch Rejected</span>
                    )}
                  </div>
                  <div style={{ marginTop: '0.35rem', color: 'var(--text-muted)' }}>
                    {uploadResult.message}
                  </div>
                  {uploadResult.validation_report && (
                    <div style={{ marginTop: '0.35rem', fontSize: '0.725rem', color: 'var(--text-main)', display: 'flex', gap: '0.75rem' }}>
                      <span>Total Found: <strong>{uploadResult.validation_report.total_extracted}</strong></span>
                      <span>Valid: <strong style={{ color: 'var(--bull-green)' }}>{uploadResult.validation_report.valid_count}</strong></span>
                      <span>Rejected: <strong style={{ color: 'var(--bear-red)' }}>{uploadResult.validation_report.rejected_count}</strong></span>
                      <span>Duplicates: <strong>{uploadResult.validation_report.duplicate_count}</strong></span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Prominent Bhavcopy Ingestion Audit Log Table */}
      <div className="card" style={{ marginBottom: '1.25rem' }}>
        <div className="card-header">
          <div>
            <div className="card-title">
              <ShieldCheck size={16} style={{ color: 'var(--bull-green)' }} />
              MCX Bhavcopy Ingestion Sessions & Audit Trail
            </div>
            <div className="card-desc">
              Audit log of all imported Bhavcopy files, date validations, duplicate counts, and rejected-row tallies
            </div>
          </div>
          <span className="badge badge-neutral mono">{bhavcopyImports.length} Recent Sessions</span>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {bhavcopyImports.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              No Bhavcopy import sessions recorded yet. Attempt a download or upload a Bhavcopy CSV above.
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="fin-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Source</th>
                    <th>Requested Date</th>
                    <th>Actual Data Date</th>
                    <th>Import Status</th>
                    <th>Total Rows</th>
                    <th>Valid Rows</th>
                    <th>Rejected Rows</th>
                    <th>Duplicate Rows</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {bhavcopyImports.map((imp) => {
                    const isSuccess = imp.status === 'SUCCESS';
                    const isMismatch = imp.status === 'DATE_MISMATCH';
                    const isWeekend = imp.status === 'WEEKEND_HOLIDAY';

                    return (
                      <tr key={imp.id}>
                        <td className="mono">#{imp.id}</td>
                        <td><strong>{imp.source}</strong></td>
                        <td className="mono">{imp.requested_date || '-'}</td>
                        <td className="mono">
                          {imp.actual_data_date ? (
                            <span className={isMismatch ? 'badge badge-red mono' : 'badge badge-green mono'}>
                              {imp.actual_data_date}
                            </span>
                          ) : '-'}
                        </td>
                        <td>
                          {isSuccess && <span className="badge badge-green">SUCCESS</span>}
                          {isMismatch && <span className="badge badge-red">DATE_MISMATCH</span>}
                          {isWeekend && <span className="badge badge-gold">WEEKEND/CLOSED</span>}
                          {!isSuccess && !isMismatch && !isWeekend && (
                            <span className="badge badge-neutral">{imp.status}</span>
                          )}
                        </td>
                        <td className="mono">{imp.total_rows_found}</td>
                        <td className="mono" style={{ color: 'var(--bull-green)', fontWeight: 600 }}>
                          {imp.valid_rows_count}
                        </td>
                        <td className="mono" style={{ color: imp.rejected_rows_count > 0 ? 'var(--bear-red)' : 'var(--text-muted)' }}>
                          {imp.rejected_rows_count}
                        </td>
                        <td className="mono">{imp.duplicate_rows_count}</td>
                        <td className="mono" style={{ color: 'var(--text-muted)' }}>{imp.created_at}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Contract Calendar Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">
              <Calendar size={16} style={{ color: 'var(--gold-600)' }} />
              MCX Gold Derivatives Contract Calendar & Delivery Tenors
            </div>
            <div className="card-desc">
              Active expiry cycles, days to maturity, average normalized pricing, and tender period indicators
            </div>
          </div>
        </div>
        <div className="card-body" style={{ padding: 0 }}>
          {calendar.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              No contract calendar records available. Ingest market data to populate expiries.
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="fin-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Expiry Date</th>
                    <th>Days to Expiry (DTE)</th>
                    <th>Delivery Status</th>
                    <th>Avg Norm. 10g Price</th>
                    <th>Cumulative Volume</th>
                    <th>Peak Open Interest</th>
                  </tr>
                </thead>
                <tbody>
                  {calendar.map((c, idx) => {
                    const isTender = c.current_dte <= 5;
                    return (
                      <tr key={`${c.symbol}-${c.expiry_date}-${idx}`}>
                        <td><strong>{c.symbol}</strong></td>
                        <td className="mono">{c.expiry_date}</td>
                        <td className="mono">
                          <span className={`badge ${c.current_dte < 10 ? 'badge-red' : 'badge-neutral'}`}>
                            {c.current_dte} days
                          </span>
                        </td>
                        <td>
                          {isTender ? (
                            <span className="badge badge-red">Tender Period (Physical Delivery)</span>
                          ) : (
                            <span className="badge badge-green">Trading Open</span>
                          )}
                        </td>
                        <td className="mono">₹{c.avg_norm_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        <td className="mono">{c.total_volume.toLocaleString('en-IN')}</td>
                        <td className="mono">{c.max_oi.toLocaleString('en-IN')}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
