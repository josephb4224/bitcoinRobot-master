from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from broker import PaperBroker
from data_provider import fetch_ohlcv
from indicators import enrich
from strategy import score_row


def load_portfolio_config(cfg: dict) -> dict:
    portfolio_cfg = cfg.get("portfolio", {})
    return {
        "target_exposure_pct": min(1.0, max(0.0, float(portfolio_cfg.get("target_exposure_pct", 0.8)))),
        "max_position_pct": min(1.0, max(0.0, float(portfolio_cfg.get("max_position_pct", 0.25)))),
        "cash_buffer_pct": min(1.0, max(0.0, float(portfolio_cfg.get("cash_buffer_pct", 0.05)))),
    }


def build_recommendations(
    symbols: Iterable[str],
    cfg: dict,
    broker: PaperBroker,
    period: str,
    interval: str,
) -> list[dict]:
    symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    portfolio_cfg = load_portfolio_config(cfg)
    positions = broker.get_positions()
    total_cash = broker.get_cash()
    rows = []

    for symbol in symbols:
        df = fetch_ohlcv(symbol, period=period, interval=interval)
        data = enrich(df, cfg["strategy"])
        last = data.iloc[-1]
        buy, sell, detail = score_row(last, cfg["strategy"])
        if buy >= int(cfg["strategy"].get("buy_score_min", 3)):
            signal = "BUY"
        elif sell >= int(cfg["strategy"].get("sell_score_min", 2)):
            signal = "SELL"
        else:
            signal = "HOLD"

        price = float(last["close"])
        current = positions.get(symbol, {"quantity": 0.0, "avg_price": 0.0})
        current_qty = float(current["quantity"])
        current_value = current_qty * price
        rows.append(
            {
                "symbol": symbol,
                "signal": signal,
                "price": price,
                "current_qty": current_qty,
                "current_value": current_value,
                "detail": detail,
            }
        )

    total_equity = total_cash + sum(row["current_value"] for row in rows)
    available_value = total_equity * portfolio_cfg["target_exposure_pct"]
    current_exposure = sum(row["current_value"] for row in rows if row["current_qty"] > 0)
    investable = max(0.0, available_value - current_exposure)
    buy_rows = [row for row in rows if row["signal"] == "BUY"]

    per_buy_target = (
        investable / len(buy_rows) if buy_rows else 0.0
    )
    per_buy_target = min(per_buy_target, total_equity * portfolio_cfg["max_position_pct"])

    recommendations = []
    for row in rows:
        target_value = row["current_value"]
        if row["signal"] == "BUY":
            target_value = max(row["current_value"], per_buy_target)
        elif row["signal"] == "SELL":
            target_value = 0.0

        target_qty = math.floor(target_value / row["price"]) if row["price"] > 0 else 0
        order_qty = target_qty - row["current_qty"]
        if order_qty > 0:
            action = "BUY"
        elif order_qty < 0:
            action = "SELL"
        else:
            action = "HOLD"

        recommendations.append(
            {
                "symbol": row["symbol"],
                "signal": row["signal"],
                "price": row["price"],
                "current_qty": row["current_qty"],
                "current_value": row["current_value"],
                "target_qty": target_qty,
                "order_qty": abs(order_qty),
                "action": action,
                "detail": row["detail"],
            }
        )

    return recommendations


def execute_recommendations(
    broker: PaperBroker,
    recommendations: list[dict],
) -> list[dict]:
    executed = []
    for rec in recommendations:
        if rec["action"] in {"BUY", "SELL"} and rec["order_qty"] > 0:
            order = broker.place_order(
                rec["symbol"],
                rec["action"],
                rec["order_qty"],
                rec["price"],
            )
            executed.append({"symbol": rec["symbol"], "action": rec["action"], "quantity": rec["order_qty"], "price": rec["price"], "order": order})
    return executed
