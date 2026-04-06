"""Historical OHLCV via yfinance (Yahoo Finance)."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def fetch_ohlcv(
    symbol: str,
    period: str = "2y",
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    period: e.g. 1mo, 3mo, 6mo, 1y, 2y, 5y, max
    interval: 1m, 5m, 15m, 1h, 1d, 1wk
    """
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=auto_adjust)
    if df.empty:
        raise ValueError(f"No data returned for {symbol!r} (check ticker / market hours for intraday).")
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )
    return df[["open", "high", "low", "close", "volume"]].dropna()
