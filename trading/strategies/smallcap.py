"""High-Risk Small-Cap Sleeve — the screener behind small-cap runners.

This does NOT chase specific past winners. It defines the repeatable PATTERN
that often precedes a small-cap run, then backtests that pattern honestly on
every stock that matched it — including all the ones that fizzled or crashed.

The screen (all must hit on the same day):
- Unusual volume spike: today's volume >= 3x the 50-day average
- Technical breakout: price closes above its prior 20-day high
- Catalyst proxy: a large overnight gap up (>= 5%) — a stand-in for "news
  happened" (FDA approval, contract win, earnings surprise). See the honesty
  note below about why this is a proxy.

⚠️ THREE HONESTY CAVEATS — these make real-world results WORSE than shown:
1. SURVIVORSHIP: free data mostly lacks companies that went bankrupt/delisted.
   Small-cap failures are exactly what's missing, so the true hit rate is
   worse than any free-data backtest suggests.
2. CATALYST IS A PROXY: we can't cheaply replay 10 years of news, so a big
   gap up stands in for "a catalyst occurred". Real catalyst filtering would
   change (and probably reduce) the signal count.
3. MARKET-CAP FILTER IS APPROXIMATE: we can't get point-in-time share counts
   from free data, so the universe is chosen from names that are small/mid
   cap today, not verified as <$2B at each signal date.

The point is to report the FULL win/loss distribution and give an honest
verdict — including "the edge doesn't justify the risk" if that's what the
numbers say — not to tune until known winners light up.
"""

import numpy as np
import pandas as pd

from trading.data.prices import get_daily_prices

# A deliberately un-cherry-picked universe of volatile small/mid-cap names
# spanning winners AND well-known disappointments. Not a list of "stocks that
# went up" — that would be the exact bias this test exists to avoid.
SMALLCAP_UNIVERSE = [
    "PLUG", "FCEL", "BLNK", "CHPT", "QS", "RIOT", "MARA", "GEVO", "CLNE",
    "SOFI", "UPST", "AFRM", "OPEN", "DKNG", "SKLZ", "PLTR", "LAZR", "DNA",
    "RIVN", "LCID", "NKLA", "GOEV", "SPCE", "COIN", "HOOD", "RUN", "ENPH",
    "BE", "SEDG", "AMC",
]

VOLUME_SPIKE = 3.0       # today's volume vs 50-day average
BREAKOUT_LOOKBACK = 20   # prior N-day high to break
GAP_CATALYST = 0.05      # overnight gap up as a catalyst proxy
HOLD_DAYS = 20           # forward window to judge each signal


def _signals_for(ticker: str) -> list[dict]:
    """Every day this ticker matched the screen, with its forward result."""
    try:
        df, _ = get_daily_prices(ticker)
    except Exception:  # noqa: BLE001 — a missing ticker just contributes nothing
        return []
    if len(df) < 120:
        return []
    close, high, vol, open_ = df["Close"], df["High"], df["Volume"], df["Open"]
    vol_avg = vol.rolling(50).mean()
    prior_high = high.rolling(BREAKOUT_LOOKBACK).max().shift(1)
    prev_close = close.shift(1)
    gap = open_ / prev_close - 1

    matched = ((vol >= VOLUME_SPIKE * vol_avg) & (close > prior_high)
               & (gap >= GAP_CATALYST) & vol_avg.notna() & prior_high.notna())

    out = []
    idx = df.index
    entries = np.flatnonzero(matched.to_numpy())
    last_exit = -1
    for i in entries:
        if i <= last_exit or i + HOLD_DAYS >= len(df):
            continue  # don't stack overlapping signals on the same name
        entry = float(close.iloc[i])
        exit_ = float(close.iloc[i + HOLD_DAYS])
        ret = exit_ / entry - 1 - 0.002  # 0.1% each side
        out.append({"ticker": ticker, "date": idx[i].strftime("%Y-%m-%d"),
                    "entry": round(entry, 2), "exit": round(exit_, 2),
                    "return": round(ret, 4)})
        last_exit = i + HOLD_DAYS
    return out


def backtest(progress=None) -> dict:
    """Run the screener across the universe; return the full distribution."""
    all_signals: list[dict] = []
    for t in SMALLCAP_UNIVERSE:
        if progress:
            progress(t)
        all_signals.extend(_signals_for(t))

    if not all_signals:
        return {"ok": False, "signals": 0,
                "message": "No signals matched — data may be unavailable."}

    rets = np.array([s["return"] for s in all_signals])
    wins = rets[rets > 0]
    losses = rets[rets <= 0]
    win_rate = len(wins) / len(rets)
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(-losses.mean()) if len(losses) else 0.0
    payoff = avg_win / avg_loss if avg_loss > 0 else float("inf")
    profit_factor = (wins.sum() / -losses.sum()
                     if len(losses) and losses.sum() < 0 else float("inf"))
    expectancy = float(rets.mean())

    median = float(np.median(rets))
    # How much of the total profit comes from just the top 3 winners? If the
    # edge is a couple of lottery tickets, that's fragile, not a real system.
    top3 = float(np.sort(rets)[-3:].sum()) if len(rets) >= 3 else float(rets.sum())
    total_win = float(wins.sum()) if len(wins) else 0.0
    outlier_driven = total_win > 0 and top3 / total_win > 0.5

    # Honest verdict: momentum/small-cap is allowed a low win rate ONLY if the
    # payoff is big enough (profit factor > 1.75, per the risk framework).
    justified = (profit_factor != float("inf") and profit_factor >= 1.75
                 and expectancy > 0 and not outlier_driven)
    if expectancy <= 0:
        verdict = ("NOT JUSTIFIED. The average signal LOSES money "
                   f"({expectancy * 100:+.1f}% expectancy). On this evidence "
                   "the sleeve should not trade — and remember survivorship "
                   "bias means the real number is worse.")
    elif profit_factor == float("inf") or profit_factor < 1.75:
        verdict = (f"MARGINAL / NOT JUSTIFIED. Expectancy is positive "
                   f"({expectancy * 100:+.1f}%) but the profit factor is below "
                   "the 1.75 bar this risk level demands. Add survivorship "
                   "bias and it likely fails.")
    elif outlier_driven:
        verdict = (f"FRAGILE — NOT JUSTIFIED AS-IS. The profit factor "
                   f"({profit_factor:.2f}) clears the bar, but over half the "
                   "total profit comes from just the 3 biggest winners, and "
                   f"the MEDIAN signal is {median * 100:+.1f}% (a typical "
                   "signal barely breaks even). This is a few lottery tickets, "
                   "not a repeatable edge. Add survivorship bias — the missing "
                   "bankruptcies — and it likely turns negative. Do NOT rely "
                   "on it; treat any live use as a tiny experiment.")
    else:
        verdict = (f"JUSTIFIED ON THIS DATA (with caveats). Profit factor "
                   f"{profit_factor:.2f} clears the 1.75 bar, expectancy is "
                   f"{expectancy * 100:+.1f}%, and it isn't driven by one or "
                   "two flukes. But survivorship bias and the catalyst proxy "
                   "still mean live results will be weaker — size the sleeve "
                   "small (10-20%) and watch the live hit rate.")

    winners = sorted(all_signals, key=lambda s: s["return"], reverse=True)
    return {
        "ok": True, "signals": len(rets),
        "win_rate": round(win_rate, 3),
        "avg_win": round(avg_win, 4), "avg_loss": round(avg_loss, 4),
        "payoff": None if payoff == float("inf") else round(payoff, 2),
        "profit_factor": None if profit_factor == float("inf") else round(profit_factor, 2),
        "expectancy": round(expectancy, 4),
        "best": winners[0], "worst": winners[-1],
        "median": round(median, 4),
        "outlier_driven": outlier_driven,
        "pct_up_over_20": round(win_rate, 3),
        "returns": [round(float(r), 4) for r in rets],
        "verdict": verdict, "justified": justified,
    }
