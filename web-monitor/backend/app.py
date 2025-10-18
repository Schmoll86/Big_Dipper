"""
Big Dipper Web Monitor - Flask Backend
Simple, beautiful, functional
"""

import os
import re
import sqlite3
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Allow React frontend to connect

# Initialize Alpaca clients
trading_client = TradingClient(
    os.getenv('ALPACA_KEY'),
    os.getenv('ALPACA_SECRET'),
    paper=os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
)

data_client = StockHistoricalDataClient(
    os.getenv('ALPACA_KEY'),
    os.getenv('ALPACA_SECRET')
)
# Database setup
# Use absolute path to avoid working directory issues
import os as _os
_BASE_DIR = _os.path.dirname(_os.path.abspath(__file__))
DB_PATH = _os.path.join(_BASE_DIR, '..', 'data', 'monitor.db')

def init_db():
    """Initialize SQLite database with tables"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Create tables if they don't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            symbol TEXT,
            quantity REAL,
            price REAL,
            total_value REAL,
            order_id TEXT UNIQUE
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS account_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            equity REAL,
            cash REAL,
            margin_ratio REAL,
            pl_dollar REAL,
            pl_percent REAL
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            symbol TEXT,
            dip_percent REAL,
            price REAL,
            score REAL,
            executed BOOLEAN DEFAULT 0,
            skip_reason TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS log_checkpoint (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            last_position INTEGER DEFAULT 0,
            last_timestamp DATETIME
        )
    ''')
    
    # Initialize checkpoint if it doesn't exist
    c.execute('''
        INSERT OR IGNORE INTO log_checkpoint (id, last_position, last_timestamp) 
        VALUES (1, 0, datetime('now'))
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()
# Log parsing patterns
LOG_PATTERNS = {
    'TRADE': re.compile(r'✅ BUY (\w+): ([\d.]+) shares @ \$([\d.]+) = \$([\d,]+\.\d+)'),
    'ACCOUNT': re.compile(r'💰 Account: \$([\d,]+\.\d+) equity, \$([\d,]+\.\d+) cash, Margin: ([\d.]+)%'),
    'OPPORTUNITY': re.compile(r'💎 (\w+) BUY: ([+-]?[\d.]+)% dip @ \$([\d.]+) \(score: ([\d.]+)x\)'),
    'SKIP': re.compile(r'(\w+): Would exceed margin limit'),
}

def parse_new_logs():
    """Parse new log entries since last checkpoint"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get last checkpoint
    checkpoint = c.execute('SELECT last_position FROM log_checkpoint WHERE id = 1').fetchone()
    last_position = checkpoint[0] if checkpoint else 0
    
    try:
        with open('/logs/big_dipper.log', 'r') as f:
            f.seek(last_position)
            
            for line in f:
                # Extract timestamp if present
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().isoformat()
                
                # Check for trade
                trade_match = LOG_PATTERNS['TRADE'].search(line)
                if trade_match:
                    symbol, qty, price, total = trade_match.groups()
                    total = float(total.replace(',', ''))                    
                    c.execute('''
                        INSERT OR IGNORE INTO trades 
                        (timestamp, symbol, quantity, price, total_value)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (timestamp, symbol, float(qty), float(price), total))
                
                # Check for account update
                account_match = LOG_PATTERNS['ACCOUNT'].search(line)
                if account_match:
                    equity, cash, margin = account_match.groups()
                    equity = float(equity.replace(',', ''))
                    cash = float(cash.replace(',', ''))
                    
                    c.execute('''
                        INSERT INTO account_snapshots 
                        (timestamp, equity, cash, margin_ratio)
                        VALUES (?, ?, ?, ?)
                    ''', (timestamp, equity, cash, float(margin)))
                
                # Check for opportunity
                opp_match = LOG_PATTERNS['OPPORTUNITY'].search(line)
                if opp_match:
                    symbol, dip, price, score = opp_match.groups()
                    
                    c.execute('''
                        INSERT INTO opportunities 
                        (timestamp, symbol, dip_percent, price, score, executed)
                        VALUES (?, ?, ?, ?, ?, 1)
                    ''', (timestamp, symbol, float(dip), float(price), float(score)))                
                # Check for skip
                skip_match = LOG_PATTERNS['SKIP'].search(line)
                if skip_match:
                    symbol = skip_match.group(1)
                    
                    # Update the most recent opportunity for this symbol as skipped
                    c.execute('''
                        UPDATE opportunities 
                        SET skip_reason = 'margin_limit', executed = 0
                        WHERE symbol = ? AND timestamp >= datetime('now', '-1 minute')
                        ORDER BY timestamp DESC LIMIT 1
                    ''', (symbol,))
            
            # Update checkpoint
            new_position = f.tell()
            c.execute('UPDATE log_checkpoint SET last_position = ? WHERE id = 1', (new_position,))
            
    except FileNotFoundError:
        print("Log file not found")
    except Exception as e:
        print(f"Error parsing logs: {e}")
    
    conn.commit()
    conn.close()

@app.route('/api/dashboard')
def dashboard():
    """Main dashboard endpoint - combines Alpaca data with parsed logs"""
    # Parse any new log entries first
    parse_new_logs()    
    # Get real-time account data from Alpaca
    try:
        account = trading_client.get_account()
        positions = trading_client.get_all_positions()
        
        account_data = {
            'equity': float(account.equity),
            'cash': float(account.cash),
            'buying_power': float(account.buying_power),
            'margin_used': 0.0,  # Calculate from positions
            'day_pl': float(account.equity) - float(account.last_equity) if hasattr(account, 'last_equity') else 0,
            'day_pl_percent': 0.0
        }
        
        # Calculate margin usage
        if float(account.equity) > 0:
            margin_debt = float(account.equity) - float(account.cash)
            if margin_debt > 0:
                account_data['margin_used'] = (margin_debt / float(account.equity)) * 100
        
        # Calculate day P/L percentage
        if hasattr(account, 'last_equity') and float(account.last_equity) > 0:
            account_data['day_pl_percent'] = (account_data['day_pl'] / float(account.last_equity)) * 100
        
        # Process positions
        positions_data = []
        for p in positions:
            positions_data.append({
                'symbol': p.symbol,
                'qty': float(p.qty),
                'market_value': float(p.market_value),
                'avg_entry': float(p.avg_entry_price),
                'current_price': float(p.current_price) if hasattr(p, 'current_price') else 0,
                'unrealized_pl': float(p.unrealized_pl),
                'unrealized_pl_percent': float(p.unrealized_plpc) * 100 if hasattr(p, 'unrealized_plpc') else 0
            })
        
    except Exception as e:
        print(f"Error fetching Alpaca data: {e}")
        # Return cached data if Alpaca fails
        account_data = {'error': 'Failed to fetch live data'}
        positions_data = []
    
    # Get today's trades from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    today = datetime.now().strftime('%Y-%m-%d')
    trades = c.execute('''
        SELECT * FROM trades 
        WHERE date(timestamp) = date('now')
        ORDER BY timestamp DESC
        LIMIT 20
    ''').fetchall()
    
    trades_data = [dict(trade) for trade in trades]    
    # Get recent opportunities
    opportunities = c.execute('''
        SELECT * FROM opportunities
        ORDER BY timestamp DESC
        LIMIT 20
    ''').fetchall()
    
    opportunities_data = [dict(opp) for opp in opportunities]
    
    conn.close()
    
    return jsonify({
        'account': account_data,
        'positions': positions_data,
        'today_trades': trades_data,
        'opportunities': opportunities_data,
        'last_update': datetime.now().isoformat()
    })

@app.route('/api/historical/<period>')
def get_historical(period):
    """Get historical account snapshots for charting"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Determine date range based on period
    if period == '1d':
        start_date = datetime.now() - timedelta(days=1)
    elif period == '1w':
        start_date = datetime.now() - timedelta(weeks=1)
    elif period == '1m':
        start_date = datetime.now() - timedelta(days=30)
    else:  # 'all'
        start_date = datetime(2000, 1, 1)    
    snapshots = c.execute('''
        SELECT timestamp, equity, cash, margin_ratio
        FROM account_snapshots
        WHERE timestamp >= ?
        ORDER BY timestamp
    ''', (start_date.isoformat(),)).fetchall()

    conn.close()

    # Transform to match frontend expectations
    snapshots_data = []
    for s in snapshots:
        snapshots_data.append({
            'timestamp': s['timestamp'],
            'equity': s['equity'],
            'positions_count': 0,  # Can be enhanced later
            'margin_ratio': s['margin_ratio'] if s['margin_ratio'] else 0
        })

    return jsonify({
        'snapshots': snapshots_data,
        'period': period
    })

@app.route('/api/health')
def health_check():
    """Simple health check"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)