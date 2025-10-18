import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trade } from '../../types';

interface TradeFeedProps {
  trades: Trade[];
}

const TradeFeed: React.FC<TradeFeedProps> = ({ trades }) => {
  // Format currency
  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(value);
  };

  // Format timestamp
  const formatTime = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Get recent trades (last 10)
  const recentTrades = trades.slice(-10).reverse();
  return (
    <motion.div
      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.3 }}
      style={{
        padding: '24px',
        gridColumn: 'span 1',
        minWidth: '350px'
      }}
    >
      {/* Title */}
      <h2 style={{ 
        fontSize: '18px', 
        fontWeight: '600',
        marginBottom: '20px',
        color: 'var(--text-primary)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>Recent Trades</span>
        <span style={{
          fontSize: '12px',
          color: 'var(--text-secondary)',
          fontWeight: '400',
          padding: '4px 8px',
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--border-radius-sm)'
        }}>
          {trades.length} today
        </span>
      </h2>

      {/* Feed Container */}
      <div style={{
        maxHeight: '350px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '8px'
      }}>
        {recentTrades.length === 0 ? (
          <div style={{
            textAlign: 'center' as const,
            color: 'var(--text-secondary)',
            padding: '20px'
          }}>
            No trades today
          </div>
        ) : (
          <AnimatePresence>
            {recentTrades.map((trade, index) => (
              <motion.div
                key={`${trade.timestamp}-${trade.symbol}-${index}`}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ 
                  duration: 0.3,
                  delay: index * 0.05
                }}
                style={{
                  padding: '12px',
                  background: 'var(--bg-secondary)',
                  borderRadius: 'var(--border-radius-sm)',
                  borderLeft: '3px solid var(--accent-blue)',
                  position: 'relative' as const,
                  overflow: 'hidden'
                }}
              >
                {/* New trade glow effect */}
                {index === 0 && (
                  <motion.div
                    initial={{ opacity: 1 }}
                    animate={{ opacity: 0 }}
                    transition={{ duration: 2 }}
                    style={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      right: 0,
                      bottom: 0,
                      background: 'radial-gradient(circle, rgba(66, 153, 225, 0.2) 0%, transparent 70%)',
                      pointerEvents: 'none' as const
                    }}
                  />
                )}
                
                {/* Trade Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: '8px'
                }}>
                  <span style={{
                    fontWeight: '600',
                    fontSize: '14px',
                    color: 'var(--text-primary)'
                  }}>
                    {trade.symbol}
                  </span>
                  <span style={{
                    fontSize: '12px',
                    color: 'var(--text-dim)'
                  }}>
                    {formatTime(trade.timestamp)}
                  </span>
                </div>
                
                {/* Trade Details */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '8px',
                  fontSize: '13px'
                }}>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Qty: </span>
                    <span style={{ 
                      color: 'var(--text-primary)',
                      fontVariantNumeric: 'tabular-nums'
                    }}>
                      {trade.quantity}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-dim)' }}>Price: </span>
                    <span style={{ 
                      color: 'var(--text-primary)',
                      fontVariantNumeric: 'tabular-nums'
                    }}>
                      {formatCurrency(trade.price)}
                    </span>
                  </div>
                </div>
                
                {/* Total Value */}
                <div style={{
                  marginTop: '8px',
                  paddingTop: '8px',
                  borderTop: '1px solid var(--border-color)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: '13px'
                }}>
                  <span style={{ color: 'var(--text-dim)' }}>Total:</span>
                  <span style={{
                    fontWeight: '500',
                    color: 'var(--accent-blue)',
                    fontVariantNumeric: 'tabular-nums'
                  }}>
                    {formatCurrency(trade.total_value)}
                  </span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  );
};

export default TradeFeed;