import React from 'react';
import { motion } from 'framer-motion';
import { Account } from '../../types';

interface MarginGaugeProps {
  account: Account;
}

const MarginGauge: React.FC<MarginGaugeProps> = ({ account }) => {
  // Calculate margin usage percentage (0-100)
  const marginPercent = account.equity > 0 
    ? (account.margin_used / account.equity) * 100 
    : 0;

  // Determine color based on margin usage
  const getColor = (percent: number): string => {
    if (percent < 50) return 'var(--profit)';
    if (percent < 75) return 'var(--warning)';
    return 'var(--loss)';
  };

  const color = getColor(marginPercent);
  
  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(value);
  };
  return (
    <motion.div
      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      whileHover={{ y: -2 }}
      style={{
        padding: '24px',
        minWidth: '350px'
      }}
    >
      {/* Title */}
      <h2 style={{ 
        fontSize: '18px', 
        fontWeight: '600',
        marginBottom: '20px',
        color: 'var(--text-primary)'
      }}>
        Margin Usage
      </h2>

      {/* Percentage Display */}
      <motion.div
        key={marginPercent}
        initial={{ scale: 1 }}
        animate={{ scale: [1, 1.02, 1] }}
        transition={{ duration: 0.3 }}
        style={{ marginBottom: '16px' }}
      >
        <div style={{ 
          fontSize: '36px', 
          fontWeight: '700',
          color: color,
          fontVariantNumeric: 'tabular-nums'
        }}>
          {marginPercent.toFixed(1)}%
        </div>
      </motion.div>

      {/* Visual Bar */}
      <div style={{
        width: '100%',
        height: '40px',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 'var(--border-radius-sm)',
        overflow: 'hidden',
        position: 'relative' as const,
        marginBottom: '16px'
      }}>
        {/* Background gradient for zones */}
        <div style={{
          position: 'absolute',
          width: '100%',
          height: '100%',
          background: 'linear-gradient(to right, var(--profit) 0%, var(--profit) 50%, var(--warning) 75%, var(--loss) 90%, var(--loss) 100%)',
          opacity: 0.2
        }} />
        
        {/* Filled portion */}
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(marginPercent, 100)}%` }}
          transition={{ 
            duration: 0.5, 
            ease: 'easeOut',
            delay: 0.2 
          }}
          style={{
            height: '100%',
            background: color,
            boxShadow: marginPercent > 75 ? '0 0 20px rgba(245, 101, 101, 0.5)' : undefined,
            position: 'relative'
          }}
        >
          {/* Animated glow effect */}
          {marginPercent > 75 && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 2, repeat: Infinity }}
              style={{
                position: 'absolute',
                top: 0,
                right: 0,
                width: '4px',
                height: '100%',
                background: 'white'
              }}
            />
          )}
        </motion.div>
        
        {/* Warning markers */}
        <div style={{
          position: 'absolute',
          left: '75%',
          top: 0,
          width: '2px',
          height: '100%',
          background: 'var(--warning)',
          opacity: 0.5
        }} />
        <div style={{
          position: 'absolute',
          left: '90%',
          top: 0,
          width: '2px',
          height: '100%',
          background: 'var(--loss)',
          opacity: 0.5
        }} />
      </div>

      {/* Stats */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        fontSize: '14px'
      }}>
        <div>
          <span style={{ color: 'var(--text-dim)' }}>Used: </span>
          <span style={{ color: color, fontWeight: '500' }}>
            {formatCurrency(account.margin_used)}
          </span>
        </div>
        <div>
          <span style={{ color: 'var(--text-dim)' }}>Available: </span>
          <span style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
            {formatCurrency(account.equity - account.margin_used)}
          </span>
        </div>
      </div>

      {/* Warning Messages */}
      {marginPercent > 75 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{
            marginTop: '16px',
            padding: '12px',
            background: marginPercent > 90 ? 'var(--loss-bg)' : 'var(--warning-bg)',
            borderRadius: 'var(--border-radius-sm)',
            fontSize: '13px',
            color: marginPercent > 90 ? 'var(--loss)' : 'var(--warning)'
          }}
        >
          {marginPercent > 90 
            ? '⚠️ Critical margin usage! Risk of liquidation.'
            : '⚠️ High margin usage. Consider reducing positions.'}
        </motion.div>
      )}
    </motion.div>
  );
};

export default MarginGauge;