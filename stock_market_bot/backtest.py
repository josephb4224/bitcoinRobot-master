"""Simple long-only backtest on daily bars."""

from __future__ import annotations

import pandas as pd

from indicators import enrich
from strategy import signals_from_df


def run_backtest(
    df: pd.DataFrame,
    strategy_cfg: dict,
    initial_cash: float = 100_000.0,
    commission_pct: float = 0.0005,
    slippage_pct: float = 0.0002,
    allocation_pct: float = 1.0,
) -> dict:
    data = enrich(df, strategy_cfg)
    sig = signals_from_df(data, strategy_cfg)
    merged = data.join(sig[["signal"]], how="inner")

    allocation_pct = max(0.0, min(float(allocation_pct), 1.0))

    cash = initial_cash
    shares = 0.0
    equity_curve = []

    for ts, row in merged.iterrows():
        price = float(row["close"])
        exec_price = price
        signal = row["signal"]

        if signal == "BUY" and shares == 0 and cash > 0:
            spend = cash * allocation_pct
            exec_price = price * (1 + slippage_pct)
            shares = (spend * (1 - commission_pct)) / exec_price
            cash -= spend
        elif signal == "SELL" and shares > 0:
            exec_price = price * (1 - slippage_pct)
            cash = shares * exec_price * (1 - commission_pct) + cash
            shares = 0.0

        equity = cash + shares * price
        equity_curve.append({"date": ts, "equity": equity, "signal": signal})

    eq_df = pd.DataFrame(equity_curve).set_index("date")
    final = float(eq_df["equity"].iloc[-1])
    ret = (final / initial_cash) - 1.0
    peak = eq_df["equity"].cummax()
    dd = ((eq_df["equity"] - peak) / peak).min()

    return {
        "initial_cash": initial_cash,
        "final_equity": final,
        "total_return_pct": ret * 100,
        "max_drawdown_pct": float(dd) * 100,
        "equity_curve": eq_df,
    }
