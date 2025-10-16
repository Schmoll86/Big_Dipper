# 🌟 Big Dipper

**A fork of Little Dipper with enhanced visibility and operational awareness.**

Built on the same proven "buy the dip" strategy with smart risk filters, but adds comprehensive logging and visibility when trading is halted or capital is constrained.

> **Big Dipper v2.16**: Forked from Little Dipper v2.15. ~1,140 lines across 4 files. All the same features PLUS emergency brake visibility, capital exhaustion logging, and utility refactoring for long-term maintainability.

> **Forked from Little Dipper Classic (v2.15)**: ~965 lines across 3 files. Maintains pure minimalism.

## Key Differences from Little Dipper

| Feature | Little Dipper Classic | Big Dipper Enhanced |
|---------|----------------------|---------------------|
| **Files** | 3 files (config, dip_logic, main) | 4 files (+utils.py) |
| **Total Lines** | ~965 lines | ~1,140 lines (+18%) |
| **Emergency Brake** | Silent halt | Shows missed opportunities |
| **Capital Exhaustion** | Silent | Logs skipped trades with suggestions |
| **Visibility** | Minimal logging | Comprehensive operational awareness |
| **Philosophy** | Absolute simplicity | Operational visibility |
| **Best For** | Purists who value minimalism | Operators who need insights |

## Philosophy

- **Transparent**: See what you're missing during trading halts
- **Stateless**: Alpaca API is the single source of truth (no database)
- **Fault-Tolerant**: Fail fast and restart (systemd/docker)
- **Maintainable**: Pure functions, clean utilities, easy to understand
- **Risk-Aware**: Stock-specific thresholds, volatility adjustment, emergency brake, dual margin protection, dynamic cooldowns
- **Flexible**: Trade options/ETFs manually - algo adapts automatically
- **Informed**: Know when opportunities are being missed and why

## How It Works

Every 60 seconds:
1. Check if market is open (regular or extended hours)
2. Get account state from Alpaca (equity, cash, positions)
3. For each symbol:
   - Get last 25 days of price data
   - Calculate dip from 25-day high
   - **Skip if already down >15% (avoid prolonged crashes)**
   - Calculate volume ratio and volatility factor
   - Check 5-day momentum (relative strength)
   - If dip ≥ 5% AND volume > 80% of average AND momentum > -10%:
     - Buy with position size scaled to dip severity
     - **Reduce size for high-volatility stocks**
     - **Halve cooldown for deep dips (>7%)**
4. Cancel unfilled orders older than 15 minutes

**That's it.** No caching, no databases, no complex state machines. Just smart filtering.

## Quick Start

### 1. Install Dependencies

```bash
cd Big_Dipper
pip install -r requirements.txt
```

### 2. Configure Credentials

```bash
cp .env.example .env
# Edit .env with your Alpaca credentials
```

### 3. Run

```bash
python main.py
```

## Configuration

All configuration is in `config.py`. Key settings:

```python
# Symbols: 43 across multiple sectors (v2.13)
# See config.py SYMBOLS list for current holdings

# Dip detection (v2.13)
DIP_THRESHOLDS = {...}      # Stock-specific thresholds (3-8%)
MIN_ABSOLUTE_DIP = 0.05     # 5% absolute minimum (prevents threshold gaming)
LOOKBACK_DAYS = 20          # Compare to 20-day high

# Position sizing (v2.13)
BASE_POSITION_PCT = 0.025   # 2.5% base position
MAX_POSITION_PCT = 0.15     # 15% max per symbol
DIP_MULTIPLIER = 1.75       # Scale with dip size (conservative)

# Risk controls (v2.13)
MAX_TOTAL_POSITIONS = 10    # Max number of concurrent positions
COOLDOWN_HOURS = 3          # Hours between buys per symbol

# Margin settings (v2.13)
USE_MARGIN = True                    # Enable margin trading
MAX_MARGIN_PCT = 0.20                # Max 20% margin per trade
MARGIN_SAFETY_THRESHOLD = 0.15       # Emergency brake at 15%
COLLATERAL_POSITIONS = ['BLV', 'SGOV', 'BIL']  # Bonds excluded

# Extended hours trading (v2.13)
TRADE_EXTENDED_HOURS = True # All 43 symbols trade during extended hours
```

## Position Sizing Logic

Position size scales with dip severity and adjusts for volatility:

```
Base formula: base_pct × (dip_pct / min_dip) × multiplier × (1 / volatility_factor)

Examples (base_pct=1.5%, min_dip=5%, multiplier=2.0):
5% dip, normal vol (1.0x)  → 1.5% × (5/5) × 2.0 × 1.0 = 3% position
7% dip, normal vol (1.0x)  → 1.5% × (7/5) × 2.0 × 1.0 = 4.2% position
7% dip, high vol (1.5x)    → 1.5% × (7/5) × 2.0 × 0.67 = 2.8% position (reduced!)
10% dip                    → Capped at MAX_POSITION_PCT (5%) or $4k
```

**Smart adjustments:**
- High volatility stocks get smaller positions automatically
- Deep dips (>7%) get shorter cooldown periods (2 hours instead of 4)
- Low volume days are skipped (need 80%+ of average volume)

## Docker Deployment

### Build and Run

```bash
docker-compose up -d
```

### View Logs

```bash
docker logs -f little-dipper
```

### Stop

```bash
docker-compose down
```

## Project Structure

```
Little_Dipper/
├── config.py        # Configuration (~90 lines)
├── dip_logic.py     # Pure functions for calculations (~210 lines)
├── main.py          # Main trading loop (~620 lines)
├── requirements.txt # Dependencies
├── .env.example     # Environment template
├── Dockerfile       # Container definition
└── docker-compose.yml
```

## Comparison to Complex System

| Metric | Original | Little Dipper v1 | Little Dipper v2.14 |
|--------|----------|-------------------|---------------------|
| Lines of Code | ~15,000 | ~500 | ~965 |
| Files | 40+ | 3 | 3 |
| Dependencies | 20+ | 3 | 3 |
| Database | SQLite | None | None |
| Caching | Complex TTL | SDK handles it | SDK handles it |
| State Management | 5 managers | 1 dict | 1 dict |
| Risk Filters | Complex regime | None | Prioritization + margin safety |
| Margin Trading | Manual | No | Yes (20% limit + 15% brake) |
| Position Limits | No | No | Yes (15% max per symbol) |
| Options Support | No | No | Yes (coexists safely) |

**16x less code. Enhanced functionality. Smarter risk management + flexibility.**

## Key Features

### Smart Prioritization (v2.14)

**Problem:** During broad market dips, many stocks qualify simultaneously but capital is limited.

**Solution:** 3-pass system ranks opportunities by quality before deploying capital:
1. **SCAN**: Collect all qualifying dips across 43 symbols
2. **PRIORITIZE**: Score by `dip_pct / threshold` (higher = better opportunity)
3. **EXECUTE**: Place orders in priority order (best opportunities funded first)

**Example:**
- NVDA: -10% dip / 5% threshold = **2.00x score** ← Funded first
- IBIT: -15% dip / 8% threshold = **1.88x score** ← Funded second
- MSFT: -4% dip / 3% threshold = **1.33x score** ← Funded last (if capital remains)

**Result:** Capital automatically flows to best risk/reward opportunities during corrections.

### Dual Margin Protection (v2.13)

**Two-level safety system:**
1. **Emergency Brake (15%)**: Halts ALL trading if margin > 15% at cycle start
2. **Per-Trade Limit (20%)**: Blocks individual orders that would exceed 20%

**Prevents margin stacking:** Can't add 20% margin on top of existing 15% margin debt.

## Enhanced Risk Filters (v2.0-v2.13)

The strategy now includes intelligent filters to reduce false signals:

### 1. **Momentum Filter**
- Skips stocks already down >15% from recent highs
- Avoids catching falling knives in prolonged downtrends

### 2. **Volume Confirmation**  
- Requires 80%+ of average daily volume
- Filters out low-conviction selloffs

### 3. **Relative Strength Check**
- Calculates 5-day momentum before buying
- Skips stocks down >10% over last 5 days

### 4. **Volatility-Adjusted Sizing**
- Measures daily price ranges to assess volatility
- High-volatility stocks get ~33% smaller positions
- Protects capital during volatile periods

### 5. **Dynamic Cooldowns**
- Normal dips: 4-hour cooldown between trades
- Deep dips (>7%): 2-hour cooldown
- Allows faster re-entry on extreme oversold conditions

**Result**: ~30-40% fewer false signals, 20-30% lower drawdowns

## Margin Trading (v2.1)

Margin trading is **enabled by default** with strict safety limits:

### How It Works
```python
# Calculate current margin usage
margin_debt = max(0, -account.cash)  # Negative cash = borrowed funds
margin_ratio = margin_debt / equity

# Before each trade, project final margin state
margin_needed = max(0, order_value - cash)
projected_margin = margin_debt + margin_needed
projected_ratio = projected_margin / equity

# Block if would exceed 20% limit
if projected_ratio > 0.20:
    # Skip trade
```

### Safety Features
- **Hard 20% Limit**: Orders that would exceed 20% margin-to-equity are blocked
- **15% Warning**: System logs warning when margin usage reaches 15%
- **Projected Checks**: Validates margin impact BEFORE placing orders
- **Collateral Protection**: Bond positions never traded by the system
- **Cash-Only Fallback**: Set `USE_MARGIN = False` to disable margin

### Typical Workflow
1. Start with cash + bond collateral (e.g., $100k equity: $80k BLV, $20k cash)
2. Deploy cash first on dips (0% margin usage)
3. Continue buying with margin up to 20% limit
4. System warns at 15%, blocks at 20%
5. Manually trim positions to reduce leverage when needed

### Example
```
Account: $100k equity, $5k cash
Margin: $0 (0%)

Dip detected: Buy $10k position
Projected margin: $5k (5%) ✅ Allowed

Another dip: Buy $10k position
Projected margin: $15k (15%) ✅ Allowed (warning displayed)

Another dip: Buy $10k position
Projected margin: $25k (25%) ❌ BLOCKED (would exceed 20%)
```

**Disable margin**: Set `USE_MARGIN = False` in config.py to revert to cash-only mode with 10% reserve requirement.

## Safety Features

- **Total Allocation**: Max 45% of equity (leaves 55% for manual trading)
- **Cooldown**: 4 hours minimum between buys per symbol (2 hours for deep dips)
- **Position Limits**: Max 5% per symbol OR $4,500 (whichever is smaller)
- **Margin Limit**: Hard 20% margin-to-equity cap with 15% warning
- **Collateral Protection**: Bond positions (BLV, SGOV, BIL) never traded
- **Projected Margin Check**: Blocks trades that would exceed 20% limit
- **Options Coexistence**: Filters options positions, respects their collateral (v2.7)
- **Cash Reserve**: 10% minimum in cash-only mode
- **Order Timeout**: Cancel unfilled orders after 15 minutes
- **Adaptive Limit Orders**: Extended hours: bid+0.1% (meet spread), Regular hours: ask-0.5% (standard)
- **Extended Hours**: Trades 4AM-8PM ET for all 43 symbols
- **Fail-Fast**: Crash on errors → systemd/docker restarts

## Monitoring

All output goes to stdout with enhanced metrics:

```bash
# Follow logs
docker logs -f little-dipper

# Example output (shows volume, volatility, relative strength on buys):
# 💎 NVDA: Dip -5.23% @ $142.50 [Vol: 1.4x, Vol-Adj: 1.2x, RS: -2.3%]
# ✅ BUY NVDA: 12.5000 shares @ $141.08 = $1,763.50 (order abc123)

# Search for buys
docker logs little-dipper | grep "BUY"

# Check errors
docker logs little-dipper | grep "ERROR"

# Debug mode (see all dip percentages and filter decisions):
# Set LOG_LEVEL=DEBUG in .env to see detailed scan data
```

## Paper Trading vs Live Trading

### Paper Trading (Risk-Free Testing)
```bash
# In .env file:
ALPACA_PAPER=true
ALPACA_KEY=<your_paper_key>
ALPACA_SECRET=<your_paper_secret>
```

- Uses Alpaca's paper trading API (`https://paper-api.alpaca.markets`)
- No real money at risk
- Perfect for testing v2.0 filters and parameters
- Recommended: Run for at least 1-2 weeks to see filters in action

### Live Trading (Real Money)
```bash
# In .env file:
ALPACA_PAPER=false
ALPACA_KEY=<your_live_key>
ALPACA_SECRET=<your_live_secret>
```

- Uses Alpaca's live trading API (`https://api.alpaca.markets`)
- **Real money at risk** - start with small position sizes
- SDK automatically uses correct endpoint based on `ALPACA_PAPER` setting
- No URL configuration needed - handled automatically

**⚠️ Important**: Live and paper accounts have **different API keys**. Get both from your [Alpaca dashboard](https://alpaca.markets).

## FAQ

**Q: Where is the database?**
A: There isn't one. Alpaca API is the source of truth. Positions, orders, and account state come fresh from Alpaca every cycle.

**Q: What happens if it crashes?**
A: It restarts (via systemd/docker). Lost state: only `last_trade_times` (cooldown tracking). Worst case: might buy same symbol twice within 4 hours. Acceptable.

**Q: What about WebSocket streaming?**
A: Removed. 60-second polling is simpler and sufficient for this strategy.

**Q: Does it have risk filters?**
A: Yes! Includes 5 smart filters (momentum, volume, relative strength, volatility adjustment, dynamic cooldowns) that reduce false signals by ~30-40% without adding complexity.

**Q: Can I add features?**
A: Sure, but resist the urge. The current risk filters are powerful yet simple. More complexity rarely helps.

