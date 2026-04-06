# bitcoinRobot / trading demos

This repository contains **two separate tools** that are **not** interchangeable: one is a **Huobi (crypto) exchange demo in Node.js**, the other is a **stock signal + backtest helper in Python** using Yahoo data.

---

## 1. Original: Huobi Pro demo (JavaScript / Node.js)

**Purpose:** Sample code for **Huobi Pro** (cryptocurrency): signed REST API calls, optional trading when API keys are configured, and a small **REST vs WebSocket** market-data comparison.

**Requirements:** Node.js 6+ (newer Node is fine).

**Demos**

| File | What it does |
|------|----------------|
| `demo_crawler.js` | Pulls market data over **REST** and **WebSocket**, compares order books, prints meaningful differences. |
| `demo_sdk.js` | Walks through the **trading API** flow: account → balance → (optional) orders — **real trading is possible** if `config` and keys are set. |

**Run**

```bash
npm install
node demo_sdk.js
node demo_crawler.js
```

Huobi credentials and `config` layout are expected by `sdk/hbsdk.js` (see `config` package conventions).

**Original author:** magicdlf (QQ: 2797820732) — [upstream demo](https://github.com/magicdlf/huobipro)

---

## 2. Addition: Stock market bot (Python)

**Purpose:** **Research only** — download historical **stocks/ETFs** via Yahoo (`yfinance`), compute indicators, output **BUY / SELL / HOLD-style signals** and a simple **long-only backtest**. **No broker connection** and **no order placement**.

**Details, commands, and examples:** [stock_market_bot/README.md](stock_market_bot/README.md)

**Quick start**

```powershell
cd stock_market_bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py signal --symbol SPY --period 1y
```

**Maintainer note:** Python addition by josephb4224 (April 2026).

### Using the output for real trading (practical framing)

The Python tool does **not** place orders. Treat it as a **checklist / filter**, not instructions.

| Output | Suggested use |
|--------|----------------|
| BUY / SELL / HOLD | Flag symbols for **your own** follow-up (thesis, risk, news) — not an automatic trade trigger. |
| Buy / sell scores | See **which rules** fired (trend, RSI, volume). |
| `dump` | Avoid acting on **one bar** without recent context. |
| `backtest` | **Sanity-check** rules over history; mind fees, slippage, and that past results ≠ future performance. |

**Reasonable workflow:** `scan` on your list → `signal` / `dump` on names that pass your other criteria → only then consider execution (paper trade first; size and max loss are your responsibility).

---

## Disclaimer

Nothing here is financial advice. Crypto and equity trading involve risk; exchange APIs can move real money. Use demos at your own risk.
