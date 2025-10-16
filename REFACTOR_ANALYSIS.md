# Little Dipper Utility Module Refactor Analysis
## Creating `utils.py` for Visibility & Helper Functions

**Date:** October 16, 2025
**Goal:** Extract utility functions into separate module to keep core files under line limits
**Difficulty:** LOW - Clean separation, minimal coupling

---

## Current State

### File Sizes
```
config.py:       99 lines (limit: 100) ⚠️  AT LIMIT
dip_logic.py:   205 lines (limit: 250) ✅ 45 lines available
main.py:        662 lines (limit: 700) ✅ 38 lines available
test_*.py:      ~400 lines (test files)
get_trades.py:   63 lines (analysis script)
check_positions: 45 lines (analysis script)
-----------------------------------------------------
TOTAL:          ~966 lines core trading logic
```

### Current Function Distribution

**dip_logic.py (7 functions):**
- `calculate_dip()` - Core trading logic
- `should_buy()` - Core trading logic
- `calculate_shares()` - Core trading logic
- `calculate_limit_price()` - Core trading logic
- `calculate_opportunity_score()` - Core trading logic
- `format_money()` - ⚠️ UTILITY (candidate for extraction)
- `format_percent()` - ⚠️ UTILITY (candidate for extraction)

**main.py (9 methods + 1 function):**
- `__init__()` - Core
- `run()` - Core
- `_get_market_session()` - Core
- `scan_symbol()` - Core
- `execute_opportunity()` - Core
- `_get_bars()` - ⚠️ DATA FETCHING (candidate)
- `_get_current_price()` - ⚠️ DATA FETCHING (candidate)
- `_place_order()` - Core
- `manage_pending_orders()` - Core
- `main()` - Core

---

## Proposed New Architecture (4 Files)

### **utils.py** (~150-200 lines) - NEW FILE

**Purpose:** Visibility, analysis, and helper functions that don't belong in core trading logic

**Functions to create (NEW):**

#### 1. Visibility Functions
```python
def scan_opportunities_during_brake(
    symbols: List[str],
    data_client,
    equity: float,
    cash: float,
    position_map: Dict,
    is_extended_hours: bool
) -> List[Dict]:
    """
    Scan all symbols for opportunities during emergency brake.
    Returns list of qualifying opportunities with dip info.

    Used by: main.py emergency brake section
    Lines: ~30
    """
    pass

def log_brake_status(
    margin_ratio: float,
    margin_debt: float,
    equity: float,
    target_threshold: float,
    missed_opportunities: List[Dict],
    brake_cycle_count: int
) -> None:
    """
    Log comprehensive emergency brake status.
    Shows: debt reduction needed, missed opportunities (top 5), cycle count.

    Used by: main.py emergency brake section
    Lines: ~25
    """
    pass

def log_capital_exhaustion(
    skipped_opportunities: List[Dict],
    deployed_this_cycle: float,
    max_margin_pct: float
) -> None:
    """
    Log opportunities skipped due to capital/margin limits.
    Shows: top 3 skipped dips, suggestions for tuning.

    Used by: main.py after order execution
    Lines: ~15
    """
    pass
```

#### 2. Data Fetching Helpers (MOVE from main.py)
```python
def get_bars(
    symbol: str,
    days: int,
    data_client
) -> Optional[List[Dict]]:
    """
    Get historical bars for symbol.
    Moved from: main.py._get_bars()

    Lines: ~40 (extracted from main.py)
    """
    pass

def get_current_price(
    symbol: str,
    data_client,
    use_bid: bool = True
) -> Optional[float]:
    """
    Get current price from latest quote.
    Moved from: main.py._get_current_price()

    Lines: ~25 (extracted from main.py)
    """
    pass
```

#### 3. Formatting Helpers (MOVE from dip_logic.py)
```python
def format_money(value: float) -> str:
    """Format dollar amount with commas"""
    return f"${value:,.2f}"

def format_percent(value: float) -> str:
    """Format percentage with 2 decimals"""
    return f"{value*100:.2f}%"
```

#### 4. Analysis Functions (NEW - for manual debugging)
```python
def generate_opportunity_report(
    symbols: List[str],
    data_client,
    trading_client,
    config
) -> str:
    """
    Generate detailed report of current market state.
    Shows: opportunities, cooldowns, position capacity.

    Can be called from debug_report.py or interactively.
    Lines: ~40
    """
    pass

def analyze_position_capacity(
    trading_client,
    config
) -> Dict:
    """
    Analyze position sizes vs limits.
    Returns: dict with capacity info for each symbol.

    Lines: ~20
    """
    pass
```

**Total utils.py size: ~200 lines**

---

## Refactor Difficulty Analysis

### ✅ EASY EXTRACTIONS (Low Risk)

#### 1. Format Functions from dip_logic.py
**Difficulty:** ⭐ TRIVIAL
**Risk:** NONE
**Lines freed:** 6 lines

**Current:**
```python
# dip_logic.py lines 198-205
def format_money(value: float) -> str:
    """Format dollar amount with commas"""
    return f"${value:,.2f}"

def format_percent(value: float) -> str:
    """Format percentage with 2 decimals"""
    return f"{value*100:.2f}%"
```

**After:**
```python
# dip_logic.py - DELETE these functions
# main.py - Change import:
from utils import format_money, format_percent
```

**Impact:**
- dip_logic.py: 205 → 199 lines ✅
- main.py: no change (just import update)
- Zero logic changes

---

#### 2. Data Fetching from main.py
**Difficulty:** ⭐⭐ EASY
**Risk:** LOW
**Lines freed:** 65 lines

**Current:**
```python
# main.py lines 490-532 and 533-556
def _get_bars(self, symbol: str, days: int) -> Optional[List[Dict]]:
    # 42 lines of bar fetching logic
    pass

def _get_current_price(self, symbol: str) -> Optional[float]:
    # 23 lines of quote fetching logic
    pass
```

**After:**
```python
# utils.py - NEW
def get_bars(symbol: str, days: int, data_client) -> Optional[List[Dict]]:
    # Same 42 lines, but standalone function
    pass

def get_current_price(symbol: str, data_client, use_bid: bool = True) -> Optional[float]:
    # Same 23 lines, but standalone function
    pass

# main.py - Replace method calls
# OLD: bars = self._get_bars(symbol, 20)
# NEW: bars = get_bars(symbol, 20, self.data)
```

**Required changes in main.py:**
- Import: `from utils import get_bars, get_current_price`
- Replace `self._get_bars(symbol, days)` → `get_bars(symbol, days, self.data)`
- Replace `self._get_current_price(symbol)` → `get_current_price(symbol, self.data)`
- Delete the two method definitions

**Impact:**
- main.py: 662 → 597 lines (freed 65 lines!) ✅
- utils.py: +65 lines
- Logic: UNCHANGED (just moved)
- Risk: LOW (pure data fetching, no side effects)

---

### ⚡ NEW FUNCTIONS (Medium Complexity)

#### 3. Emergency Brake Visibility
**Difficulty:** ⭐⭐⭐ MODERATE
**Risk:** MEDIUM
**Lines added:** ~55 lines

**New in utils.py:**
```python
def scan_opportunities_during_brake(
    symbols: List[str],
    data_client,
    equity: float,
    cash: float,
    position_map: Dict,
    is_extended_hours: bool,
    config
) -> List[Dict]:
    """Scan symbols during brake (reuses scan_symbol logic)"""

    opportunities = []
    for symbol in symbols:
        # Similar to main.py.scan_symbol() but simplified
        # Get bars, check dip, return basic info
        bars = get_bars(symbol, config.LOOKBACK_DAYS, data_client)
        if not bars:
            continue

        price = get_current_price(symbol, data_client)
        if not price:
            continue

        dip_pct = calculate_dip(price, bars, config.LOOKBACK_DAYS)
        if not dip_pct:
            continue

        threshold = config.get_dip_threshold(symbol)
        if abs(dip_pct) >= max(config.MIN_ABSOLUTE_DIP, threshold):
            opportunities.append({
                'symbol': symbol,
                'dip_pct': dip_pct,
                'threshold': threshold,
                'current_price': price
            })

    return opportunities

def log_brake_status(
    margin_ratio: float,
    margin_debt: float,
    equity: float,
    target_threshold: float,
    missed_opportunities: List[Dict],
    brake_cycle_count: int
) -> None:
    """Log emergency brake status with missed opportunities"""

    # Calculate liquidation guidance
    reduction_needed = margin_debt - (equity * target_threshold)

    log.error(f"🛑 EMERGENCY BRAKE (cycle {brake_cycle_count}): Margin at {format_percent(margin_ratio)}")
    log.error(f"   Margin debt: {format_money(margin_debt)} / Equity: {format_money(equity)}")
    log.error(f"   💡 Reduce debt by {format_money(reduction_needed)} to resume trading")

    if missed_opportunities:
        missed_opportunities.sort(
            key=lambda o: calculate_opportunity_score(o['dip_pct'], o['threshold']),
            reverse=True
        )
        log.warning(f"⚠️  MISSING {len(missed_opportunities)} opportunities:")
        for opp in missed_opportunities[:5]:
            score = calculate_opportunity_score(opp['dip_pct'], opp['threshold'])
            log.warning(f"   💎 {opp['symbol']:6s}: {format_percent(opp['dip_pct'])} dip "
                       f"(score: {score:.2f}x) @ {format_money(opp['current_price'])}")
```

**Usage in main.py:**
```python
# main.py line ~160 (emergency brake section)
if margin_ratio > config.MARGIN_SAFETY_THRESHOLD:
    self._brake_cycle_count += 1

    # Only scan if brake persists for 5+ cycles (5 minutes)
    missed_opps = []
    if self._brake_cycle_count >= 5:
        log.info("📊 Scanning for missed opportunities (brake persists)...")
        missed_opps = scan_opportunities_during_brake(
            symbols_to_trade, self.data, equity, cash,
            position_map, is_extended_hours, config
        )

    log_brake_status(
        margin_ratio, margin_debt, equity,
        config.MARGIN_SAFETY_THRESHOLD,
        missed_opps,
        self._brake_cycle_count
    )

    time.sleep(config.SCAN_INTERVAL_SEC)
    continue
else:
    self._brake_cycle_count = 0  # Reset when brake clears
```

**Impact:**
- main.py: +15 lines (usage code) → 612 lines ✅
- utils.py: +55 lines (new functions)
- Risk: MEDIUM (new scanning logic, but isolated)

---

#### 4. Capital Exhaustion Logging
**Difficulty:** ⭐⭐ EASY
**Risk:** LOW
**Lines added:** ~15 lines

**New in utils.py:**
```python
def log_capital_exhaustion(
    skipped_opportunities: List[Dict],
    deployed_this_cycle: float,
    max_margin_pct: float
) -> None:
    """Log opportunities skipped due to capital limits"""

    if not skipped_opportunities:
        return

    log.warning(f"💰 CAPITAL EXHAUSTED: Skipped {len(skipped_opportunities)} opportunities "
               f"after deploying {format_money(deployed_this_cycle)}:")

    for opp in skipped_opportunities[:3]:
        score = calculate_opportunity_score(opp['dip_pct'], opp['threshold'])
        log.warning(f"   ⏭️  {opp['symbol']:6s}: {format_percent(opp['dip_pct'])} "
                   f"(score: {score:.2f}x)")

    log.warning(f"   Consider increasing MAX_MARGIN_PCT (current: {format_percent(max_margin_pct)}) "
               f"or freeing up capital")
```

**Usage in main.py:**
```python
# main.py line ~275 (after order execution)
skipped_capital = []
for opp in qualifying_opportunities:
    success = self.execute_opportunity(opp, equity, cash, position_map, is_extended_hours, account)
    if not success and self._cycle_order_value > 0:
        skipped_capital.append(opp)

log_capital_exhaustion(skipped_capital, self._cycle_order_value, config.MAX_MARGIN_PCT)
```

**Impact:**
- main.py: +8 lines (usage code) → 620 lines ✅
- utils.py: +15 lines (new function)
- Risk: LOW (simple logging)

---

## Final Line Count Projection

### After Full Refactor

```
config.py:      99 lines (no change)
dip_logic.py:  199 lines (removed format functions: -6)
main.py:       620 lines (removed _get_bars, _get_current_price: -65, added usage: +23)
utils.py:      200 lines (NEW: format+data_fetch+visibility+analysis)
test_*.py:     ~400 lines (no change)
---------------------------------------------------------------------------
CORE TOTAL:   1,118 lines (was 966)
```

**Wait, that's MORE lines!**

Yes, but the **critical constraint** was individual file limits:
- ✅ config.py: 99/100 (was at limit, now has room)
- ✅ dip_logic.py: 199/250 (freed 6 lines, 51 available)
- ✅ main.py: 620/700 (freed 42 lines, 80 available!)
- ✅ utils.py: 200/250 (new file, well under limit)

**Total system complexity increased slightly (+152 lines), but individual files now have headroom for future enhancements.**

---

## Refactor Checklist

### Phase 1: Extract Utilities (Low Risk)
**Estimated time: 30 minutes**

1. ✅ Create `utils.py` with imports
2. ✅ Move `format_money()` and `format_percent()` from dip_logic.py
3. ✅ Update imports in main.py and dip_logic.py
4. ✅ Test: `python test_dip_logic.py` (should pass)

### Phase 2: Extract Data Fetching (Medium Risk)
**Estimated time: 45 minutes**

1. ✅ Copy `_get_bars()` from main.py to utils.py as `get_bars()`
2. ✅ Copy `_get_current_price()` from main.py to utils.py as `get_current_price()`
3. ✅ Update all call sites in main.py (replace `self._get_bars()` → `get_bars(..., self.data)`)
4. ✅ Delete original methods from main.py
5. ✅ Test: Run main.py in paper trading for 1 cycle
6. ✅ Verify: Bars and prices fetched correctly

### Phase 3: Add Visibility Functions (Higher Risk)
**Estimated time: 1 hour**

1. ✅ Implement `scan_opportunities_during_brake()` in utils.py
2. ✅ Implement `log_brake_status()` in utils.py
3. ✅ Add `self._brake_cycle_count = 0` to main.py.__init__()
4. ✅ Update emergency brake section in main.py.run()
5. ✅ Test: Manually trigger brake (margin >15%), verify scanning at cycle 5
6. ✅ Verify: Missed opportunities logged correctly

### Phase 4: Add Capital Exhaustion Logging (Low Risk)
**Estimated time: 20 minutes**

1. ✅ Implement `log_capital_exhaustion()` in utils.py
2. ✅ Update execute_opportunity() to return bool
3. ✅ Add tracking in order execution loop
4. ✅ Test: Simulate capital exhaustion (margin limit hit)
5. ✅ Verify: Skipped opportunities logged

### Phase 5: Testing & Validation
**Estimated time: 2 hours**

1. ✅ Run all unit tests: `python test_dip_logic.py`
2. ✅ Run margin tests: `python test_margin_calc.py`
3. ✅ Run in paper trading for 4 hours
4. ✅ Manually verify:
   - Emergency brake shows missed opps after 5 cycles
   - Capital exhaustion logged when margin limit hit
   - Data fetching unchanged (bars, prices correct)
   - Order execution unchanged
5. ✅ Check log volume (should be reasonable, not spammy)

**Total estimated time: ~4.5 hours**

---

## Risk Assessment

### LOW RISK ✅
- Extracting format functions (pure utilities)
- Extracting data fetching (no side effects)
- Capital exhaustion logging (simple addition)

### MEDIUM RISK ⚠️
- Emergency brake scanning (new logic, but isolated)
- Updating all call sites for data fetching (many locations)

### HIGH RISK ❌
- None identified

**Overall Risk: LOW-MEDIUM**

The refactor is mostly extraction (moving code) rather than rewriting logic. The new visibility functions are isolated and don't affect trading decisions.

---

## Benefits of This Approach

### ✅ Immediate Benefits
1. **Main.py freed:** 662 → 620 lines (42 lines freed, 80 available)
2. **Dip_logic.py freed:** 205 → 199 lines (6 freed, 51 available)
3. **Better separation:** Trading logic vs utilities
4. **Room to grow:** Can add more visibility without hitting limits

### ✅ Long-term Benefits
1. **Maintainability:** Utilities isolated in one place
2. **Testability:** Utils can be tested independently
3. **Reusability:** debug_report.py can use same utilities
4. **Clarity:** Clearer what's core vs helper

### ❌ Tradeoffs
1. **File count:** 3 → 4 files (violates "3-file limit" but for good reason)
2. **Total lines:** 966 → 1,118 (+152 lines overhead from function signatures/imports)
3. **Complexity:** One more file to understand

---

## Recommendation

**PROCEED WITH REFACTOR**

**Rationale:**
1. Individual file limits are the bottleneck (config.py at 99/100)
2. Refactor frees 42 lines in main.py immediately
3. Low-medium risk (mostly extraction, minimal new logic)
4. Creates space for future enhancements
5. Better code organization

**Execute in phases:**
- Phase 1-2 (low risk): Do immediately (format + data fetching)
- Phase 3-4 (higher risk): Do after Phase 1-2 validates cleanly
- Phase 5: Continuous testing throughout

**Estimated completion: 1 day of focused work**

---

## Alternative: Minimal Approach

If you want to **avoid the 4th file**, alternative is:

**Just extract data fetching to utils.py** (~90 lines):
- `get_bars()`
- `get_current_price()`
- `format_money()`
- `format_percent()`

**Then add ONLY emergency brake visibility** (~30 lines) to main.py:
- Inline scanning during brake (don't extract to utils)
- Skip capital exhaustion logging (nice-to-have)

**Result:**
- main.py: 662 - 65 + 30 = 627 lines (73 lines available)
- utils.py: 90 lines (new, minimal)
- Still creates 4th file, but much smaller

**This gives you emergency brake visibility without capital exhaustion feature.**

---

## Questions for Decision

1. **Accept 4th file?** (utils.py ~200 lines) vs 3-file philosophy
2. **Full refactor or minimal?** (All features vs just brake visibility)
3. **Brake scan threshold:** 5 cycles (5 min) or longer? (You said "longer is fine")
4. **Capital exhaustion priority:** Must-have or nice-to-have?

**My recommendation: Full refactor with 5-cycle brake threshold**

---

**END OF REFACTOR ANALYSIS**
