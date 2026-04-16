#!/usr/bin/env python3
"""
Stock market research bot — backtest, scan, and latest-bar signals.

Default mode is analysis only (no broker orders).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from backtest import run_backtest
from broker import PaperBroker
from data_provider import fetch_ohlcv
from indicators import enrich
from portfolio import build_recommendations, execute_recommendations
from strategy import score_row, signals_from_df


def load_config(path: Path | None) -> dict:
    base = {
        "watchlist": ["SPY", "QQQ", "AAPL"],
        "strategy": {},
        "backtest": {},
        "portfolio": {},
    }
    if path and path.is_file():
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        base.update(user)
        base["strategy"] = {**base.get("strategy", {}), **user.get("strategy", {})}
        base["backtest"] = {**base.get("backtest", {}), **user.get("backtest", {})}
    return base


def cmd_backtest(args: argparse.Namespace, cfg: dict) -> None:
    try:
        df = fetch_ohlcv(args.symbol, period=args.period, interval=args.interval)
    except Exception as exc:
        print(f"Error fetching data for {args.symbol}: {exc}")
        sys.exit(1)
    bt_cfg = cfg.get("backtest", {})
    res = run_backtest(
        df,
        cfg["strategy"],
        initial_cash=float(bt_cfg.get("initial_cash", 100_000)),
        commission_pct=float(bt_cfg.get("commission_pct", 0.0005)),
        slippage_pct=float(bt_cfg.get("slippage_pct", 0.0002)),
        allocation_pct=float(bt_cfg.get("allocation_pct", 1.0)),
    )
    print(f"Symbol: {args.symbol}")
    print(f"Period: {args.period}  Interval: {args.interval}")
    print(f"Initial: ${res['initial_cash']:,.2f}")
    print(f"Final:   ${res['final_equity']:,.2f}")
    print(f"Return:  {res['total_return_pct']:.2f}%")
    print(f"Max DD:  {res['max_drawdown_pct']:.2f}%")


def cmd_signal(args: argparse.Namespace, cfg: dict) -> None:
    try:
        df = fetch_ohlcv(args.symbol, period=args.period, interval=args.interval)
    except Exception as exc:
        print(f"Error fetching data for {args.symbol}: {exc}")
        sys.exit(1)
    data = enrich(df, cfg["strategy"])
    last = data.iloc[-1]
    b, s, detail = score_row(last, cfg["strategy"])
    buy_min = int(cfg["strategy"].get("buy_score_min", 3))
    sell_min = int(cfg["strategy"].get("sell_score_min", 2))
    if b >= buy_min and s >= sell_min:
        action = "SELL"
    elif b >= buy_min:
        action = "BUY"
    elif s >= sell_min:
        action = "SELL"
    else:
        action = "HOLD"

    print(f"Symbol: {args.symbol}  (last bar: {data.index[-1]})")
    print(f"Close: {last['close']:.4f}")
    print(f"Buy score: {b}/4  Sell score: {s}/4")
    print(f"Suggested action (rules only): {action}")
    print(f"Factors: {detail}")


def cmd_scan(args: argparse.Namespace, cfg: dict) -> None:
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        symbols = cfg.get("watchlist", [])

    print(f"Scanning {len(symbols)} symbols (period={args.period})...\n")
    rows = []
    strat = cfg["strategy"]
    buy_min = int(strat.get("buy_score_min", 3))
    sell_min = int(strat.get("sell_score_min", 2))

    for sym in symbols:
        try:
            df = fetch_ohlcv(sym, period=args.period, interval="1d")
            data = enrich(df, strat)
            last = data.iloc[-1]
            b, s, _ = score_row(last, strat)
            if b >= buy_min and s >= sell_min:
                act = "SELL"
            elif b >= buy_min:
                act = "BUY"
            elif s >= sell_min:
                act = "SELL"
            else:
                act = "HOLD"
            rows.append((sym, act, b, s, float(last["close"])))
        except Exception as e:
            rows.append((sym, f"ERR: {e}", 0, 0, 0.0))

    rows.sort(key=lambda x: (x[2] - x[3]), reverse=True)
    print(f"{'Ticker':<8} {'Action':<6} {'Buy':>4} {'Sell':>4} {'Close':>12}")
    for sym, act, b, s, cl in rows:
        if act.startswith("ERR"):
            print(f"{sym:<8} {act}")
        else:
            print(f"{sym:<8} {act:<6} {b:>4} {s:>4} {cl:>12.2f}")


def cmd_portfolio(args: argparse.Namespace, cfg: dict) -> None:
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        symbols = cfg.get("watchlist", [])
    broker = PaperBroker(Path(args.portfolio_file or "portfolio_state.json"))
    try:
        recommendations = build_recommendations(symbols, cfg, broker, args.period, args.interval)
    except Exception as exc:
        print(f"Error generating portfolio recommendations: {exc}")
        sys.exit(1)

    print(f"Portfolio recommendations for {len(symbols)} symbols")
    print(f"Cash available: ${broker.get_cash():,.2f}")
    print(f"{'Symbol':<8} {'Signal':<5} {'Current':>8} {'Target':>8} {'Action':>6} {'Price':>10}")
    for rec in recommendations:
        print(
            f"{rec['symbol']:<8} {rec['signal']:<5} {rec['current_qty']:>8.0f} {rec['target_qty']:>8.0f} {rec['action']:>6} {rec['price']:>10.2f}"
        )


def cmd_paper_trade(args: argparse.Namespace, cfg: dict) -> None:
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    if not symbols:
        symbols = cfg.get("watchlist", [])
    broker = PaperBroker(Path(args.portfolio_file or "portfolio_state.json"))
    try:
        recommendations = build_recommendations(symbols, cfg, broker, args.period, args.interval)
    except Exception as exc:
        print(f"Error generating trade recommendations: {exc}")
        sys.exit(1)

    executed = []
    for rec in recommendations:
        if rec["action"] in {"BUY", "SELL"} and rec["order_qty"] > 0:
            try:
                executed.append(execute_recommendations(broker, [rec])[0])
            except Exception as exc:
                print(f"Failed to execute {rec['action']} {rec['symbol']}: {exc}")

    print(f"Executed {len(executed)} paper trades. New cash: ${broker.get_cash():,.2f}")
    for item in executed:
        print(
            f"{item['symbol']}: {item['action']} {item['quantity']} @ {item['price']:.2f}"
        )


def cmd_dump(args: argparse.Namespace, cfg: dict) -> None:
    try:
        df = fetch_ohlcv(args.symbol, period=args.period, interval=args.interval)
    except Exception as exc:
        print(f"Error fetching data for {args.symbol}: {exc}")
        sys.exit(1)
    data = enrich(df, cfg["strategy"])
    sig = signals_from_df(data, cfg["strategy"])
    out = data.join(sig[["buy_score", "sell_score", "signal"]], how="inner")
    tail = out.tail(args.last)
    cols = ["close", "ema_fast", "ema_slow", "rsi", "buy_score", "sell_score", "signal"]
    print(tail[cols].to_string())


def _add_config_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to config JSON (see config.example.json)",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stock market signal & backtest bot")
    sub = parser.add_subparsers(dest="command", required=True)

    p_bt = sub.add_parser("backtest", help="Run long-only backtest on one symbol")
    _add_config_arg(p_bt)
    p_bt.add_argument("--symbol", required=True)
    p_bt.add_argument("--period", default="2y")
    p_bt.add_argument("--interval", default="1d")
    p_bt.set_defaults(func=cmd_backtest)

    p_sig = sub.add_parser("signal", help="Latest-bar scores for one symbol")
    _add_config_arg(p_sig)
    p_sig.add_argument("--symbol", required=True)
    p_sig.add_argument("--period", default="1y")
    p_sig.add_argument("--interval", default="1d")
    p_sig.set_defaults(func=cmd_signal)

    p_sc = sub.add_parser("scan", help="Scan watchlist or comma-separated symbols")
    _add_config_arg(p_sc)
    p_sc.add_argument("--symbols", default="", help="e.g. SPY,QQQ,AAPL (else use config watchlist)")
    p_sc.add_argument("--period", default="6mo")
    p_sc.set_defaults(func=cmd_scan)

    p_pf = sub.add_parser("portfolio", help="Generate portfolio position recommendations")
    _add_config_arg(p_pf)
    p_pf.add_argument("--symbols", default="", help="e.g. SPY,QQQ,AAPL (else use config watchlist)")
    p_pf.add_argument("--period", default="6mo")
    p_pf.add_argument("--interval", default="1d")
    p_pf.add_argument("--portfolio-file", default="portfolio_state.json", help="Path to paper portfolio state file")
    p_pf.set_defaults(func=cmd_portfolio)

    p_pt = sub.add_parser("paper-trade", help="Execute paper trades against a local portfolio state")
    _add_config_arg(p_pt)
    p_pt.add_argument("--symbols", default="", help="e.g. SPY,QQQ,AAPL (else use config watchlist)")
    p_pt.add_argument("--period", default="6mo")
    p_pt.add_argument("--interval", default="1d")
    p_pt.add_argument("--portfolio-file", default="portfolio_state.json", help="Path to paper portfolio state file")
    p_pt.set_defaults(func=cmd_paper_trade)

    p_d = sub.add_parser("dump", help="Print recent rows with scores (debug)")
    _add_config_arg(p_d)
    p_d.add_argument("--symbol", required=True)
    p_d.add_argument("--period", default="1y")
    p_d.add_argument("--interval", default="1d")
    p_d.add_argument("--last", type=int, default=15)
    p_d.set_defaults(func=cmd_dump)

    args = parser.parse_args()
    cfg = load_config(args.config)
    args.func(args, cfg)


if __name__ == "__main__":
    main()
