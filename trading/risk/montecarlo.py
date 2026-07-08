"""Monte Carlo risk-of-ruin — how likely is a book to breach its drawdown cap?

A single backtest shows ONE path history happened to take. But the same set
of trades in a different order could have been far worse. Monte Carlo asks:
if we shuffle and resample this book's real trades thousands of times, in how
many of those alternate histories does the account fall past its drawdown
limit (20% for core books, 30-35% for the small-cap sleeve)?

That probability — the "risk of ruin" for the drawdown budget — is a far
more honest gauge of downside than a single backtest number.

Assumption stated plainly: trades are simulated one-at-a-time at the book's
position size. Real books hold several positions at once, which changes the
exact number; this is a clear, conservative-leaning approximation, not a
guarantee.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def risk_of_ruin(daily_returns, *, dd_limit: float = 0.20,
                 path_years: float = 1.0, block: int = 10,
                 n_sims: int = 5000, seed: int = 7) -> dict:
    """Probability a book breaches its drawdown limit over a ~1-year path.

    Method: BLOCK bootstrap of the book's ACTUAL daily returns. We resample
    the real return stream in short blocks (to keep the real clustering of
    good and bad days), build thousands of alternate 1-year equity paths, and
    count how many fall past the drawdown limit at any point.

    Using the book's own daily returns — which already reflect its real
    position sizing and how many names it holds at once — makes these numbers
    consistent with the observed backtest drawdown, unlike a naive
    one-trade-at-a-time simulation which understates the danger.
    """
    r = pd.Series(daily_returns).dropna().to_numpy()
    if len(r) < 60:
        return {"ok": False,
                "message": f"Only {len(r)} days of returns — need at least 60 "
                           "to simulate meaningfully."}
    rng = np.random.default_rng(seed)
    path_len = int(path_years * TRADING_DAYS)
    n_blocks = path_len // block + 1
    max_start = len(r) - block

    breaches = 0
    final_returns = np.empty(n_sims)
    max_dds = np.empty(n_sims)
    for i in range(n_sims):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        seq = np.concatenate([r[s:s + block] for s in starts])[:path_len]
        equity = np.cumprod(1 + seq)
        peak = np.maximum.accumulate(equity)
        dd = (equity / peak - 1).min()
        max_dds[i] = -dd
        final_returns[i] = equity[-1] - 1
        if -dd >= dd_limit:
            breaches += 1

    return {
        "ok": True, "n_sims": n_sims, "path_days": path_len,
        "prob_breach": round(breaches / n_sims, 4),
        "median_max_dd": round(float(np.median(max_dds)), 4),
        "worst_1pct_max_dd": round(float(np.percentile(max_dds, 99)), 4),
        "median_final_return": round(float(np.median(final_returns)), 4),
        "worst_5pct_final_return": round(float(np.percentile(final_returns, 5)), 4),
        "dd_limit": dd_limit,
    }
