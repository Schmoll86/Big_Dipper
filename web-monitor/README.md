# Big Dipper Web Monitor

**Real-time monitoring dashboard for Big Dipper trading bot**

Beautiful dark theme • Live Alpaca data • Smooth animations • 5-second updates

---

## Quick Start

### Start Everything
```bash
./start_monitor.sh
```

This will:
- Load environment variables
- Start Flask backend (port 5001)
- Start React frontend (port 3000)
- Open browser automatically

### Stop Everything
```bash
./stop_monitor.sh
```

### Access
- **Dashboard:** http://localhost:3000
- **API:** http://localhost:5001/api

---

## What You'll See

### Account Overview
- Total equity with animated updates
- Day P/L with color coding (green/red)
- Cash and buying power

### Margin Gauge
- Visual bar showing margin usage
- Warning zones at 75% and 90%
- Real-time percentage calculation

### Positions Table
- All current positions with live P/L
- Sortable by symbol, value, or P/L
- Hover effects and smooth animations

### Recent Trades
- Today's executed trades
- Entry animations for new trades
- Timestamp and trade details

### Opportunity Radar
- Qualified dip opportunities
- Executed vs skipped status
- Score visualization with reasons

### Equity Chart
- Historical performance line chart
- Time period selector (1D, 1W, 1M, All)
- Gradient fill and custom tooltips

---

## Tech Stack

### Backend (Flask)
- **Port:** 5001
- **Framework:** Flask + Flask-CORS
- **Data Source:** Alpaca API (live) + SQLite (historical)
- **Polling:** Parses Big Dipper logs on each request

### Frontend (React)
- **Port:** 3000
- **Framework:** React 19 + TypeScript
- **Animations:** Framer Motion
- **Charts:** Recharts
- **Styling:** Custom dark theme with glass morphism
- **Updates:** Polls backend every 5 seconds

---

## API Endpoints

| Endpoint | Description | Response |
|----------|-------------|----------|
| `GET /api/health` | Health check | `{status, timestamp}` |
| `GET /api/dashboard` | Main data | `{account, positions, trades, opportunities}` |
| `GET /api/historical/<period>` | Historical snapshots | `{snapshots[], period}` |

**Periods:** `1d`, `1w`, `1m`, `all`

### Test Backend
```bash
# Health check
curl http://localhost:5001/api/health

# Dashboard data
curl http://localhost:5001/api/dashboard | python3 -m json.tool

# Historical data
curl http://localhost:5001/api/historical/1d
```

---

## Project Structure

```
web-monitor/
├── backend/
│   ├── app.py              # Flask API server
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/
│   ├── src/
│   │   ├── components/     # 6 main components
│   │   ├── services/       # API client with polling
│   │   ├── types/          # TypeScript interfaces
│   │   └── styles/         # Dark theme CSS
│   ├── package.json
│   └── Dockerfile          # Frontend container (nginx)
├── data/
│   └── monitor.db          # SQLite database
├── .env                    # Alpaca credentials
├── start_monitor.sh        # One-command startup
├── stop_monitor.sh         # Clean shutdown
└── docker-compose.yml      # Container orchestration
```

---

## Manual Startup (Development)

### Backend Only
```bash
cd backend
export ALPACA_KEY=your_key
export ALPACA_SECRET=your_secret
export ALPACA_PAPER=false
python3 app.py
```

### Frontend Only
```bash
cd frontend
npm start
```

---

## Environment Variables

Create `.env` file in web-monitor directory:
```bash
ALPACA_KEY=your_alpaca_key
ALPACA_SECRET=your_alpaca_secret
ALPACA_PAPER=false  # or true for paper trading
LOG_LEVEL=INFO
```

---

## Logs

- **Backend:** `/tmp/big_dipper_backend.log`
- **Frontend:** `/tmp/big_dipper_frontend.log`

View in real-time:
```bash
tail -f /tmp/big_dipper_backend.log
tail -f /tmp/big_dipper_frontend.log
```

---

## Troubleshooting

### Backend won't start
```bash
# Check Python dependencies
cd backend
pip install -r requirements.txt

# Verify Alpaca credentials
env | grep ALPACA

# Check log
cat /tmp/big_dipper_backend.log
```

### Frontend won't compile
```bash
# Install dependencies
cd frontend
npm install

# Check log
cat /tmp/big_dipper_frontend.log
```

### No historical data in chart
**Expected on first run** - Historical snapshots accumulate over time as the bot runs. The chart will show "No data available" until snapshots are collected.

### Opportunities/Trades empty
**Expected behavior** - These only populate when:
- Opportunities: Big Dipper detects a qualified dip
- Trades: Big Dipper executes a buy order

---

## Docker Deployment (Alternative)

```bash
# Build and start
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Note:** Docker setup uses ports 5000 (backend) and 3000 (frontend). The standalone scripts use port 5001 for backend to avoid conflicts.

---

## Design System

### Colors
- **Background:** Deep space (#0a0e1a, #141925)
- **Accent:** Blue (#4299e1), Purple (#9f7aea)
- **Profit:** Green (#48bb78)
- **Loss:** Red (#f56565)
- **Warning:** Orange (#ed8936)

### Effects
- Glass morphism with blur(10px)
- Smooth transitions (300-500ms)
- Scale animations on value changes
- Slide-in animations for new items
- Glow effects on critical warnings

---

## Known Limitations

1. **Historical chart empty on first run** - Needs time to collect snapshots
2. **No exit signals** - Monitor only, Big Dipper handles trading logic
3. **60-second Big Dipper cycles** - May miss very brief dips
4. **No authentication** - Intended for local/private use only

---

## Development Notes

See [CLAUDE.md](CLAUDE.md) for:
- Issues found during development
- Configuration gotchas
- API response format details
- Future enhancement ideas

---

## License

Personal use only. Same license as Big Dipper.
