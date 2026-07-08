"""Walk-forward testing — the honest alternative to a single backtest.

The trap it avoids: if you tune rules on ALL of history and then measure
them on that same history, you get a flattering, useless number ("curve
fitting"). Walk-forward instead repeats, window by window:

    1. TRAIN: tune each book's settings on 3 years of data
    2. TEST:  freeze those settings and run them on the NEXT 1 year —
              data the tuning never saw
    3. Roll one year forward and repeat across all available history

The stitched-together TEST years form the "out-of-sample" track record —
the closest a backtest gets to how rules behave on genuinely unseen data.
The decay table (train score vs test score per window) shows how much of
the tuned performance was real vs. flukes.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from trading.backtest.engine import BOOK_BUILDERS, PARAM_GRIDS, BookResult, run_weights
from trading.backtest.universe import BENCHMARK, UNIVERSE
from trading.data.prices import get_daily_prices

TRAIN_YEARS = 3
TEST_YEARS = 1


def load_close_prices(tickers: list[str] | None = None,
                      progress=None) -> pd.DataFrame:
    """Daily closing prices for the whole universe + SPY, one column each."""
    tickers = tickers or (list(UNIVERSE) + [BENCHMARK])
    columns = {}
    for t in tickers:
        if progress:
            progress(t)
        df, _source = get_daily_prices(t)
        columns[t] = df["Close"]
    prices = pd.DataFrame(columns).sort_index()
    # Drop days where the benchmark itself has no data (holidays/gaps).
    return prices[prices[BENCHMARK].notna()]


@dataclass
class WindowReport:
    train_start: int
    test_year: int
    chosen_params: dict
    train_sharpe: float
    test_sharpe: float


@dataclass
class WalkForwardResult:
    book: str
    oos_returns: pd.Series               # stitched test-year daily returns
    oos_weights: pd.DataFrame
    trades: pd.DataFrame
    windows: list[WindowReport] = field(default_factory=list)


def _sharpe(returns: pd.Series) -> float:
    std = returns.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(returns.mean() / std * np.sqrt(252))


def run_book(book: str, prices: pd.DataFrame) -> WalkForwardResult:
    """Walk one strategy book forward across all available history."""
    builder = BOOK_BUILDERS[book]
    grid = PARAM_GRIDS[book]
    universe_prices = prices[[c for c in prices.columns if c != BENCHMARK]]

    years = sorted(prices.index.year.unique())
    # First usable test year: needs TRAIN_YEARS before it, plus the first
    # year is mostly indicator warm-up (200-day averages need history).
    test_years = [y for y in years[1:] if y - TRAIN_YEARS >= years[0]]

    oos_parts, weight_parts, trade_parts, windows = [], [], [], []
    for test_year in test_years:
        train_mask = (prices.index.year >= test_year - TRAIN_YEARS) & \
                     (prices.index.year < test_year)
        test_mask = prices.index.year == test_year
        if train_mask.sum() < 250 or test_mask.sum() < 20:
            continue

        # TRAIN: try every allowed setting, keep the best risk-adjusted one.
        # Weights are computed on FULL history (so indicators are warmed up)
        # but each setting is judged only on its train-period returns.
        best_params, best_sharpe, best_weights = None, -np.inf, None
        for params in grid:
            weights = builder(universe_prices, **params)
            result = run_weights(book, weights, universe_prices)
            s = _sharpe(result.daily_returns[train_mask])
            if s > best_sharpe:
                best_params, best_sharpe, best_weights = params, s, weights

        # TEST: frozen settings on the unseen year.
        result = run_weights(book, best_weights, universe_prices)
        test_returns = result.daily_returns[test_mask]
        oos_parts.append(test_returns)
        weight_parts.append(result.weights[test_mask])
        test_dates = prices.index[test_mask]
        in_window = (result.trades["exit"] >= test_dates[0]) & \
                    (result.trades["exit"] <= test_dates[-1])
        trade_parts.append(result.trades[in_window])
        windows.append(WindowReport(
            train_start=test_year - TRAIN_YEARS, test_year=test_year,
            chosen_params=best_params, train_sharpe=round(best_sharpe, 2),
            test_sharpe=round(_sharpe(test_returns), 2)))

    return WalkForwardResult(
        book=book,
        oos_returns=pd.concat(oos_parts) if oos_parts else pd.Series(dtype=float),
        oos_weights=pd.concat(weight_parts) if weight_parts else pd.DataFrame(),
        trades=pd.concat(trade_parts) if trade_parts else pd.DataFrame(
            columns=["ticker", "entry", "exit", "days", "return"]),
        windows=windows)


def run_all(prices: pd.DataFrame, progress=None) -> dict[str, WalkForwardResult]:
    results = {}
    for book in BOOK_BUILDERS:
        if progress:
            progress(book)
        results[book] = run_book(book, prices)
    return results
