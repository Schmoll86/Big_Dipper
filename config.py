"""
Big Dipper - Configuration
Simple configuration using environment variables and constants.
Fork of Little Dipper v2.15 with enhanced operational visibility.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    """Trading system configuration - simple and clear"""

    # ===== ALPACA CREDENTIALS =====
    ALPACA_KEY: str = os.getenv('ALPACA_KEY', '')
    ALPACA_SECRET: str = os.getenv('ALPACA_SECRET', '')
    PAPER: bool = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'

    # ===== SYMBOLS TO TRADE =====
    SYMBOLS: List[str] = field(default_factory=lambda: [
        'NVDA', 'AVGO', 'AMD', 'TSM', 'MRVL', 'TER',
        'MSFT', 'META', 'ORCL', 'NOW', 'PLTR',
        'ANET', 'DELL',
        'ETN', 'PWR', 'CEG', 'GEV', 'NEE', 'ABB',
        'EQIX', 'DLR', 'AMT', 'CCI',
        'LMT', 'NOC', 'RTX', 'GD', 'HII', 'HWM', 'AVAV', 'KTOS',
        'ISRG', 'LLY', 'FIGR',
        'VMC', 'MLM', 'MP',
        'XYL', 'AWK', 'WTRG',
        'GLD', 'URNM',
        'IBIT', 'ARKK'
    ])

    # ===== DIP DETECTION =====
    # Effective threshold = max(MIN_ABSOLUTE_DIP, stock_threshold)
    DIP_THRESHOLDS: dict = field(default_factory=lambda: {
        'DEFAULT': 0.04,        # 4% → effective 5% (overridden by MIN_ABSOLUTE_DIP)
        'MSFT': 0.03, 'LLY': 0.03, 'GLD': 0.03,          # 3% → effective 5%
        'NVDA': 0.05, 'AMD': 0.05, 'PLTR': 0.06,         # 5-6% → as specified
        'MRVL': 0.05, 'DELL': 0.05, 'FIGR': 0.07,        # 5-7% → as specified
        'IBIT': 0.08, 'ARKK': 0.08, 'URNM': 0.07,        # 7-8% → as specified
        'AVAV': 0.06, 'KTOS': 0.07, 'MP': 0.07,          # 6-7% → as specified
        'CEG': 0.03, 'NEE': 0.03, 'AWK': 0.03,           # 3% → effective 5%
        'WTRG': 0.03, 'EQIX': 0.035, 'DLR': 0.035,       # 3-3.5% → effective 5%
    })
    LOOKBACK_DAYS: int = 20

    # ===== POSITION SIZING =====
    BASE_POSITION_PCT: float = 0.025
    MAX_POSITION_PCT: float = 0.15
    DIP_MULTIPLIER: float = 1.75
    MIN_ABSOLUTE_DIP: float = 0.05  # 5% floor (prevents threshold gaming)

    # ===== RISK LIMITS =====
    MAX_TOTAL_POSITIONS: int = 10

    # ===== MARGIN SETTINGS =====
    USE_MARGIN: bool = True
    MAX_MARGIN_PCT: float = 0.20
    MARGIN_SAFETY_THRESHOLD: float = 0.15
    COLLATERAL_POSITIONS: List[str] = field(default_factory=lambda: [
        'BLV', 'SGOV', 'BIL'
    ])

    # ===== TRADING CONTROLS =====
    COOLDOWN_HOURS: int = 3
    ORDER_TIMEOUT_MINUTES: int = 15
    LIMIT_OFFSET_PCT: float = 0.005

    # ===== INTRADAY VOLATILITY =====
    VOLATILE_TICKERS: List[str] = field(default_factory=lambda: [
        'IBIT', 'ARKK', 'KTOS', 'FIGR', 'URNM', 'MP'
    ])
    INTRADAY_DROP_THRESHOLD: float = 0.06  # 6% drop triggers 1.5x
    INTRADAY_MULTIPLIER: float = 1.5

    # ===== EXTENDED HOURS =====
    TRADE_EXTENDED_HOURS: bool = True

    # ===== SYSTEM =====
    SCAN_INTERVAL_SEC: int = 60
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    def get_dip_threshold(self, symbol: str) -> float:
        """Get dip threshold for symbol (override or default)"""
        return self.DIP_THRESHOLDS.get(symbol, self.DIP_THRESHOLDS['DEFAULT'])

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.ALPACA_KEY or not self.ALPACA_SECRET:
            raise ValueError("ALPACA_KEY and ALPACA_SECRET must be set")

        if 'DEFAULT' not in self.DIP_THRESHOLDS:
            raise ValueError("DIP_THRESHOLDS must contain 'DEFAULT' key")

        for symbol, threshold in self.DIP_THRESHOLDS.items():
            if threshold <= 0 or threshold > 0.5:
                raise ValueError(f"DIP_THRESHOLD for {symbol} must be between 0 and 0.5")

        if self.MAX_POSITION_PCT <= self.BASE_POSITION_PCT:
            raise ValueError("MAX_POSITION_PCT must be greater than BASE_POSITION_PCT")

        return True


# Global config instance
config = Config()