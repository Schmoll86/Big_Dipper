"""
Little Dipper - Dip Detection and Position Sizing Logic
Pure functions with no side effects - easy to test and reason about.
"""

from datetime import datetime
from typing import Optional, List, Dict


def calculate_dip(
    current_price: float,
    bars: List[Dict],
    lookback_days: int = 20
) -> Optional[float]:
    """
    Calculate dip as percentage from recent high.

    Args:
        current_price: Current market price
        bars: List of OHLCV bar dicts with 'close' key
        lookback_days: Number of days to look back for high

    Returns:
        Negative percentage (e.g., -0.05 for 5% dip) or None if insufficient data
    """
    if not bars or len(bars) < lookback_days:
        return None

    try:
        recent_high = max(bar['close'] for bar in bars[-lookback_days:])

        if recent_high <= 0:
            return None

        dip_pct = (current_price - recent_high) / recent_high

        return dip_pct if dip_pct < 0 else None

    except (KeyError, TypeError, ValueError):
        return None


def should_buy(
    symbol: str,
    dip_pct: float,
    min_dip: float,
    position_value: float,
    max_position: float,
    last_trade_time: Optional[datetime],
    cooldown_hours: int,
    min_absolute_dip: float = 0.05
) -> tuple[bool, str]:
    """
    Decide if we should buy based on simple rules.

    Args:
        symbol: Stock symbol
        dip_pct: Dip percentage (negative number)
        min_dip: Minimum dip required to trade (stock-specific threshold)
        position_value: Current position value in dollars
        max_position: Maximum position value allowed
        last_trade_time: When we last traded this symbol
        cooldown_hours: Minimum hours between trades
        min_absolute_dip: Minimum absolute dip required regardless of threshold

    Returns:
        (should_buy: bool, reason: str)
    """
    # Check 1: Meets minimum absolute dip (prevents threshold gaming)
    if abs(dip_pct) < min_absolute_dip:
        return False, f"Dip {dip_pct:.1%} < absolute min {min_absolute_dip:.1%}"

    # Check 2: Dip big enough for stock-specific threshold?
    if abs(dip_pct) < min_dip:
        return False, f"Dip {dip_pct:.1%} < threshold {min_dip:.1%}"

    # Check 3: Position not maxed?
    if position_value >= max_position:
        return False, f"Position ${position_value:.0f} at max ${max_position:.0f}"

    # Check 4: Dynamic cooldown - deeper dips get shorter cooldowns
    effective_cooldown = cooldown_hours
    if abs(dip_pct) > 0.07:
        effective_cooldown = max(1, cooldown_hours // 2)

    if last_trade_time:
        hours_since = (datetime.now() - last_trade_time).total_seconds() / 3600
        if hours_since < effective_cooldown:
            return False, f"Cooldown: {hours_since:.1f}h < {effective_cooldown}h"

    return True, "OK"


def calculate_shares(
    dip_pct: float,
    current_price: float,
    equity: float,
    current_position_value: float,
    base_pct: float,
    max_pct: float,
    dip_multiplier: float,
    fractional: bool = True,
    volatility_factor: float = 1.0  # New: volatility adjustment
) -> float:
    """
    Calculate shares to buy: bigger dip = bigger position, adjusted for volatility.

    Linear scaling formula with volatility adjustment:
        size = base_pct * (abs(dip_pct) / 0.03) * dip_multiplier * (1 / volatility_factor)

    Examples (with base_pct=0.02, dip_multiplier=2.0):
        3% dip, normal vol → 2% * (0.03/0.03) * 2.0 * 1.0 = 4% position
        6% dip, normal vol → 2% * (0.06/0.03) * 2.0 * 1.0 = 8% position
        6% dip, high vol (1.5x) → 2% * (0.06/0.03) * 2.0 * 0.67 = 5.3% position

    Args:
        dip_pct: Dip percentage (negative)
        current_price: Stock price
        equity: Account equity
        current_position_value: Current position value
        base_pct: Base position size as % of equity
        max_pct: Maximum position size as % of equity
        dip_multiplier: Multiplier for dip sizing
        fractional: Allow fractional shares
        volatility_factor: Stock's volatility relative to normal (new)

    Returns:
        Number of shares to buy
    """
    # Calculate size multiplier based on dip severity
    dip_ratio = abs(dip_pct) / 0.03  # Normalize to 3% baseline
    size_multiplier = dip_ratio * dip_multiplier
    
    # Apply volatility adjustment - reduce size for high-volatility stocks
    safe_vol_factor = max(0.5, min(2.0, volatility_factor)) if volatility_factor > 0 else 1.0
    vol_adjusted_multiplier = size_multiplier / safe_vol_factor

    # Calculate target position value
    target_value = equity * base_pct * vol_adjusted_multiplier

    # Cap at maximum position size
    max_value = equity * max_pct
    target_value = min(target_value, max_value)

    # Only add to existing position (don't overshoot max)
    additional_value = max(0, target_value - current_position_value)

    # Convert to shares
    if additional_value < 100:  # Less than $100 to deploy (min order size)
        return 0

    shares = additional_value / current_price

    # Round based on fractional setting
    return shares if fractional else int(shares)


def calculate_limit_price(ask_price: float, offset_pct: float) -> float:
    """
    Calculate limit price below ask to improve fill probability.

    Args:
        ask_price: Current ask price
        offset_pct: Percentage below ask (e.g., 0.01 for 1%)

    Returns:
        Limit price rounded to 2 decimals

    Example:
        ask = $100, offset = 0.01 → $99.00
    """
    return round(ask_price * (1 - offset_pct), 2)




def calculate_opportunity_score(dip_pct: float, threshold: float) -> float:
    """
    Calculate opportunity quality score.

    Higher score = better opportunity (larger dip relative to threshold)

    Args:
        dip_pct: Actual dip percentage (negative, e.g., -0.15 for 15% dip)
        threshold: Required threshold for this stock (e.g., 0.08 for 8%)

    Returns:
        Score representing how many multiples of threshold was breached

    Examples:
        IBIT: -15% / 8% threshold = 1.875 score
        MSFT: -4% / 3% threshold = 1.33 score
        NVDA: -10% / 5% threshold = 2.0 score
    """
    return abs(dip_pct) / threshold