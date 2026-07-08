# Agentic Paper-Trading System

**Plain-English guide — no coding knowledge needed.**

This is an AI-assisted stock research system. It studies the market, and once
a day it hands you a short list of trade ideas with full reasoning in plain
English. **It never trades on its own.** Nothing reaches your (fake-money)
Alpaca account until you personally approve each trade.

> **Important:** everything runs against Alpaca's *paper trading* service.
> Paper trading uses simulated money — you cannot lose real money with this
> system as built.

---

## The big picture (how the pieces fit together)

Think of it as a small investment team that works for you:

| Team member | Job |
|---|---|
| **Research agent** | Reads company financials (revenue, profit, debt) to decide **what** is worth buying |
| **Sentiment agent** | Reads recent news headlines to gauge the mood around a stock |
| **Technical agent** | Reads price charts to decide **when** the timing looks right |
| **Risk agent** | The safety officer. Sizes every position, and can **veto any trade**. If the portfolio ever falls 20% from its peak, it halts all new buying (a "circuit breaker") |
| **Orchestrator** | The team lead. Collects everyone's opinion, weighs it, and writes the daily digest you approve or reject |

The team runs **four separate "strategy books"** (think: four sub-portfolios):

1. **Swing** — trades held days to weeks
2. **Monthly** — trades held roughly a month or more
3. **Long-term** — positions held many months to years
4. **High-Risk Small-Cap Sleeve** — 10–20% of capital, hunting small companies
   with unusual volume and a real catalyst. Higher risk is accepted here
   (up to 30–35% drawdown) but it is walled off from the core books.

There is **no day trading** anywhere in the system.

---

## Build phases (where we are)

- [x] Phase 1 — Skeleton + Alpaca connection test
- [x] **Phase 2 — Data pipeline (prices, fundamentals, news)** ← *you are here*
- [ ] Phase 3 — The 4 agents + orchestrator, first example recommendation
- [ ] Phase 4 — Backtesting with walk-forward windows + metrics dashboard
- [ ] Phase 5 — Daily digest + your approval workflow + learning loop
- [ ] Phase 6 — Risk calibration: regimes, correlation limits, Kelly sizing,
      Monte Carlo, small-cap screener (backtested honestly, losers included)

---

## Setting up — one time only

### Step 1: Get free Alpaca paper-trading keys (5 minutes)

Alpaca is a US broker with a free practice ("paper") account.

1. Go to **https://alpaca.markets** and click **Sign Up** (free, no card needed).
2. After signing in you land on the dashboard. Make sure the toggle near the
   top-left says **Paper** (not "Live"). Paper = fake money.
3. On the right side of the paper dashboard, find the box called
   **"API Keys"** and click **Generate New Keys**.
4. You'll be shown two codes:
   - **API Key ID** — like a username (starts with `PK...`)
   - **Secret Key** — like a password. **Copy it immediately** — Alpaca only
     shows it once. If you lose it, just generate new keys.

Treat these like passwords. They only unlock your *paper* account, but keep
them private anyway.

### Step 2: Put your keys in the settings file

In this `trading` folder there is a file called `.env.example`. Make a copy
of it named exactly `.env` (just the two words "dot env", no other name), and
open it in any text editor. Fill in:

```
ALPACA_API_KEY=your key ID here
ALPACA_SECRET_KEY=your secret key here
```

Leave the other lines alone for now (the Claude and Finnhub keys are needed
from Phase 2–3 onward — the file explains each one).

The `.env` file is deliberately **excluded from GitHub** so your keys never
get uploaded anywhere.

### Step 3: Install the software the system needs

Open a terminal in the project folder and run:

```
pip install -r trading/requirements.txt
```

(This downloads the free libraries the system is built on. It can take a
couple of minutes the first time.)

---

### Step 4 (from Phase 2): Get a free Finnhub key for news

1. Go to **https://finnhub.io** and click **Get free API key** (free forever
   tier, no card needed).
2. After signing in, your API key is shown right on the dashboard.
3. Paste it into your `.env` file on the `FINNHUB_API_KEY=` line.

Until you do this, the system simply skips news — everything else works.

---

## Test it yourself — one command per phase

**Phase 1 — broker connection:**

```
python -m trading.test_connection
```

**What you should see:** a friendly report confirming it reached your Alpaca
paper account, showing your fake-money balance (new accounts start with
$100,000), and confirming the market's open/closed status. Every check gets a
✅ or a ❌ with an explanation.

If anything is wrong (missing keys, typo in the keys, no internet), the test
tells you in plain English what to fix.

**Phase 2 — data pipeline:**

```
python -m trading.test_data
```

**What you should see:** a checklist covering the three data feeds —
prices (Apple and the S&P 500 as guinea pigs), company fundamentals
(including Apple's officially filed revenue straight from the SEC), and
news headlines. News shows a ⚠️ skip note until you add the free Finnhub
key (Step 4 above) — that's expected, not a failure.

---

## What could break

### Phase 2 (data pipeline)

- **Yahoo Finance rate-limiting** — Yahoo sometimes temporarily blocks
  networks that ask too often (very common on shared cloud machines, rare at
  home). The system automatically falls back to Alpaca's own price data, so
  prices keep working; the "fundamentals snapshot" (market value, margins)
  shows a ⚠️ until Yahoo cools off. The official SEC numbers are unaffected.
- **SEC EDGAR slowness** — it's a government website; occasionally slow.
  Retry a few minutes later.
- **A wrong ticker symbol** — asking for "Apple" instead of "AAPL" gives a
  clear error saying to check the spelling.
- **Survivorship bias (important, permanent)** — free data sources mostly
  carry companies that still exist. Companies that went bankrupt are missing
  from history, which flatters backtest results. The backtester (Phase 4)
  will flag this on every report.

### Phase 1 (broker connection)

- **Wrong or swapped keys** — the most common issue. If the test says
  "unauthorized", re-check that the Key ID went in `ALPACA_API_KEY` and the
  Secret in `ALPACA_SECRET_KEY`, with no extra spaces.
- **Keys from the Live dashboard instead of Paper** — live keys won't work
  against the paper system. Make sure the toggle said "Paper" when you
  generated them.
- **No internet / firewall** — the test needs to reach `alpaca.markets`.
- **Alpaca maintenance windows** — rarely, their paper API is briefly down;
  the test will say it couldn't connect. Just retry later.

---

## Where things live (for the curious)

```
trading/
├── broker/        The "phone line" to the broker. Written so Alpaca can be
│                  swapped for Interactive Brokers later without rewriting
│                  the rest of the system.
├── agents/        The 4 AI agents + orchestrator (Phase 3)
├── strategies/    The 4 strategy books (Phase 3+)
├── data/          Price/fundamentals/news pipeline (Phase 2)
├── backtest/      Walk-forward backtesting harness (Phase 4)
├── dashboard/     The metrics web page (Phase 4–5)
├── learning/      The recursive learning ledger (Phase 5)
├── logs/          Human-readable audit trail of every agent decision —
│                  open any file here in a text editor to see *why* a
│                  recommendation was made
└── test_connection.py   The Phase 1 test you just ran
```
