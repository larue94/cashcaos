"""Phase 4 test: walk-forward backtest of the 3 core books + the dashboard.

Run it with:

    python -m trading.test_backtest

What happens (takes a few minutes the first time):
1. Downloads daily prices for a 20-stock universe + SPY (cached afterwards)
2. Walk-forward tests each core strategy book: tune settings on 3 years,
   test on the NEXT unseen year, roll forward through all available history
3. Computes the full institutional metric set per book and for the combined
   portfolio (capital split equally across the three books)
4. Writes the dashboard: trading/dashboard/output/dashboard.html — open it
   in any browser
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

OUTPUT = Path(__file__).resolve().parent / "dashboard" / "output" / "dashboard.html"

_BOOK_INTRO = {
    "swing": ("Swing book (days–weeks)",
              "Buys fundamentally-screened stocks in an uptrend on short-term "
              "dips; sells when the bounce plays out. Mean-reversion style."),
    "monthly": ("Monthly book (~1–3 months)",
                "Each month holds the few strongest stocks by 6-month "
                "momentum, if still in an uptrend. Momentum style."),
    "long-term": ("Long-term book (6+ months)",
                  "Stays invested in each stock while its long-term trend is "
                  "up; steps to cash when it breaks. Trend-following style."),
}


def main() -> int:
    print()
    print("Walk-forward backtest — 3 core books vs buy-and-hold SPY")
    print("=" * 62)

    from trading.audit_log import log_event
    from trading.backtest.metrics import (compute_metrics, monthly_table,
                                          overfit_warning)
    from trading.backtest.universe import BENCHMARK, UNIVERSE
    from trading.backtest.walkforward import load_close_prices, run_all
    from trading.dashboard.build import build

    print("Step 1/4: fetching prices for 20 stocks + SPY (cached after first run)...")
    prices = load_close_prices(progress=lambda t: print(f"    {t}", flush=True))
    start, end = prices.index[0], prices.index[-1]
    coverage = f"{start.date()} to {end.date()}"
    print(f"    Coverage: {coverage}")

    print("Step 2/4: walk-forward testing each book (tune 3y -> test next 1y)...")
    results = run_all(prices, progress=lambda b: print(f"    {b} book...", flush=True))

    print("Step 3/4: computing the institutional metric set...")
    spy_all = prices[BENCHMARK].pct_change(fill_method=None).fillna(0.0)
    styles = {"swing": "mean-reversion", "monthly": "momentum",
              "long-term": "momentum"}
    sections, book_returns = [], {}
    for book, res in results.items():
        spy = spy_all.reindex(res.oos_returns.index).fillna(0.0)
        metrics = compute_metrics(res.oos_returns, spy, res.trades,
                                  res.oos_weights, UNIVERSE, styles[book])
        title, subtitle = _BOOK_INTRO[book]
        sections.append({"name": title, "subtitle": subtitle,
                         "metrics": metrics, "returns": res.oos_returns,
                         "spy": spy, "monthly": monthly_table(res.oos_returns),
                         "windows": res.windows})
        book_returns[book] = res.oos_returns

    # Whole portfolio: capital split equally across the three books.
    combined = pd.DataFrame(book_returns).dropna().mean(axis=1)
    spy_c = spy_all.reindex(combined.index).fillna(0.0)
    all_trades = pd.concat([r.trades for r in results.values()])
    portfolio_metrics = compute_metrics(combined, spy_c, all_trades,
                                        None, UNIVERSE, "momentum")
    sections.insert(0, {
        "name": "Whole portfolio (all three books, equal split)",
        "subtitle": "One third of capital in each core book. The small-cap "
                    "sleeve is added in Phase 6.",
        "metrics": portfolio_metrics, "returns": combined, "spy": spy_c,
        "monthly": monthly_table(combined)})

    corr = pd.DataFrame(book_returns).corr().round(2)

    # Save a small headline summary the live web app can show inline.
    import json as _json
    headline = {mm.name: {"display": mm.display, "rag": mm.rag}
                for mm in portfolio_metrics
                if mm.name in ("Total return", "CAGR", "Sharpe ratio",
                               "Sortino ratio", "Calmar ratio", "Max drawdown",
                               "1-day VaR 95%", "Jensen's alpha (annualized)",
                               "Information ratio vs SPY")}
    (OUTPUT.parent / "summary.json").write_text(_json.dumps({
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "coverage": coverage, "metrics": headline}))

    banners = [
        "Survivorship bias: this backtest trades 20 large companies that are "
        "still successful TODAY. Companies that collapsed along the way are "
        "missing from free data, so results look better than live reality "
        "would have. Treat these numbers as how the RULES behave, not as a "
        "promised return.",
        f"Data coverage: {coverage}. The design target is 2010–2026; on this "
        "network the free price source with the longest history was "
        "unavailable, so the backup source (2016+) was used. On a home "
        "computer the window extends automatically.",
        "All results are OUT-OF-SAMPLE: every year's performance uses "
        "settings tuned only on the 3 years before it. Includes 0.1% "
        "per-trade costs. Risk-free rate treated as 0.",
    ]
    metrics_by_book = {s["name"]: s["metrics"] for s in sections}
    warning = overfit_warning(metrics_by_book)
    if warning:
        banners.insert(0, warning)

    print("Step 4/4: writing the dashboard...")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    build(OUTPUT, "Paper-Trading System — Backtest Dashboard", banners,
          sections, corr,
          f"Generated {datetime.now():%Y-%m-%d %H:%M}. Walk-forward, "
          f"out-of-sample, costs included. Benchmark: buy-and-hold SPY.")

    # Console summary.
    spy_total = float((1 + spy_c).prod() - 1)
    print()
    print("=" * 62)
    print(f"OUT-OF-SAMPLE RESULTS ({combined.index[0].date()} to "
          f"{combined.index[-1].date()})")
    print("-" * 62)
    for s in sections:
        total = float((1 + s["returns"]).prod() - 1)
        sharpe = next(m for m in s["metrics"] if m.name == "Sharpe ratio")
        dd = next(m for m in s["metrics"] if m.name == "Max drawdown")
        print(f"  {s['name'][:44]:<46} {total * 100:+7.1f}%  "
              f"Sharpe {sharpe.display:>5}  MaxDD {dd.display:>6}")
    print(f"  {'SPY buy & hold (the bar to beat)':<46} {spy_total * 100:+7.1f}%")
    print("-" * 62)
    if warning:
        print("  ⚠️ OVERFITTING FLAG RAISED — see dashboard banner.")
    print(f"""
Dashboard written to:
  {OUTPUT}
Open that file in any web browser (double-click it). Every metric has a
plain-English explanation and a red/amber/green flag next to it.
""")
    log_event("system", "backtest",
              f"Walk-forward backtest complete ({coverage}). Portfolio "
              f"{float((1 + combined).prod() - 1) * 100:+.1f}% vs SPY "
              f"{spy_total * 100:+.1f}%. Dashboard: {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
