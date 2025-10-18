# How Big Dipper Works - Plain Language Explanation

## The Simple Idea

**Buy quality stocks when they temporarily dip, using smart risk management.**

You give it a list of stocks you like. Every 60 seconds, it checks if any are significantly down from their recent highs. If yes, it buys a calculated amount. That's it.

---

## The 60-Second Cycle

**Every minute, Big Dipper:**

1. **Gets fresh data from Alpaca** - No caching, no database, just "what's true right now"
2. **Checks all your stocks** - Are any dipping from their 20-day high?
3. **Filters out bad opportunities** - Uses 5 smart filters
4. **Ranks remaining opportunities** - Best dips first
5. **Buys in priority order** - Until it runs out of buying power
6. **Manages old orders** - Cancels stale orders after 15 minutes
7. **Sleeps 60 seconds** - Then repeats

---

## Configuration Breakdown

### Stocks to Watch (38 stocks)
```
Tech Chips: NVDA, AVGO, AMD, TSM, MRVL, TER
Tech Software: MSFT, META, ORCL, NOW, PLTR, ANET, DELL
Infrastructure: ETN, PWR, CEG, GEV, NEE, ABB
Data Centers: EQIX, DLR, AMT, CCI
Defense: LMT, NOC, RTX, GD, HII, HWM, AVAV, KTOS
Healthcare: ISRG, LLY, FIGR
Materials: VMC, MLM, MP
Water: XYL, AWK, WTRG
Commodities: GLD, URNM
Crypto/Growth: IBIT, ARKK
```

### What Counts as a "Dip"?

**Two requirements (BOTH must be met):**

1. **Stock-specific threshold** - Each stock has its own percentage
   - Stable stocks (MSFT, GLD): 3% dip needed
   - Normal stocks (NVDA, AMD): 5-6% dip needed
   - Volatile stocks (IBIT, ARKK): 7-8% dip needed

2. **Absolute minimum: 5%** - Prevents gaming the system
   - Even if MSFT's threshold is 3%, it still needs a 5% dip
   - This is the "floor" - you can't set thresholds below it

**Example:**
- MSFT configured at 3%, but **effective threshold is 5%** (floor overrides)
- NVDA configured at 5%, **effective threshold is 5%** (meets floor)
- IBIT configured at 8%, **effective threshold is 8%** (above floor)

### How Much to Buy?

**Base formula:**
```
Position Size = 2.5% of equity × (dip_size / 3%) × 1.75 multiplier
```

**Then adjusted for:**
1. **Volatility** - Reduces size for unpredictable stocks
2. **Intraday drops** - Increases size 50% if stock dropped >6% today
3. **Maximum cap** - Can never exceed 15% of equity per stock

**Examples (with $35,000 equity):**

| Dip | Stock | Volatility | Intraday | Base Size | Final Size |
|-----|-------|-----------|----------|-----------|------------|
| 5% | MSFT | Normal | No | $1,458 | $1,458 (4.2%) |
| 5% | AMD | High | No | $1,458 | $729 (2.1%) |
| 6% | IBIT | Normal | 7% today | $1,750 | $2,625 (7.5%) |
| 10% | NVDA | Normal | No | $2,917 | $2,917 (8.3%) |

**Hard limits:**
- Minimum order: $100
- Maximum position: $5,250 (15% of $35k equity)

### Position Limits

**You configure:**
- `MAX_TOTAL_POSITIONS: 10` - But code doesn't enforce this!

**What actually limits positions:**
- Margin limit (20% max)
- 15% max per stock
- Available buying power

**Currently you have 18 positions** - More than configured limit of 10. This is because the code doesn't check total position count, only margin and individual stock limits.

### Margin Rules

**Dual-layer protection:**

**Layer 1 - Emergency Brake (15% threshold):**
```python
if margin_debt / equity > 15%:
    halt_all_trading()
    log_what_youre_missing()
```
This stops ALL buying until margin drops below 15%.

**Layer 2 - Per-Trade Check (20% hard limit):**
```python
if (margin_debt + order_value) / equity > 20%:
    skip_this_trade()
```
Prevents individual orders from pushing margin too high.

**Your current state:** 92.7% margin used
- Wait, this doesn't match the config! Let me verify...
- Config says max 20% margin
- You're showing 92.7% in the web monitor
- This is margin **of equity**, not margin ratio

Actually, looking at your data:
- Equity: $34,829.87
- Cash: $2,532.41
- This means: Margin debt = $34,829.87 - $2,532.41 = $32,297.46
- Margin as % of equity = $32,297.46 / $34,829.87 = 92.7%

**CRITICAL FINDING:** Your margin usage is 92.7%, but config says MAX_MARGIN_PCT = 0.20 (20%).

This is WAY over the configured limit!

### Trading Controls

**Cooldown between buys:**
- Normal: 3 hours between buys of same stock
- Deep dips (>7%): 1.5 hours (halved cooldown)

**Order timeout:**
- Cancel unfilled orders after 15 minutes
- Prevents stale orders from executing at wrong prices

**Extended hours:**
- Enabled - Trades 4 AM to 8 PM ET
- Uses bid price + 0.5% for limit orders (more aggressive in extended hours)

### Intraday Volatility Boost

**For these 6 volatile tickers only:**
- IBIT, ARKK, KTOS, FIGR, URNM, MP

**If stock drops >6% intraday:**
- Position size increases by 50%
- Example: Normal $1,000 → Boosted to $1,500

**Why:** Capitalize on panic selling in volatile stocks

### Collateral Positions (Don't Trade)

**These 3 symbols are excluded:**
- BLV, SGOV, BIL (bond ETFs)

**Why:** Reserved for manual trading / cash management

---

## The 5 Smart Risk Filters

**Before buying, every opportunity must pass:**

### Filter 1: Absolute Minimum Dip (5%)
```
if dip < 5%: skip
```
Prevents buying on minor fluctuations.

### Filter 2: Stock-Specific Threshold
```
if dip < stock's threshold: skip
```
Respects configured sensitivity per stock.

### Filter 3: Position Size Limit (15% max)
```
if current_position >= 15% of equity: skip
```
Prevents concentration risk.

### Filter 4: Cooldown Timer
```
if last_buy < 3 hours ago: skip
if last_buy < 1.5 hours ago and dip > 7%: allow (dynamic)
```
Prevents overtrading same stock.

### Filter 5: Volatility Adjustment
```
size = base_size / volatility_factor
```
Reduces position size for unpredictable stocks.

**MISSING FILTERS (mentioned in docs but NOT in code):**
- ❌ Crash filter (skip if down >15% from high) - **NOT IMPLEMENTED**
- ❌ Volume confirmation (require 80% of avg volume) - **NOT IMPLEMENTED**
- ❌ Relative strength (skip if 5-day momentum < -10%) - **NOT IMPLEMENTED**

---

## Priority Scoring

**When multiple stocks qualify, buy in this order:**

```
Score = (actual_dip / stock_threshold) ^ 2
```

**Examples:**
- 6% dip with 3% threshold: (6/3)² = 4.0x score
- 6% dip with 5% threshold: (6/5)² = 1.44x score
- 10% dip with 5% threshold: (10/5)² = 4.0x score

**Best scores buy first**, until capital exhausted.

---

## What Can Stop Trading

### 1. Emergency Brake (Margin >15%)
- Halts ALL trading
- Logs what you're missing
- Resumes when margin drops below 15%

### 2. Capital Exhaustion
- Out of buying power
- Logs opportunities skipped due to lack of capital

### 3. Position Read Failure
- If Alpaca API fails to return positions (e.g., due to options)
- Halts trading for safety
- Auto-resumes next cycle when positions load

### 4. Network Issues
- Can't reach Alpaca API
- Skips entire cycle
- Retries next cycle (60 seconds)

### 5. Wash Sale Detection
- If you have an open position in the same stock
- Wait, this doesn't make sense...

Actually, wash sale code checks:
```python
if symbol in current_positions:
    skip "wash sale conflict"
```

**BUG:** This prevents buying MORE of a stock you already own! That's not what wash sales are.

**Real wash sale:** Selling at a loss, then buying back within 30 days.

---

## Code vs Config Verification

### ✅ What Matches Config

1. **Dip thresholds** - Code uses config.DIP_THRESHOLDS correctly
2. **Absolute minimum 5%** - Code enforces MIN_ABSOLUTE_DIP
3. **Position sizing formula** - Matches config values
4. **15% max position** - Code enforces MAX_POSITION_PCT
5. **Cooldown (3 hours)** - Code uses COOLDOWN_HOURS
6. **Dynamic cooldown** - Halves for dips >7%
7. **Extended hours** - Code checks TRADE_EXTENDED_HOURS
8. **Intraday boost** - Code implements VOLATILE_TICKERS logic
9. **Margin limits** - Code checks both thresholds

### ❌ What Doesn't Match Config

1. **MAX_TOTAL_POSITIONS = 10** - Code never checks this!
   - You have 18 positions right now
   - Config says max 10
   - Code doesn't enforce it

2. **"5 Smart Risk Filters" (from docs)** - Only 2 are implemented!
   - ✅ Crash filter - **NOT IN CODE**
   - ✅ Volume confirmation - **NOT IN CODE**
   - ✅ Relative strength - **NOT IN CODE**
   - ✅ Volatility adjustment - **IMPLEMENTED**
   - ✅ Dynamic cooldown - **IMPLEMENTED**

3. **Wash sale detection** - Code is WRONG
   - Checks if symbol in current_positions
   - This prevents adding to existing positions
   - Real wash sales: sell at loss → buy within 30 days
   - This check doesn't do that at all

4. **Margin usage** - You're at 92.7%, config says max 20%
   - Either config is wrong
   - Or margin calculation is wrong
   - Or you manually added positions outside Big Dipper

### ⚠️ Questionable Design Choices

1. **No pending order deduplication** - Can submit duplicate orders during network issues
2. **No total position count enforcement** - Configured limit ignored
3. **Wash sale logic is backwards** - Prevents buying more, not actual wash sales
4. **No sector limits** - Could get all tech stocks if they all dip

---

## How It Should Work (According to Config)

**Simple version:**
1. Every 60 seconds, check 38 stocks
2. Buy ones that dipped >5% from 20-day high
3. Size based on dip severity (bigger dip = bigger buy)
4. Never exceed 15% per stock
5. Never exceed 20% margin usage
6. Never exceed 10 total positions
7. Wait 3 hours between buys of same stock

**What actually happens:**
1. ✅ Every 60 seconds, check 38 stocks
2. ✅ Buy ones that dipped >5% from 20-day high
3. ✅ Size based on dip severity
4. ✅ Never exceed 15% per stock
5. ❌ Never exceed 20% margin (you're at 92.7%!)
6. ❌ Never exceed 10 positions (you have 18!)
7. ✅ Wait 3 hours between buys

---

## Critical Findings

### 1. Position Limit Not Enforced
**Config says:** MAX_TOTAL_POSITIONS = 10
**You have:** 18 positions
**Code:** Never checks this limit

### 2. Margin Calculation May Be Wrong
**Config says:** MAX_MARGIN_PCT = 0.20 (20%)
**You have:** 92.7% margin usage
**This means:**
- Either config is outdated
- Or margin is calculated differently than expected
- Or you added positions manually

### 3. "5 Smart Risk Filters" Are Marketing
**Docs claim:**
- Crash filter
- Volume confirmation
- Relative strength
- Volatility adjustment ✅
- Dynamic cooldown ✅

**Reality:** Only 2 of 5 are implemented

### 4. Wash Sale Logic Is Backwards
**Current code:** Prevents buying MORE of stocks you own
**Real wash sales:** Sell at loss, buy back within 30 days
**This isn't implemented at all**

---

## Recommendations

### Immediate Fixes Needed

1. **Fix margin calculation or config**
   - Either update MAX_MARGIN_PCT to 0.95
   - Or fix margin calculation
   - Current state is dangerous (92.7% vs 20% limit)

2. **Enforce position count limit**
   - Add check: `if len(positions) >= MAX_TOTAL_POSITIONS: halt`
   - Or remove from config if not intended

3. **Fix or remove wash sale check**
   - Current logic prevents adding to positions (wrong)
   - Either implement real wash sale check
   - Or remove this check entirely

4. **Document missing risk filters**
   - Remove "5 smart filters" claim from docs
   - Or implement the 3 missing filters

### Optional Improvements

5. **Add pending order check** - Prevent duplicates during network issues
6. **Add sector limits** - Prevent over-concentration
7. **Add volume filter** - Avoid low-liquidity dips
8. **Add momentum filter** - Avoid catching falling knives

---

## Bottom Line

**Big Dipper works as advertised for:**
- ✅ Detecting dips from 20-day highs
- ✅ Position sizing based on dip severity
- ✅ Cooldown management
- ✅ Extended hours trading
- ✅ Intraday volatility boost
- ✅ Stateless operation

**Big Dipper DOESN'T work as configured for:**
- ❌ Total position limit (10 max → you have 18)
- ❌ Margin limit (20% max → you have 92.7%)
- ❌ Wash sale detection (logic is backwards)
- ❌ 3 of the "5 smart risk filters" (not implemented)

**Most critical issue:** Margin usage is 4.6x higher than configured limit. This needs immediate attention.
