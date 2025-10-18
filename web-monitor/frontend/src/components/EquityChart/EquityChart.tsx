import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart 
} from 'recharts';
import { api } from '../../services/api';
import { HistoricalSnapshot } from '../../types';

type TimePeriod = '1d' | '1w' | '1m' | 'all';

const EquityChart: React.FC = () => {
  const [period, setPeriod] = useState<TimePeriod>('1d');
  const [data, setData] = useState<HistoricalSnapshot[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch historical data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const response = await api.getHistorical(period);
        setData(response.snapshots);
      } catch (error) {
        console.error('Failed to fetch historical data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [period]);
  // Format data for chart
  const chartData = data.map(snapshot => ({
    time: new Date(snapshot.timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }),
    equity: snapshot.equity,
    timestamp: snapshot.timestamp
  }));

  // Calculate change
  const firstValue = data[0]?.equity || 0;
  const lastValue = data[data.length - 1]?.equity || 0;
  const change = lastValue - firstValue;
  const changePercent = firstValue > 0 ? ((change / firstValue) * 100) : 0;

  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };

  // Custom Tooltip
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload[0]) {
      return (
        <div style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          borderRadius: 'var(--border-radius-sm)',
          padding: '8px 12px',
          backdropFilter: 'blur(10px)'
        }}>
          <p style={{ 
            color: 'var(--text-primary)',
            fontSize: '14px',
            fontWeight: '500',
            margin: 0
          }}>
            {formatCurrency(payload[0].value)}
          </p>
          <p style={{ 
            color: 'var(--text-secondary)',
            fontSize: '12px',
            margin: 0,
            marginTop: '4px'
          }}>
            {payload[0].payload.time}
          </p>
        </div>
      );
    }
    return null;
  };
  return (
    <motion.div
      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      style={{
        padding: '24px',
        gridColumn: 'span 2',
        minWidth: '350px',
        minHeight: '350px'
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '20px'
      }}>
        <div>
          <h2 style={{ 
            fontSize: '18px', 
            fontWeight: '600',
            marginBottom: '8px',
            color: 'var(--text-primary)'
          }}>
            Equity Curve
          </h2>
          {data.length > 0 && (
            <div style={{
              display: 'flex',
              alignItems: 'baseline',
              gap: '12px'
            }}>
              <span style={{
                fontSize: '24px',
                fontWeight: '600',
                color: change >= 0 ? 'var(--profit)' : 'var(--loss)'
              }}>
                {formatCurrency(lastValue)}
              </span>
              <span style={{
                fontSize: '14px',
                color: change >= 0 ? 'var(--profit)' : 'var(--loss)'
              }}>
                {change >= 0 ? '+' : ''}{formatCurrency(change)} ({changePercent.toFixed(2)}%)
              </span>
            </div>
          )}
        </div>

        {/* Period Selector */}
        <div style={{
          display: 'flex',
          gap: '4px',
          background: 'var(--bg-secondary)',
          padding: '4px',
          borderRadius: 'var(--border-radius-sm)'
        }}>
          {(['1d', '1w', '1m', 'all'] as TimePeriod[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                padding: '6px 12px',
                background: period === p ? 'var(--accent-blue)' : 'transparent',
                color: period === p ? 'white' : 'var(--text-secondary)',
                border: 'none',
                borderRadius: 'var(--border-radius-sm)',
                fontSize: '12px',
                fontWeight: '500',
                cursor: 'pointer',
                transition: 'all var(--transition-fast)',
                textTransform: 'uppercase' as const
              }}
            >
              {p === 'all' ? 'All' : p}
            </button>
          ))}
        </div>
      </div>

      {/* Chart */}
      {loading ? (
        <div style={{
          height: '250px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            style={{ 
              width: 40, 
              height: 40, 
              border: '3px solid var(--accent-blue)', 
              borderTopColor: 'transparent',
              borderRadius: '50%' 
            }}
          />
        </div>
      ) : data.length === 0 ? (
        <div style={{
          height: '250px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-secondary)'
        }}>
          No data available for this period
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                <stop 
                  offset="5%" 
                  stopColor={change >= 0 ? 'var(--profit)' : 'var(--loss)'} 
                  stopOpacity={0.3}
                />
                <stop 
                  offset="95%" 
                  stopColor={change >= 0 ? 'var(--profit)' : 'var(--loss)'} 
                  stopOpacity={0}
                />
              </linearGradient>
            </defs>
            <CartesianGrid 
              strokeDasharray="3 3" 
              stroke="var(--border-color)" 
              opacity={0.3}
            />
            <XAxis 
              dataKey="time" 
              stroke="var(--text-secondary)"
              fontSize={12}
              tickLine={false}
            />
            <YAxis 
              stroke="var(--text-secondary)"
              fontSize={12}
              tickLine={false}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="equity"
              stroke={change >= 0 ? 'var(--profit)' : 'var(--loss)'}
              strokeWidth={2}
              fill="url(#colorEquity)"
              animationDuration={500}
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
};

export default EquityChart;