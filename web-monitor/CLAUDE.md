# Web Monitor Development Notes

**For Claude/AI assistants working on this project**

---

## Project Context

This is the web monitoring dashboard for Big Dipper, a buy-the-dip trading bot. The monitor is separate from the bot itself - it's a read-only dashboard that:
1. Fetches live data from Alpaca API
2. Parses Big Dipper's log files for historical data
3. Displays everything in a beautiful React frontend

**Philosophy:** Simple backend, beautiful frontend, stateless operation.

---

## Critical Configuration Issues

### 1. Environment Variables
**Problem:** .env file location can be confusing

**Current Setup:**
- `.env` is in `/web-monitor/` directory
- Backend loads it via `load_dotenv()` with no path specified
- Works when backend is run from backend directory
- Breaks if run from elsewhere

**Fix Options:**
- Move .env to backend directory
- OR use `load_dotenv('../.env')` in app.py
- OR use startup script that exports env vars (current solution)

**Current Solution:** `start_monitor.sh` exports env vars before starting backend.

---

### 2. API Response Format Mismatch (FIXED)
**Problem:** Historical endpoint returned wrong format

**Original Code:**
```python
return jsonify([dict(s) for s in snapshots])  # Returns []
```

**Frontend Expected:**
```typescript
{
  snapshots: HistoricalSnapshot[],
  period: string
}
```

**Fixed Code:**
```python
return jsonify({
    'snapshots': snapshots_data,
    'period': period
})
```

**Location:** `backend/app.py` line 302

---

### 3. Database Path Issues
**Problem:** Relative path `../data/monitor.db` only works from backend directory

**Current State:** Works because startup script cd's into backend

**Better Approach:**
```python
import os
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'monitor.db')
```

**Decision:** Keep current approach for simplicity, document in startup scripts.

---

### 4. Port Inconsistencies
**Watch Out:**
- Docker setup uses port 5000 for backend
- Standalone scripts use port 5001 for backend
- Frontend always uses port 3000

**Reason:** Port 5001 avoids conflicts with macOS AirPlay Receiver

**Frontend API Config:** `frontend/src/services/api.ts` line 6
```typescript
baseURL: process.env.REACT_APP_API_URL || 'http://localhost:5001/api'
```

---

## API Response Formats

### Dashboard Response
```typescript
{
  account: {
    equity: number,
    cash: number,
    buying_power: number,
    margin_used: number,        // Calculated as %
    day_pl: number,
    day_pl_percent: number
  },
  positions: [{
    symbol: string,
    qty: number,
    market_value: number,
    avg_entry: number,
    current_price: number,
    unrealized_pl: number,
    unrealized_pl_percent: number
  }],
  today_trades: [{
    timestamp: string,
    symbol: string,
    quantity: number,
    price: number,
    total_value: number
  }],
  opportunities: [{
    timestamp: string,
    symbol: string,
    dip_percent: number,
    price: number,
    score: number,
    executed: boolean,
    skip_reason: string | null
  }],
  last_update: string  // ISO format
}
```

### Historical Response (FIXED FORMAT)
```typescript
{
  snapshots: [{
    timestamp: string,
    equity: number,
    positions_count: number,
    margin_ratio: number
  }],
  period: string  // '1d', '1w', '1m', 'all'
}
```

---

## Frontend Component Structure

All components are in `frontend/src/components/`:

1. **AccountCard** - Main account metrics
   - Animated equity display
   - Day P/L with color coding
   - Cash and buying power

2. **MarginGauge** - Visual margin indicator
   - Animated progress bar
   - Warning thresholds at 75%, 90%
   - Glow effect when critical

3. **PositionsTable** - All positions
   - Sortable columns
   - Hover effects
   - Entry/exit animations

4. **TradeFeed** - Recent trades
   - Slide-in animations
   - Glow on newest trade
   - Scrollable list

5. **OpportunityRadar** - Qualified opportunities
   - Status badges (executed, skipped, brake, wash)
   - Score visualization
   - Skip reason display

6. **EquityChart** - Historical performance
   - Recharts line chart
   - Period selector
   - Gradient fill
   - Empty state for no data

---

## Animation Patterns

All animations use Framer Motion:

**Value Changes:**
```typescript
animate={{ scale: [1, 1.02, 1] }}
transition={{ duration: 0.3 }}
```

**List Entry:**
```typescript
initial={{ opacity: 0, x: -20 }}
animate={{ opacity: 1, x: 0 }}
exit={{ opacity: 0, x: 20 }}
```

**Card Entry:**
```typescript
initial={{ opacity: 0, scale: 0.95 }}
animate={{ opacity: 1, scale: 1 }}
```

**Hover Effects:**
```typescript
whileHover={{ y: -2 }}
```

---

## Common Gotchas

### 1. Empty Historical Data
**Not a bug** - Chart shows "No data available" on first run. Database needs time to accumulate snapshots from Big Dipper logs.

### 2. Empty Opportunities/Trades
**Expected** - Only populates when:
- Big Dipper detects qualified dips (opportunities)
- Big Dipper executes trades (trades)

### 3. Webpack Deprecation Warnings
**Harmless** - These are from react-scripts:
- `fs.F_OK is deprecated`
- `onAfterSetupMiddleware` deprecation
- `onBeforeSetupMiddleware` deprecation

**Action:** Ignore, everything still works.

### 4. Polling Dependency Warning
Dashboard.tsx has a useEffect dependency issue with `data` in fetchData callback. This is intentional - we want to keep showing stale data if API fails.

**Fix if needed:**
```typescript
const fetchData = useCallback(async () => {
  // ... fetch logic
}, []); // Remove data dependency
```

---

## Database Schema

SQLite database at `data/monitor.db`:

**trades:**
- id, timestamp, symbol, quantity, price, total_value, order_id

**account_snapshots:**
- id, timestamp, equity, cash, margin_ratio, pl_dollar, pl_percent

**opportunities:**
- id, timestamp, symbol, dip_percent, price, score, executed, skip_reason

**log_checkpoint:**
- id (always 1), last_position, last_timestamp

---

## Log Parsing Strategy

Backend parses Big Dipper logs on every dashboard request:
1. Check checkpoint for last read position
2. Seek to that position in log file
3. Parse new lines with regex patterns
4. Insert into database
5. Update checkpoint

**Patterns matched:**
- `[INFO] ✅ BUY` - Trade executed
- `[INFO] 💰 Account:` - Account snapshot
- `[INFO] 💎` - Qualified opportunity
- `[WARNING]` - Skipped opportunities

---

## Startup Scripts Workflow

### start_monitor.sh
1. Load .env file
2. Stop any existing processes
3. Start backend, wait for health check
4. Start frontend, wait for compilation
5. Open browser

### stop_monitor.sh
1. Kill backend process
2. Kill frontend process
3. Show status

**Log files:** `/tmp/big_dipper_backend.log` and `/tmp/big_dipper_frontend.log`

---

## Future Enhancements

### Low Priority
- Add WebSocket for real-time updates (currently 5s polling is fine)
- Backfill historical data from Alpaca API
- Add authentication for remote access
- Export data to CSV
- Add alerts/notifications

### Medium Priority
- Better error messages in UI
- Retry logic for failed API calls
- Loading skeletons for components
- Responsive mobile layout improvements

### High Priority if Issues
- Make database path absolute
- Centralize env var loading
- Add health check endpoint for frontend

---

## Testing Checklist

When making changes, verify:
- [ ] Backend starts without errors
- [ ] Frontend compiles without TypeScript errors
- [ ] Dashboard API returns all fields
- [ ] Historical API returns correct format
- [ ] Browser console has no errors
- [ ] All 6 components render
- [ ] Animations are smooth
- [ ] 5-second polling works
- [ ] Sorting works in positions table
- [ ] Period selector works in chart

---

## Code Style

**Backend (Python):**
- Simple functions, no complex classes
- Direct Alpaca SDK usage
- SQLite with context managers
- Print statements for logging (no fancy logger)

**Frontend (TypeScript):**
- Functional components with hooks
- Framer Motion for all animations
- Inline styles (no CSS-in-JS library)
- Number formatting with Intl.NumberFormat

**Philosophy:** Keep it simple. No over-engineering.

---

## When Things Break

### Backend won't start
1. Check `/tmp/big_dipper_backend.log`
2. Verify env vars are exported
3. Test Alpaca connection manually
4. Check database file exists and is writable

### Frontend won't compile
1. Check `/tmp/big_dipper_frontend.log`
2. Verify node_modules exists (`npm install`)
3. Look for TypeScript errors
4. Clear npm cache if needed

### Data not showing
1. Test backend endpoints directly with curl
2. Check browser network tab for failed requests
3. Verify Big Dipper is running and logging
4. Check database has data: `sqlite3 data/monitor.db "SELECT COUNT(*) FROM trades;"`

### CORS errors
1. Verify Flask-CORS is installed
2. Check CORS(app) is called in app.py
3. Ensure frontend is calling correct backend URL

---

## Don't Break These Rules

1. **Keep it stateless** - Backend should be restartable anytime
2. **Keep it simple** - No complex state management or abstractions
3. **Keep it 4 files** - No new top-level files (except docs)
4. **Keep dependencies minimal** - Only what's in package.json/requirements.txt
5. **Keep animations smooth** - 300-500ms duration, easeOut easing

---

## Quick Reference

**Backend health:** `curl http://localhost:5001/api/health`
**Frontend status:** http://localhost:3000
**Restart:** `./start_monitor.sh`
**Stop:** `./stop_monitor.sh`
**Logs:** `tail -f /tmp/big_dipper_{backend,frontend}.log`

---

**Last Updated:** 2025-10-18
**Status:** ✅ Working - Both servers running successfully
