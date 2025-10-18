import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { api, PollingService } from './services/api';
import { DashboardResponse } from './types';
import AccountCard from './components/AccountCard/AccountCard';
import MarginGauge from './components/MarginGauge/MarginGauge';
import PositionsTable from './components/PositionsTable/PositionsTable';
import TradeFeed from './components/TradeFeed/TradeFeed';
import OpportunityRadar from './components/OpportunityRadar/OpportunityRadar';
import EquityChart from './components/EquityChart/EquityChart';
import './styles/theme.css';

const Dashboard: React.FC = () => {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [isStale, setIsStale] = useState(false);

  // Fetch dashboard data
  const fetchData = useCallback(async () => {
    try {
      const response = await api.getDashboard();
      setData(response);
      setError(null);
      setLastUpdate(new Date());
      setIsStale(false);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch dashboard:', err);
      // Keep showing last data if available
      if (!data) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard');
        setLoading(false);
      } else {
        // Mark data as stale but keep showing it
        setIsStale(true);
      }
    }
  }, [data]);
  // Set up polling
  useEffect(() => {
    const polling = new PollingService();
    polling.start(fetchData, 5000); // Poll every 5 seconds

    // Cleanup on unmount
    return () => polling.stop();
  }, [fetchData]);

  // Loading state
  if (loading) {
    return (
      <div className="dashboard-container" style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-primary)' 
      }}>
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          style={{ 
            width: 50, 
            height: 50, 
            border: '3px solid var(--accent-blue)', 
            borderTopColor: 'transparent',
            borderRadius: '50%' 
          }}
        />
      </div>
    );
  }

  // Error state (no data at all)
  if (error && !data) {
    return (
      <div className="dashboard-container" style={{ 
        minHeight: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        flexDirection: 'column',
        gap: '20px'
      }}>
        <div style={{ color: 'var(--loss)', fontSize: '18px' }}>
          ⚠️ {error}
        </div>
        <button 
          onClick={fetchData}
          style={{
            padding: '10px 20px',
            background: 'var(--accent-blue)',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--border-radius-sm)',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard-container" style={{
      minHeight: '100vh',
      background: 'linear-gradient(180deg, var(--bg-primary) 0%, var(--bg-secondary) 100%)',
      padding: '24px'
    }}>
      {/* Header */}
      <motion.header 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        style={{
          marginBottom: '32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <h1 style={{ 
          fontSize: '32px', 
          fontWeight: '700',
          background: 'var(--accent-gradient)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          Big Dipper Monitor
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {isStale && (
            <span style={{ 
              color: 'var(--warning)', 
              fontSize: '14px',
              padding: '4px 12px',
              background: 'var(--warning-bg)',
              borderRadius: 'var(--border-radius-sm)'
            }}>
              ⚠️ Connection Issues
            </span>
          )}
          <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Last update: {lastUpdate.toLocaleTimeString()}
          </span>
        </div>
      </motion.header>

      {/* Main Grid */}
      <div className="dashboard-grid" style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
        gap: '24px',
        maxWidth: '1600px',
        margin: '0 auto'
      }}>
        {/* Account Overview */}
        {data && (
          <>
            <AccountCard account={data.account} />
            <MarginGauge account={data.account} />
            <EquityChart />
            <PositionsTable positions={data.positions} />
            <TradeFeed trades={data.today_trades} />
            <OpportunityRadar opportunities={data.opportunities} />
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;