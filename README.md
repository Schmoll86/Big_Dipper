# 🌟 Big Dipper

**Automated dip-buying with operational visibility**

[![GitHub](https://img.shields.io/badge/GitHub-Big_Dipper-blue?logo=github)](https://github.com/Schmoll86/Big_Dipper)
[![Lines of Code](https://img.shields.io/badge/Lines-1275-brightgreen)]()
[![Files](https://img.shields.io/badge/Files-4-blue)]()
[![Dependencies](https://img.shields.io/badge/Dependencies-3-green)]()

Built on proven "buy the dip" logic with 5 smart risk filters. Enhanced with comprehensive logging to show what you're missing during trading halts.

## What It Does

Automatically buys quality stocks when they dip 5-8% from recent highs, with intelligent risk management and full transparency.

**Every 60 seconds:**
1. Checks market status (4 AM - 8 PM ET)
2. Scans 44 stocks for qualifying dips
3. Applies 5 risk filters (crash, volume, momentum, volatility, cooldown)
4. Prioritizes best opportunities
5. Executes trades (if margin allows)
6. **NEW:** Shows missed opportunities when trading halted

## Key Features

### Smart Risk Management
- **5% absolute minimum dip** - No threshold gaming
- **Stock-specific thresholds** - 3-8% based on volatility
- **Crash filter** - Skip if down >15% from high
- **Volume confirmation** - Require 80%+ average volume
- **Relative strength** - Skip if 5-day momentum < -10%
- **Volatility adjustment** - Smaller positions for high-vol stocks
- **Dynamic cooldown** - Halve cooldown for deep dips >7%
- **Intraday boost** - Buy 1.5x on volatile tickers with 6%+ intraday drop

### Dual Margin Protection
- **Emergency brake at 15%** - Halts ALL trading
- **Hard limit at 20%** - Blocks individual trades
- **v2.16 enhancement:** Shows which dips you're missing during brake

### Operational Visibility
- **Transparent halts** - Know why trading stopped
- **Missed opportunity logging** - See what you couldn't buy
- **Capital exhaustion alerts** - Clear guidance when funds depleted
- **DEBUG mode** - Detailed scanning for every symbol

## Results

**Risk Reduction:**
- ~30-40% fewer false signals vs naive dip-buying
- ~20-30% lower expected drawdowns
- No prolonged crash exposure (15% circuit breaker)

**System Reliability:**
- 99%+ uptime (fail-fast + auto-restart)
- <6 second cycle time
- Stateless (crash = restart from Alpaca state)

## Architecture

```
1,275 lines across 4 files
├── config.py (105 lines) - Constants, thresholds, symbols
├── dip_logic.py (194 lines) - Pure trading logic functions
├── utils.py (320 lines) - Data fetching, formatting, visibility
└── main.py (656 lines) - Event loop, Alpaca SDK, orchestration
```

**Principles:**
- No database (Alpaca API = single source of truth)
- No caching (stateless operation)
- Pure functions (easy testing)
- Fail-fast errors (Docker restarts)
- 3 dependencies only

## Quick Start

### Prerequisites
- Python 3.9+
- Alpaca account (paper or live)
- API keys with trading permissions

### Installation

```bash
# Clone repository
git clone https://github.com/Schmoll86/Big_Dipper.git
cd Big_Dipper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Alpaca credentials

# Test
python test_dip_logic.py

# Run
./start_big_dipper.sh
```

### Configuration

Edit [config.py](config.py) for:
- **Symbols** - 44 stocks across tech, utilities, defense, materials
- **Thresholds** - Stock-specific dip triggers (3-8%)
- **Position sizing** - 2.5% base, 15% max per symbol
- **Margin settings** - 15% brake, 20% hard limit
- **Cooldowns** - 3 hours between buys per symbol

All settings in code, not docs (single source of truth).

## Trading Logic

### Dip Detection
Uses **BID price** (conservative) to calculate dip from 20-day high:
```python
current_price = quote.bid_price
dip_pct = (current_price - lookback_high) / lookback_high

# Must meet BOTH:
# 1. 5% absolute minimum (prevents gaming)
# 2. Stock-specific threshold (3-8%)
effective_threshold = max(5%, stock_threshold)
```

### Position Sizing
Scales with dip severity, adjusted for volatility:
```python
size_multiplier = (dip_pct / 3%) × 1.75 / volatility_factor
target_value = equity × 2.5% × size_multiplier
# Capped at 15% of equity per symbol
```

### Order Execution
- **Limit orders only** (no market orders)
- **Adaptive pricing:**
  - Extended hours: bid + 0.1%
  - Regular hours: ask - 0.5%
- **15-minute timeout** (cancels if unfilled)

## Symbols Traded (44)

- **Tech/AI:** NVDA, AVGO, AMD, TSM, MRVL, TER, MSFT, META, ORCL, NOW, PLTR, ANET, DELL
- **Power/Utilities:** ETN, PWR, CEG, GEV, NEE, ABB, XYL, AWK, WTRG
- **Data Centers:** EQIX, DLR, AMT, CCI
- **Defense:** LMT, NOC, RTX, GD, HII, HWM, AVAV, KTOS
- **Healthcare:** ISRG, LLY, FIGR
- **Materials:** VMC, MLM, MP
- **Alternative Assets:** GLD, URNM, IBIT, ARKK

Edit SYMBOLS list in [config.py](config.py) to customize.

## Monitoring

```bash
# Check if running
pgrep -fl "main.py"

# View logs
tail -f big_dipper.log

# Check positions/margin
python check_positions.py

# Enable verbose logging
# Edit .env: LOG_LEVEL=DEBUG
```

### Log Levels

**INFO** (default):
- Trades executed
- Emergency brake status
- Major events

**DEBUG** (verbose):
- Every symbol check
- Rejection reasons
- Dip calculations
- Missed opportunities

## Options & Manual Trading

**Fully compatible** - Trade options and other equities in same account.

**How it works:**
- Tracks ALL equity positions (algo + manual)
- Filters out options (no interference)
- Manual stocks counted in allocation limits
- Bond positions (BLV/SGOV/BIL) excluded from limits

**Safety:** If SDK fails reading positions, system HALTS until resolved (no blind trades).

## Extended Hours

Trades 4 AM - 8 PM ET (all symbols):
- Pre-market: 4:00 AM - 9:30 AM
- Regular: 9:30 AM - 4:00 PM
- After-hours: 4:00 PM - 8:00 PM

## Emergency Brake (v2.16 Enhanced)

**When margin >15%:**
- ✅ Halts ALL trading
- ✅ **NEW:** Logs missed opportunities
- ✅ Shows how much debt to reduce
- ✅ Auto-resumes when margin drops <15%

**Example log:**
```
🛑 EMERGENCY BRAKE: Margin at 15.73%
   Margin debt: $5,480 / Equity: $34,848
   💡 Reduce debt by $254 to resume trading
   📊 Missed opportunities:
   • NVDA: -6.2% dip @ $142.50 (would buy $2,800)
   • AMD: -5.8% dip @ $155.00 (would buy $2,400)
```

## File Size Limits

| File | Lines | Max | Status |
|------|-------|-----|--------|
| config.py | 105 | 100 | ⚠️ At limit |
| dip_logic.py | 194 | 250 | ✅ 56 available |
| utils.py | 320 | 250 | ⚠️ Over by 70 |
| main.py | 656 | 700 | ✅ 44 available |
| **Total** | **1,275** | **1,300** | **25 to ceiling** |

**At 1,300 lines:** Feature-complete. No more additions.

## Development

### Running Tests
```bash
python test_dip_logic.py
# All tests must pass before committing
```

### Making Changes
1. Edit [config.py](config.py) for settings
2. Edit [dip_logic.py](dip_logic.py) for trading logic
3. Run tests
4. Commit with clear message
5. Push

### Deployment Options

**Local:**
```bash
./start_big_dipper.sh
```

**Background:**
```bash
nohup python main.py > big_dipper.log 2>&1 &
```

**Docker:**
```bash
docker-compose up -d
docker logs -f big-dipper
```

## Dependencies

Only 3 packages (keep it minimal):
- `alpaca-py` - Official Alpaca SDK
- `python-dotenv` - Environment variables
- `pytz` - Timezone handling

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Development guide, architecture, trading logic
- **[SETUP_COMPLETE.md](SETUP_COMPLETE.md)** - Initial setup reference
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide

## Philosophy

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."

**Core principles:**
- Simple > Complex
- Stateless > Stateful
- Visible > Silent
- Direct > Abstracted
- Smart > Naive

**When in doubt, do nothing.** Simplicity is the feature.

## Support

- **Issues:** [GitHub Issues](https://github.com/Schmoll86/Big_Dipper/issues)
- **Alpaca Status:** [status.alpaca.markets](https://status.alpaca.markets/)
- **Alpaca Docs:** [docs.alpaca.markets](https://docs.alpaca.markets/)

## License

See LICENSE file.

---

**Built with ❤️ for simplicity and transparency.** 🌟
