import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-page)',
          padding: '2rem'
        }}>
          <div style={{
            maxWidth: '600px',
            width: '100%',
            background: '#ffffff',
            borderRadius: '8px',
            border: '1px solid #fecaca',
            boxShadow: '0 4px 6px -1px rgba(0,0,0,0.08)',
            padding: '2rem',
            textAlign: 'center'
          }}>
            <AlertCircle size={40} style={{ color: '#dc2626', margin: '0 auto 1rem' }} />
            <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: '#0f172a', marginBottom: '0.5rem' }}>
              Application Render Exception
            </h3>
            <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1.25rem' }}>
              An unexpected error occurred while rendering the institutional analytics view.
            </p>
            {this.state.error && (
              <pre style={{
                textAlign: 'left',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                padding: '0.75rem',
                borderRadius: '6px',
                fontSize: '0.75rem',
                color: '#dc2626',
                overflowX: 'auto',
                marginBottom: '1.25rem'
              }}>
                {this.state.error.toString()}
              </pre>
            )}
            <button
              className="btn btn-primary"
              onClick={this.handleReload}
              style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <RefreshCw size={14} />
              Reload AurumIQ Dashboard
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
