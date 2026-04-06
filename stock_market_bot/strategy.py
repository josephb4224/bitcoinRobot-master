"""
Multi-factor scoring strategy (signals only — not financial advice).

Bullish factors (each adds 1 to buy_score):
- Short-term EMA above longer EMA (momentum alignment)
- Price above medium trend EMA (regime filter)
- RSI not overbought and shows room to run (configurable band)
- Volume above its moving average (participation)

Bearish exit factors (sell_score):
- EMA cross down
- RSI extended / overbought
"""

from __future__ import annotations

import pandas as pd


def score_row(row: pd.Series, cfg: dict) -> tuple[int, int, dict]:
    buy = 0
    sell = 0
    detail = {}

    if pd.isna(row.get("ema_fast")) or pd.isna(row.get("ema_slow")):
        return 0, 0, {"note": "warmup"}

    if row["ema_fast"] > row["ema_slow"]:
        buy += 1
        detail["ema_bull"] = True
    else:
        sell += 1
        detail["ema_bear"] = True

    if row["close"] > row["ema_trend"]:
        buy += 1
        detail["above_trend"] = True
    else:
        detail["below_trend"] = True

    rsi_val = row["rsi"]
    rsi_buy_max = float(cfg.get("rsi_buy_max", 65))
    rsi_sell_min = float(cfg.get("rsi_sell_min", 72))
    if rsi_val < rsi_buy_max:
        buy += 1
        detail["rsi_ok"] = True
    if rsi_val > rsi_sell_min:
        sell += 1
        detail["rsi_hot"] = True

    vol_ma = row["vol_ma"]
    if not pd.isna(vol_ma) and row["volume"] > vol_ma:
        buy += 1
        detail["volume_confirm"] = True

    max_atr = cfg.get("max_atr_pct")
    if max_atr is not None and not pd.isna(row.get("atr_pct")):
        if float(row["atr_pct"]) > float(max_atr):
            buy = max(0, buy - 2)
            detail["high_volatility"] = True

    return buy, sell, detail


def signals_from_df(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    enriched = df.copy()
    rows = []
    for i, row in enriched.iterrows():
        b, s, d = score_row(row, cfg)
        rows.append({"date": i, "buy_score": b, "sell_score": s, "detail": d})
    sig = pd.DataFrame(rows).set_index("date")
    buy_min = int(cfg.get("buy_score_min", 3))
    sell_min = int(cfg.get("sell_score_min", 2))
    sig["signal"] = "HOLD"
    sig.loc[sig["buy_score"] >= buy_min, "signal"] = "BUY"
    sig.loc[sig["sell_score"] >= sell_min, "signal"] = "SELL"
    # If both fire, prefer risk-off
    both = (sig["buy_score"] >= buy_min) & (sig["sell_score"] >= sell_min)
    sig.loc[both, "signal"] = "SELL"
    return sig
