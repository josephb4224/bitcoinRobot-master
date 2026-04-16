"""Technical indicators (pandas only, no extra TA libs)."""

from __future__ import annotations

import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    out = 100 - (100 / (1 + rs))
    return out.fillna(50.0)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def enrich(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    out = df.copy()
    c = out["close"]
    fast = max(1, int(cfg.get("fast_ema", 12)))
    slow = max(1, int(cfg.get("slow_ema", 26)))
    trend = max(1, int(cfg.get("trend_ema", 50)))
    vol_ma = max(1, int(cfg.get("volume_ma", 20)))
    atr_period = max(1, int(cfg.get("atr_period", 14)))
    rsi_period = max(1, int(cfg.get("rsi_period", 14)))

    out["ema_fast"] = ema(c, fast)
    out["ema_slow"] = ema(c, slow)
    out["ema_trend"] = ema(c, trend)
    out["rsi"] = rsi(c, rsi_period)
    out["vol_ma"] = out["volume"].rolling(vol_ma).mean()
    out["atr"] = atr(out, atr_period)
    out["atr_pct"] = out["atr"] / c.replace(0, pd.NA)
    return out
