import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Opportunity } from '../../types';

interface OpportunityRadarProps {
  opportunities: Opportunity[];
}

const OpportunityRadar: React.FC<OpportunityRadarProps> = ({ opportunities }) => {
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
      minute: '2-digit'
    });
  };

  // Get recent opportunities (last 10)
  const recentOpps = opportunities.slice(-10).reverse();
  // Get score color
  const getScoreColor = (score: number): string => {
    if (score >= 8) return 'var(--profit)';
    if (score >= 6) return 'var(--accent-blue)';
    if (score >= 4) return 'var(--warning)';
    return 'var(--text-secondary)';
  };

  // Get status badge
  const getStatusBadge = (opp: Opportunity) => {
    if (opp.executed) {
      return { text: '✓ Executed', color: 'var(--profit)', bg: 'var(--profit-bg)' };
    }
    if (opp.skip_reason) {
      const reason = opp.skip_reason.toLowerCase();
      if (reason.includes('brake')) {
        return { text: '⚠️ Brake', color: 'var(--loss)', bg: 'var(--loss-bg)' };
      }
      if (reason.includes('wash')) {
        return { text: '🚫 Wash', color: 'var(--warning)', bg: 'var(--warning-bg)' };
      }
      return { text: '⏭️ Skipped', color: 'var(--text-secondary)', bg: 'rgba(160, 174, 192, 0.1)' };
    }
    return { text: '⏳ Pending', color: 'var(--accent-blue)', bg: 'rgba(66, 153, 225, 0.1)' };
  };
  return (
    <motion.div
      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.4 }}
      style={{
        padding: '24px',
        gridColumn: 'span 2',
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
        <span>Opportunity Radar</span>
        <span style={{
          fontSize: '12px',
          color: 'var(--text-secondary)',
          fontWeight: '400'
        }}>
          {opportunities.filter(o => o.executed).length} / {opportunities.length} executed
        </span>
      </h2>
      {/* Opportunities List */}
      <div style={{
        maxHeight: '400px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column' as const,
        gap: '8px'
      }}>
        {recentOpps.length === 0 ? (
          <div style={{
            textAlign: 'center' as const,
            color: 'var(--text-secondary)',
            padding: '20px'
          }}>
            No opportunities detected
          </div>
        ) : (
          <AnimatePresence>
            {recentOpps.map((opp, index) => {
              const status = getStatusBadge(opp);
              const scoreColor = getScoreColor(opp.score);
              
              return (
                <motion.div
                  key={`${opp.timestamp}-${opp.symbol}-${index}`}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ 
                    duration: 0.2,
                    delay: index * 0.03
                  }}
                  whileHover={{ scale: 1.02 }}
                  style={{
                    padding: '16px',
                    background: 'var(--bg-secondary)',
                    borderRadius: 'var(--border-radius-sm)',
                    border: `1px solid ${opp.executed ? 'var(--profit)' : 'var(--border-color)'}`,
                    display: 'grid',
                    gridTemplateColumns: '1fr auto',
                    gap: '12px',
                    position: 'relative' as const
                  }}
                >
                  {/* Left side - Main info */}
                  <div>
                    {/* Symbol and Time */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      marginBottom: '8px'
                    }}>
                      <span style={{
                        fontWeight: '600',
                        fontSize: '16px',
                        color: 'var(--text-primary)'
                      }}>
                        {opp.symbol}
                      </span>
                      <span style={{
                        fontSize: '12px',
                        color: 'var(--text-dim)'
                      }}>
                        {formatTime(opp.timestamp)}
                      </span>
                    </div>

                    {/* Metrics Grid */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(3, 1fr)',
                      gap: '8px',
                      fontSize: '13px'
                    }}>
                      <div>
                        <div style={{ color: 'var(--text-dim)', marginBottom: '2px' }}>
                          Dip
                        </div>
                        <div style={{ 
                          color: 'var(--loss)',
                          fontWeight: '500',
                          fontVariantNumeric: 'tabular-nums'
                        }}>
                          -{opp.dip_percent.toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-dim)', marginBottom: '2px' }}>
                          Price
                        </div>
                        <div style={{ 
                          color: 'var(--text-primary)',
                          fontWeight: '500',
                          fontVariantNumeric: 'tabular-nums'
                        }}>
                          {formatCurrency(opp.price)}
                        </div>
                      </div>
                      <div>
                        <div style={{ color: 'var(--text-dim)', marginBottom: '2px' }}>
                          Score
                        </div>
                        <div style={{ 
                          color: scoreColor,
                          fontWeight: '600',
                          fontSize: '16px'
                        }}>
                          {opp.score}/10
                        </div>
                      </div>
                    </div>

                    {/* Skip Reason if present */}
                    {opp.skip_reason && (
                      <div style={{
                        marginTop: '8px',
                        fontSize: '12px',
                        color: 'var(--text-secondary)',
                        fontStyle: 'italic'
                      }}>
                        {opp.skip_reason}
                      </div>
                    )}
                  </div>

                  {/* Right side - Status Badge */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'flex-start'
                  }}>
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.1 + index * 0.03 }}
                      style={{
                        padding: '6px 12px',
                        background: status.bg,
                        color: status.color,
                        borderRadius: 'var(--border-radius-sm)',
                        fontSize: '12px',
                        fontWeight: '500',
                        whiteSpace: 'nowrap' as const
                      }}
                    >
                      {status.text}
                    </motion.div>
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </motion.div>
  );
};

export default OpportunityRadar;