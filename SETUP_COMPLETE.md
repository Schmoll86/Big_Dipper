# Big Dipper Setup Complete ✅

**Setup Date:** October 17, 2025
**Version:** v2.16
**Mode:** LIVE TRADING (real money)

## ✅ Setup Summary

All systems verified and ready to trade:

- ✅ **Virtual environment**: Fresh install at `/Users/ryanschmoll/Desktop/Big_Dipper/venv`
- ✅ **Dependencies**: alpaca-py 0.42.2, python-dotenv 1.1.1, pytz 2025.2
- ✅ **Core files**: 4 files totaling 1,275 lines
  - config.py: 105 lines
  - dip_logic.py: 194 lines
  - utils.py: 320 lines
  - main.py: 656 lines
- ✅ **Unit tests**: All tests passing
- ✅ **Alpaca API**: Connected successfully (LIVE account)
- ✅ **Test run**: Successfully completed one cycle
- ✅ **Branding**: Updated from Little Dipper to Big Dipper

## 🚨 Current Account Status

**Critical Finding from Test Run:**

```
Emergency Brake: 🛑 ACTIVE
Margin Ratio: 15.73%
Equity: $34,842.64
Margin Debt: $5,480.82
Action Required: Reduce debt by $254.42 to resume trading
```

**What this means:**
- Trading is HALTED until margin drops below 15%
- System will scan for opportunities but won't execute trades
- New v2.16 feature: You'll see which dips you're missing in logs

## 🚀 How to Start Big Dipper

### Option 1: Quick Start Script
```bash
cd /Users/ryanschmoll/Desktop/Big_Dipper
./start_big_dipper.sh
```

### Option 2: Manual Start
```bash
cd /Users/ryanschmoll/Desktop/Big_Dipper
source venv/bin/activate
python main.py
```

### Option 3: Background (with logs)
```bash
cd /Users/ryanschmoll/Desktop/Big_Dipper
source venv/bin/activate
nohup python main.py > big_dipper.log 2>&1 &
```

## 📊 Monitoring

### Check if running:
```bash
pgrep -fl "main.py"
```

### View live logs:
```bash
tail -f /Users/ryanschmoll/Desktop/Big_Dipper/big_dipper.log
```

### Check current positions:
```bash
cd /Users/ryanschmoll/Desktop/Big_Dipper
source venv/bin/activate
python check_positions.py
```

## ⚙️ Configuration

**Mode:** LIVE TRADING (ALPACA_PAPER=false)
**Log Level:** DEBUG (shows detailed opportunity scanning)
**Symbols:** 44 stocks across tech, utilities, defense, healthcare, materials
**Scan Interval:** 60 seconds
**Emergency Brake:** Active at 15.73% margin

## 🔄 Key Features (v2.16)

**Enhanced from Little Dipper:**
1. **Emergency Brake Visibility** - Shows missed opportunities during margin halt
2. **Capital Exhaustion Logging** - Logs skipped trades when funds depleted
3. **Utility Functions** - Refactored for cleaner code and maintainability
4. **Same Risk Filters** - All Little Dipper v2.15 protections intact

**Inherited from Little Dipper:**
- 5 smart risk filters (crash, volume, momentum, volatility, dynamic cooldown)
- Stock-specific thresholds (3-8% based on volatility)
- 5% absolute minimum dip (prevents threshold gaming)
- Dual margin protection (15% emergency brake, 20% hard limit)
- Extended hours trading (4 AM - 8 PM ET)
- Options/manual trading coexistence

## 📝 Next Steps

1. **Reduce margin debt by ~$255** to drop below 15% threshold
2. **Start Big Dipper** using one of the methods above
3. **Monitor logs** to see opportunities being scanned
4. **Review trades** as they execute (when margin allows)

## 🛟 Troubleshooting

**If Big Dipper won't start:**
```bash
cd /Users/ryanschmoll/Desktop/Big_Dipper
source venv/bin/activate
python test_dip_logic.py  # Should show all tests passing
```

**If API errors occur:**
- Check internet connection
- Verify Alpaca API status: https://status.alpaca.markets/
- Check .env credentials are correct

**To switch to paper trading:**
```bash
# Edit .env file
ALPACA_PAPER=true  # Change false to true
```

## 📚 Documentation

- [CLAUDE.md](CLAUDE.md) - Development guide and architecture
- [README.md](README.md) - Features and comparison with Little Dipper
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide

## ✅ Pre-Launch Checklist

- [x] No Little Dipper processes running
- [x] Virtual environment created and activated
- [x] Dependencies installed
- [x] Unit tests passing
- [x] Alpaca API connected
- [x] Test cycle completed successfully
- [x] Emergency brake working correctly
- [x] Branding updated to Big Dipper
- [x] Documentation updated

**System is ready. Start when margin allows or manually reduce positions to resume trading.**

---

Generated: October 17, 2025 at 12:02 PM PT
