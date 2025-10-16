#!/usr/bin/env python3
"""Quick script to check current positions"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()

# Initialize client
trading = TradingClient(
    api_key=os.getenv('ALPACA_KEY'),
    secret_key=os.getenv('ALPACA_SECRET'),
    paper=(os.getenv('ALPACA_PAPER', 'true').lower() == 'true')
)

# Get account info
account = trading.get_account()
equity = float(account.equity)

print(f"\n💰 Account: ${equity:,.2f} equity, ${float(account.cash):,.2f} cash")
print(f"📊 Buying Power: ${float(account.buying_power):,.2f}")

# Get all positions
positions = trading.get_all_positions()

# Filter to equity only
equity_positions = [p for p in positions if p.asset_class == 'us_equity']

print(f"\n📍 Total Positions: {len(equity_positions)}")
print("-" * 70)

# Sort by market value (largest first)
equity_positions.sort(key=lambda p: float(p.market_value), reverse=True)

total_invested = 0
for pos in equity_positions:
    symbol = pos.symbol
    qty = float(pos.qty)
    market_value = float(pos.market_value)
    pct_of_equity = (market_value / equity) * 100
    unrealized_pl = float(pos.unrealized_pl)
    unrealized_plpc = float(pos.unrealized_plpc) * 100

    total_invested += market_value

    print(f"{symbol:6s} | {qty:6.0f} shares | ${market_value:9,.2f} | {pct_of_equity:5.2f}% | P/L: {unrealized_plpc:+6.2f}%")

pct_invested = (total_invested / equity) * 100
print("-" * 70)
print(f"TOTAL INVESTED: ${total_invested:,.2f} ({pct_invested:.2f}% of equity)")

# Calculate margin status
cash = float(account.cash)
margin_debt = max(0, -cash)
margin_ratio = margin_debt / equity if equity > 0 else 0

print(f"\n💰 MARGIN STATUS:")
print(f"Cash: ${cash:,.2f}")
print(f"Margin Debt: ${margin_debt:,.2f}")
print(f"Margin Ratio: {margin_ratio*100:.2f}%")
print(f"Emergency Brake: {'🛑 ACTIVE' if margin_ratio > 0.15 else '✅ OK'} (15% threshold)")
print(f"Max Margin: {'⚠️  EXCEEDED' if margin_ratio > 0.20 else '✅ OK'} (20% limit)")
