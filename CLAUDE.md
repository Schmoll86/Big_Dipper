# Big Dipper - Development Guide

**Version:** v2.17+
**Purpose:** Buy-the-dip automation with operational visibility

## Core Philosophy

**Smart risk management with transparency.** Buy quality stocks when they dip, with visibility into what you're missing during trading halts.

```
~1,300 lines of Python across 4 files
Simple > Complex | Stateless > Stateful | Visible > Silent
Direct SDK usage | Pure functions | No database | Fail-fast errors
```

## Architecture

```
config.py       → Constants, thresholds, symbol list
dip_logic.py    → Pure trading logic functions (no side effects)
utils.py        → Data fetching, formatting, visibility helpers
main.py         → Event loop, Alpaca SDK, orchestration
```

**Single source of truth:** Alpaca API (no database, no cache, no state)

---

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
- ❌ GUI/dashboard (use web monitor or Alpaca UI)
- ❌ Notifications (logs are enough, web monitor handles this)
- ❌ Stop losses or exit signals (user manages manually)
- ❌ Market regime detection (keep it simple)

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

---

## Configuration

**All settings in [config.py](config.py) - NOT in docs.**

Configuration is **manually editable** - see config.py for current values.

### Key Concepts

**Position Sizing Strategy:**
- Base allocation percentage (applied to all trades)
- Max allocation percentage (hard cap per symbol)
- Dip multiplier (scales with severity)
- Absolute minimum dip floor (prevents threshold gaming)

**Dip Detection:**
- Stock-specific thresholds (based on historical volatility)
- DEFAULT threshold (fallback for symbols without custom threshold)
- Lookback period in days
- Effective threshold = `max(MIN_ABSOLUTE_DIP, stock_threshold)`

**Margin Protection (Dual Layer):**
- Safety threshold (emergency brake - halts all trading)
- Hard limit per trade (blocks individual orders)
- Collateral positions excluded from trading logic

**Trading Controls:**
- Cooldown between buys per symbol (hours)
- Order timeout (minutes before cancellation)
- Limit price offset (from ask/bid)

**Intraday Volatility Boost:**
- List of volatile tickers (eligible for boost)
- Intraday drop threshold (triggers multiplier)
- Intraday multiplier (size boost on sharp drops)

**Extended Hours:**
- Enable/disable extended hours trading
- Scan interval (seconds between cycles)

---

## Trading Logic

### Dip Detection Strategy

**Price Source:** Uses BID price (conservative - lower than ASK)

**Calculation:**
```
dip_pct = (current_price - lookback_high) / lookback_high
```

**Qualification Criteria:**
Must meet BOTH:
1. Stock-specific threshold (per DIP_THRESHOLDS config)
2. Absolute minimum threshold (floor to prevent gaming)

**Example Logic:**
```
effective_threshold = max(MIN_ABSOLUTE_DIP, DIP_THRESHOLDS[symbol])
```

This ensures a stock with 3% configured threshold still needs 5% dip if MIN_ABSOLUTE_DIP is 5%.

### 5 Smart Risk Filters

**Why these filters:** Reduce false signals ~30-40%, lower drawdowns ~20-30%

1. **Crash Filter** - Skip if down >15% from lookback high (avoid prolonged crashes)
2. **Volume Confirmation** - Require 80%+ of average volume (avoid low-liquidity dips)
3. **Relative Strength** - Skip if 5-day momentum < -10% (avoid weak stocks)
4. **Volatility Adjustment** - Reduce position size for high-volatility stocks
5. **Dynamic Cooldown** - Halve cooldown time for deep dips >7% (capitalize on extreme selloffs)

### Position Sizing Formula

**Base calculation:**
```
size_multiplier = (abs(dip_pct) / reference_dip) * dip_multiplier / volatility_factor
```

**Intraday boost (if applicable):**
```
final_multiplier = size_multiplier * intraday_multiplier
```

**Target value:**
```
target_value = equity * base_position_pct * final_multiplier
target_value = min(target_value, equity * max_position_pct)  # Cap
```

**Rationale:** Larger dips get larger positions, but capped to prevent over-concentration. Volatility reduces size for unpredictable stocks.

### Margin Protection (Dual Layer)

**Layer 1 - Emergency Brake (Cycle Start):**
```
if margin_debt / equity > safety_threshold:
    halt_all_trading()
    log_missed_opportunities()
```
**Prevents:** Adding margin on margin (compounding risk)

**Layer 2 - Per-Trade Limit:**
```
projected_margin = (margin_debt + order_value) / equity
if projected_margin > hard_limit:
    skip_trade()
```
**Prevents:** Individual trades from pushing margin too high

### Order Execution Strategy

**Order Type:** Limit orders only (no market orders)

**Adaptive Pricing:**
- Extended hours: `bid + offset_pct` (slightly above bid to improve fill rate)
- Regular hours: `ask - offset_pct` (slightly below ask for better price)

**Rationale:** Limit orders protect against volatility spikes, adaptive pricing balances fill rate vs price.

**Timeout:** Orders cancel after timeout minutes if unfilled (prevents stale orders)

---

## File Size Philosophy

**Hard limit:** 1,300 lines total across 4 files

**Current state:** Check README.md for latest counts

**Rationale:** Enforces simplicity. If adding feature pushes over limit, must refactor or reject feature.

**Individual limits serve as guidelines:**
- config.py: ~100 lines (just constants)
- dip_logic.py: ~250 lines (pure functions)
- utils.py: ~250 lines (helpers)
- main.py: ~700 lines (orchestration)

**At 1,300 lines:** Big Dipper is feature-complete. Focus on optimization, not new features.

---

## Logging Strategy

**Philosophy:** Log decisions and state transitions, not raw data.

**Log Levels:**
- **INFO** - Trades, emergency brake, major events, account state
- **DEBUG** - Every symbol check, rejection reasons, dip calculations

**Structured Tags (for web monitor parsing):**
- `[TRADE]` - Successful buy orders
- `[SKIP]` - Rejected opportunities with reason
- `[OPPORTUNITY]` - Qualified dips (scored)
- `[ACCOUNT]` - Account state snapshot (equity, cash, margin, P/L)
- `[BRAKE]` - Emergency brake events

**Set in .env:**
```bash
LOG_LEVEL=DEBUG  # Verbose (every symbol)
LOG_LEVEL=INFO   # Default (trades and events)
```

**Visibility Enhancements (v2.16+):**
- Emergency brake shows missed opportunities
- Capital exhaustion logging
- Position P/L from Alpaca (accurate, no calculations)
- Wash sale conflict detection

---

## Options & Manual Trading

**Fully compatible** - Trade options and other equities in same account.

**How It Works:**
- Tracks ALL equity positions (algo + manual)
- Filters out options positions (no interference)
- Manual stock trades counted in allocation limits
- Bond/stable positions (from COLLATERAL_POSITIONS config) excluded from trading

**Safety:** If SDK fails reading positions (e.g., due to options complexity), system HALTS trading until resolved. No blind trades.

---

## Error Handling Philosophy

**Fail-Fast Approach:**
- Catch errors early and loudly
- Log error details
- Halt trading for safety
- Auto-retry on next cycle

**Examples:**
- **Wash sale conflict** - Log `[SKIP]` with reason, continue to next symbol
- **Non-fractionable asset** - Log `[SKIP]`, continue
- **Position read failure** - HALT entire cycle, retry next cycle
- **Negative equity** - HALT all trading until resolved

**Rationale:** Better to miss an opportunity than to trade incorrectly.

---

## Testing

```bash
# Run all tests (must pass before committing)
python test_dip_logic.py

# Expected: All tests passing
```

**No mocking** - Pure functions don't need it. Functions take inputs, return outputs, zero side effects.

**What's tested:**
- Dip calculation accuracy
- Buy decision logic
- Position sizing math
- Margin calculations
- Opportunity scoring
- Emergency brake activation

**What's NOT tested:**
- Alpaca API calls (external dependency)
- WebSocket connections (not used)
- File I/O (minimal, hard to break)

---

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
See [DEPLOYMENT.md](DEPLOYMENT.md) for Docker specifics.

### Monitoring
```bash
# Check if running
pgrep -fl "main.py"

# View logs
tail -f big_dipper.log

# Check positions
python check_positions.py
```

---

## Data Flow

**Every 60-second cycle:**

1. **Query Alpaca:**
   - Get account state (equity, cash, margin)
   - Get all positions (for allocation tracking)
   - Check market clock (open/closed/extended)

2. **Emergency Checks:**
   - Is equity > 0? (sanity check)
   - Is margin ratio < safety threshold? (emergency brake)

3. **Scan Symbols:**
   - For each symbol in SYMBOLS list:
     - Fetch historical bars (lookback period)
     - Get current quote (bid/ask)
     - Calculate dip from high
     - Calculate intraday drop (if volatile ticker)
     - Apply 5 risk filters
     - Score opportunity if qualifies

4. **Prioritize & Execute:**
   - Sort opportunities by score (best first)
   - For each opportunity:
     - Calculate position size
     - Check margin limit (layer 2)
     - Place limit order
     - Track order for timeout

5. **Order Management:**
   - Check pending orders
   - Cancel orders past timeout
   - Log fills/cancellations

**Stateless:** Every cycle rebuilds state from Alpaca. Crash = restart, no corruption.

---

## Known Shortcomings

**By Design (Will Not Fix):**
1. **No exit signals** - User manages sells manually (keeps code simple)
2. **No market regime detection** - Buys in bull and bear (simplicity > sophistication)
3. **No portfolio rebalancing** - Position sizing handles this naturally over time
4. **No stop losses** - User responsibility (but causes wash sale issues if auto-buys)

**Limitations:**
1. **60-second cycle** - Can miss very brief dips (acceptable tradeoff for simplicity)
2. **Wash sale conflicts** - Manual stop losses trigger wash sale protection (feature, not bug)
3. **Extended hours liquidity** - Some symbols have poor extended hours liquidity (order timeout mitigates)

**Potential Improvements (If Under Line Limit):**
1. Sector allocation limits (prevent over-concentration)
2. Dynamic position sizing based on recent win rate
3. Configurable risk filters (enable/disable per filter)

---

## When to Reject Feature Requests

❌ Reject if it:
- Adds a 5th file
- Requires database/cache
- Needs >50 lines for single feature
- Can't be explained in 2 sentences
- Adds complexity without clear 10%+ benefit
- Duplicates Alpaca functionality
- Pushes past 1,300 line limit

✅ Consider if it:
- Reduces risk
- Improves visibility
- Simplifies existing code (net negative lines)
- Fixes actual production issue

---

## Git Workflow

```bash
# Make changes
edit config.py

# Test
python test_dip_logic.py

# Commit (atomic changes only)
git add config.py
git commit -m "Adjust volatility factor calculation"
git push
```

**Commit Guidelines:**
- One logical change per commit
- Descriptive message (what & why)
- Never commit `.env` file
- Tag releases: `git tag v2.X -m "Description"`

---

## Manual Configuration Workflow

**Big Dipper is designed for manual config editing.**

**To modify trading parameters:**

1. **Stop Big Dipper** - `pkill -f "main.py"` or `docker-compose down`
2. **Edit config.py** - Modify SYMBOLS, DIP_THRESHOLDS, position sizing, etc.
3. **Validate syntax** - `python -m py_compile config.py`
4. **Restart** - `./start_big_dipper.sh` or `docker-compose up -d`
5. **Verify** - Check startup logs show expected values

**No UI needed** - config.py is the UI. Clear, version-controlled, no abstraction.

---

## Engineering Decisions

### Why SQLite is NOT used for trading state?
**Decision:** Alpaca API is single source of truth
**Rationale:** Eliminates sync bugs, no schema migrations, crash = restart from truth

### Why 60-second polling instead of WebSocket?
**Decision:** Simple polling loop
**Rationale:** WebSocket adds complexity (reconnect logic, buffering). 60s is fast enough for dip-buying strategy.

### Why limit orders instead of market orders?
**Decision:** All orders are limit orders
**Rationale:** Protects against volatility spikes, acceptable fill-rate tradeoff

### Why fail-fast instead of retry loops?
**Decision:** Error = halt cycle, retry next cycle
**Rationale:** Prevents cascading failures, logs make issues visible

### Why pure functions in dip_logic.py?
**Decision:** No side effects, no mutable state
**Rationale:** Testable without mocking, reasoning is local to function

### Why 4-file limit?
**Decision:** Arbitrary constraint to enforce simplicity
**Rationale:** Forces thoughtful additions, prevents feature bloat

### Why manual config editing?
**Decision:** No config UI, edit config.py directly
**Rationale:** Git tracks changes, no abstraction layer, validation at startup

---

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

# Edit config
vim config.py
python -m py_compile config.py  # Validate
./start_big_dipper.sh           # Restart
```

---

## Success Metrics

**Code Quality:**
- ✅ Under 1,300 lines total
- ✅ All tests passing
- ✅ Startup < 2 seconds
- ✅ 3 dependencies only

**Trading Performance:**
- ✅ Uptime >99%
- ✅ Cycle time <10 seconds
- ✅ False signals reduced (vs naive dip-buying)
- ✅ Drawdown management via risk filters

**Operational:**
- ✅ Config changes without code edits
- ✅ Crashes recoverable (stateless)
- ✅ Logs provide full visibility
- ✅ Manual trading coexistence

---

## Remember

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

**When in doubt, do nothing.** Simplicity is the feature.

**Focus on:** Logic, data flow, strategy, engineering decisions, known limitations.

**Avoid documenting:** Specific symbols, exact thresholds, current line counts, one-time setup steps.

**Source of truth for values:** [config.py](config.py) itself.

---

**That's everything you need to develop Big Dipper.**
