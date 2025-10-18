"""
Big Dipper Utilities Module (v2.16)

Helper functions for:
- Data fetching (bars, quotes)
- Formatting (money, percentages)
- Visibility (emergency brake, capital exhaustion)
- Opportunity scoring

Created in Big Dipper fork to keep main.py under 700 line limit while adding visibility.
Forked from Little Dipper v2.15.
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame

log = logging.getLogger(__name__)


# ============================================================================
# FORMATTING UTILITIES (moved from dip_logic.py)
# ============================================================================

def format_money(value: float) -> str:
    """Format dollar amount with commas"""
    return f"${value:,.2f}"


def format_percent(value: float) -> str:
    """Format percentage with 2 decimals"""
    return f"{value*100:.2f}%"


# ============================================================================
# SCORING UTILITIES
# ============================================================================

def calculate_opportunity_score(dip_pct: float, threshold: float) -> float:
    """Calculate opportunity score (abs(dip_pct) / threshold). Higher = better opportunity."""
    if threshold <= 0:
        return 1.0
    return abs(dip_pct) / threshold


# ============================================================================
# DATA FETCHING UTILITIES (moved from main.py)
# ============================================================================

def get_bars(
    symbol: str,
    days: int,
    data_client: StockHistoricalDataClient
) -> Optional[List[Dict]]:
    """Get historical bars (OHLCV dicts) for symbol, or None if failed."""
    try:
        # Request extra calendar days to ensure we get enough trading days
        # 20 trading days ≈ 30 calendar days (weekends + holidays)
        # Use 2x multiplier for safety during holiday weeks
        calendar_days = days * 2
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.now() - timedelta(days=calendar_days)
        )

        bars_response = data_client.get_stock_bars(request)

        # BarSet object has .data dict
        if not hasattr(bars_response, 'data') or symbol not in bars_response.data:
            return None

        # Convert to simple dict list
        bars = [
            {
                'timestamp': bar.timestamp,
                'open': float(bar.open),
                'high': float(bar.high),
                'low': float(bar.low),
                'close': float(bar.close),
                'volume': int(bar.volume)
            }
            for bar in bars_response.data[symbol]
        ]

        return bars if bars else None

    except Exception as e:
        log.debug(f"Failed to get bars for {symbol}: {e}")
        return None


def get_current_price(
    symbol: str,
    data_client: StockHistoricalDataClient,
    use_bid: bool = True
) -> Optional[float]:
    """Get current bid or ask price from latest quote, or None if failed."""
    try:
        quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
        quote_response = data_client.get_stock_latest_quote(quote_request)

        if symbol not in quote_response:
            log.debug(f"No quote returned for {symbol}")
            return None

        quote = quote_response[symbol]

        if use_bid:
            # Use bid price (more conservative for buy decisions)
            price = float(quote.bid_price) if quote.bid_price > 0 else float(quote.ask_price)
        else:
            # Use ask price
            price = float(quote.ask_price) if quote.ask_price > 0 else float(quote.bid_price)

        return price if price > 0 else None

    except Exception as e:
        log.debug(f"Failed to get current price for {symbol}: {e}")
        return None


# ============================================================================
# EMERGENCY BRAKE VISIBILITY
# ============================================================================

def scan_opportunities_during_brake(
    symbols: List[str],
    data_client: StockHistoricalDataClient,
    lookback_days: int,
    min_absolute_dip: float,
    get_dip_threshold_func
) -> List[Dict]:
    """Scan symbols for qualifying dips during brake (no position checks or orders)."""
    from dip_logic import calculate_dip  # Import here to avoid circular

    opportunities = []

    for symbol in symbols:
        try:
            # Get historical bars
            bars = get_bars(symbol, lookback_days, data_client)
            if not bars or len(bars) < lookback_days:
                continue

            # Get current price (use BID for consistency)
            current_price = get_current_price(symbol, data_client, use_bid=True)
            if not current_price:
                continue

            # Calculate dip percentage
            dip_pct = calculate_dip(current_price, bars, lookback_days)
            if dip_pct is None or dip_pct >= 0:  # Not a dip
                continue

            # Check if meets threshold
            threshold = get_dip_threshold_func(symbol)
            effective_threshold = max(min_absolute_dip, threshold)

            if abs(dip_pct) >= effective_threshold:
                opportunities.append({
                    'symbol': symbol,
                    'dip_pct': dip_pct,
                    'threshold': threshold,
                    'current_price': current_price
                })

        except Exception as e:
            log.debug(f"Error scanning {symbol} during brake: {e}")
            continue

    return opportunities


def log_brake_status(
    margin_ratio: float,
    margin_debt: float,
    equity: float,
    target_threshold: float,
    missed_opportunities: List[Dict],
    brake_cycle_count: int
) -> None:
    """Log emergency brake status with missed opportunities and reduction guidance."""
    # Calculate how much to liquidate
    target_debt = equity * target_threshold
    reduction_needed = max(0, margin_debt - target_debt)

    # Log brake status with structured tag for web monitor
    log.error(f"[BRAKE] 🛑 EMERGENCY BRAKE (cycle {brake_cycle_count}): "
             f"Margin at {format_percent(margin_ratio)}")
    log.error(f"   Margin debt: {format_money(margin_debt)} / "
             f"Equity: {format_money(equity)}")

    if reduction_needed > 0:
        log.error(f"   💡 Reduce debt by {format_money(reduction_needed)} "
                 f"to resume trading")

    # Log missed opportunities if any
    if missed_opportunities:
        # Sort by score (best first)
        missed_opportunities.sort(
            key=lambda o: calculate_opportunity_score(o['dip_pct'], o['threshold']),
            reverse=True
        )

        log.warning(f"⚠️  MISSING {len(missed_opportunities)} opportunities "
                   f"due to emergency brake:")

        # Show top 5
        for opp in missed_opportunities[:5]:
            score = calculate_opportunity_score(opp['dip_pct'], opp['threshold'])
            log.warning(f"   💎 {opp['symbol']:6s}: {format_percent(opp['dip_pct'])} dip "
                       f"(score: {score:.2f}x) @ {format_money(opp['current_price'])}")
    else:
        log.info("   ✅ No qualifying opportunities at this time")


# ============================================================================
# INTRADAY VOLATILITY DETECTION
# ============================================================================

def calculate_intraday_drop(bars: List[Dict]) -> Optional[float]:
    """Calculate today's drop from open (negative % if down, None otherwise)."""
    if not bars or len(bars) < 1:
        return None

    try:
        today_bar = bars[-1]  # Most recent bar (today)
        open_price = today_bar['open']
        close_price = today_bar['close']

        if open_price <= 0:
            return None

        intraday_pct = (close_price - open_price) / open_price

        return intraday_pct if intraday_pct < 0 else None  # Only return if down

    except (KeyError, TypeError, ValueError):
        return None


# ============================================================================
# CAPITAL EXHAUSTION VISIBILITY
# ============================================================================

def log_capital_exhaustion(
    skipped_opportunities: List[Dict],
    deployed_this_cycle: float,
    max_margin_pct: float
) -> None:
    """Log opportunities skipped due to capital/margin limits (if any)."""
    if not skipped_opportunities:
        return

    log.warning(f"💰 CAPITAL EXHAUSTED: Skipped {len(skipped_opportunities)} opportunities "
               f"after deploying {format_money(deployed_this_cycle)} this cycle:")

    # Sort by score (best skipped opportunities first)
    skipped_opportunities.sort(
        key=lambda o: calculate_opportunity_score(o['dip_pct'], o['threshold']),
        reverse=True
    )

    # Show top 3 skipped
    for opp in skipped_opportunities[:3]:
        score = calculate_opportunity_score(opp['dip_pct'], opp['threshold'])
        log.warning(f"   ⏭️  {opp['symbol']:6s}: {format_percent(opp['dip_pct'])} dip "
                   f"(score: {score:.2f}x)")

    log.warning(f"   💡 Consider increasing MAX_MARGIN_PCT (current: "
               f"{format_percent(max_margin_pct)}) or freeing up capital")
