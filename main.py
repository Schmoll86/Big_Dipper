#!/usr/bin/env python3
"""
Big Dipper - Simplified Buy The Dip Trading System

Forked from Little Dipper v2.15 with enhanced operational visibility.

Does one thing well: Buy stocks when they dip significantly from recent highs.
New in v2.16: See what you're missing during trading halts.

Philosophy:
- Alpaca API is the single source of truth (no database)
- Every cycle recalculates from scratch (stateless)
- Fail fast and restart (systemd/docker)
- Simple is better than complex
- Visible is better than silent

Author: Enhanced from Little Dipper v2.15
"""

import time
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.timeframe import TimeFrame
from alpaca.data.requests import (
    StockBarsRequest, StockLatestQuoteRequest
)
from alpaca.trading.requests import LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from config import config
from dip_logic import (
    calculate_dip, should_buy, calculate_shares,
    calculate_limit_price, calculate_opportunity_score
)
from utils import (
    format_money, format_percent, get_bars, get_current_price,
    scan_opportunities_during_brake, log_brake_status, log_capital_exhaustion
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


class LittleDipper:
    """
    Buy The Dip - Simplified Trading System

    State stored in memory (lost on restart):
    - last_trade_times: When we last traded each symbol
    - pending_orders: Orders we've placed but not yet filled

    All other state comes from Alpaca API on each cycle.
    """

    def __init__(self):
        """Initialize Alpaca clients and minimal state"""
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            log.error(f"Configuration error: {e}")
            sys.exit(1)

        # Initialize Alpaca clients (direct SDK usage) with timeout for network resilience
        try:
            self.trading = TradingClient(
                config.ALPACA_KEY,
                config.ALPACA_SECRET,
                paper=config.PAPER
            )
            self.data = StockHistoricalDataClient(
                config.ALPACA_KEY,
                config.ALPACA_SECRET
            )
        except Exception as e:
            log.error(f"Failed to initialize Alpaca clients: {e}")
            sys.exit(1)

        # Minimal in-memory state (lost on restart, that's OK)
        self.last_trade_times: Dict[str, datetime] = {}
        self.pending_orders: Dict[str, dict] = {}
        self._retry_count: int = 0
        self._recent_trades: Dict[str, float] = {}
        self._cycle_order_value: float = 0.0
        self._brake_cycle_count: int = 0  # Track consecutive emergency brake cycles

        # Log startup
        mode = "PAPER" if config.PAPER else "LIVE"
        log.info(f"🌟 Big Dipper v2.16 started in {mode} mode")
        log.info(f"📊 Watching {len(config.SYMBOLS)} symbols: {', '.join(config.SYMBOLS)}")
        default_dip = config.DIP_THRESHOLDS.get('DEFAULT', 0.04)
        dip_range = f"{min(config.DIP_THRESHOLDS.values())*100:.1f}%-{max(config.DIP_THRESHOLDS.values())*100:.1f}%"
        log.info(f"📉 Default dip: {format_percent(default_dip)}, Range: {dip_range}, "
                f"Base position: {format_percent(config.BASE_POSITION_PCT)}")

    def run(self):
        """Main event loop - runs forever"""
        log.info("🚀 Starting main loop...")

        cycle_count = 0

        while True:
            try:
                cycle_count += 1
                cycle_start = time.time()

                log.info(f"\n{'='*60}")
                log.info(f"Cycle #{cycle_count} - {datetime.now().strftime('%H:%M:%S')}")
                log.info(f"{'='*60}")

                # 1. Check market hours (including extended hours)
                clock = self.trading.get_clock()
                session_type, session_name = self._get_market_session(clock)

                if session_type == 'closed':
                    next_open = clock.next_open.strftime('%Y-%m-%d %H:%M ET')
                    log.info(f"💤 Market closed. Next open: {next_open}")
                    log.info(f"Sleeping {config.SCAN_INTERVAL_SEC} seconds...\n")
                    time.sleep(config.SCAN_INTERVAL_SEC)
                    continue

                # Log current session
                if session_type == 'extended':
                    log.info(f"🌙 {session_name} (extended hours)")
                else:
                    log.info(f"☀️ {session_name} (regular hours)")

                # Trade all symbols all the time
                symbols_to_trade = config.SYMBOLS
                is_extended_hours = (session_type == 'extended')

                # 2. Get account state (fresh from Alpaca)
                self._cycle_order_value = 0.0
                account = self.trading.get_account()
                equity = float(account.equity)
                cash = float(account.cash)

                # Calculate margin status (with negative equity protection)
                if equity <= 0:
                    log.error(f"❌ CRITICAL: Account equity is ${equity:.2f} (≤ 0) - halting trading")
                    return False

                # Calculate actual margin debt (negative cash = borrowed funds)
                # Note: maintenance_margin is collateral requirement, NOT actual debt
                margin_debt = max(0, -cash)
                margin_ratio = margin_debt / equity if equity > 0 else 0

                # SAFETY CHECK: If already near margin limit at cycle START, skip all trading
                # This prevents adding margin on top of existing margin debt
                if config.USE_MARGIN and margin_ratio > config.MARGIN_SAFETY_THRESHOLD:
                    # Increment brake counter
                    self._brake_cycle_count += 1

                    # Scan for opportunities every 10 cycles (10 minutes)
                    # Stop scanning after 30 cycles (30 minutes) to prevent log spam
                    missed_opps = []
                    if 10 <= self._brake_cycle_count <= 30 and self._brake_cycle_count % 10 == 0:
                        log.info("📊 Scanning for missed opportunities (brake persists)...")
                        missed_opps = scan_opportunities_during_brake(
                            symbols_to_trade,
                            self.data,
                            config.LOOKBACK_DAYS,
                            config.MIN_ABSOLUTE_DIP,
                            config.get_dip_threshold
                        )

                    # Log comprehensive brake status
                    log_brake_status(
                        margin_ratio,
                        margin_debt,
                        equity,
                        config.MARGIN_SAFETY_THRESHOLD,
                        missed_opps,
                        self._brake_cycle_count
                    )

                    log.error(f"   HALTING ALL TRADING this cycle")
                    time.sleep(config.SCAN_INTERVAL_SEC)
                    continue
                else:
                    # Reset brake counter when margin healthy
                    self._brake_cycle_count = 0

                if config.USE_MARGIN:
                    log.info(f"💰 Account: {format_money(equity)} equity, "
                            f"{format_money(cash)} cash, "
                            f"Margin: {format_percent(margin_ratio)}/{format_percent(config.MAX_MARGIN_PCT)}")

                    if margin_ratio > config.MAX_MARGIN_PCT - 0.05:
                        log.warning(f"⚠️  APPROACHING MARGIN LIMIT")
                else:
                    log.info(f"💰 Account: {format_money(equity)} equity, "
                            f"{format_money(cash)} cash ({format_percent(cash/equity)})")

                # 3. Get current positions (fresh from Alpaca)
                # Filter to equity positions only (exclude options/crypto if present)
                try:
                    try:
                        all_positions = self.trading.get_all_positions()
                    except Exception as validation_error:
                        # SDK validation fails when options positions exist
                        log.error(f"❌ POSITION TRACKING FAILED (likely due to options positions)")
                        log.error(f"   SDK error: {validation_error}")
                        log.error(f"⏸️  HALTING ALL TRADING this cycle to prevent over-allocation")
                        log.error(f"   System will automatically resume when positions load successfully")
                        log.error(f"   Next retry in {config.SCAN_INTERVAL_SEC} seconds...")

                        # Sleep and skip this entire cycle (do NOT trade blind)
                        time.sleep(config.SCAN_INTERVAL_SEC)
                        continue  # Go to next cycle

                    # Defensive filtering - handle each position individually
                    equity_positions = []
                    options_count = 0

                    for p in all_positions:
                        try:
                            # Safely access asset_class (avoid Pydantic validation errors)
                            asset_class = getattr(p, 'asset_class', None)

                            # Only include equity positions in tracking
                            if asset_class == 'us_equity':
                                equity_positions.append(p)
                            elif asset_class == 'us_option':
                                options_count += 1
                        except Exception:
                            # Skip positions that can't be validated
                            continue

                    # Log options detection once per session
                    if options_count > 0 and not hasattr(self, '_options_logged'):
                        log.info(f"ℹ️  Detected {options_count} options position(s) - excluded from Little Dipper")
                        self._options_logged = True

                    # Filter out collateral bonds (reserves for manual trading)
                    tradeable_positions = [p for p in equity_positions
                                          if p.symbol not in config.COLLATERAL_POSITIONS]
                    position_map = {p.symbol: float(p.market_value) for p in tradeable_positions}

                except Exception as e:
                    # Catch-all for any other position-related errors
                    log.error(f"❌ UNEXPECTED ERROR getting positions: {e}")
                    log.error(f"⏸️  HALTING ALL TRADING this cycle for safety")
                    log.error(f"   Next retry in {config.SCAN_INTERVAL_SEC} seconds...")
                    time.sleep(config.SCAN_INTERVAL_SEC)
                    continue  # Go to next cycle

                if tradeable_positions:
                    total_invested = sum(position_map.values())
                    log.info(f"📊 Positions: {len(tradeable_positions)} stocks, "
                            f"{format_money(total_invested)} invested "
                            f"({format_percent(total_invested/equity)})")
                else:
                    log.info(f"📊 Positions: None")

                # Log margin debt if using margin (removed misleading diagnostics)

                # 4. Scan for opportunities (2-pass: scan, then prioritize, then execute)
                # PASS 1: Scan all symbols and collect qualifying opportunities
                qualifying_opportunities = []
                largest_dip = (None, 0.0)

                for symbol in symbols_to_trade:
                    result = self.scan_symbol(symbol, equity, cash, position_map, is_extended_hours)
                    if result:
                        qualifying_opportunities.append(result)
                        dip_pct = result['dip_pct']
                        if dip_pct < largest_dip[1]:
                            largest_dip = (symbol, dip_pct)

                # PASS 2: Prioritize by opportunity quality (best dips first)
                if qualifying_opportunities:
                    qualifying_opportunities.sort(
                        key=lambda opp: calculate_opportunity_score(opp['dip_pct'], opp['threshold']),
                        reverse=True  # Best opportunities first
                    )

                # Log summary
                summary = f"🔍 Scan complete: {len(qualifying_opportunities)} opportunities found"
                if largest_dip[0]:
                    summary += f" | Largest dip: {largest_dip[0]} {format_percent(largest_dip[1])}"
                if qualifying_opportunities:
                    # Show top 3 opportunities by score
                    top_3 = qualifying_opportunities[:3]
                    scores = [calculate_opportunity_score(o['dip_pct'], o['threshold']) for o in top_3]
                    top_symbols = [f"{o['symbol']}({s:.2f}x)" for o, s in zip(top_3, scores)]
                    summary += f" | Priority: {', '.join(top_symbols)}"
                log.info(summary)

                # PASS 3: Execute orders in priority order
                executed_count = 0
                skipped_capital = []

                for opp in qualifying_opportunities:
                    success, reason = self.execute_opportunity(opp, equity, cash, position_map, is_extended_hours, account)
                    if success:
                        executed_count += 1
                    elif reason == 'capital' and self._cycle_order_value > 0:
                        # Only track as capital exhaustion if we already executed some orders
                        skipped_capital.append(opp)
                    # Other failures (too_small, error) are ignored

                # Log capital exhaustion if it occurred
                if skipped_capital:
                    log_capital_exhaustion(
                        skipped_capital,
                        self._cycle_order_value,
                        config.MAX_MARGIN_PCT
                    )

                # Reset retry count on successful cycle
                self._retry_count = 0

                # 5. Manage pending orders
                self.manage_pending_orders()

                # 6. Sleep until next cycle
                elapsed = time.time() - cycle_start
                sleep_time = max(0, config.SCAN_INTERVAL_SEC - elapsed)
                log.info(f"⏱️  Cycle took {elapsed:.1f}s, sleeping {sleep_time:.1f}s...\n")
                time.sleep(sleep_time)

            except KeyboardInterrupt:
                log.info("\n👋 Shutting down gracefully...")
                break
            except Exception as e:
                # Exponential backoff for network resilience: 10s, 20s, 40s, max 60s
                wait_time = min(10 * (2 ** self._retry_count), 60)
                log.error(f"❌ Cycle error: {e}", exc_info=True)
                log.warning(f"⏸️  Pausing {wait_time}s before retry (attempt {self._retry_count + 1})...")
                self._retry_count += 1
                time.sleep(wait_time)

        log.info("🌙 Little Dipper stopped")

    def _get_market_session(self, clock) -> tuple[str, str]:
        """
        Determine current market session including extended hours.

        Returns:
            (session_type, session_name) where session_type is 'regular', 'extended', or 'closed'
        """
        from datetime import datetime
        import pytz

        # Get current time in ET
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        current_time = now_et.time()

        # Check if market is closed for the day
        if not clock.is_open:
            # Check if we're in extended hours
            from datetime import time as dt_time

            # Pre-market: 4:00 AM - 9:30 AM ET
            if dt_time(4, 0) <= current_time < dt_time(9, 30):
                return ('extended', 'Pre-Market')

            # After-hours: 4:00 PM - 8:00 PM ET
            elif dt_time(16, 0) <= current_time < dt_time(20, 0):
                return ('extended', 'After-Hours')

            # Closed
            else:
                return ('closed', 'Closed')

        # Regular market hours
        return ('regular', 'Regular Hours')

    def scan_symbol(
        self,
        symbol: str,
        equity: float,
        cash: float,
        position_map: Dict[str, float],
        is_extended_hours: bool = False
    ) -> dict:
        """
        Scan a single symbol and return opportunity data if it qualifies.

        Returns:
            dict with opportunity data if qualifies, None otherwise
        """
        try:
            # Skip collateral positions (don't trade these)
            if symbol in config.COLLATERAL_POSITIONS:
                return None

            # Get historical bars for 20-day high calculation
            bars = get_bars(symbol, days=config.LOOKBACK_DAYS + 1, data_client=self.data)
            if not bars:
                return None

            # Get CURRENT price (not stale daily bar close)
            current_price = get_current_price(symbol, data_client=self.data)
            if not current_price:
                # Fallback to last bar close if quote unavailable
                current_price = bars[-1]['close']

            # Calculate volatility factor (simplified using high-low range)
            recent_ranges = [(bar['high'] - bar['low']) / bar['close']
                           for bar in bars[-21:-1] if bar['close'] > 0]
            avg_daily_range = sum(recent_ranges) / len(recent_ranges) if recent_ranges else 0.02
            volatility_factor = avg_daily_range / 0.02  # Normalize to 2% baseline

            # Calculate dip from 20-day high
            dip_pct = calculate_dip(current_price, bars, config.LOOKBACK_DAYS)
            if dip_pct is None:
                return None

            # Calculate intraday drop (for volatile tickers only)
            intraday_multiplier = 1.0
            intraday_drop_pct = None
            if symbol in config.VOLATILE_TICKERS:
                from utils import calculate_intraday_drop
                intraday_drop_pct = calculate_intraday_drop(bars)
                if intraday_drop_pct and abs(intraday_drop_pct) >= config.INTRADAY_DROP_THRESHOLD:
                    intraday_multiplier = config.INTRADAY_MULTIPLIER

            # Get stock-specific dip threshold
            min_dip_threshold = config.get_dip_threshold(symbol)

            # Log dip percentage for debugging
            if dip_pct <= -min_dip_threshold:
                log.debug(f"{symbol}: {format_percent(dip_pct)} from {config.LOOKBACK_DAYS}d high ✓ (threshold: {format_percent(-min_dip_threshold)})")
            else:
                log.debug(f"{symbol}: {format_percent(dip_pct)} from {config.LOOKBACK_DAYS}d high (need {format_percent(-min_dip_threshold)})")

            # Found a dip - check if we should buy
            current_position_value = position_map.get(symbol, 0)
            max_position_value = equity * config.MAX_POSITION_PCT

            last_trade = self.last_trade_times.get(symbol)

            # Backup cooldown check using local cache
            last_trade_timestamp = self._recent_trades.get(symbol, 0)
            if time.time() - last_trade_timestamp < config.COOLDOWN_HOURS * 3600:
                log.debug(f"{symbol}: Cooldown active (local cache)")
                return None

            should, reason = should_buy(
                symbol, dip_pct, min_dip_threshold,
                current_position_value, max_position_value,
                last_trade, config.COOLDOWN_HOURS,
                config.MIN_ABSOLUTE_DIP
            )

            if not should:
                log.debug(f"{symbol}: {reason}")
                return None

            # Qualifies! Return opportunity data for prioritization
            return {
                'symbol': symbol,
                'dip_pct': dip_pct,
                'threshold': min_dip_threshold,
                'current_price': current_price,
                'volatility_factor': volatility_factor,
                'intraday_multiplier': intraday_multiplier,
                'intraday_drop_pct': intraday_drop_pct,
                'current_position_value': current_position_value,
                'max_position_value': max_position_value
            }

        except Exception as e:
            log.error(f"{symbol}: Scan error - {e}")
            return None

    def execute_opportunity(
        self,
        opp: dict,
        equity: float,
        cash: float,
        position_map: Dict[str, float],
        is_extended_hours: bool = False,
        account = None
    ) -> Tuple[bool, str]:
        """
        Execute an order for a qualified opportunity.

        Returns:
            Tuple of (success: bool, reason: str)
            - (True, 'executed'): Order placed successfully
            - (False, 'too_small'): Position size < 0.01 shares
            - (False, 'capital'): Margin or buying power limit hit
            - (False, 'error'): Exception occurred
        """
        try:
            symbol = opp['symbol']
            dip_pct = opp['dip_pct']
            current_price = opp['current_price']
            volatility_factor = opp['volatility_factor']
            intraday_multiplier = opp.get('intraday_multiplier', 1.0)
            intraday_drop_pct = opp.get('intraday_drop_pct')
            current_position_value = opp['current_position_value']
            threshold = opp['threshold']

            # Calculate position size
            shares = calculate_shares(
                dip_pct, current_price, equity, current_position_value,
                config.BASE_POSITION_PCT, config.MAX_POSITION_PCT,
                config.DIP_MULTIPLIER, fractional=True,
                volatility_factor=volatility_factor,
                intraday_multiplier=intraday_multiplier
            )

            if shares < 0.01:
                log.debug(f"{symbol}: Position size too small ({shares:.4f} shares)")
                return (False, 'too_small')

            order_value = shares * current_price

            # Check margin limits
            if config.USE_MARGIN:
                projected_cash = cash - self._cycle_order_value - order_value
                margin_debt = max(0, -projected_cash)
                projected_ratio = margin_debt / equity if equity > 0 else 0

                if projected_ratio > config.MAX_MARGIN_PCT:
                    log.warning(f"{symbol}: Would exceed margin limit "
                               f"({format_percent(projected_ratio)} > {format_percent(config.MAX_MARGIN_PCT)})")
                    log.debug(f"  Pending this cycle: {format_money(self._cycle_order_value)}")
                    return (False, 'capital')

                buying_power = float(account.regt_buying_power)
                if order_value > buying_power:
                    log.warning(f"{symbol}: Insufficient buying power "
                               f"(need {format_money(order_value)}, have {format_money(buying_power)})")
                    return (False, 'capital')

            # Place order!
            score = calculate_opportunity_score(dip_pct, threshold)
            log.info(f"💎 {symbol} BUY: {format_percent(dip_pct)} dip @ {format_money(current_price)} (score: {score:.2f}x)")

            # Show intraday drop if multiplier was applied
            if intraday_multiplier > 1.0 and intraday_drop_pct:
                log.info(f"   📊 Filters: VolAdj {volatility_factor:.1f}x, Threshold: {format_percent(threshold)}, Intraday: {format_percent(intraday_drop_pct)} → {intraday_multiplier:.1f}x size")
            else:
                log.info(f"   📊 Filters: VolAdj {volatility_factor:.1f}x, Threshold: {format_percent(threshold)}")

            self._place_order(symbol, shares, current_price, is_extended_hours)
            self._cycle_order_value += order_value
            return (True, 'executed')

        except Exception as e:
            log.error(f"{opp['symbol']}: Execution error - {e}")
            return (False, 'error')

    def _place_order(self, symbol: str, shares: float, current_price: float, is_extended_hours: bool = False):
        """Place limit order with simple pricing"""
        try:
            # Get current quote for limit pricing
            quote_request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote_response = self.data.get_stock_latest_quote(quote_request)

            if symbol not in quote_response:
                log.error(f"{symbol}: No quote available")
                return

            quote = quote_response[symbol]
            ask_price = float(quote.ask_price) if quote.ask_price > 0 else float(quote.bid_price)
            bid_price = float(quote.bid_price) if quote.bid_price > 0 else 0

            if ask_price <= 0:
                log.error(f"{symbol}: No valid quote price (ask={quote.ask_price}, bid={quote.bid_price})")
                return

            # Adaptive pricing: bid-based in extended hours, ask-based in regular hours
            if is_extended_hours and bid_price > 0:
                # Extended hours: bid + 0.1% (meet the spread instead of crossing it)
                limit_price = round(bid_price * 1.001, 2)
            else:
                # Regular hours: ask - 0.5% (standard approach)
                limit_price = calculate_limit_price(ask_price, config.LIMIT_OFFSET_PCT)

            # Submit order (with extended hours flag if applicable)
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=shares,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price,
                extended_hours=is_extended_hours
            )

            order = self.trading.submit_order(order_request)

            # Track order
            self.pending_orders[order.id] = {
                'symbol': symbol,
                'shares': shares,
                'limit': limit_price,
                'submitted': datetime.now()
            }

            # Update last trade time (both methods for redundancy)
            self.last_trade_times[symbol] = datetime.now()
            self._recent_trades[symbol] = time.time()  # Local cache backup

            order_value = shares * limit_price
            log.info(f"✅ BUY {symbol}: {shares:.4f} shares @ {format_money(limit_price)} "
                    f"= {format_money(order_value)} (order {order.id})")

        except Exception as e:
            log.error(f"❌ Failed to place order for {symbol}: {e}")

    def manage_pending_orders(self):
        """Simple order management: cancel old unfilled orders"""
        try:
            # Get all open orders from Alpaca
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus

            order_request = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            open_orders = self.trading.get_orders(filter=order_request)

            for order in open_orders:
                order_id = str(order.id)

                # Check if we're tracking this order
                if order_id not in self.pending_orders:
                    continue

                tracked = self.pending_orders[order_id]
                age_minutes = (datetime.now() - tracked['submitted']).total_seconds() / 60

                # Cancel orders older than timeout
                if age_minutes > config.ORDER_TIMEOUT_MINUTES:
                    try:
                        self.trading.cancel_order_by_id(order_id)
                        log.warning(f"⏱️  Cancelled {order.symbol} order {order_id} "
                                   f"after {age_minutes:.0f} minutes")
                    except Exception as e:
                        log.error(f"Failed to cancel order {order_id}: {e}")

                    del self.pending_orders[order_id]

            # Clean up tracking for filled/cancelled orders
            all_order_ids = {str(o.id) for o in open_orders}
            completed = set(self.pending_orders.keys()) - all_order_ids

            for order_id in completed:
                tracked = self.pending_orders[order_id]
                log.info(f"✅ Order completed: {tracked['symbol']} {order_id}")
                del self.pending_orders[order_id]

        except Exception as e:
            log.error(f"Order management error: {e}")


def main():
    """Entry point"""
    try:
        dipper = LittleDipper()
        dipper.run()
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()