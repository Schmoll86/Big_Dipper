#!/usr/bin/env python3
"""Quick script to show current positions"""
import os
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient

load_dotenv()
api_key = os.getenv('ALPACA_KEY')
api_secret = os.getenv('ALPACA_SECRET')
paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'

client = TradingClient(api_key, api_secret, paper=paper)
positions = client.get_all_positions()

# Filter to equity only
equity_positions = [p for p in positions if p.asset_class == 'us_equity']

# Sort by value descending
equity_positions.sort(key=lambda p: float(p.market_value), reverse=True)

print(f"\n{'Symbol':<8} {'Shares':<8} {'Avg Cost':<10} {'Current':<10} {'Value':<12} {'P/L %':<8}")
print("=" * 70)

total_value = 0
for p in equity_positions:
    symbol = p.symbol
    qty = float(p.qty)
    avg_cost = float(p.avg_entry_price)
    current = float(p.current_price)
    value = float(p.market_value)
    pl_pct = ((current - avg_cost) / avg_cost) * 100

    total_value += value

    print(f"{symbol:<8} {qty:<8.0f} ${avg_cost:<9.2f} ${current:<9.2f} ${value:<11.2f} {pl_pct:>6.1f}%")

print("=" * 70)
print(f"{'TOTAL':<8} {'':<8} {'':<10} {'':<10} ${total_value:<11.2f}")
print(f"\nTotal invested: ${total_value:,.2f} across {len(equity_positions)} positions")
