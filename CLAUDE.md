# Big Dipper - Development Guide

**v2.16: Automated dip-buying with operational visibility**

## Core Philosophy

**Smart risk management with transparency.** Buy quality stocks when they dip, with visibility into what you're missing during trading halts.

```
~1,275 lines of Python across 4 files
Simple > Complex | Stateless > Stateful | Visible > Silent
Direct SDK usage | Pure functions | No database | Fail-fast errors
```

## Architecture

```
config.py (105 lines)
  ↓ Constants, thresholds, symbol list

dip_logic.py (194 lines)
  ↓ Pure trading logic functions (no side effects)

utils.py (320 lines)
  ↓ Data fetching, formatting, visibility helpers

main.py (656 lines)
  ↓ Event loop, Alpaca SDK, orchestration
```

**Single source of truth:** Alpaca API (no database, no cache, no state)

## Development Rules

**Before making changes, ask:**
1. Does it integrate cleanly with existing code?
2. Is it the simplest fault-tolerant approach?
3. What code becomes deprecated?
4. How will documentation be updated?

**Reference:** [Alpaca SDK](https://docs.alpaca.markets/docs/sdks-and-tools) | [GitHub](https://github.com/alpacahq/alpaca-py)

### 🚫 Never Add

- ❌ Database/caching layer
- ❌ Abstraction patterns or wrappers
- ❌ Complex state management
- ❌ WebSocket streaming (60s polling sufficient)
- ❌ GUI/dashboard (use Alpaca UI)
- ❌ Notifications (logs are enough)
- ❌ Stop losses or exit signals
- ❌ Market regime detection

### ✅ Always Maintain

- ✅ Pure functions in `dip_logic.py`
- ✅ Direct SDK usage (no adapters)
- ✅ Stateless operation (crash = restart from Alpaca state)
- ✅ 4-file architecture (NO 5th file)
- ✅ Fail-fast errors
- ✅ 3 dependencies only (alpaca-py, python-dotenv, pytz)

### 📏 Code Quality

1. **Functions < 50 lines** - Split if longer
2. **Prefer functions over classes**
3. **Type hints required**
4. **Max 3 indentation levels**
5. **One concept per function**
6. **Test all pure functions**
7. **Log decisions, not data**

## Configuration

**All settings in [config.py](config.py) - NOT in docs.**

### Key Settings

```python
# Position Sizing
BASE_POSITION_PCT = 0.025     # 2.5% base allocation
DIP_MULTIPLIER = 1.75         # Scale with dip severity
MAX_POSITION_PCT = 0.15       # 15% max per symbol
MIN_ABSOLUTE_DIP = 0.05       # 5% floor (prevents gaming)

# Dip Thresholds (stock-specific, 3-8%)
DIP_THRESHOLDS = {
    'DEFAULT': 0.04,          # 4% → effective 5% (floor override)
    'MSFT': 0.03,             # Low volatility
    'NVDA': 0.05,             # Medium volatility
    'PLTR': 0.06,             # Higher volatility
    'IBIT': 0.08,             # Highest volatility
    # ... see config.py for full list
}

# Margin Protection
USE_MARGIN = True             # Enable margin trading
MARGIN_SAFETY_THRESHOLD = 0.15  # Emergency brake (halt trading)
MAX_MARGIN_PCT = 0.20         # Hard limit per trade

# Trading Controls
COOLDOWN_HOURS = 3            # Between buys per symbol
LOOKBACK_DAYS = 20            # For dip detection
SCAN_INTERVAL_SEC = 60        # Cycle frequency
```

### Symbols Traded

44 stocks across sectors (edit SYMBOLS list in [config.py](config.py)):
- **Tech/AI:** NVDA, AVGO, AMD, TSM, MRVL, TER, MSFT, META, ORCL, NOW, PLTR, ANET, DELL
- **Power/Utilities:** ETN, PWR, CEG, GEV, NEE, ABB, XYL, AWK, WTRG
- **Data Centers:** EQIX, DLR, AMT, CCI
- **Defense:** LMT, NOC, RTX, GD, HII, HWM, AVAV, KTOS
- **Healthcare:** ISRG, LLY, FIGR
- **Materials:** VMC, MLM, MP
- **Alternative Assets:** GLD, URNM, IBIT, ARKK

## Trading Logic

### How It Works (Every 60 Seconds)

1. **Check Market Status** - Regular or extended hours (4 AM - 8 PM ET)
2. **Get Account State** - Equity, cash, margin, positions from Alpaca
3. **Emergency Brake Check** - Halt if margin >15%
4. **Scan All Symbols:**
   - Fetch 25-day price history
   - Calculate dip from 20-day high using BID price
   - Apply 5 risk filters (see below)
   - Calculate opportunity score
5. **Prioritize & Execute** - Best opportunities first (largest dip ratio)

### Dip Detection

**Price Source:** Uses **BID price** (conservative - lower than ASK)

```python
current_price = quote.bid_price
dip_pct = (current_price - lookback_high) / lookback_high

# Qualification: Must meet BOTH
effective_threshold = max(MIN_ABSOLUTE_DIP, DIP_THRESHOLDS[symbol])
# Examples:
#   MSFT: max(5%, 3%) = 5% (floor overrides)
#   NVDA: max(5%, 5%) = 5% (matches)
#   PLTR: max(5%, 6%) = 6% (stock threshold wins)
#   IBIT: max(5%, 8%) = 8% (stock threshold wins)
```

### 5 Smart Risk Filters

1. **Crash Filter:** Skip if down >15% from 20-day high (avoid prolonged crashes)
2. **Volume Confirmation:** Require 80%+ of 20-day average volume
3. **Relative Strength:** Skip if 5-day momentum < -10%
4. **Volatility Adjustment:** Reduce position size for high-volatility stocks
5. **Dynamic Cooldown:** Halve cooldown time for deep dips >7%

**Result:** ~30-40% fewer false signals, ~20-30% lower drawdowns

### Position Sizing

```python
# Scale with dip severity, adjust for volatility and intraday drops
size_multiplier = (abs(dip_pct) / 0.03) * dip_multiplier / volatility_factor
intraday_multiplier = 1.5 if (symbol in VOLATILE_TICKERS and intraday_drop >= 6%) else 1.0
target_value = equity * base_position_pct * size_multiplier * intraday_multiplier

# Cap at max position size
target_value = min(target_value, equity * MAX_POSITION_PCT)
```

**Intraday Boost** (v2.17): For volatile tickers (IBIT, ARKK, KTOS, FIGR, URNM, MP) with 6%+ intraday drop, buy 1.5x normal size to capitalize on sharp selloffs that often bounce.

### Margin Protection (Dual Layer)

**Layer 1 - Emergency Brake (Cycle Start):**
```python
if margin_debt / equity > 0.15:
    halt_all_trading()  # Prevents adding margin on margin
    log_missed_opportunities()  # v2.16 enhancement
```

**Layer 2 - Per-Trade Limit:**
```python
projected_margin = (margin_debt + order_value) / equity
if projected_margin > 0.20:
    skip_trade()
```

### Order Execution

- **Limit orders only** (no market orders)
- **Adaptive pricing:**
  - Extended hours: bid + 0.1%
  - Regular hours: ask - 0.5%
- **Timeout:** 15 minutes (cancels if not filled)

## File Size Limits (HARD STOP)

| File | Current | Max | Notes |
|------|---------|-----|-------|
| config.py | 105 | 100 | ⚠️ At limit |
| dip_logic.py | 194 | 250 | 56 lines available |
| utils.py | 320 | 250 | ⚠️ Over by 70 (refactor if adding) |
| main.py | 656 | 700 | 44 lines available |
| **Total** | **1,275** | **1,300** | **25 lines to ceiling** |

**At 1,300 lines:** Big Dipper is feature-complete. No more additions.

## Logging & Visibility

**Log Levels:**
- **INFO:** Trades, emergency brake, major events
- **DEBUG:** Every symbol check, rejection reasons, dip calculations

**Set in .env:**
```bash
LOG_LEVEL=DEBUG  # Verbose
LOG_LEVEL=INFO   # Default
```

**v2.16 Enhancements:**
- Shows missed opportunities during emergency brake
- Logs capital exhaustion with suggestions
- Reports largest dips even when not trading

**Debug Example:**
```
NVDA: -2.1% from 20d high (need -5.0%) ❌
AMD: -6.5% from 20d high ✓ qualifies
  → Volume: 850K / 1M avg (85%) ✓
  → 5d momentum: -3.2% (> -10%) ✓
  → Crash filter: -6.5% (< -15%) ✓
  → Target: $2,625 (2.5% × 2.17x) ✓
```

## Options & Manual Trading

**Fully compatible** - Trade options and other equities in the same account.

**How It Works:**
- Tracks ALL equity positions (algo + manual)
- Filters out options positions (no interference)
- Manual stock trades counted in allocation limits
- Bond positions (BLV/SGOV/BIL) excluded from limits

**Safety:** If SDK fails reading positions (due to options), system HALTS trading until resolved. No blind trades.

## Testing

```bash
# Run all tests (must pass before committing)
python test_dip_logic.py

# Expected output
============================================================
✅ All tests passed!
============================================================
```

**No mocking** - Pure functions don't need it.

## Deployment

### Local Development
```bash
source venv/bin/activate
python main.py
```

### Background Mode
```bash
./start_big_dipper.sh
# or
nohup python main.py > big_dipper.log 2>&1 &
```

### Docker (Production)
```bash
docker-compose up -d
docker logs -f big-dipper
docker-compose down
```

### Monitoring
```bash
# Check if running
pgrep -fl "main.py"

# View logs
tail -f big_dipper.log

# Check positions
python check_positions.py
```

## Debugging Workflow

```bash
# 1. Check recent logs
tail -50 big_dipper.log

# 2. See trades only
grep "BUY" big_dipper.log

# 3. Check for errors
grep "ERROR" big_dipper.log

# 4. Verify system health
python test_dip_logic.py

# 5. Restart if needed
pkill -f "main.py" && ./start_big_dipper.sh
```

**Crashes are OK** - System is designed to fail-fast and restart with fresh state from Alpaca.

## When to Reject Feature Requests

❌ Reject if it:
- Adds a 5th file
- Requires database/cache
- Needs >50 lines
- Can't be explained in 2 sentences
- Adds complexity without clear benefit
- Duplicates Alpaca functionality
- Pushes past file size limits

## Git Workflow

```bash
# Make changes
edit config.py

# Test
python test_dip_logic.py

# Commit
git add .
git commit -m "Adjust NVDA threshold to 6%"
git push
```

**Keep commits atomic** - One logical change per commit.

## Quick Reference

```bash
# Start
./start_big_dipper.sh

# Test
python test_dip_logic.py

# Monitor
tail -f big_dipper.log

# Status
python check_positions.py

# Stop
pkill -f "main.py"
```

## Success Metrics

**Code:**
- ✅ 1,275 lines across 4 files
- ✅ 3 dependencies
- ✅ Startup < 2 seconds

**Trading:**
- ✅ Uptime >99%
- ✅ Cycle time <6 seconds
- ✅ False signals reduced ~30-40%
- ✅ Expected drawdown reduction ~20-30%

## Remember

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."

**When in doubt, do nothing.** Simplicity is the feature.

---

**That's everything you need.** 🌟
