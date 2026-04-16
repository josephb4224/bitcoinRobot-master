from __future__ import annotations

import json
from pathlib import Path


class BrokerError(Exception):
    pass


class PaperBroker:
    def __init__(self, state_path: Path, initial_cash: float = 100_000.0):
        self.state_path = state_path
        self.state = self._load_state(initial_cash)

    def _load_state(self, initial_cash: float) -> dict:
        if self.state_path.is_file():
            try:
                with open(self.state_path, encoding="utf-8") as f:
                    state = json.load(f)
                state.setdefault("cash", float(initial_cash))
                state.setdefault("positions", {})
                state.setdefault("history", [])
                return state
            except (json.JSONDecodeError, OSError):
                pass
        state = {"cash": float(initial_cash), "positions": {}, "history": []}
        self._save_state(state)
        return state

    def _save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def get_cash(self) -> float:
        return float(self.state.get("cash", 0.0))

    def get_positions(self) -> dict[str, dict[str, float]]:
        return self.state.get("positions", {})

    def get_position(self, symbol: str) -> dict[str, float]:
        return self.get_positions().get(symbol.upper(), {"quantity": 0.0, "avg_price": 0.0})

    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
    ) -> dict:
        symbol = symbol.upper()
        side = side.upper()
        if quantity <= 0 or price <= 0:
            raise BrokerError("Quantity and price must be positive")

        cash = self.get_cash()
        positions = self.get_positions()
        position = positions.get(symbol, {"quantity": 0.0, "avg_price": 0.0})

        if side == "BUY":
            cost = quantity * price
            if cost > cash:
                raise BrokerError(f"Not enough cash to buy {quantity} {symbol} at {price}")
            cash -= cost
            total_cost = position["quantity"] * position["avg_price"] + cost
            quantity_total = position["quantity"] + quantity
            avg_price = total_cost / quantity_total
            positions[symbol] = {"quantity": quantity_total, "avg_price": avg_price}
        elif side == "SELL":
            if quantity > position["quantity"]:
                raise BrokerError(f"Not enough shares to sell {quantity} {symbol}")
            proceeds = quantity * price
            cash += proceeds
            remaining = position["quantity"] - quantity
            if remaining > 0:
                positions[symbol] = {"quantity": remaining, "avg_price": position["avg_price"]}
            else:
                positions.pop(symbol, None)
        else:
            raise BrokerError(f"Unsupported order side: {side}")

        self.state["cash"] = cash
        self.state["positions"] = positions
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "cash": cash,
            "positions": positions,
        }
        self.state["history"].append(order)
        self._save_state(self.state)
        return order

    def save(self) -> None:
        self._save_state(self.state)
