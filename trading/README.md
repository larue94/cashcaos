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
- [x] Phase 2 — Data pipeline (prices, fundamentals, news)
- [x] Phase 3 — The 4 agents + orchestrator, first example recommendation
- [x] Phase 4 — Backtesting with walk-forward windows + metrics dashboard
- [x] Phase 5 — Daily digest + your approval workflow + learning loop
- [x] **Phase 6 — Risk calibration: regimes, correlation limits, Kelly sizing,
      Monte Carlo, small-cap screener (backtested honestly, losers included)** ← *complete*

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

**Phase 3 — the agent team (needs all keys set up):**

```
python -m trading.test_agents
```

**What you should see:** the team analyzes a small watchlist (takes a couple
of minutes — real data, real AI reasoning), then prints ONE recommendation in
plain English: what to buy, how much, which strategy book, why, what could go
wrong, and when it would sell — or an honest "do nothing today". The Risk
agent's sizing/veto reasoning is shown too. **Nothing is executed** — orders
can only ever happen through the Phase 5 approval workflow, after you say yes
to each trade.

The AI setup: judgment calls use Claude (HIGH tier); news-reading grunt work
uses a free open-source model, Llama 3.3 70B via Groq's free tier (LOW tier).
Model choices can be changed in `.env` — including pointing the LOW tier at
Ollama on your own computer (see `.env.example`).

**Phase 4 — walk-forward backtest + dashboard:**

```
python -m trading.test_backtest
```

**What you should see:** the three core books are tested the honest way —
settings tuned on 3 years, then run on the NEXT unseen year, rolled forward
across all history, with 0.1% per-trade costs. The console prints each book
vs buy-and-hold SPY, and a full dashboard is written to
`trading/dashboard/output/dashboard.html` — double-click it to open in your
browser. Every metric has a plain-English explanation and a red/amber/green
flag against institutional benchmarks; honesty banners (survivorship bias,
data coverage, overfitting) sit at the top.

---

## The easy way — the clickable app (recommended)

```
python -m trading.webapp
```

Then open **http://127.0.0.1:8787** in any web browser. One window shows
everything and lets you do everything with buttons — no terminal typing:

- your account value, positions, and equity chart
- each recommendation as a card with a **✓ Approve & send order** and
  **✗ Reject** button
- **“View the analysis”** on each card expands the full reasoning: every
  agent's score and notes, the plain-English why / risks / exit plan, and a
  price chart with the 50-day and 200-day trend lines
- big buttons to **▶ Run today's analysis** and **📋 Weekly review**
- the agent report card and completed-trades history

It runs only on your own computer (nothing is exposed to the internet), and
every button uses the exact same rules and broker path as the commands
below — the app is just a friendlier face on the identical engine. Approving
still asks you to confirm before any order is sent.

## Get alerts on your phone (Telegram bot)

The bot messages you each recommendation with **Approve / Reject** buttons and
runs the analysis automatically every weekday — so exits (including the new
safety stop-loss) get checked daily without you remembering to.

**One-time setup (about 3 minutes):**

1. In Telegram, search for **@BotFather** (the official blue-tick account) and
   open a chat with it.
2. Send **`/newbot`**. It asks for a name (anything, e.g. "My Trading Bot")
   and a username ending in `bot` (e.g. `my_caos_trading_bot`).
3. BotFather replies with a **token** — a long string like
   `8123456:AAE...`. Copy it.
4. Paste it into `trading/.env` on the `TELEGRAM_BOT_TOKEN=` line.
5. Start the bot:
   ```
   python -m trading.telegram
   ```
6. On your phone, open your new bot and send it **`/start`**. You become its
   owner (only you can approve trades). Done.

**Using it:** each morning (default 9:45, set `TELEGRAM_DIGEST_TIME`) the bot
runs the analysis and sends any recommendations with buttons. Approving asks
for a second confirming tap before the order is sent. Commands: `/pending`,
`/status`, `/digest` (run now), `/help`.

**To have it run 24/7** (check daily even when your computer is off), deploy it
to an always-on host — the start command is `python -m trading.telegram`. Set
the host's timezone (`TZ`) so the daily time matches your local morning, and
put your keys in the host's environment variables.

## The command-line way (same engine, no browser)

```
python -m trading.digest     # each market morning (~3 minutes)
python -m trading.approve    # decide y/n on each recommendation
python -m trading.review     # once a week, e.g. Saturday
```

- **digest** syncs yesterday's fills, grades any completed trades into the
  learning ledger, checks exit rules on open positions (each book's trend
  exit **plus a hard stop-loss safety net** — sell if a holding drops >15%
  below entry, 30% for the small-cap sleeve; set `STOP_LOSS_PCT` in `.env`),
  asks the agent team for today's best new idea, and refreshes the live
  dashboard (`trading/dashboard/output/live.html`). Exits become SELL
  recommendations that also wait for your approval. The stop-loss is a live
  safety overlay not present in the historical backtest.
- **approve** is the ONLY command that can ever send an order — it asks you
  y/n per trade, on a real keyboard, and logs your decision. Rejections are
  recorded; pending items expire after 3 days.
- **review** writes the weekly plain-English self-review from real numbers,
  proposes rule adjustments (words only — nothing changes without you), and
  calls out any metric red two weeks running.
- The learning loop grades every agent on every CLOSED trade and adapts
  their influence automatically (0.3x–1.2x). All of it persists in a local
  database (`trading/data/cache/journal.db`) so learning survives restarts.

**Phase 6 — risk calibration report:**

```
python -m trading.test_risk
```

**What you should see:** a full risk report (console + a browser page at
`trading/dashboard/output/risk.html`) covering all five risk tools:

1. **Market regime** — today's classification (bull / choppy / bear) and a
   table of how each book actually performed in each regime historically.
   The live agents now weight signals by regime automatically.
2. **Correlation limits** — the Risk agent blocks a buy that would pile onto
   a cluster of holdings that all move together, or overload one sector.
3. **Kelly sizing** — position size from each book's real win rate and payoff
   (half-Kelly, hard-capped); flat 5% until a book has 20+ closed trades.
4. **Monte Carlo risk-of-ruin** — each book's real returns reshuffled
   thousands of times; the % of those alternate histories that breach the
   20% drawdown limit (honestly, that's 12–35% — which is exactly why the
   circuit breaker and these limits exist).
5. **High-risk small-cap sleeve** — the runner-pattern screener backtested
   with every losing signal included, a full win/loss histogram, and an
   honest verdict (it will say "not justified" if the numbers say so).

These run as analysis/config; the regime, correlation, and Kelly rules are
already wired into the live daily digest.

---

## What could break

### Phase 6 (risk calibration)

- **Small-cap results are optimistic** — free data omits bankrupt/delisted
  companies (survivorship bias) and the "catalyst" is proxied by a price
  gap. The report says this loudly; treat the sleeve as a small experiment.
- **Monte Carlo is an estimate**, not a promise — it resamples the past, and
  the future can be worse than any past the data contains.

### Phase 5 (digest / approval / learning)

- **Orders execute at the next market open** if you approve while the
  market is closed — the digest confirms the fill the next morning.
- **The learning ledger starts empty.** Agent report cards show "—" until
  ~5 trades have fully closed; weights stay neutral (1.0x) until then.
- **If an order is rejected by the broker** (rare on paper), the
  recommendation stays pending and `approve` explains what happened —
  just run it again after fixing the issue.

### Phase 4 (backtest + dashboard)

- **First run is slow** (~5 minutes): 21 stocks' full history is downloaded,
  then cached — later runs take seconds.
- **Backtest ≠ promise.** Even the honest walk-forward method can't fix
  survivorship bias in free data, and the mechanical rules are a simplified
  skeleton of what the live agents do. The dashboard says this on its face.
- **Results change slightly between runs months apart** — new data arrives,
  and the newest partial year is included and marked as partial.

### Phase 3 (agent team)

- **A key stops working** — every key-related failure prints which line of
  `.env` to fix.
- **Groq free-tier limits** — very generous, but if you run the analysis many
  times in one day it can briefly say "rate limited"; wait a minute and rerun.
- **AI judgment is not a guarantee** — the reasoning is real but can still be
  wrong; that's exactly why every trade waits for your approval and why the
  Phase 5 learning loop tracks each agent's accuracy over time.

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
