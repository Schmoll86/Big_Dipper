# Big Dipper - Development Guide

**Version:** v2.18 (Margin Fix)
**Purpose:** Buy-the-dip automation with leverage-based risk management

## Critical Fix (v2.18)

**Margin calculation completely rewritten:**
- Old: `margin_debt = max(0, -cash)` → Always showed 0% with positive cash
- New: `leverage_ratio = total_positions / equity` → Correct Option B implementation
- Emergency brake now triggers at **115% leverage** (not broken 15% margin)
- Hard limit now enforces **120% leverage** (not broken 20% margin)

**What this means:**
- Positions can be up to 120% of equity (using margin)
- Current: 92.7% leverage = $32,297 positions / $34,830 equity
- Margin debt: $0 (currently not using margin, all owned outright)
- Headroom: $9,498 until hitting 120% limit

## Architecture

```
config.py       → Constants, thresholds, 38 symbols, leverage limits
dip_logic.py    → Pure trading logic (dip detection, position sizing)
utils.py        → Data fetching, formatting helpers
main.py         → Event loop, Alpaca SDK, leverage checks
```

**Single source of truth:** Alpaca API (stateless, crash-safe)

## Development Rules

### 🚫 Never Add
- Database/caching (Alpaca is truth)
- Abstraction layers (direct SDK)
- Complex state (stateless design)
- WebSockets (60s polling works)
- GUI (use web monitor)
- Stop losses (manual only)

### ✅ Always Maintain
- Pure functions in dip_logic.py
- Stateless operation
- 4-file limit
- Direct SDK usage
- Fail-fast errors
- Under 1,300 total lines

## Configuration

**Edit config.py directly - all settings in one place:**

### Position Sizing
```python
BASE_POSITION_PCT = 0.025      # 2.5% base
MAX_POSITION_PCT = 0.15        # 15% cap per stock
DIP_MULTIPLIER = 1.75          # Scale with dip size
MIN_ABSOLUTE_DIP = 0.05        # 5% floor
```

### Leverage Limits (Option B)
```python
USE_MARGIN = True
MAX_MARGIN_PCT = 0.20          # Max 120% leverage (1.0 + 0.20)
MARGIN_SAFETY_THRESHOLD = 0.15 # Brake at 115% leverage
```

**Interpretation:**
- Emergency brake: positions > 115% of equity
- Hard limit: positions > 120% of equity
- With $35k equity: max $42k in positions

### Filters & Controls
```python
COOLDOWN_HOURS = 3             # Wait between buys (halved for >7% dips)
LOOKBACK_DAYS = 20             # High water mark period
TRADE_EXTENDED_HOURS = True    # 4 AM - 8 PM ET
MAX_TOTAL_POSITIONS = 20       # Position count limit
```

### Intraday Volatility Boost
```python
VOLATILE_TICKERS = ['IBIT', 'ARKK', 'KTOS', 'FIGR', 'URNM', 'MP']
INTRADAY_DROP_THRESHOLD = 0.06  # 6% triggers boost
INTRADAY_MULTIPLIER = 1.5       # 50% larger positions
```

## Margin/Leverage Explained

### How It Works
1. **Calculate leverage:** `total_position_value / equity`
2. **Emergency brake:** Halt if leverage > 115%
3. **Per-trade check:** Block if trade would push leverage > 120%

### Example
- Equity: $35,000
- Positions: $32,000
- Leverage: 91.4% ✅
- Can add: $10,000 more (to reach 120%)

### Your Buying Power
- Regular buying power from Alpaca = what you can deploy
- Includes available margin (2:1 typically)
- Big Dipper limits leverage to 120% for safety

## Common Gotchas

### 1. Wash Sale Logic
**Current behavior:** Catches Alpaca error 40310000 when you have opposing orders

**Use case:** You place manual stop-loss on AMD, Big Dipper tries to buy more
- Alpaca rejects (can't have BUY + SELL orders simultaneously)
- Big Dipper logs as "opposing order exists" and skips
- **This is working correctly!**

### 2. Position Count Limit
```python
MAX_TOTAL_POSITIONS = 20  # Not enforced in code yet
```

**To add enforcement:**
```python
if len(tradeable_positions) >= config.MAX_TOTAL_POSITIONS:
    log.warning("Position limit reached")
    # Option: allow adding to existing only
    # Option: halt all trading
```

### 3. Web Monitor Margin Display
- Shows "Leverage: 92.7%" (positions / equity)
- Shows "Margin Debt: $0" (actual borrowed amount)
- This matches Big Dipper's calculation now

## File Structure

```
Big_Dipper/
├── config.py              # All settings
├── dip_logic.py          # Pure functions
├── utils.py              # Helpers
├── main.py               # Main loop
├── test_dip_logic.py     # Tests
├── .env                  # Alpaca keys
└── web-monitor/          # Dashboard
    ├── backend/          # Flask API
    └── frontend/         # React UI
```

## Quick Commands

```bash
# Test
python test_dip_logic.py

# Run
python main.py

# Background
nohup python main.py > big_dipper.log 2>&1 &

# Monitor
tail -f big_dipper.log

# Web Monitor
cd web-monitor && ./start_monitor.sh
```

## Testing Margin Logic

```bash
# Your current state
python3 << 'EOF'
equity = 34829.87
positions = 32297.46
leverage = positions / equity
print(f"Leverage: {leverage:.1%}")
print(f"Brake at: {equity * 1.15:,.0f} (115%)")
print(f"Limit at: {equity * 1.20:,.0f} (120%)")
print(f"Headroom: {equity * 1.20 - positions:,.0f}")
EOF
```

## Important Notes

- **Stateless:** Every cycle rebuilds from Alpaca - crash = restart safely
- **No wash sale tracking:** Only catches Alpaca's opposing order error
- **Intraday boost works:** 50% larger positions on 6%+ intraday drops
- **Extended hours:** Trades 4 AM - 8 PM ET with adjusted limit prices
- **Collateral exclusion:** BLV, SGOV, BIL never traded (manual reserves)

## When Things Break

**Emergency brake stuck:** Check leverage > 115%
**No trades executing:** Check buying power, leverage limit, cooldowns
**Web monitor shows wrong margin:** Restart backend
**Alpaca rejections:** Check for opposing orders (stop losses)

## Remember

> Simple is better than complex. Stateless is safer than stateful. Visible is better than silent.

**Focus:** Dip detection, position sizing, leverage management, operational visibility.
