# 🖥️ Big Dipper Web Monitor - Technical Design

**Version:** 1.0
**Date:** October 2025
**Purpose:** Real-time web dashboard for Big Dipper trading monitoring
**Goal:** Minimize Claude queries for basic stats and trade visibility

---

## Executive Summary

Build a modular, real-time web dashboard to monitor Big Dipper trading activity. All data parsed from structured logs and Alpaca API, designed for extensibility and aesthetic flexibility.

**Key Features:**
- Real-time trade monitoring (WebSocket updates)
- Historical performance analytics
- Wash sale tracking and visibility
- Position P/L from Alpaca (accurate data)
- Mobile-responsive design
- Docker deployment ready

---

## 1. Architecture Overview

### Three-Tier Design (Modular & Decoupled)

```
┌─────────────────────────────────────────────────────────┐
│                     FRONTEND (Tier 3)                   │
│  - React/Vue/Svelte (choose later)                      │
│  - Chart.js/D3.js for visualizations                    │
│  - Mobile-responsive (TailwindCSS/Bootstrap)            │
│  - Themeable (light/dark mode ready)                    │
└────────────────────┬────────────────────────────────────┘
                     │ REST API / WebSocket
┌────────────────────▼────────────────────────────────────┐
│                   BACKEND (Tier 2)                      │
│  - FastAPI (Python) or Express.js (Node)                │
│  - REST endpoints for historical data                   │
│  - WebSocket for real-time updates                      │
│  - Data aggregation & caching layer                     │
└────────────────────┬────────────────────────────────────┘
                     │ File I/O / API calls
┌────────────────────▼────────────────────────────────────┐
│                 DATA LAYER (Tier 1)                     │
│  - Log Parser (tail -f big_dipper.log)                  │
│  - Alpaca API Client (direct SDK calls)                 │
│  - SQLite for historical aggregation                    │
│  - Redis for real-time state (optional)                 │
└─────────────────────────────────────────────────────────┘
```

**Why this structure:**
- **Tier 1** = Single source of truth (logs + Alpaca)
- **Tier 2** = Business logic, swappable without touching UI
- **Tier 3** = Presentation, redesignable without touching backend

---

## 2. Data Layer (Tier 1)

### 2.1 Log Parser Service

**Technology:** Python (async) or Node.js streams

**Core Functionality:**
```python
class LogParser:
    """Parse Big Dipper logs in real-time"""

    def __init__(self, log_path: str):
        self.log_path = log_path
        self.handlers = {}  # Event handlers by tag type

    def register_handler(self, tag: str, callback):
        """Register callback for specific log tag"""
        self.handlers[tag] = callback

    async def tail_and_parse(self):
        """Tail log file and emit events"""
        async for line in tail_file_async(self.log_path):
            event = self.parse_line(line)
            if event and event['tag'] in self.handlers:
                await self.handlers[event['tag']](event)

    def parse_line(self, line: str) -> dict:
        """Parse single log line into structured event"""
        # Extract timestamp
        # Extract tag [TRADE|SKIP|ACCOUNT|BRAKE|OPPORTUNITY]
        # Extract data based on regex patterns
        # Return structured dict
```

**Regex Patterns:**
```python
PATTERNS = {
    'TRADE': r'\[TRADE\] BUY (\w+) ([\d.]+) @ \$([\d.]+) = \$([\d.]+)',
    'ACCOUNT': r'\[ACCOUNT\] equity=\$([\d.]+) cash=\$([\d.]+) margin=([\d.]+)% pl=\$([+-]?[\d.]+) pl_pct=([+-]?[\d.]+)%',
    'SKIP': r'\[SKIP\] (\w+) (.+)',
    'OPPORTUNITY': r'\[OPPORTUNITY\] (\w+) ([+-]?[\d.]+)% @ \$([\d.]+) score=([\d.]+)x',
    'BRAKE': r'\[BRAKE\].*Margin at ([\d.]+)%',
    'WINNERS': r'Winners: (.+)',
    'LOSERS': r'Losers: (.+)',
    'CYCLE': r'Cycle #(\d+)',
    'MARKET_STATUS': r'(Market closed|Pre-Market|Regular|After-Hours)',
}
```

**Event Schema:**
```typescript
interface LogEvent {
    timestamp: string;      // ISO 8601
    tag: string;           // TRADE | SKIP | ACCOUNT | etc
    raw: string;           // Original log line
    data: {                // Parsed data (varies by tag)
        symbol?: string;
        quantity?: number;
        price?: number;
        equity?: number;
        margin?: number;
        pl_dollar?: number;
        pl_percent?: number;
    };
}
```

---

### 2.2 Database Schema (SQLite)

**Why SQLite:**
- Single file, no server needed
- Perfect for time-series data <10GB
- Easy backups (copy file)
- Embeddable in backend
- Docker volume friendly

**Tables:**

```sql
-- Account snapshots (every cycle)
CREATE TABLE account_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    cycle_number INTEGER,
    equity REAL NOT NULL,
    cash REAL NOT NULL,
    margin_ratio REAL NOT NULL,
    pl_dollar REAL,
    pl_percent REAL,
    market_status TEXT,  -- 'open' | 'closed' | 'extended'
    INDEX idx_timestamp (timestamp)
);

-- Trade history
CREATE TABLE trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    total_value REAL NOT NULL,
    order_id TEXT,
    INDEX idx_symbol (symbol),
    INDEX idx_timestamp (timestamp)
);

-- Skipped opportunities
CREATE TABLE skips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    reason TEXT NOT NULL,  -- 'wash_sale_conflict' | 'cooldown' | etc
    dip_percent REAL,
    INDEX idx_symbol (symbol),
    INDEX idx_reason (reason)
);

-- Qualified opportunities (not executed)
CREATE TABLE opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    dip_percent REAL NOT NULL,
    price REAL NOT NULL,
    score REAL NOT NULL,
    executed BOOLEAN DEFAULT 0,
    INDEX idx_timestamp (timestamp)
);

-- Emergency brake events
CREATE TABLE brake_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    cycle_number INTEGER,
    margin_ratio REAL NOT NULL,
    margin_debt REAL,
    equity REAL,
    duration_seconds INTEGER,
    INDEX idx_timestamp (timestamp)
);

-- Position snapshots (periodic)
CREATE TABLE position_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    market_value REAL NOT NULL,
    unrealized_pl REAL NOT NULL,
    unrealized_pl_pct REAL NOT NULL,
    avg_entry_price REAL,
    INDEX idx_timestamp (timestamp),
    INDEX idx_symbol (symbol)
);

-- Daily aggregations (for performance)
CREATE TABLE daily_stats (
    date DATE PRIMARY KEY,
    trades_count INTEGER DEFAULT 0,
    total_deployed REAL DEFAULT 0,
    starting_equity REAL,
    ending_equity REAL,
    peak_equity REAL,
    trough_equity REAL,
    max_margin_ratio REAL DEFAULT 0,
    brake_events INTEGER DEFAULT 0,
    wash_sales_blocked INTEGER DEFAULT 0
);
```

---

### 2.3 Alpaca API Integration

**Purpose:** Fetch live data not in logs

```python
class AlpacaDataService:
    """Direct Alpaca API integration"""

    def get_current_positions(self) -> List[Position]:
        """Real-time positions (fresher than logs)"""
        return trading_client.get_all_positions()

    def get_account_snapshot(self) -> Account:
        """Current account state"""
        return trading_client.get_account()

    def get_recent_orders(self, limit=50) -> List[Order]:
        """Order history (for reconciliation)"""
        return trading_client.get_orders(...)

    def get_market_clock(self) -> Clock:
        """Is market open? When next open?"""
        return trading_client.get_clock()
```

**Refresh Strategy:**
- **Positions:** Every 60 seconds (match Big Dipper cycle)
- **Account:** Every 60 seconds
- **Orders:** Every 5 minutes
- **Clock:** Every 5 minutes

---

## 3. Backend API (Tier 2)

### 3.1 Technology Choice

**Recommendation:** **FastAPI (Python)**

**Why:**
- Native async/await for WebSocket
- Same language as Big Dipper (easy Alpaca SDK reuse)
- Auto-generated API docs (Swagger)
- Fast enough for real-time updates
- Great typing with Pydantic

**Alternative:** Express.js (Node) if you prefer JavaScript

---

### 3.2 API Endpoints (RESTful)

```python
# ===== DASHBOARD OVERVIEW =====
GET /api/v1/dashboard
→ Returns: {
    account: { equity, cash, margin, pl_dollar, pl_percent },
    market: { is_open, session_type, next_open },
    positions_count: int,
    today_trades: int,
    active_brake: boolean,
    last_update: timestamp
}

# ===== ACCOUNT METRICS =====
GET /api/v1/account/current
→ Current account state (from Alpaca)

GET /api/v1/account/history?period=1d|1w|1m|all
→ Historical equity/margin chart data

GET /api/v1/account/performance?period=1d|1w|1m
→ Returns: {
    starting_equity, ending_equity, total_pl, pl_percent,
    peak_equity, max_drawdown, sharpe_ratio (optional)
}

# ===== POSITIONS =====
GET /api/v1/positions/current
→ Live positions with P/L from Alpaca

GET /api/v1/positions/history/{symbol}?period=1w
→ Historical P/L for specific symbol

GET /api/v1/positions/allocation
→ Pie chart data: { symbol, value, percent }[]

# ===== TRADES =====
GET /api/v1/trades/recent?limit=50
→ Most recent trades

GET /api/v1/trades/by-symbol/{symbol}
→ All trades for specific symbol

GET /api/v1/trades/daily-summary?date=2025-10-17
→ { date, count, total_deployed, symbols: [...] }

# ===== OPPORTUNITIES =====
GET /api/v1/opportunities/recent?limit=20
→ Recently qualified dips (executed + skipped)

GET /api/v1/opportunities/missed?reason=wash_sale
→ Filter by skip reason

GET /api/v1/opportunities/best-scores?period=1d
→ Top opportunities by score

# ===== BRAKE EVENTS =====
GET /api/v1/brake/current
→ Is brake active? Current margin ratio?

GET /api/v1/brake/history?period=1w
→ Past brake events with duration

# ===== ANALYTICS =====
GET /api/v1/analytics/wash-sales?period=1w
→ Wash sale blocks by symbol

GET /api/v1/analytics/win-rate?period=1m
→ Winning vs losing positions

GET /api/v1/analytics/dip-distribution
→ Histogram: how deep were qualifying dips?

# ===== CONFIGURATION =====
GET /api/v1/config/current
→ Current Big Dipper config (read from config.py)

POST /api/v1/config/validate
→ Validate config changes before restart
```

---

### 3.3 WebSocket for Real-Time Updates

```python
# WebSocket endpoint
WS /ws/live

# Client subscribes to channels:
→ {"subscribe": ["trades", "account", "opportunities", "brake"]}

# Server pushes events:
← {"channel": "trades", "event": {...}}
← {"channel": "account", "event": {equity: 35000, ...}}
← {"channel": "brake", "event": {active: true, margin: 0.16}}
```

**Subscription Channels:**
- `trades` - New trades as they happen
- `account` - Account updates every cycle
- `opportunities` - New qualified dips
- `brake` - Brake activation/deactivation
- `skips` - Wash sales and other rejections
- `positions` - Position P/L changes

---

## 4. Frontend (Tier 3)

### 4.1 Technology Stack (Choose Later)

**Options:**
1. **React** - Most popular, huge ecosystem
2. **Vue.js** - Simpler, easier learning curve
3. **Svelte** - Fastest, smallest bundle
4. **Vanilla JS** - No framework, maximum control

**Recommendation:** Start with **React** or **Vue** for component modularity

---

### 4.2 Component Architecture (Framework-Agnostic)

```
src/
├── components/
│   ├── dashboard/
│   │   ├── AccountSummary.tsx
│   │   ├── MarketStatus.tsx
│   │   ├── QuickStats.tsx
│   │   └── BrakeAlert.tsx
│   ├── charts/
│   │   ├── EquityChart.tsx
│   │   ├── MarginGauge.tsx
│   │   ├── PLPieChart.tsx
│   │   └── DipHistogram.tsx
│   ├── tables/
│   │   ├── TradeHistory.tsx
│   │   ├── PositionTable.tsx
│   │   ├── OpportunityList.tsx
│   │   └── WashSaleLog.tsx
│   ├── realtime/
│   │   ├── LiveTicker.tsx      (WebSocket)
│   │   ├── CycleCounter.tsx    (WebSocket)
│   │   └── BrakeMonitor.tsx    (WebSocket)
│   └── config/
│       ├── SymbolManager.tsx
│       ├── ThresholdEditor.tsx
│       └── ConfigValidator.tsx
├── services/
│   ├── api.ts              (REST client)
│   ├── websocket.ts        (WebSocket client)
│   └── alpaca.ts           (Direct Alpaca, if needed)
├── stores/                  (State management)
│   ├── accountStore.ts
│   ├── tradesStore.ts
│   └── opportunitiesStore.ts
└── pages/
    ├── Dashboard.tsx       (Main view)
    ├── Trades.tsx          (Trade history)
    ├── Analytics.tsx       (Charts & metrics)
    ├── Positions.tsx       (Current positions)
    ├── Opportunities.tsx   (Missed/qualified)
    └── Config.tsx          (Settings)
```

---

### 4.3 Page Layouts (Wireframe Concepts)

**Dashboard Page:**
```
┌──────────────────────────────────────────────────────┐
│ [Account: $35,000 | Cash: $2,500 | Margin: 0%]       │
│ [P/L: +$342 (+0.98%) | Trades Today: 3]              │
├──────────────────────────────────────────────────────┤
│ ┌────────────────┐  ┌────────────────┐              │
│ │  Equity Chart  │  │  Margin Gauge  │              │
│ │  (7 days)      │  │  15% / 20%     │              │
│ └────────────────┘  └────────────────┘              │
├──────────────────────────────────────────────────────┤
│ Recent Trades                                        │
│ • MSFT: 10 @ $483.08 = $4,830 [2 min ago]           │
│ • PLTR: 8 @ $168.59 = $1,348  [15 min ago]          │
├──────────────────────────────────────────────────────┤
│ Active Positions (18)                                │
│ META: $5,132 (+0.00%) | MSFT: $5,060 (+0.28%) | ...  │
├──────────────────────────────────────────────────────┤
│ Missed Opportunities                                 │
│ ⚠️ TER: -13.44% (wash sale conflict)                │
│ ⚠️ FIGR: -23.73% (not fractionable)                 │
└──────────────────────────────────────────────────────┘
```

**Analytics Page:**
```
┌──────────────────────────────────────────────────────┐
│ Performance Metrics (Last 30 Days)                   │
│ • Total P/L: +$1,250 (+3.7%)                         │
│ • Win Rate: 62% (18/29 positions)                    │
│ • Max Drawdown: -4.2%                                │
│ • Sharpe Ratio: 1.85                                 │
├──────────────────────────────────────────────────────┤
│ ┌────────────────┐  ┌────────────────┐              │
│ │ Dip Histogram  │  │ Allocation Pie │              │
│ │ (qualifying %) │  │ (by sector)    │              │
│ └────────────────┘  └────────────────┘              │
├──────────────────────────────────────────────────────┤
│ Top Performers                   Bottom Performers   │
│ 1. MSFT: +14.2%                  1. KTOS: -7.6%     │
│ 2. BLV: +9.8%                    2. AVAV: -6.5%     │
│ 3. PLTR: +8.1%                   3. MP: -3.5%       │
└──────────────────────────────────────────────────────┘
```

---

## 5. Docker Deployment

### 5.1 File Structure

```
big-dipper/              (existing repo)
├── main.py
├── config.py
├── dip_logic.py
├── utils.py
├── big_dipper.log       ← Shared with monitor
├── Dockerfile           (existing)
└── ...

web-monitor/             (new directory)
├── backend/
│   ├── Dockerfile
│   ├── main.py          (FastAPI app)
│   ├── models.py        (SQLAlchemy models)
│   ├── parsers/
│   │   ├── log_parser.py
│   │   └── patterns.py
│   ├── services/
│   │   ├── alpaca_service.py
│   │   ├── aggregation_service.py
│   │   └── alert_service.py
│   ├── routes/
│   │   ├── account.py
│   │   ├── trades.py
│   │   ├── opportunities.py
│   │   └── websocket.py
│   ├── database.py
│   ├── config.py
│   └── requirements.txt
│
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── stores/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml   (orchestrates all services)
```

---

### 5.2 Docker Compose Configuration

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  # Big Dipper trading bot (existing)
  big-dipper:
    build:
      context: ./big-dipper
      dockerfile: Dockerfile
    container_name: big-dipper
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
      - ./big_dipper.log:/app/big_dipper.log
    environment:
      - ALPACA_KEY=${ALPACA_KEY}
      - ALPACA_SECRET=${ALPACA_SECRET}
      - ALPACA_PAPER=${ALPACA_PAPER:-true}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    networks:
      - dipper-network

  # Web Monitor Backend (new)
  monitor-backend:
    build:
      context: ./web-monitor/backend
      dockerfile: Dockerfile
    container_name: monitor-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./big_dipper.log:/logs/big_dipper.log:ro  # Read-only
      - ./web-monitor-data:/data                   # SQLite DB
    environment:
      - ALPACA_KEY=${ALPACA_KEY}
      - ALPACA_SECRET=${ALPACA_SECRET}
      - ALPACA_PAPER=${ALPACA_PAPER:-true}
      - LOG_PATH=/logs/big_dipper.log
      - DB_PATH=/data/web-monitor.db
    depends_on:
      - big-dipper
    networks:
      - dipper-network

  # Web Monitor Frontend (new)
  monitor-frontend:
    build:
      context: ./web-monitor/frontend
      dockerfile: Dockerfile
    container_name: monitor-frontend
    restart: unless-stopped
    ports:
      - "80:80"      # HTTP
      - "443:443"    # HTTPS (optional)
    environment:
      - API_URL=http://monitor-backend:8000
      - WS_URL=ws://monitor-backend:8000/ws
    depends_on:
      - monitor-backend
    networks:
      - dipper-network

networks:
  dipper-network:
    driver: bridge

volumes:
  web-monitor-data:
    driver: local
```

---

### 5.3 Backend Dockerfile

**web-monitor/backend/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /data

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run FastAPI with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**requirements.txt:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alpaca-py==0.20.1
python-dotenv==1.0.0
pydantic==2.5.0
websockets==12.0
aiofiles==23.2.1
```

---

### 5.4 Frontend Dockerfile

**web-monitor/frontend/Dockerfile:**
```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

### 5.5 Deployment Commands

**Local Development:**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Restart specific service
docker-compose restart monitor-backend

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

**Production:**
```bash
# Build images
docker-compose build

# Start in production mode
docker-compose up -d

# View backend logs
docker-compose logs -f monitor-backend

# Check health
curl http://localhost:8000/health

# Access frontend
open http://localhost
```

---

### 5.6 Environment Variables

**.env file:**
```bash
# Alpaca credentials (shared between Big Dipper and Monitor)
ALPACA_KEY=your_key_here
ALPACA_SECRET=your_secret_here
ALPACA_PAPER=true

# Logging
LOG_LEVEL=INFO

# Monitor Backend
DB_PATH=/data/web-monitor.db
LOG_PATH=/logs/big_dipper.log

# Frontend API endpoints
API_URL=http://localhost:8000
WS_URL=ws://localhost:8000/ws
```

---

### 5.7 Volume Persistence

**Persisted data:**
- `/data/web-monitor.db` - SQLite database (historical data)
- `/logs/big_dipper.log` - Shared log file (read-only by monitor)

**Backup strategy:**
```bash
# Backup database
docker cp monitor-backend:/data/web-monitor.db ./backups/

# Restore database
docker cp ./backups/web-monitor.db monitor-backend:/data/

# Backup logs
docker cp big-dipper:/app/big_dipper.log ./backups/
```

---

## 6. Implementation Phases

### Phase 1: Foundation (MVP) - Week 1
- [ ] Set up FastAPI backend skeleton
- [ ] Build log parser with 5 core tags
- [ ] Create SQLite schema
- [ ] Implement 5 essential REST endpoints
- [ ] Build Alpaca integration service
- [ ] Create Docker setup
- [ ] Simple HTML dashboard to test API

**Deliverable:** Working API returning data via Docker

---

### Phase 2: Real-Time - Week 2
- [ ] Add WebSocket support
- [ ] Implement log tailing service
- [ ] Add real-time event broadcasting
- [ ] Build simple frontend with live updates
- [ ] Test with Big Dipper running in Docker

**Deliverable:** Live dashboard updating as Big Dipper trades

---

### Phase 3: Visualizations - Week 3
- [ ] Choose frontend framework
- [ ] Build equity chart component
- [ ] Build margin gauge
- [ ] Build position allocation pie chart
- [ ] Build trade history table
- [ ] Add styling framework
- [ ] Update Docker frontend build

**Deliverable:** Polished dashboard with charts

---

### Phase 4: Analytics - Week 4
- [ ] Implement aggregation service
- [ ] Build analytics page
- [ ] Add dip distribution histogram
- [ ] Add performance metrics
- [ ] Build wash sale analysis view

**Deliverable:** Full analytics suite

---

### Phase 5: Polish - Week 5+
- [ ] Add alerting module
- [ ] Build config editor UI
- [ ] Add export functionality
- [ ] Mobile optimization
- [ ] Dark mode
- [ ] Production hardening

**Deliverable:** Production-ready monitor

---

## 7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **SQLite** | Simple, no server, <10GB fine, easy backups, Docker friendly |
| **FastAPI** | Python (matches Big Dipper), async, auto docs |
| **WebSocket** | Real-time updates without polling |
| **Structured logs** | Machine-parseable, no coupling |
| **3-tier architecture** | Modularity, swappable components |
| **Docker Compose** | Easy orchestration, reproducible deploys |
| **Shared log volume** | Monitor reads Big Dipper logs directly |
| **Component-based UI** | Reusable, testable, framework-agnostic |

---

## 8. Modular Extension Points

### Easy to Swap:
1. **Frontend Framework** - All components use standard API
2. **Database** - SQLAlchemy ORM makes Postgres/MySQL swap trivial
3. **Charts Library** - Just component replacement
4. **Styling** - CSS modules keep styles isolated
5. **Alerting** - Plugin architecture

### Easy to Extend:
1. **New log tags** - Add pattern to `patterns.py`
2. **New endpoints** - FastAPI auto-generates docs
3. **New charts** - Drop component into `src/charts/`
4. **New metrics** - Add to aggregation service

### Easy to Scale:
- SQLite → Postgres (change connection string)
- Single server → Load balanced (stateless API)
- WebSocket → Redis pub/sub (multi-instance)

---

## 9. Success Criteria

**MVP Success:**
- [ ] Dashboard loads in <2 seconds
- [ ] Real-time updates <5 seconds after log entry
- [ ] Accurate P/L matches Alpaca
- [ ] No manual Claude queries needed
- [ ] Mobile-accessible
- [ ] Docker deployment working

**Full Success:**
- [ ] All historical data queryable
- [ ] Charts interactive
- [ ] Alerts working
- [ ] Config editable via UI
- [ ] Zero downtime during restarts

---

## 10. Getting Started

### Prerequisites
- Docker & Docker Compose installed
- Big Dipper running and logging to `big_dipper.log`
- Alpaca API credentials in `.env`

### Quick Start
```bash
# 1. Clone or create web-monitor directory
mkdir -p web-monitor/{backend,frontend}

# 2. Follow Phase 1 implementation steps
cd web-monitor/backend
# (Set up FastAPI skeleton)

# 3. Build and run with Docker
cd ../../
docker-compose up -d

# 4. Access dashboard
open http://localhost
```

### Development Workflow
```bash
# Edit code in web-monitor/backend or web-monitor/frontend
# Rebuild specific service
docker-compose up -d --build monitor-backend

# View logs
docker-compose logs -f monitor-backend

# Run tests (add later)
docker-compose exec monitor-backend pytest
```

---

## 11. Configuration File

**web-monitor/backend/config.yaml:**
```yaml
database:
  type: sqlite
  path: /data/web-monitor.db

big_dipper:
  log_path: /logs/big_dipper.log
  config_path: /app/config.py  # If mounted

alpaca:
  refresh_interval_seconds: 60

api:
  host: 0.0.0.0
  port: 8000
  cors_origins:
    - "http://localhost"
    - "http://localhost:3000"

websocket:
  max_connections: 100
  heartbeat_interval: 30

aggregation:
  daily_stats_update_interval: 60
  metrics_cache_ttl: 300
```

---

## 12. Security Considerations

**For Production:**
1. **HTTPS** - Use Let's Encrypt with Nginx
2. **Authentication** - Add BasicAuth or OAuth
3. **API Keys** - Secure Alpaca credentials
4. **CORS** - Restrict origins in production
5. **Rate Limiting** - Prevent API abuse
6. **Firewall** - Only expose ports 80/443

**Docker Security:**
```yaml
# In docker-compose.yml
services:
  monitor-backend:
    read_only: true  # Filesystem read-only
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

---

## 13. Troubleshooting

**Backend won't start:**
```bash
docker-compose logs monitor-backend
# Check for missing env vars, DB permissions
```

**Frontend can't reach backend:**
```bash
# Check network
docker-compose exec monitor-frontend ping monitor-backend

# Verify API_URL in frontend env
docker-compose exec monitor-frontend env | grep API_URL
```

**Database locked:**
```bash
# Check for multiple writers
docker-compose ps | grep monitor
# Restart backend
docker-compose restart monitor-backend
```

**Log not updating:**
```bash
# Verify log volume mount
docker-compose exec monitor-backend ls -la /logs/
# Check Big Dipper is writing
docker-compose exec big-dipper tail -f big_dipper.log
```

---

## 14. Next Steps

1. **Create Phase 1 skeleton** - Set up FastAPI + Docker
2. **Implement log parser** - Test with current logs
3. **Build database layer** - Create tables, test inserts
4. **Create simple HTML frontend** - Verify API works
5. **Add WebSocket** - Test real-time updates
6. **Choose frontend framework** - Build dashboard
7. **Add charts** - Visualize data
8. **Deploy** - Docker Compose production

---

**This plan is living documentation. Update as implementation progresses.**

**Author:** Claude
**License:** Same as Big Dipper
**Support:** See main README.md
