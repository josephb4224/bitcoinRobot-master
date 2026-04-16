import tempfile
from pathlib import Path

from broker import PaperBroker, BrokerError


def test_paper_broker_buy_and_sell():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "portfolio_state.json"
        broker = PaperBroker(state_path, initial_cash=1000.0)

        assert broker.get_cash() == 1000.0
        assert broker.get_position("SPY")["quantity"] == 0.0

        order = broker.place_order("SPY", "BUY", 1.0, 100.0)
        assert broker.get_cash() == 900.0
        assert broker.get_position("SPY")["quantity"] == 1.0
        assert order["symbol"] == "SPY"

        order = broker.place_order("SPY", "SELL", 1.0, 105.0)
        assert broker.get_cash() == 1005.0
        assert broker.get_position("SPY")["quantity"] == 0.0

        try:
            broker.place_order("SPY", "SELL", 1.0, 105.0)
            assert False, "Expected BrokerError when selling more than held"
        except BrokerError:
            pass
