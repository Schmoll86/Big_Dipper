import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Position } from '../../types';

interface PositionsTableProps {
  positions: Position[];
}

type SortField = 'symbol' | 'unrealized_pl' | 'market_value';
type SortDirection = 'asc' | 'desc';

const PositionsTable: React.FC<PositionsTableProps> = ({ positions }) => {
  const [sortField, setSortField] = useState<SortField>('unrealized_pl');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

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
  // Sort positions
  const sortedPositions = [...positions].sort((a, b) => {
    const aValue = a[sortField];
    const bValue = b[sortField];
    
    if (typeof aValue === 'string' && typeof bValue === 'string') {
      return sortDirection === 'asc' 
        ? aValue.localeCompare(bValue)
        : bValue.localeCompare(aValue);
    }
    
    const aNum = aValue as number;
    const bNum = bValue as number;
    return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
  });

  // Handle sort
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Empty state
  if (positions.length === 0) {
    return (
      <motion.div
        className="glass shadow-md"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3, delay: 0.2 }}
        style={{
          padding: '24px',
          gridColumn: 'span 3',
          textAlign: 'center' as const,
          color: 'var(--text-secondary)'
        }}
      >
        <h2 style={{ 
          fontSize: '18px', 
          fontWeight: '600',
          marginBottom: '20px',
          color: 'var(--text-primary)'
        }}>
          Positions
        </h2>
        <p>No open positions</p>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="glass shadow-md"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, delay: 0.2 }}
      style={{
        padding: '24px',
        gridColumn: 'span 3',
        overflow: 'hidden'
      }}
    >
      {/* Title */}
      <h2 style={{ 
        fontSize: '18px', 
        fontWeight: '600',
        marginBottom: '20px',
        color: 'var(--text-primary)'
      }}>
        Open Positions ({positions.length})
      </h2>

      {/* Table Container */}
      <div style={{ 
        overflowX: 'auto',
        overflowY: 'auto',
        maxHeight: '400px',
        borderRadius: 'var(--border-radius-sm)'
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'separate',
          borderSpacing: 0
        }}>
          <thead>
            <tr style={{ background: 'var(--bg-secondary)' }}>
              <th 
                onClick={() => handleSort('symbol')}
                style={{
                  padding: '12px',
                  textAlign: 'left' as const,
                  fontSize: '12px',
                  fontWeight: '600',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  userSelect: 'none' as const,
                  position: 'sticky' as const,
                  top: 0,
                  background: 'var(--bg-secondary)',
                  zIndex: 1
                }}
              >
                Symbol {sortField === 'symbol' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th style={{
                padding: '12px',
                textAlign: 'right' as const,
                fontSize: '12px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                position: 'sticky' as const,
                top: 0,
                background: 'var(--bg-secondary)'
              }}>
                Qty
              </th>
              <th style={{
                padding: '12px',
                textAlign: 'right' as const,
                fontSize: '12px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                position: 'sticky' as const,
                top: 0,
                background: 'var(--bg-secondary)'
              }}>
                Avg Entry
              </th>
              <th style={{
                padding: '12px',
                textAlign: 'right' as const,
                fontSize: '12px',
                fontWeight: '600',
                color: 'var(--text-secondary)',
                position: 'sticky' as const,
                top: 0,
                background: 'var(--bg-secondary)'
              }}>
                Current
              </th>
              <th 
                onClick={() => handleSort('market_value')}
                style={{
                  padding: '12px',
                  textAlign: 'right' as const,
                  fontSize: '12px',
                  fontWeight: '600',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  userSelect: 'none' as const,
                  position: 'sticky' as const,
                  top: 0,
                  background: 'var(--bg-secondary)'
                }}
              >
                Value {sortField === 'market_value' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
              <th 
                onClick={() => handleSort('unrealized_pl')}
                style={{
                  padding: '12px',
                  textAlign: 'right' as const,
                  fontSize: '12px',
                  fontWeight: '600',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  userSelect: 'none' as const,
                  position: 'sticky' as const,
                  top: 0,
                  background: 'var(--bg-secondary)'
                }}
              >
                P/L {sortField === 'unrealized_pl' && (sortDirection === 'asc' ? '↑' : '↓')}
              </th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence>
              {sortedPositions.map((position, index) => (
                <motion.tr
                  key={position.symbol}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ duration: 0.2, delay: index * 0.02 }}
                  whileHover={{ 
                    backgroundColor: 'var(--bg-hover)'
                  }}
                  style={{
                    borderBottom: '1px solid var(--border-color)'
                  }}
                >
                  <td style={{
                    padding: '16px 12px',
                    fontWeight: '500',
                    fontSize: '14px',
                    color: 'var(--text-primary)'
                  }}>
                    {position.symbol}
                  </td>
                  <td style={{
                    padding: '16px 12px',
                    textAlign: 'right' as const,
                    fontVariantNumeric: 'tabular-nums',
                    fontSize: '14px',
                    color: 'var(--text-primary)'
                  }}>
                    {position.qty}
                  </td>
                  <td style={{
                    padding: '16px 12px',
                    textAlign: 'right' as const,
                    fontVariantNumeric: 'tabular-nums',
                    fontSize: '14px',
                    color: 'var(--text-secondary)'
                  }}>
                    {formatCurrency(position.avg_entry)}
                  </td>
                  <td style={{
                    padding: '16px 12px',
                    textAlign: 'right' as const,
                    fontVariantNumeric: 'tabular-nums',
                    fontSize: '14px',
                    color: 'var(--text-primary)'
                  }}>
                    {formatCurrency(position.current_price)}
                  </td>
                  <td style={{
                    padding: '16px 12px',
                    textAlign: 'right' as const,
                    fontVariantNumeric: 'tabular-nums',
                    fontSize: '14px',
                    color: 'var(--text-primary)'
                  }}>
                    {formatCurrency(position.market_value)}
                  </td>
                  <td style={{
                    padding: '16px 12px',
                    textAlign: 'right' as const
                  }}>
                    <motion.div
                      key={position.unrealized_pl}
                      initial={{ scale: 1 }}
                      animate={{ scale: [1, 1.05, 1] }}
                      transition={{ duration: 0.3 }}
                    >
                      <div style={{
                        fontVariantNumeric: 'tabular-nums',
                        fontSize: '14px',
                        fontWeight: '500',
                        color: position.unrealized_pl >= 0 ? 'var(--profit)' : 'var(--loss)'
                      }}>
                        {formatCurrency(position.unrealized_pl)}
                      </div>
                      <div style={{
                        fontSize: '12px',
                        opacity: 0.8,
                        color: position.unrealized_pl >= 0 ? 'var(--profit)' : 'var(--loss)'
                      }}>
                        {formatPercent(position.unrealized_pl_percent)}
                      </div>
                    </motion.div>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
};

export default PositionsTable;