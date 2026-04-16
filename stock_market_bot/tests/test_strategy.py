import unittest
import pandas as pd

from indicators import enrich
from strategy import score_row, signals_from_df
from backtest import run_backtest


def make_test_frame() -> pd.DataFrame:
    dates = pd.date_range(start="2026-01-01", periods=20, freq="D")
    close = [100 + i for i in range(20)]
    high = [c + 1 for c in close]
    low = [c - 1 for c in close]
    open_ = [c - 0.5 for c in close]
    volume = [1000 + i * 10 for i in range(20)]
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=dates,
    )


class TestStockMarketBot(unittest.TestCase):
    def test_score_and_signal(self):
        df = make_test_frame()
        cfg = {
            "fast_ema": 2,
            "slow_ema": 5,
            "trend_ema": 8,
            "rsi_period": 3,
            "rsi_buy_max": 65,
            "rsi_sell_min": 72,
            "volume_ma": 3,
            "buy_score_min": 3,
            "sell_score_min": 2,
        }
        data = enrich(df, cfg)
        sig = signals_from_df(data, cfg)
        self.assertIn("signal", sig.columns)
        self.assertEqual(sig.index[-1], df.index[-1])

        last = data.iloc[-1]
        buy, sell, detail = score_row(last, cfg)
        self.assertIsInstance(buy, int)
        self.assertIsInstance(sell, int)
        self.assertIsInstance(detail, dict)

    def test_backtest_allocation(self):
        df = make_test_frame()
        cfg = {
            "fast_ema": 2,
            "slow_ema": 5,
            "trend_ema": 8,
            "rsi_period": 3,
            "rsi_buy_max": 65,
            "rsi_sell_min": 72,
            "volume_ma": 3,
        }
        result = run_backtest(
            df,
            cfg,
            initial_cash=1000.0,
            commission_pct=0.0,
            slippage_pct=0.0,
            allocation_pct=0.5,
        )
        self.assertGreaterEqual(result["final_equity"], 0.0)
        self.assertEqual(result["initial_cash"], 1000.0)


if __name__ == "__main__":
    unittest.main()
