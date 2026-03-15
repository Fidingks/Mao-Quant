"""CatQuant - A-share backtesting toolkit for AI coding agents."""

__version__ = "0.1.0"

from catquant.models import SecurityData, LatestData, PriceData, normalize_symbol
from catquant import data_engine
from catquant import backtest
from catquant import scanner
from catquant import indicators
from catquant import chart
from catquant import signals
from catquant import resolve

__all__ = [
    "SecurityData", "LatestData", "PriceData", "normalize_symbol",
    "data_engine", "backtest", "scanner", "indicators", "chart", "signals",
    "resolve",
]
