import React from 'react';
import { motion } from 'framer-motion';
import { Account } from '../../types';

interface AccountCardProps {
  account: Account;
}

const AccountCard: React.FC<AccountCardProps> = ({ account }) => {
  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format percentage
  const formatPercent = (value: number): string => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
  };

  // Determine P/L color
  const plColor = account.day_pl >= 0 ? 'var(--profit)' : 'var(--loss)';
  const plBg = account.day_pl >= 0 ? 'var(--profit-bg)' : 'var(--loss-bg)';

  return (
    <motion.div      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -2 }}
      style={{
        padding: '24px',
        minWidth: '350px',
        gridColumn: 'span 2'
      }}
    >
      {/* Title */}
      <h2 style={{ 
        fontSize: '18px', 
        fontWeight: '600',
        marginBottom: '20px',
        color: 'var(--text-primary)'
      }}>
        Account Overview
      </h2>

      {/* Main Equity Display */}
      <motion.div
        key={account.equity}
        initial={{ scale: 1 }}
        animate={{ scale: [1, 1.02, 1] }}
        transition={{ duration: 0.3 }}
        style={{ marginBottom: '24px' }}
      >
        <div style={{ 
          fontSize: '14px', 
          color: 'var(--text-secondary)',
          marginBottom: '8px'
        }}>
          Total Equity
        </div>
        <div style={{ 
          fontSize: '36px', 
          fontWeight: '700',
          fontVariantNumeric: 'tabular-nums',
          background: 'var(--accent-gradient)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent'
        }}>
          {formatCurrency(account.equity)}
        </div>
      </motion.div>

      {/* Day P/L */}
      <motion.div
        key={account.day_pl}
        initial={{ backgroundColor: plBg }}
        animate={{ backgroundColor: plBg }}
        transition={{ duration: 0.3 }}
        style={{
          padding: '12px 16px',
          borderRadius: 'var(--border-radius-sm)',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Day P/L
        </span>
        <div style={{ textAlign: 'right' }}>
          <div style={{ 
            color: plColor, 
            fontSize: '20px', 
            fontWeight: '600',
            fontVariantNumeric: 'tabular-nums'
          }}>
            {formatCurrency(account.day_pl)}
          </div>
          <div style={{ 
            color: plColor, 
            fontSize: '14px',
            opacity: 0.8
          }}>
            {formatPercent(account.day_pl_percent)}
          </div>
        </div>
      </motion.div>

      {/* Additional Stats */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '16px'
      }}>
        <div>
          <div style={{ 
            fontSize: '12px', 
            color: 'var(--text-dim)',
            marginBottom: '4px'
          }}>
            Cash
          </div>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '500',
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--text-primary)'
          }}>
            {formatCurrency(account.cash)}
          </div>
        </div>
        <div>
          <div style={{ 
            fontSize: '12px', 
            color: 'var(--text-dim)',
            marginBottom: '4px'
          }}>
            Buying Power
          </div>
          <div style={{ 
            fontSize: '18px', 
            fontWeight: '500',
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--text-primary)'
          }}>
            {formatCurrency(account.buying_power)}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default AccountCard;