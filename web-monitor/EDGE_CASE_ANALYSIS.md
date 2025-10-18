# Edge Case Analysis: Network Outage During Active Trading

## Scenario
**Market hours + Multiple trades occurring + Manual sell by user + Momentary network outage**

---

## What Could Go Wrong

### 1. **Web Monitor Display Issues**

#### During Outage (5-30 seconds)
**Problem:** Frontend shows stale data
- Last known positions still displayed
- Manual sell by user not reflected
- New Big Dipper buys not shown
- Margin calculations outdated

**User Impact:**
- User doesn't see their manual sell reflected
- May think sell didn't execute
- May accidentally sell again
- Position count appears wrong

**Current Behavior:**
```typescript
// Dashboard.tsx shows stale data during outage
if (!data) {
  setError(...);
} else {
  setIsStale(true);  // Shows "Connection Issues" warning
}
```

**Missing Feature:** No visual indication of HOW stale the data is (timestamp of last successful update)

---

### 2. **Database Synchronization Issues**

#### Log Parsing During Outage
**Problem:** Web monitor backend can't parse Big Dipper logs if it can't reach them

**Current State:**
- Log parser runs on every `/api/dashboard` request
- If file system is accessible, parsing continues
- If network outage affects file access, parsing fails silently

**Missing:**
- No retry mechanism for failed parses
- No queue for missed log entries
- Checkpoint may not update if parse fails mid-stream

**Risk:** Historical data gaps in web monitor database

---

### 3. **Big Dipper Trading Logic Issues**

#### Alpaca API Failures
**Problem:** Network outage means Big Dipper can't:
- Fetch current positions (doesn't know about manual sell)
- Get current prices
- Submit new buy orders
- Check order status

**Current Big Dipper Behavior:**
```python
# main.py - Fail-fast approach
try:
    account = trading_client.get_account()
    positions = trading_client.get_all_positions()
except Exception as e:
    logger.error(f"Failed to fetch account data: {e}")
    # HALTS trading for this cycle
    continue  # Skip to next 60-second cycle
```

**What This Means:**
- Big Dipper skips the entire cycle during outage
- No new buys attempted
- No position validation
- Resumes on next cycle when network returns

**Missing Awareness:**
1. **Manual sell not detected** - Big Dipper's in-memory state still thinks position exists
2. **Position allocation wrong** - May calculate position limits based on outdated data
3. **Wash sale risk** - If user sold at loss and Big Dipper tries to buy back immediately

---

### 4. **State Reconciliation After Outage**

#### When Network Returns
**Big Dipper:**
```python
# Next successful cycle
account = trading_client.get_account()  # ✅ Gets fresh data
positions = trading_client.get_all_positions()  # ✅ Sees manual sell is gone
```

**This works correctly** because Big Dipper is stateless - every cycle rebuilds state from Alpaca.

**Web Monitor:**
- Frontend polls backend every 5 seconds
- Backend calls Alpaca API on every request
- When network returns, next poll gets fresh data
- Frontend updates within 5 seconds

**This also works correctly** - both are stateless.

---

### 5. **The Real Risks**

#### Risk #1: Wash Sale Violation
**Scenario:**
1. 10:00 AM - User manually sells TICKER at $100 (loss)
2. 10:01 AM - Network outage for 30 seconds
3. 10:01 AM - TICKER dips to $95 (qualified opportunity)
4. 10:01:15 AM - Network returns
5. 10:01:20 AM - Big Dipper sees dip, buys TICKER (wash sale!)

**Current Protection:**
```python
# main.py checks for wash sales
if wash_sale_conflict_check(symbol, positions):
    logger.warning(f"[SKIP] {symbol}: Wash sale conflict detected")
    continue
```

**Problem:** This check looks at current positions from Alpaca. It doesn't know about recent sales that happened during the outage because those positions are already gone.

**What's Missing:**
- No check for recent sells in last 30 days
- Relies only on current positions, not trade history
- Could buy back immediately after user sells at loss

#### Risk #2: Over-Allocation During Recovery
**Scenario:**
1. User sells 5 positions manually during outage
2. Big Dipper has several pending limit orders from before outage
3. Network returns
4. All pending orders fill simultaneously
5. Big Dipper doesn't know positions were sold
6. Next cycle: Total position count way higher than expected

**Current Protection:**
```python
# Position sizing checks buying power and margin
if projected_margin > MARGIN_HARD_LIMIT:
    skip_trade()
```

**This works** - margin checks will catch over-leverage.

**What Could Still Go Wrong:**
- Sector concentration (all 5 new fills in tech)
- Symbol concentration (accidentally added to existing position)

#### Risk #3: Duplicate Orders
**Scenario:**
1. Big Dipper submits buy order for TICKER
2. Network outage before order confirmation received
3. Big Dipper thinks order failed
4. Network returns
5. Big Dipper tries to buy TICKER again
6. Now has 2 orders for same symbol

**Current Protection:**
```python
# Big Dipper doesn't retry failed orders
# Each cycle is independent
# Orders timeout after ORDER_TIMEOUT minutes
```

**Problem:** If network is flaky (up/down/up), multiple orders could be submitted.

**What's Missing:**
- No check for pending orders before submitting new ones
- No order deduplication by symbol

#### Risk #4: Log Data Loss
**Scenario:**
1. Big Dipper executes trades during outage
2. Logs are written successfully to local file
3. Web monitor backend can't reach log file during outage
4. Log checkpoint doesn't advance
5. When network returns, log parsing resumes
6. **What if Big Dipper rotated logs or log got truncated?**

**Current State:**
```python
# parse_new_logs() uses file position checkpoint
with open('/logs/big_dipper.log', 'r') as f:
    f.seek(checkpoint['position'])  # Could fail if file was truncated
    for line in f:
        parse_line(line)
```

**Risk:** If log file was rotated/truncated during outage, checkpoint position is invalid.

**What's Missing:**
- No validation that checkpoint position is still valid
- No detection of log rotation
- No fallback to timestamp-based parsing

---

## Recommendations

### High Priority Fixes

#### 1. Add Order Deduplication
**File:** `main.py`
```python
# Before submitting order, check for existing pending orders
pending_orders = trading_client.get_orders(status='open')
pending_symbols = {order.symbol for order in pending_orders}

if symbol in pending_symbols:
    logger.info(f"[SKIP] {symbol}: Already has pending order")
    continue
```

#### 2. Enhance Wash Sale Detection
**File:** `dip_logic.py`
```python
def check_wash_sale_history(symbol: str, trading_client) -> bool:
    """Check if symbol was sold at loss in last 30 days"""
    # Get closed positions from Alpaca
    # Check for sales at loss
    # Return True if wash sale risk detected
    pass
```

**Note:** Alpaca API may not provide this easily. Consider:
- Maintaining local trade history in web monitor database
- Checking database for recent sells before buying

#### 3. Add Staleness Indicator to Web Monitor
**File:** `frontend/src/Dashboard.tsx`
```typescript
<span>Last update: {lastUpdate.toLocaleTimeString()}</span>
{isStale && (
  <span>⚠️ Data is {Math.floor((Date.now() - lastUpdate) / 1000)}s stale</span>
)}
```

#### 4. Add Log Checkpoint Validation
**File:** `backend/app.py`
```python
def parse_new_logs():
    checkpoint = get_checkpoint()

    # Validate checkpoint is still valid
    file_size = os.path.getsize(LOG_PATH)
    if checkpoint['position'] > file_size:
        logger.warning("Log file truncated, resetting checkpoint")
        checkpoint['position'] = 0
```

### Medium Priority Improvements

#### 5. Add Position Change Detection
**File:** `main.py`
```python
# At start of each cycle
previous_symbols = set(last_positions.keys())
current_symbols = set(p.symbol for p in positions)

removed = previous_symbols - current_symbols
if removed:
    logger.warning(f"[ALERT] Positions removed since last cycle: {removed}")
    # Could be manual sells, stop losses, or liquidations
```

#### 6. Add Network Outage Detection
**File:** `backend/app.py`
```python
last_successful_alpaca_call = None

def dashboard():
    global last_successful_alpaca_call
    try:
        account = trading_client.get_account()
        last_successful_alpaca_call = datetime.now()
    except Exception as e:
        outage_duration = datetime.now() - last_successful_alpaca_call
        logger.error(f"Alpaca API down for {outage_duration}")
```

### Low Priority Enhancements

#### 7. Add Trade Reconciliation
**File:** `web-monitor/backend/app.py`
- Compare trades in database vs Alpaca trade history
- Flag discrepancies
- Backfill missing trades

#### 8. Add Position Limit Warnings
**File:** `main.py`
- Warn if total position count > expected
- Warn if sector concentration > threshold
- Warn if single position > max allocation

---

## What's Actually Missing Right Now

### Critical Gaps:
1. ❌ **No wash sale history check** - Only checks current positions
2. ❌ **No pending order deduplication** - Could submit duplicate orders
3. ❌ **No log checkpoint validation** - Could fail if logs rotated

### Important Gaps:
4. ⚠️ **No staleness timestamp in UI** - User doesn't know how old data is
5. ⚠️ **No position change detection** - Big Dipper doesn't alert on unexpected changes
6. ⚠️ **No network outage logging** - Hard to diagnose issues post-facto

### Nice-to-Have:
7. ℹ️ Trade reconciliation between logs and Alpaca
8. ℹ️ Position limit warnings
9. ℹ️ Sector concentration alerts

---

## Immediate Action Items

**For Web Monitor:**
1. Add staleness timestamp to UI
2. Validate log checkpoint before seeking
3. Add retry logic for failed Alpaca calls

**For Big Dipper:**
1. Check for pending orders before submitting new ones
2. Log position changes between cycles
3. Consider maintaining 30-day sell history for wash sale checks

**For Both:**
1. Add more verbose logging during errors
2. Add health check that includes Alpaca API status
3. Document network failure recovery behavior

---

**Severity Assessment:**
- 🔴 **Wash sale risk:** HIGH - Could trigger IRS issues
- 🟡 **Duplicate orders:** MEDIUM - Margin checks will prevent disaster
- 🟡 **Log data loss:** MEDIUM - Historical data only, not critical
- 🟢 **UI staleness:** LOW - Annoying but not dangerous
- 🟢 **Over-allocation:** LOW - Protected by margin limits

---

**Conclusion:**
The biggest risk is **wash sale violations** because Big Dipper doesn't track sell history, only current positions. During network outages, if user manually sells at a loss, Big Dipper could immediately buy back when network returns, creating a wash sale.

**Quick Fix:** Add pending order check to prevent duplicates. This is a 5-line change.

**Proper Fix:** Build trade history tracking in web monitor database and check for recent sells before buying.
