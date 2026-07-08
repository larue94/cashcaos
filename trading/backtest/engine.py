"""The backtest engine — replays strategy rules over historical prices.

Design choice, in plain language: instead of a large third-party backtesting
framework, this is a small, fully transparent engine (~100 lines of actual
math) so every number on the dashboard can be traced to arithmetic you can
read. The core idea:

1. A strategy book produces a WEIGHTS table: for every day and every stock,
   what fraction of the portfolio is held (0 = not held).
2. The engine turns weights into daily portfolio returns:
       today's return = yesterday's weights x today's stock moves
                        minus trading costs (0.1% of every dollar traded)
   Using YESTERDAY's weights is the honesty rule — you can't buy a stock
   with today's close price using information from today's close.
3. It also extracts the individual TRADES (entry date, exit date, profit)
   so win rate, profit factor etc. can be reported.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADE_COST = 0.001  # 0.1% of traded value, charged on every buy and sell


@dataclass
class BookResult:
    """Everything the metrics module needs about one backtested book."""

    name: str
    daily_returns: pd.Series          # portfolio daily % moves, after costs
    weights: pd.DataFrame             # what was held, day by day
    trades: pd.DataFrame              # one row per completed round-trip


def run_weights(name: str, weights: pd.DataFrame, prices: pd.DataFrame) -> BookResult:
    """Turn a weights table into daily returns and a trade list."""
    weights = weights.reindex(prices.index).fillna(0.0)
    stock_returns = prices.pct_change(fill_method=None).fillna(0.0)

    # Yesterday's holdings earn today's moves (no lookahead).
    held = weights.shift(1).fillna(0.0)
    gross = (held * stock_returns).sum(axis=1)

    # Trading cost: 0.1% of every dollar's worth of position change.
    traded = (weights - held).abs().sum(axis=1)
    daily = gross - traded * TRADE_COST

    return BookResult(name=name, daily_returns=daily, weights=weights,
                      trades=_extract_trades(weights, prices))


def _extract_trades(weights: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """List each completed round-trip: when in, when out, what it made."""
    rows = []
    for ticker in weights.columns:
        w = weights[ticker].to_numpy()
        px = prices[ticker].to_numpy()
        dates = weights.index
        entry_i = None
        for i in range(len(w)):
            holding = w[i] > 0
            if holding and entry_i is None:
                entry_i = i
            elif not holding and entry_i is not None:
                if px[entry_i] > 0 and not np.isnan(px[entry_i]) and not np.isnan(px[i]):
                    ret = px[i] / px[entry_i] - 1 - 2 * TRADE_COST
                    rows.append({"ticker": ticker, "entry": dates[entry_i],
                                 "exit": dates[i], "days": i - entry_i,
                                 "return": ret})
                entry_i = None
        # A position still open at the end is not counted as a completed trade.
    return pd.DataFrame(rows, columns=["ticker", "entry", "exit", "days", "return"])


# ----------------------------------------------------------------------
# The three core strategy books, as mechanical rules.
#
# Why mechanical? A 16-year backtest replays thousands of days — the AI
# reasoning layer can't be asked about each one. These rules are the
# testable skeleton of what each book does; in live operation the agents
# add judgment ON TOP of rules like these, never instead of them.
# ----------------------------------------------------------------------

def swing_weights(prices: pd.DataFrame, rsi_entry: int = 40,
                  rsi_exit: int = 65) -> pd.DataFrame:
    """Swing book (days-weeks): buy healthy stocks on short-term dips.

    Enter when a stock is in a long-term uptrend (above its 200-day average
    price) but short-term washed out (RSI below `rsi_entry`). Exit when the
    bounce has played out (RSI above `rsi_exit`) or the uptrend breaks.
    """
    sma200 = prices.rolling(200).mean()
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))

    uptrend = (prices > sma200) & sma200.notna()
    enter = uptrend & (rsi < rsi_entry)
    leave = (rsi > rsi_exit) | ~uptrend

    holding = pd.DataFrame(False, index=prices.index, columns=prices.columns)
    state = np.zeros(len(prices.columns), dtype=bool)
    enter_np, leave_np = enter.to_numpy(), leave.to_numpy()
    out = np.zeros(enter_np.shape, dtype=bool)
    for i in range(len(prices)):
        state = (state & ~leave_np[i]) | enter_np[i]
        out[i] = state
    holding.iloc[:, :] = out
    return _equal_weight(holding)


def monthly_weights(prices: pd.DataFrame, lookback: int = 126,
                    top_n: int = 3) -> pd.DataFrame:
    """Monthly book (~1-3 months): each month, hold the few strongest stocks.

    At each month start, rank the universe by how far each stock has run
    over the last `lookback` trading days (momentum) and hold the `top_n`
    leaders for the month — but only ones still above their 200-day average
    (never buy a downtrend just because it fell less than others).
    """
    momentum = prices.pct_change(lookback, fill_method=None)
    sma200 = prices.rolling(200).mean()
    ok = (prices > sma200) & momentum.notna()

    month_starts = prices.groupby(prices.index.to_period("M")).head(1).index
    holding = pd.DataFrame(False, index=prices.index, columns=prices.columns)
    current = pd.Series(False, index=prices.columns)
    for date in prices.index:
        if date in month_starts:
            ranked = momentum.loc[date].where(ok.loc[date]).dropna()
            ranked = ranked.sort_values(ascending=False)
            picks = ranked.head(top_n).index
            current = pd.Series(prices.columns.isin(picks), index=prices.columns)
        holding.loc[date] = current
    return _equal_weight(holding)


def longterm_weights(prices: pd.DataFrame, fast: int = 50,
                     slow: int = 200) -> pd.DataFrame:
    """Long-term book (6+ months): stay invested while the big trend is up.

    Hold every stock whose `fast`-day average price is above its `slow`-day
    average (the classic sign of a durable uptrend); step aside when it
    isn't. Positions naturally last many months.
    """
    fast_ma = prices.rolling(fast).mean()
    slow_ma = prices.rolling(slow).mean()
    holding = (fast_ma > slow_ma) & slow_ma.notna()
    return _equal_weight(holding)


def _equal_weight(holding: pd.DataFrame) -> pd.DataFrame:
    """Split capital equally among whatever is held; all-cash when nothing is."""
    count = holding.sum(axis=1)
    weights = holding.astype(float).div(count.replace(0, np.nan), axis=0)
    return weights.fillna(0.0)


# What the walk-forward optimizer is allowed to try for each book.
# Small grids on purpose: a huge grid finds flukes ("overfitting").
PARAM_GRIDS = {
    "swing": [{"rsi_entry": e, "rsi_exit": x}
              for e in (35, 40, 45) for x in (60, 65, 70)],
    "monthly": [{"lookback": lb, "top_n": n}
                for lb in (63, 126, 189) for n in (3, 4)],
    "long-term": [{"fast": f, "slow": 200} for f in (50, 100)],
}

BOOK_BUILDERS = {
    "swing": swing_weights,
    "monthly": monthly_weights,
    "long-term": longterm_weights,
}
