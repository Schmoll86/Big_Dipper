// API Response Types for Big Dipper Monitor

export interface Account {
  equity: number;
  cash: number;
  buying_power: number;
  margin_used: number;
  day_pl: number;
  day_pl_percent: number;
}

export interface Position {
  symbol: string;
  qty: number;
  market_value: number;
  avg_entry: number;
  current_price: number;
  unrealized_pl: number;
  unrealized_pl_percent: number;
}

export interface Trade {
  timestamp: string;
  symbol: string;
  quantity: number;
  price: number;
  total_value: number;
}

export interface Opportunity {
  timestamp: string;
  symbol: string;
  dip_percent: number;
  price: number;
  score: number;
  executed: boolean;
  skip_reason: string | null;
}

export interface DashboardResponse {
  account: Account;
  positions: Position[];
  today_trades: Trade[];
  opportunities: Opportunity[];
  last_update: string;
}

export interface HistoricalSnapshot {
  timestamp: string;
  equity: number;
  positions_count: number;
  margin_ratio: number;
}

export interface HistoricalResponse {
  snapshots: HistoricalSnapshot[];
  period: string;
}
