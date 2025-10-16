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
    """
    Calculate opportunity score: how much the dip exceeds threshold.

    Args:
        dip_pct: Negative percentage (e.g., -0.0836 for -8.36%)
        threshold: Required dip threshold (e.g., 0.05 for 5%)

    Returns:
        Score >= 1.0, higher = better opportunity
        Example: -8.36% dip with 5% threshold = 1.67x score
    """
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
    """
    Get historical bars for symbol.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        days: Number of days of history to fetch
        data_client: Alpaca data client instance

    Returns:
        List of bar dicts with OHLCV data, or None if failed
        Each dict has: timestamp, open, high, low, close, volume
    """
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
    """
    Get current price from latest quote.

    Args:
        symbol: Stock symbol (e.g., 'AAPL')
        data_client: Alpaca data client instance
        use_bid: If True, use bid price (conservative). Otherwise ask.

    Returns:
        Current price (bid or ask), or None if failed
    """
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
    """
    Scan all symbols for opportunities during emergency brake.

    This is a simplified scan - only checks if dips qualify.
    Does NOT check cooldowns, positions, or place orders.

    Args:
        symbols: List of symbols to scan
        data_client: Alpaca data client
        lookback_days: Days to look back for high
        min_absolute_dip: Minimum dip regardless of threshold (e.g., 0.05)
        get_dip_threshold_func: Function to get per-symbol threshold

    Returns:
        List of opportunity dicts, each containing:
        - symbol: Stock symbol
        - dip_pct: Current dip percentage (negative)
        - threshold: Symbol's configured threshold
        - current_price: Current bid price
    """
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
    """
    Log comprehensive emergency brake status with actionable information.

    Args:
        margin_ratio: Current margin ratio (e.g., 0.1838)
        margin_debt: Current margin debt in dollars
        equity: Account equity in dollars
        target_threshold: Target margin threshold (e.g., 0.15)
        missed_opportunities: List from scan_opportunities_during_brake()
        brake_cycle_count: Number of consecutive brake cycles
    """
    # Calculate how much to liquidate
    target_debt = equity * target_threshold
    reduction_needed = max(0, margin_debt - target_debt)

    # Log brake status
    log.error(f"🛑 EMERGENCY BRAKE (cycle {brake_cycle_count}): "
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
# CAPITAL EXHAUSTION VISIBILITY
# ============================================================================

def log_capital_exhaustion(
    skipped_opportunities: List[Dict],
    deployed_this_cycle: float,
    max_margin_pct: float
) -> None:
    """
    Log opportunities skipped due to capital/margin limits.

    Only logs if opportunities were actually skipped.

    Args:
        skipped_opportunities: List of opportunity dicts that were skipped
        deployed_this_cycle: Dollar amount already deployed this cycle
        max_margin_pct: Current MAX_MARGIN_PCT setting (e.g., 0.20)
    """
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
