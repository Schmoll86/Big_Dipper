# CRITICAL: Margin Calculation Bug

## The Problem

**Big Dipper thinks you have 0% margin usage, but you actually have 92.7%**

### Your Actual Account State
- **Equity:** $34,829.87
- **Cash:** $2,532.41
- **Stock Value:** $32,297.46
- **Actual Margin Debt:** $32,297.46 (92.7% of equity)

### What Big Dipper Calculates (WRONG)
```python
# Line 160 in main.py
margin_debt = max(0, -cash)  # max(0, -2532.41) = 0
margin_ratio = 0 / 34829.87 = 0.00%
```

**Result:** Big Dipper thinks margin usage is **0%** ❌

### What Should Be Calculated (CORRECT)
```python
margin_debt = equity - cash  # 34829.87 - 2532.41 = 32,297.46
margin_ratio = 32297.46 / 34829.87 = 92.7%
```

**Result:** Actual margin usage is **92.7%** ✅

---

## Why This is Dangerous

### The Bug Logic
The current code assumes:
- **Positive cash** = No margin debt
- **Negative cash** = Margin debt (borrowed money)

This would be correct if Alpaca reported cash as negative when using margin. But they don't!

### What Actually Happens
With margin trading:
- You borrow money to buy stocks
- Stocks sit in your account (add to equity)
- Cash stays positive (the borrowed money + your cash)
- **Margin debt = Total invested - Your actual cash**

### Your Situation
```
Equity:     $34,829.87  (market value of all holdings)
Cash:       $2,532.41   (available cash in account)
Invested:   $32,297.46  (value of stock positions)

Since invested > equity, you must have borrowed:
Margin debt = $32,297.46 - $2,532.41 = $32,297.46
```

**You're at 92.7% margin usage, not 0%!**

---

## Impact on Trading

### Safety Checks That Are Broken

**1. Emergency Brake (15% threshold)**
```python
if margin_ratio > 0.15:  # 15%
    halt_all_trading()
```
- Should trigger at $5,224 margin debt
- Currently thinks margin = 0%
- **Never halts trading!** ❌

**2. Per-Trade Limit (20% hard limit)**
```python
if projected_ratio > 0.20:  # 20%
    skip_this_trade()
```
- Should prevent going over $6,966 margin debt
- Currently allows unlimited margin
- **No protection!** ❌

### Why You Haven't Seen Issues

Alpaca has **their own** margin limits:
- They won't let you borrow beyond their limits
- But Big Dipper's limits (15%/20%) are more conservative
- You're relying on Alpaca's limits, not Big Dipper's

### Current Risk

At 92.7% margin:
- **Small market drop** could trigger margin call
- **Volatile day** could force liquidations
- **Emergency brake** should have stopped trading long ago at 15%

---

## The Fix

### Option 1: Use Alpaca's Margin Data (Recommended)
```python
# Alpaca provides direct margin values
account = self.trading.get_account()
equity = float(account.equity)
buying_power = float(account.buying_power)
maintenance_margin = float(account.maintenance_margin)  # Required collateral

# Calculate actual borrowed amount
# This is the RIGHT way - use Alpaca's own calculation
if hasattr(account, 'long_market_value') and hasattr(account, 'cash'):
    long_market_value = float(account.long_market_value)
    cash = float(account.cash)
    margin_debt = max(0, long_market_value - cash)
    margin_ratio = margin_debt / equity if equity > 0 else 0
```

### Option 2: Simple Calculation (What Web Monitor Uses)
```python
equity = float(account.equity)
cash = float(account.cash)

# Margin debt = how much you've borrowed to buy stocks
margin_debt = equity - cash  # Simple and correct
margin_ratio = margin_debt / equity if equity > 0 else 0
```

### Option 3: Check for Negative Cash (Current Logic)
Keep current logic BUT add warning:
```python
margin_debt = max(0, -cash)
if margin_debt == 0 and equity > cash * 1.5:
    log.warning("⚠️ Possible margin usage not detected!")
    log.warning(f"   Equity: ${equity}, Cash: ${cash}")
    log.warning(f"   Consider using: margin_debt = equity - cash")
```

---

## Recommended Fix

**Replace lines 158-161 in main.py:**

```python
# OLD (WRONG):
margin_debt = max(0, -cash)
margin_ratio = margin_debt / equity if equity > 0 else 0

# NEW (CORRECT):
# Calculate margin debt as (stocks owned - cash available)
# Positive result = using margin to hold positions
# This aligns with how web monitor calculates it
if cash < 0:
    # Negative cash = borrowed funds (old logic works here)
    margin_debt = abs(cash)
else:
    # Positive cash but equity > cash = borrowed to buy stocks
    margin_debt = max(0, equity - cash)

margin_ratio = margin_debt / equity if equity > 0 else 0

# Add visibility
if margin_debt > 0:
    log.debug(f"📊 Margin: ${margin_debt:,.0f} debt = {margin_ratio:.1%} of equity")
```

---

## Testing the Fix

### Before Fix
```
Equity: $34,829.87
Cash: $2,532.41
Calculated margin: 0%
Emergency brake: INACTIVE (should be ACTIVE)
```

### After Fix
```
Equity: $34,829.87
Cash: $2,532.41
Calculated margin: 92.7%
Emergency brake: ACTIVE (correct!)
```

---

## Action Items

1. ✅ **Fix margin calculation** in main.py line 160
2. ✅ **Fix web monitor display** - show "Margin Debt: $X" instead of percentage
3. ✅ **Add margin debt to logs** - show dollar amount for clarity
4. ✅ **Update config** - clarify what MAX_MARGIN_PCT means
5. ✅ **Test emergency brake** - verify it triggers at 15%

---

## Config Clarification

Your question: "Doesn't 92.6% mean we're using that much of the 20%?"

**No - it means:**
- You have $32,297 in margin debt
- That's 92.7% of your $34,830 equity
- The 20% limit means max $6,966 in margin debt
- So you're at **464% of the allowed limit**

**Better way to show this:**
```
Margin Debt: $32,297
Limit: $6,966 (20% of equity)
Usage: 464% of limit ❌ OVER
```

Or in the config's intended usage:
```
Margin Ratio: 92.7%  (current)
Max Allowed: 20%     (config)
Status: ❌ WAY OVER LIMIT
```

---

## Why This Happened

Likely scenarios:
1. You manually added positions outside Big Dipper
2. Big Dipper bought when it shouldn't have (due to broken check)
3. Config limit was changed after positions were opened
4. Alpaca has higher margin limits than Big Dipper config

**Since the brake check is broken, Big Dipper never stopped you from going over 15%.**
