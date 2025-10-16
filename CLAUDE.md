# Big Dipper - Development Guide

**Forked from Little Dipper v2.15 to add operational visibility**

## Project Philosophy

**Core Principle:** Smart risk management with operational transparency. Same proven dip-buying logic, but you can SEE what you're missing.

```
~1,140 lines of Python (forked from Little Dipper's 965)
Simple > Complex | Stateless > Stateful | Direct > Abstracted | Smart > Naive
Visible > Silent | Informed > Blind
3-pass prioritization: SCAN → PRIORITIZE → EXECUTE (best opportunities funded first)
```

## Architecture (4 Files)

```
config.py (~99 lines)
  ↓ Constants & env vars - see file for current symbol list
dip_logic.py (~199 lines)
  ↓ Pure functions with risk filters (no side effects)
utils.py (~200 lines) ← NEW in v2.16
  ↓ Data fetching, formatting, visibility logging
main.py (~642 lines)
  ↓ Event loop + Alpaca SDK + options-aware processing
```

**No database. No caching. No abstraction layers.**
Alpaca API is the single source of truth.
**Smart filters reduce false signals by ~30-40%.**
**Enhanced visibility shows missed opportunities during trading halts.**

## Development Rules

  Do not make assumptoins.  You must ask questions if you are not certain of your actions.  If you identify a problem, you must suggest a specific fix with proposed code changes.  You should reference Alpaca SDK https://docs.alpaca.markets/docs/sdks-and-tools. and the latest github repos https://github.com/alpacahq/alpaca-py. For every function or code added, you should confirm:  1). it properly integrates with the overall code base.  2)  it is added in the most simple and fault tolerant way.  3). what code it will deprecate and how to remove the deprecated code without harming data flow and function 4) how you will update existing documentation to make it clear to future developers what you did and why. 

### 🚫 **NEVER Add These:**
- ❌ Database (SQLite, PostgreSQL, etc.)
- ❌ Caching layer (Redis, Memcached, etc.)
- ❌ Abstraction/gateway patterns
- ❌ Complex state management
- ❌ ORM or query builders
- ❌ Message queues
- ❌ WebSocket streaming (60s polling is sufficient)
- ❌ GUI/dashboard (use Alpaca dashboard)
- ❌ Discord/Slack notifications (logs are enough)
- ❌ Multiple config files or hot-reload
- ❌ Stop losses (conflicts with buy-hold strategy)
- ❌ Exit signals (let winners run)
- ❌ Market regime detection (overcomplicates sizing)

### ✅ **Always Maintain:**
- ✅ **Pure functions** in `dip_logic.py` (easy to test, no side effects)
- ✅ **Direct SDK usage** (no wrappers or adapters)
- ✅ **Stateless operation** (crash = restart, state from Alpaca)
- ✅ **Simple constants** in `config.py` (no complex validation)
- ✅ **4-file architecture** (config, dip_logic, utils, main - no more!)
- ✅ **Fail-fast errors** (crash loudly, let Docker restart)
- ✅ **Minimal dependencies** (currently: alpaca-py, python-dotenv, pytz)

### 📏 **Code Quality Rules:**

1. **Keep functions under 50 lines** - If longer, split into smaller functions
2. **No classes unless necessary** - Prefer functions over objects
3. **Type hints required** - All function signatures must have types
4. **Max 3 levels of indentation** - Nested code is hard to read
5. **One concept per function** - Calculate OR validate, not both
6. **Test pure functions** - Every function in `dip_logic.py` needs a test
7. **Log decisions, not data** - Log "why", not "what"

### 🔧 **Making Changes:**

**All configuration changes happen in config.py - NOT in docs.**

Examples:

**Adjusting allocation for manual trading:**
```python
# config.py
MAX_TOTAL_INVESTED_PCT = 0.45  # Default: 45% (leaves 55% for manual)
```

**Adding/removing symbols:**
```python
# config.py - Edit the SYMBOLS list directly
```

**Adjusting position sizing:**
```python
# config.py
BASE_POSITION_PCT = 0.025     # Default: 2.5%
DIP_MULTIPLIER = 1.75         # Default: 1.75x
MAX_POSITION_PCT = 0.15       # Default: 15%
MIN_ABSOLUTE_DIP = 0.05       # Default: 5% (floor for all stocks)
DIP_THRESHOLDS = {...}        # Stock-specific entry points (3-8%)
```

**Adjusting margin settings:**
```python
# config.py
USE_MARGIN = True          # Default: enabled
MAX_MARGIN_PCT = 0.20      # Default: 20%
COLLATERAL_POSITIONS = ['BLV', 'SGOV', 'BIL']  # Default bonds
```

**Using bonds as reserves (v2.10 feature):**
```python
# config.py
MAX_TOTAL_INVESTED_PCT = 0.45  # 45% cap applies only to stocks
COLLATERAL_POSITIONS = ['BLV', 'SGOV', 'BIL']  # Excluded from cap

# How it works:
# - Bonds NOT counted toward 45% allocation limit
# - Shift to bonds = defensive positioning, but Little Dipper keeps full capacity
# - Manual stock trades outside symbol list ARE counted in 45% cap
# - Allows automated dip buying while maintaining bond reserves for manual trading
```

**Enhanced Risk Filters (v2.0+):**

See `dip_logic.py` for implementation details:
- Crash filter: Skip if down >15% from high
- Volume confirmation: Need 80%+ of average volume
- Relative strength: Skip if 5d momentum < -10%
- Volatility adjustment: Reduce size for high-vol stocks
- Dynamic cooldown: Halve cooldown for deep dips (>7%)

**DON'T do this:**
```python
# ❌ BAD: Adding a cache
class VolumeCache:
    def __init__(self):
        self.cache = {}

    def get_volume(self, symbol):
        if symbol not in self.cache:
            self.cache[symbol] = self._fetch_volume(symbol)
        return self.cache[symbol]

# ❌ BAD: Adding state management
class StateManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)

    def save_state(self, key, value):
        self.db.execute("INSERT INTO state...")
```

**DO this:**
```python
# ✅ GOOD: Direct and simple
def get_volume(symbol: str, data_client) -> int:
    """Get current volume directly from Alpaca"""
    bars = data_client.get_stock_bars(symbol, limit=1)
    return bars[-1].volume
```

### 🐛 **Debugging:**

System crashed? Good! That means:
1. Error was caught immediately
2. Docker/systemd will restart it
3. State reconstructs from Alpaca API
4. Trading resumes with exponential backoff (10s → 20s → 40s → 60s max)

**Log Levels:**
- **INFO** (default): Shows trades, emergency brake, major events
- **DEBUG**: Verbose - shows every symbol check, rejection reasons, dip calculations

Set `LOG_LEVEL=DEBUG` in .env to see:
- Each symbol's dip percentage vs 20-day high
- Why symbols qualify or don't qualify
- Largest dip detected in each cycle
- Example: `NVDA: -2.1% from 20d high (need -5.0%)`
- Example: `AMD: -6.5% from 20d high ✓ dip detected`

**Understanding What You're NOT Seeing:**

**During Emergency Brake (margin >15%):**
- System halts ALL trading
- Does NOT show which dips are occurring
- **Blind spot:** NVDA could be -10% and you'd never know
- **Workaround:** Check manually or wait for proposed enhancement

**Silent Rejections:**
- Cooldowns (3 hours) - only visible in DEBUG
- Position limits - only logged when exceeded
- Capital exhaustion - not currently logged (proposed enhancement)

**Debug workflow:**
```bash
# 1. Check logs
docker logs little-dipper | tail -50

# 2. See actual trades (INFO level)
docker logs little-dipper | grep "BUY"

# 3. Check for network issues
docker logs little-dipper | grep ERROR

# 4. Reproduce locally
source venv/bin/activate
python main.py

# 5. Test
python test_dip_logic.py

# 6. Restart
docker-compose restart
```

### 📦 **Dependencies:**

**Current (3 packages):**
- `alpaca-py` - Official Alpaca SDK
- `python-dotenv` - Load .env files
- `pytz` - Timezone handling

**Before adding a new dependency, ask:**
1. Can I write this function myself in < 20 lines?
2. Will this dependency add more than 1 MB?
3. Does it require configuration or setup?

If yes to any: **Don't add it.**

### 🔄 **Git Workflow:**

```bash
# Make changes
edit config.py

# Test
python test_dip_logic.py

# Commit
git add .
git commit -m "Adjust position sizing to 3%"
git push
```

**Keep commits atomic** - One logical change per commit.

### 🚀 **Deployment:**

```bash
# Local development
python main.py

# Production (Docker)
docker-compose up -d

# Check status
docker logs -f little-dipper

# Stop
docker-compose down
```

**That's it.** No Kubernetes, no CI/CD pipelines, no infrastructure complexity.

## Trading Logic Reference

See `dip_logic.py` for actual implementation. Key formulas:

### Dip Detection

**Price Source:** Uses **BID price** (more conservative than ASK)
```python
current_price = quote.bid_price  # Conservative: bid < ask
dip_pct = (current_price - lookback_high) / lookback_high
```

**Qualification Requirements - Must meet BOTH:**
1. **MIN_ABSOLUTE_DIP** (5% floor) - Prevents threshold gaming
2. **Stock-specific threshold** (3-8% based on volatility)

**Effective Thresholds:**
```python
effective_threshold = max(MIN_ABSOLUTE_DIP, DIP_THRESHOLDS[symbol])

# Examples:
# MSFT: max(5%, 3%) = 5% (absolute floor overrides)
# DEFAULT: max(5%, 4%) = 5% (absolute floor overrides)
# NVDA: max(5%, 5%) = 5% (matches)
# PLTR: max(5%, 6%) = 6% (stock threshold higher)
# IBIT: max(5%, 8%) = 8% (stock threshold higher)
```

**Why BID price?** More conservative buy decision - BID is lower than ASK, so dip appears larger. This triggers buys at better prices.

### Position Sizing
```python
size_multiplier = (abs(dip_pct) / 0.03) * dip_multiplier / volatility_factor
target_value = equity * base_position_pct * size_multiplier
# Capped at MAX_POSITION_PCT
```

### Risk Limits
- Max 15% per symbol (15% of equity)
- 5% absolute minimum dip (prevents threshold gaming)
- 3-hour cooldown between buys per symbol
- Limit orders only (adaptive pricing: bid+0.1% extended hours, ask-0.5% regular hours)
- Margin capped at 20% of equity

**See config.py for all current values - don't hardcode in docs!**

### Margin Trading
```python
USE_MARGIN = True                    # Enable margin (default)
MAX_MARGIN_PCT = 0.20                # Hard 20% limit per trade
MARGIN_SAFETY_THRESHOLD = 0.15       # Emergency brake (v2.13)
COLLATERAL_POSITIONS = ['BLV', 'SGOV', 'BIL']  # Bonds excluded

# TWO-LEVEL PROTECTION (v2.13):
# 1. EMERGENCY BRAKE (cycle start):
starting_margin = margin_debt / equity
if starting_margin > 0.15:  # Halt ALL trading if already leveraged
    skip_entire_cycle()

# 2. PER-TRADE LIMIT (each order):
projected_margin = (margin_debt + order_value) / equity
if projected_margin > 0.20:  # Block individual trades
    skip_trade()
```

**Key features (v2.13):**
- **Emergency brake at 15%** - Prevents adding margin on top of margin
- **Hard 20% limit per trade** - Enforced on every individual order
- **Dual protection** - Checks both cycle start AND each trade
- Uses Alpaca's `regt_buying_power` (Regulation T overnight margin)
- Collateral positions never traded
- Set `USE_MARGIN = False` for cash-only mode

## Extended Hours Trading

**Enabled by default:**
- Pre-market: 4:00 AM - 9:30 AM ET
- Regular: 9:30 AM - 4:00 PM ET
- After-hours: 4:00 PM - 8:00 PM ET

**All 43 symbols trade during extended hours (simplified in v2.12)**

## File Size Limits

| File | Current | Max Allowed | Notes |
|------|---------|-------------|-------|
| config.py | 99 lines | 100 lines | Configuration constants |
| dip_logic.py | 199 lines | 250 lines | Pure trading logic functions |
| utils.py | 200 lines | 250 lines | Helpers & visibility (v2.16) |
| main.py | 642 lines | 700 lines | Event loop & orchestration |
| **Total** | **1,140 lines** | **1,300 lines** | Hard stop - this is the FINAL feature |

**If you hit these limits:** This is Big Dipper's ceiling. Do NOT add more features.

## Testing

```bash
# Run tests
python test_dip_logic.py

# All tests must pass before committing
# No mocking - pure functions don't need it
```

## Options & Manual Trading Coexistence (v2.9)

**You can trade options AND equity outside the 23-symbol list in the same account!**

### How It Works

**Position Tracking (Updated v2.10):**
- ✅ Tracks ALL equity positions (algo + your manual trades)
- ✅ Manual stock trades counted in 45% allocation cap
- ✅ **Bond positions (BLV/SGOV/BIL) excluded from 45% cap** (reserves)
- ✅ Won't add to positions you manually opened
- ✅ Filters options positions from equity tracking
- ✅ Uses `maintenance_margin` for accurate margin calculation

**Safety System (v2.9 CRITICAL FIX):**
When the Alpaca SDK fails to read positions (usually due to options):
1. 🛑 **HALTS all trading** for that cycle (no blind trades!)
2. 🚨 **Logs clear ERROR messages** (visible in logs)
3. ♻️ **Auto-retries every 60 seconds**
4. ✅ **Resumes automatically** when positions load successfully

**Previous Bug (v2.7-v2.8):**
- SDK failed → fell back to empty position map → over-bought
- **FIXED in v2.9** - now halts instead of trading blind

**Example Logs:**

*Normal operation with options:*
```
ℹ️  Detected 1 options position(s) - excluded from Little Dipper
📊 Positions: 5 stocks, $7,626 invested (48.11%)
💎 NVDA QUALIFIES: Dip -4.2% @ $145.32
```

*SDK failure (safe halt):*
```
❌ POSITION TRACKING FAILED (likely due to options positions)
   SDK error: [validation error details]
⏸️  HALTING ALL TRADING this cycle to prevent over-allocation
   System will automatically resume when positions load successfully
   Next retry in 60 seconds...
```

**Best Practices:**
- ✅ **Safe to run continuously** - even with active options trading
- ✅ Manual equity trades (AAPL, GOOGL, etc.) counted in allocation
- ✅ System auto-recovers when you close options positions
- ⚠️ Expect trading pauses when options positions exist (~3-7 days/month typical)
- ⚠️ Monitor logs for position tracking errors

**Technical Implementation:**
```python
# main.py:166-215 - Defensive position tracking
try:
    all_positions = self.trading.get_all_positions()
except Exception as validation_error:
    # SDK fails with options → HALT (don't trade blind!)
    log.error("❌ POSITION TRACKING FAILED")
    log.error("⏸️  HALTING ALL TRADING this cycle")
    time.sleep(60)
    continue  # Skip cycle, retry next

# Filter to equity only
equity_positions = [p for p in all_positions
                    if p.asset_class == 'us_equity']

# Include ALL equity (algo + manual trades) in limits
position_map = {p.symbol: float(p.market_value) for p in positions}
total_invested = sum(position_map.values())  # Includes your AAPL, etc.

if total_invested >= equity * 0.45:  # 45% cap
    log.info("⛔ Little Dipper at max allocation")
```

## When to Reject a Feature Request

**Reject if the request:**
- Adds a 4th file
- Requires a database
- Needs more than 50 lines
- Can't be explained in 2 sentences
- Adds complexity without clear benefit
- Duplicates what Alpaca already provides

## Success Metrics

**Code quality:**
- Total lines < 1000 ✅ (~920 lines)
- Files ≤ 3 ✅
- Dependencies ≤ 5 ✅ (3 packages)
- Startup time < 2 seconds ✅

**Trading quality:**
- System uptime > 99% ✅
- Average cycle time < 6 seconds ✅
- Crashes per day < 1 ✅
- False signals reduced by ~30-40% ✅
- Expected drawdown reduction ~20-30% ✅
- Network resilience with exponential backoff ✅
- Clean debug logging (v2.4) ✅

## Remember

**"Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."**

If you're about to add complexity, ask yourself:
1. Can the existing system already do this?
2. Can Alpaca's API already provide this?
3. Is this actually needed, or just nice-to-have?

**When in doubt, do nothing.** The system works because it's simple.

---

## Quick Reference

```bash
# Run locally
python main.py

# Run tests
python test_dip_logic.py

# Deploy
docker-compose up -d

# Monitor
docker logs -f little-dipper

# Stop
docker-compose down
```

**That's all you need to know.** 🌙