import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  GitCompare,
  TrendingUp,
  FlaskConical,
  Database
} from 'lucide-react';
import Header from './components/Header';
import OverviewDashboard from './pages/OverviewDashboard';
import CrossContractComparison from './pages/CrossContractComparison';
import HistoricalSpreadAnalysis from './pages/HistoricalSpreadAnalysis';
import BacktestingLab from './pages/BacktestingLab';
import DataQualityCalendar from './pages/DataQualityCalendar';
import { getApiUrl } from './config';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [health, setHealth] = useState(null);
  const [overviewData, setOverviewData] = useState(null);
  const [crossContractData, setCrossContractData] = useState(null);
  const [dataQualityData, setDataQualityData] = useState(null);
  const [loadingAction, setLoadingAction] = useState(false);

  // Global fetchers
  const fetchHealth = async () => {
    try {
      const res = await fetch(getApiUrl('/api/health'));
      const data = await res.json();
      setHealth(data);
    } catch (err) {
      console.error('Health check failed:', err);
    }
  };

  const fetchOverview = async () => {
    try {
      const res = await fetch(getApiUrl('/api/overview'));
      const data = await res.json();
      setOverviewData(data);
    } catch (err) {
      console.error('Failed to fetch overview:', err);
    }
  };

  const fetchCrossContract = async () => {
    try {
      const res = await fetch(getApiUrl('/api/cross-contract'));
      const data = await res.json();
      setCrossContractData(data);
    } catch (err) {
      console.error('Failed to fetch cross-contract data:', err);
    }
  };

  const fetchDataQuality = async () => {
    try {
      const res = await fetch(getApiUrl('/api/data-quality'));
      const data = await res.json();
      setDataQualityData(data);
    } catch (err) {
      console.error('Failed to fetch data quality:', err);
    }
  };

  const refreshAllData = async () => {
    await Promise.all([
      fetchHealth(),
      fetchOverview(),
      fetchCrossContract(),
      fetchDataQuality()
    ]);
  };

  useEffect(() => {
    refreshAllData();
  }, []);

  const handleLoadSample = async () => {
    setLoadingAction(true);
    try {
      await fetch(getApiUrl('/api/data-quality/ingest-sample'), {
        method: 'POST'
      });
      await refreshAllData();
    } catch (err) {
      console.error('Failed to load sample dataset:', err);
    } finally {
      setLoadingAction(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset database to initial empty state? This will remove all loaded records.')) {
      return;
    }
    setLoadingAction(true);
    try {
      await fetch(getApiUrl('/api/data-quality/reset'), { method: 'POST' });
      await refreshAllData();
    } catch (err) {
      console.error('Failed to reset database:', err);
    } finally {
      setLoadingAction(false);
    }
  };

  const hasData = health?.has_data;

  return (
    <div className="app-container">
      <Header
        health={health}
        onLoadSample={handleLoadSample}
        onReset={handleReset}
        loadingAction={loadingAction}
        onNavigateToDataQuality={() => setActiveTab('data_quality')}
      />

      {/* Institutional Tab Bar */}
      <nav className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <LayoutDashboard size={16} />
          Overview Dashboard
        </button>

        <button
          className={`tab-btn ${activeTab === 'cross_contract' ? 'active' : ''}`}
          onClick={() => setActiveTab('cross_contract')}
        >
          <GitCompare size={16} />
          Cross-Contract Comparison
        </button>

        <button
          className={`tab-btn ${activeTab === 'spreads' ? 'active' : ''}`}
          onClick={() => setActiveTab('spreads')}
        >
          <TrendingUp size={16} />
          Historical Spread Analysis
        </button>

        <button
          className={`tab-btn ${activeTab === 'backtest' ? 'active' : ''}`}
          onClick={() => setActiveTab('backtest')}
        >
          <FlaskConical size={16} />
          Backtesting Lab
        </button>

        <button
          className={`tab-btn ${activeTab === 'data_quality' ? 'active' : ''}`}
          onClick={() => setActiveTab('data_quality')}
        >
          <Database size={16} />
          Data Quality & Calendar
        </button>
      </nav>

      {/* Main View Area */}
      <main className="main-content">
        {activeTab === 'overview' && (
          <OverviewDashboard
            data={overviewData}
            onLoadSample={handleLoadSample}
            onGoToUpload={() => setActiveTab('data_quality')}
            loadingAction={loadingAction}
          />
        )}

        {activeTab === 'cross_contract' && (
          <CrossContractComparison
            data={crossContractData}
            onLoadSample={handleLoadSample}
            onGoToUpload={() => setActiveTab('data_quality')}
            loadingAction={loadingAction}
          />
        )}

        {activeTab === 'spreads' && (
          <HistoricalSpreadAnalysis
            hasData={hasData}
            onLoadSample={handleLoadSample}
            onGoToUpload={() => setActiveTab('data_quality')}
            loadingAction={loadingAction}
          />
        )}

        {activeTab === 'backtest' && (
          <BacktestingLab
            hasData={hasData}
            health={health}
            onLoadSample={handleLoadSample}
            onGoToUpload={() => setActiveTab('data_quality')}
            loadingAction={loadingAction}
          />
        )}

        {activeTab === 'data_quality' && (
          <DataQualityCalendar
            data={dataQualityData}
            onLoadSample={handleLoadSample}
            onReset={handleReset}
            loadingAction={loadingAction}
            onRefreshData={refreshAllData}
          />
        )}
      </main>
    </div>
  );
}
