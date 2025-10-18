# 🌟 Big Dipper

**Automated dip-buying with real-time web monitoring**

[![Lines of Code](https://img.shields.io/badge/Lines-~730-brightgreen)]()
[![Files](https://img.shields.io/badge/Files-4-blue)]()
[![Dependencies](https://img.shields.io/badge/Dependencies-3-green)]()

Automatically buys quality stocks when they dip from recent highs, with intelligent risk management and live dashboard.

## What It Does

**Every 60 seconds:**
1. Scans 44 stocks for 5-8% dips from 20-day highs
2. Applies smart risk filters (volatility, cooldown, leverage limits)
3. Prioritizes best opportunities
4. Executes limit orders (if buying power allows)
5. Logs all decisions transparently

**Web Monitor (port 3000):**
- Real-time account status, positions, P&L
- Live trade feed with color-coded entries
- Opportunity radar showing current dips
- Historical equity chart (1D/1W/1M/3M/1Y)

## Key Features

### Smart Risk Management
- **5% absolute minimum dip** - No threshold gaming
- **Stock-specific thresholds** - 3-8% based on volatility
- **Volatility adjustment** - Smaller positions for high-vol stocks
- **Dynamic cooldown** - Halve cooldown (3h → 1.5h) for deep dips >7%
- **Intraday boost** - Buy 1.5x on volatile tickers (IBIT, ARKK, etc.) with 6%+ intraday drop

### Leverage Protection (v2.18 Fix)
- **Emergency brake at 115%** - Halts ALL trading if positions > 115% of equity
- **Hard limit at 120%** - Blocks individual trades that would exceed 120% leverage
- **Real-time monitoring** - Web dashboard shows current leverage vs limits

### Web Monitor (v2.17+)
- **Live dashboard** - Account status, positions, real-time P&L
- **Trade feed** - Recent trades with entry prices, sizes, results
- **Opportunity radar** - Current qualifying dips with scores
- **Equity chart** - Historical performance over 1D/1W/1M/3M/1Y
- **React + TypeScript** - Fast, modern UI with Framer Motion animations

## Architecture

### Core Bot (~730 lines)
```
├── config.py (~105 lines) - Constants, thresholds, symbols
├── dip_logic.py (~195 lines) - Pure trading logic functions
├── utils.py (~280 lines) - Data fetching, formatting
└── main.py (~730 lines) - Event loop, Alpaca SDK, orchestration
```

### Web Monitor
```
├── backend/app.py - Flask API serving Alpaca data + SQLite history
├── frontend/ - React + TypeScript dashboard (5s polling)
└── data/monitor.db - SQLite for historical snapshots
```

**Principles:**
- Stateless bot (Alpaca = single source of truth, crash = safe restart)
- Pure functions (no side effects, easy testing)
- Fail-fast errors (log and halt vs silent failures)
- Minimal dependencies (3 for bot, standard web stack for monitor)

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ (for web monitor)
- Alpaca account (paper or live)
- API keys with trading permissions

### Installation

```bash
# Clone repository
git clone https://github.com/Schmoll86/Big_Dipper.git
cd Big_Dipper

# Setup bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Alpaca credentials

# Test
python test_dip_logic.py

# Run bot
./start_big_dipper.sh

# Run web monitor (separate terminal)
cd web-monitor
./start_monitor.sh
# Frontend: http://localhost:3000
# Backend: http://localhost:5001
```

### Configuration

Edit [config.py](config.py) for:
- **Symbols** - 44 stocks across tech, utilities, defense, materials
- **Thresholds** - Stock-specific dip triggers (3-8%)
- **Position sizing** - 2.5% base, 15% max per symbol
- **Leverage limits** - 115% emergency brake, 120% hard limit
- **Cooldowns** - 3 hours between buys (1.5h for deep dips)
- **Extended hours** - Enabled (4 AM - 8 PM ET)

All settings in code, not docs (single source of truth).

## Trading Logic

### Dip Detection
Uses **BID price** (conservative) to calculate dip from 20-day high:
```python
dip_pct = (current_price - lookback_high) / lookback_high
effective_threshold = max(5%, stock_threshold)  # Floor + custom threshold
```

### Position Sizing
Scales with dip severity, adjusted for volatility:
```python
size_multiplier = (dip_pct / 3%) × 1.75 / volatility_factor
target_value = equity × 2.5% × size_multiplier
# Capped at 15% of equity per symbol
```

### Leverage Limits (v2.18 Fix)
```python
leverage_ratio = total_position_value / equity
emergency_brake = 1.15  # 115% of equity
hard_limit = 1.20       # 120% of equity

# Before each trade:
if projected_leverage > hard_limit:
    skip_trade()
```

### Order Execution
- **Limit orders only** (no market orders)
- **Adaptive pricing:** Extended hours: bid + 0.5%, Regular: ask - 0.5%
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

### Web Dashboard (Recommended)
```bash
cd web-monitor
./start_monitor.sh
# Open http://localhost:3000
```

### Command Line
```bash
# Check if running
pgrep -fl "main.py"

# View logs
tail -f big_dipper.log

# Enable verbose logging
# Edit .env: LOG_LEVEL=DEBUG
```

**Log Levels:**
- **INFO** (default): Trades, emergency brake, major events
- **DEBUG** (verbose): Every symbol check, rejection reasons, dip calculations

## Options & Manual Trading

**Fully compatible** - Trade options and other equities in same account.

**How it works:**
- Tracks ALL equity positions (algo + manual)
- Filters out options (no interference)
- Manual stocks counted in allocation limits
- Bond positions (BLV/SGOV/BIL) excluded from limits

**Safety:** If SDK fails reading positions, system HALTS until resolved (no blind trades).

## Extended Hours

Trades 4 AM - 8 PM ET:
- Pre-market: 4:00 AM - 9:30 AM
- Regular: 9:30 AM - 4:00 PM
- After-hours: 4:00 PM - 8:00 PM

## Emergency Brake (v2.18)

**When leverage >115%:**
```
🛑 EMERGENCY BRAKE: Leverage at 117.3%
   Position value: $40,950 / Equity: $34,900
   💡 Reduce positions by $804 to resume trading
   📊 Missed opportunities (would have bought):
   • NVDA: -6.2% dip @ $142.50 ($2,800)
   • AMD: -5.8% dip @ $155.00 ($2,400)
```

- Halts ALL trading until leverage drops below 115%
- Logs missed opportunities for visibility
- Auto-resumes when safe to trade

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

**Bot (3 packages):**
- `alpaca-py` - Official Alpaca SDK
- `python-dotenv` - Environment variables
- `pytz` - Timezone handling

**Web Monitor:**
- Backend: Flask, alpaca-py, SQLite
- Frontend: React, TypeScript, Framer Motion

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Developer guide, architecture, critical fixes
- **[web-monitor/README.md](web-monitor/README.md)** - Web monitor setup guide

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
