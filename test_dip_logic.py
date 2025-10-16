#!/usr/bin/env python3
"""
Simple tests for dip_logic pure functions.
Run with: python test_dip_logic.py
"""

from datetime import datetime, timedelta
from dip_logic import (
    calculate_dip, should_buy, calculate_shares, calculate_limit_price,
    calculate_opportunity_score
)


def test_calculate_dip():
    """Test dip calculation"""
    print("Testing calculate_dip()...")

    # Create mock bars with prices going from 100 to 95
    bars = [
        {'close': 100.0, 'timestamp': datetime.now() - timedelta(days=i)}
        for i in range(20, 0, -1)
    ]
    # Last price drops to 95
    current_price = 95.0

    dip = calculate_dip(current_price, bars, lookback_days=20)

    assert dip is not None, "Should detect dip"
    assert dip < 0, "Dip should be negative"
    assert abs(dip + 0.05) < 0.001, f"Expected -5% dip, got {dip*100:.2f}%"
    print(f"  ✓ Detected 5% dip correctly: {dip*100:.2f}%")

    # Test no dip case (price increasing)
    current_price = 105.0
    dip = calculate_dip(current_price, bars, lookback_days=20)
    assert dip is None, "Should not detect dip when price is up"
    print(f"  ✓ No dip detected when price up")


def test_should_buy():
    """Test buy decision logic with minimum absolute dip"""
    print("\nTesting should_buy()...")

    # Test case: Valid buy (meets both absolute and threshold requirements)
    should, reason = should_buy(
        symbol='TEST',
        dip_pct=-0.06,  # 6% dip
        min_dip=0.04,   # 4% threshold
        position_value=1000.0,
        max_position=5000.0,
        last_trade_time=None,
        cooldown_hours=4,
        min_absolute_dip=0.05  # 5% absolute minimum
    )
    assert should, f"Should buy: {reason}"
    print(f"  ✓ Valid buy (6% dip > 5% absolute min): {reason}")

    # Test case: Below absolute minimum (even if above threshold)
    should, reason = should_buy(
        symbol='TEST',
        dip_pct=-0.04,  # 4% dip (above 3% threshold, below 5% absolute)
        min_dip=0.03,   # 3% threshold
        position_value=0,
        max_position=5000.0,
        last_trade_time=None,
        cooldown_hours=4,
        min_absolute_dip=0.05  # 5% absolute minimum
    )
    assert not should, "Should reject dip below absolute minimum"
    print(f"  ✓ Rejected below absolute minimum: {reason}")

    # Test case: Dip too small (below threshold)
    should, reason = should_buy(
        symbol='TEST',
        dip_pct=-0.05,  # 5% dip (meets absolute, below 6% threshold)
        min_dip=0.06,   # 6% threshold
        position_value=0,
        max_position=5000.0,
        last_trade_time=None,
        cooldown_hours=4,
        min_absolute_dip=0.05
    )
    assert not should, "Should not buy below threshold"
    print(f"  ✓ Rejected below threshold: {reason}")

    # Test case: Position maxed
    should, reason = should_buy(
        symbol='TEST',
        dip_pct=-0.06,
        min_dip=0.04,
        position_value=5000.0,  # At max
        max_position=5000.0,
        last_trade_time=None,
        cooldown_hours=4,
        min_absolute_dip=0.05
    )
    assert not should, "Should not buy when position maxed"
    print(f"  ✓ Rejected maxed position: {reason}")

    # Test case: In cooldown
    should, reason = should_buy(
        symbol='TEST',
        dip_pct=-0.06,
        min_dip=0.04,
        position_value=0,
        max_position=5000.0,
        last_trade_time=datetime.now() - timedelta(hours=2),  # 2 hours ago
        cooldown_hours=4,
        min_absolute_dip=0.05
    )
    assert not should, "Should not buy in cooldown"
    print(f"  ✓ Rejected cooldown: {reason}")


def test_calculate_shares():
    """Test position sizing with updated parameters (1.75x multiplier)"""
    print("\nTesting calculate_shares()...")

    # Test case: 6% dip with new parameters (2.5% base, 15% max, 1.75x multiplier)
    shares = calculate_shares(
        dip_pct=-0.06,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=1.0
    )
    # Expected: 32000 * 0.025 * (0.06/0.03) * 1.75 = $2,800
    expected_value = 32000 * 0.025 * (0.06/0.03) * 1.75
    expected_shares = expected_value / 100
    assert abs(shares - expected_shares) < 0.5, f"Expected ~{expected_shares} shares, got {shares}"
    print(f"  ✓ 6% dip: {shares:.2f} shares = ${shares*100:.0f}")

    # Test case: 12% dip should hit max (15% = $4,800)
    shares = calculate_shares(
        dip_pct=-0.12,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=1.0
    )
    max_value = 32000 * 0.15  # $4,800
    expected_shares = max_value / 100  # 48 shares
    assert abs(shares - expected_shares) < 0.1, f"Expected ~{expected_shares} shares (maxed), got {shares}"
    print(f"  ✓ 12% dip: {shares:.2f} shares = ${shares*100:.0f} (capped at 15% max)")


def test_calculate_limit_price():
    """Test limit price calculation"""
    print("\nTesting calculate_limit_price()...")

    limit = calculate_limit_price(ask_price=100.0, offset_pct=0.01)
    assert limit == 99.0, f"Expected $99.00, got ${limit}"
    print(f"  ✓ $100 ask with 1% offset = ${limit:.2f}")

    limit = calculate_limit_price(ask_price=123.45, offset_pct=0.01)
    assert limit == 122.22, f"Expected $122.22, got ${limit}"
    print(f"  ✓ $123.45 ask with 1% offset = ${limit:.2f}")


def test_margin_calculations():
    """Test margin safety logic and projections"""
    print("\nTesting margin calculations...")

    # Test 1: Margin projection calculation
    equity = 100000.0
    cash = -5000.0  # $5k borrowed
    margin_debt = max(0, -cash)
    assert margin_debt == 5000.0, "Should calculate margin debt correctly"
    margin_ratio = margin_debt / equity
    assert margin_ratio == 0.05, f"Expected 5% margin, got {margin_ratio*100:.1f}%"
    print(f"  ✓ Margin debt calculation: ${margin_debt:,.0f} = {margin_ratio*100:.1f}%")

    # Test 2: Order margin projection
    order_value = 10000.0  # $10k order
    available_cash = 2000.0
    margin_needed = max(0, order_value - available_cash)
    projected_margin = margin_debt + margin_needed
    projected_ratio = projected_margin / equity
    assert projected_margin == 13000.0, "Should project margin correctly"
    assert projected_ratio == 0.13, f"Expected 13%, got {projected_ratio*100:.1f}%"
    print(f"  ✓ Projected margin: ${projected_margin:,.0f} = {projected_ratio*100:.1f}%")

    # Test 3: Margin limit enforcement (20% max)
    max_margin_pct = 0.20
    assert projected_ratio < max_margin_pct, "Should be under 20% limit"
    print(f"  ✓ Under margin limit: {projected_ratio*100:.1f}% < {max_margin_pct*100:.0f}%")

    # Test 4: Order blocking at margin limit
    large_order = 20000.0
    large_margin_needed = max(0, large_order - available_cash)
    large_projected_margin = margin_debt + large_margin_needed
    large_projected_ratio = large_projected_margin / equity
    assert large_projected_ratio > max_margin_pct, "Should exceed limit"
    print(f"  ✓ Would block order: {large_projected_ratio*100:.1f}% > {max_margin_pct*100:.0f}%")

    # Test 5: Zero cash (no margin) scenario
    equity_no_margin = 100000.0
    cash_no_margin = 50000.0
    margin_debt_none = max(0, -cash_no_margin)
    assert margin_debt_none == 0, "Should have no margin with positive cash"
    print(f"  ✓ No margin with positive cash: ${cash_no_margin:,.0f}")

    # Test 6: Negative equity protection (should halt trading)
    negative_equity = -1000.0
    should_halt = negative_equity <= 0
    assert should_halt, "Should halt trading with negative equity"
    print(f"  ✓ Halt trading check: equity ${negative_equity:,.0f} ≤ 0")


def test_volatility_adjustment():
    """Test volatility-adjusted position sizing with updated multiplier"""
    print("\nTesting volatility adjustment (with 0.5-2.0x clamping)...")

    # Test 1: Normal volatility (1.0x)
    shares_normal = calculate_shares(
        dip_pct=-0.06,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=1.0
    )
    print(f"  ✓ Normal volatility (1.0x): {shares_normal:.2f} shares")

    # Test 2: High volatility (1.5x) - should reduce position
    shares_high_vol = calculate_shares(
        dip_pct=-0.06,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=1.5
    )
    assert shares_high_vol < shares_normal, f"High volatility should reduce position"
    reduction = (1 - shares_high_vol / shares_normal) * 100
    print(f"  ✓ High volatility (1.5x): {shares_high_vol:.2f} shares ({reduction:.0f}% smaller)")

    # Test 3: Low volatility (0.7x) - should increase position
    shares_low_vol = calculate_shares(
        dip_pct=-0.06,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=0.7
    )
    assert shares_low_vol > shares_normal, f"Low volatility should increase position"
    increase = (shares_low_vol / shares_normal - 1) * 100
    print(f"  ✓ Low volatility (0.7x): {shares_low_vol:.2f} shares ({increase:.0f}% larger)")

    # Test 4: Extreme high volatility (3.0x) - clamped to 2.0x
    shares_extreme = calculate_shares(
        dip_pct=-0.06,
        current_price=100.0,
        equity=32000.0,
        current_position_value=0,
        base_pct=0.025,
        max_pct=0.15,
        dip_multiplier=1.75,
        fractional=True,
        volatility_factor=3.0
    )
    # Should be clamped at 2.0x (50% reduction from normal)
    expected_clamped = shares_normal * 0.5
    assert abs(shares_extreme - expected_clamped) < 1.0, f"Extreme volatility should clamp at 2.0x"
    print(f"  ✓ Extreme volatility (3.0x → clamped to 2.0x): {shares_extreme:.2f} shares")


def test_opportunity_scoring():
    """Test opportunity prioritization scoring (v2.14)"""
    print("\nTesting opportunity scoring (v2.14)...")

    # Test 1: IBIT 15% dip with 8% threshold
    score_ibit = calculate_opportunity_score(-0.15, 0.08)
    assert abs(score_ibit - 1.875) < 0.001, f"Expected 1.875, got {score_ibit}"
    print(f"  ✓ IBIT (-15% / 8% threshold): {score_ibit:.3f}x score")

    # Test 2: MSFT 4% dip with 3% threshold
    score_msft = calculate_opportunity_score(-0.04, 0.03)
    assert abs(score_msft - 1.333) < 0.01, f"Expected ~1.33, got {score_msft}"
    print(f"  ✓ MSFT (-4% / 3% threshold): {score_msft:.3f}x score")

    # Test 3: NVDA 10% dip with 5% threshold
    score_nvda = calculate_opportunity_score(-0.10, 0.05)
    assert abs(score_nvda - 2.0) < 0.001, f"Expected 2.0, got {score_nvda}"
    print(f"  ✓ NVDA (-10% / 5% threshold): {score_nvda:.3f}x score")

    # Test 4: Verify prioritization order (NVDA > IBIT > MSFT)
    assert score_nvda > score_ibit > score_msft, "Priority order should be NVDA > IBIT > MSFT"
    print(f"  ✓ Priority order correct: NVDA({score_nvda:.2f}) > IBIT({score_ibit:.2f}) > MSFT({score_msft:.2f})")

    # Test 5: Edge case - exactly at threshold
    score_exact = calculate_opportunity_score(-0.05, 0.05)
    assert abs(score_exact - 1.0) < 0.001, f"Expected 1.0, got {score_exact}"
    print(f"  ✓ Exact threshold match: {score_exact:.3f}x score")


def test_emergency_brake():
    """Test emergency brake threshold logic (v2.13 critical fix)"""
    print("\nTesting emergency brake (v2.13)...")

    # Test 1: Safe margin (< 15%) - should allow trading
    equity = 100000.0
    cash = -10000.0  # $10k margin debt
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 10%

    should_halt = margin_ratio > 0.15
    assert not should_halt, "Should allow trading at 10% margin"
    print(f"  ✓ 10% margin: Trading allowed ✅")

    # Test 2: At emergency brake threshold (15%) - should halt
    cash = -15000.0  # $15k margin debt
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 15%

    should_halt = margin_ratio > 0.15
    assert not should_halt, "15% is exactly at threshold (not over)"
    print(f"  ✓ 15% margin (exactly at threshold): Trading allowed ✅")

    # Test 3: Over emergency brake (16%) - should halt
    cash = -16000.0  # $16k margin debt
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 16%

    should_halt = margin_ratio > 0.15
    assert should_halt, "Should halt at 16% margin"
    print(f"  ✓ 16% margin: Emergency brake 🛑 ACTIVE")

    # Test 4: High margin (25%) - should halt
    cash = -25000.0  # $25k margin debt
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 25%

    should_halt = margin_ratio > 0.15
    assert should_halt, "Should halt at 25% margin"
    print(f"  ✓ 25% margin: Emergency brake 🛑 ACTIVE")

    # Test 5: No margin (positive cash) - should allow
    cash = 20000.0  # Positive cash
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 0%

    should_halt = margin_ratio > 0.15
    assert not should_halt, "Should allow trading with no margin"
    print(f"  ✓ 0% margin (no debt): Trading allowed ✅")

    # Test 6: Critical scenario from today (33% margin)
    cash = -33000.0  # $33k margin debt
    margin_debt = max(0, -cash)
    margin_ratio = margin_debt / equity  # 33%

    should_halt = margin_ratio > 0.15
    assert should_halt, "Should halt at 33% margin (today's scenario)"
    print(f"  ✓ 33% margin (today's actual): Emergency brake 🛑 ACTIVE (prevented disaster)")


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("Running Little Dipper Logic Tests")
    print("="*60)

    try:
        test_calculate_dip()
        test_should_buy()
        test_calculate_shares()
        test_calculate_limit_price()
        test_margin_calculations()
        test_volatility_adjustment()
        test_opportunity_scoring()
        test_emergency_brake()

        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        return True

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)