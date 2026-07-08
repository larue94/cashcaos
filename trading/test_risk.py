"""Phase 6 test: regime detection, correlation limits, Kelly sizing, Monte
Carlo risk-of-ruin, and the high-risk small-cap sleeve.

Run it with:

    python -m trading.test_risk

It runs all five risk tools on real data and prints a plain-English report,
then writes trading/dashboard/output/risk.html for the visual version.
"""

import sys
from datetime import datetime
from pathlib import Path

RISK_HTML = Path(__file__).resolve().parent / "dashboard" / "output" / "risk.html"


def main() -> int:
    print()
    print("Risk calibration report (Phase 6)")
    print("=" * 64)

    import pandas as pd

    from trading.backtest.universe import BENCHMARK
    from trading.backtest.walkforward import load_close_prices, run_all
    from trading.risk import correlation, kelly, montecarlo, regime
    from trading.strategies import smallcap

    print("Loading prices + running the walk-forward books (cached after "
          "Phase 4)...")
    prices = load_close_prices()
    results = run_all(prices)
    spy = prices[BENCHMARK]

    # ---- 1. Regime detection ----
    print("\n" + "-" * 64)
    print("1) MARKET REGIME")
    label, info = regime.current_regime(spy)
    print(f"   Today: {label.upper()} — {info['explain']}")
    print(f"   (SPY ${info['price']} vs its 200-day avg ${info['sma200']}; "
          f"volatility {info['volatility'] * 100:.0f}%/yr)")
    regime_series = regime.classify_series(spy)
    print("\n   How each book performed in each regime (out-of-sample):")
    print(f"   {'book':<12}{'regime':<9}{'days':>6}{'total':>10}{'Sharpe':>8}")
    regime_perf = {}
    for book, res in results.items():
        perf = regime.performance_by_regime(res.oos_returns, regime_series)
        regime_perf[book] = perf
        for reg in ("bull", "choppy", "bear"):
            c = perf[reg]
            tot = "—" if c["total"] is None else f"{c['total'] * 100:+.0f}%"
            sh = "—" if c["sharpe"] is None else f"{c['sharpe']:.2f}"
            print(f"   {book:<12}{reg:<9}{c['days']:>6}{tot:>10}{sh:>8}")

    # ---- 2. Correlation limits (demonstration) ----
    print("\n" + "-" * 64)
    print("2) CORRELATION LIMITS (Risk agent guard)")
    # Demonstrate on tightly-correlated small-cap names (crypto miners move
    # together) so you can see the guard actually BLOCK a crowded bet.
    try:
        demo_prices = _demo_prices(["RIOT", "MARA", "COIN", "CLSK", "XOM"])
        demo_sectors = {"RIOT": "Crypto", "MARA": "Crypto", "COIN": "Crypto",
                        "CLSK": "Crypto", "XOM": "Energy"}
        cases = [("XOM", ["RIOT", "MARA"]),          # different sector -> allow
                 ("COIN", ["RIOT", "MARA"]),         # 3rd crypto -> at limit
                 ("CLSK", ["RIOT", "MARA", "COIN"])] # 4th crypto -> BLOCK
        for cand, holds in cases:
            allowed, reasons = correlation.check(cand, holds, demo_prices,
                                                 sectors=demo_sectors)
            verdict = "ALLOW ✓" if allowed else "BLOCK ✗"
            print(f"   Holding {holds}, considering {cand}: {verdict}")
            print(f"      {reasons[0] if not allowed else reasons[-1]}")
    except Exception as e:  # noqa: BLE001
        print(f"   (correlation demo skipped — data hiccup: {e})")

    # ---- 3. Kelly sizing (from each book's backtest trades) ----
    print("\n" + "-" * 64)
    print("3) KELLY POSITION SIZING (from each book's real trade record)")
    kelly_rows = {}
    for book, res in results.items():
        rets = res.trades["return"].tolist()
        stats = kelly.kelly_stats(rets)
        frac, reason = kelly.position_fraction(rets)
        kelly_rows[book] = (stats, frac, reason)
        wr = "—" if stats["win_rate"] is None else f"{stats['win_rate'] * 100:.0f}%"
        pay = "—" if stats["payoff"] is None else f"{stats['payoff']}x"
        print(f"   {book:<12} {len(rets):>3} trades  win {wr:>4}  payoff {pay:>5}"
              f"  -> size {frac * 100:.1f}%")
        print(f"      {reason}")

    # ---- 4. Monte Carlo risk of ruin ----
    print("\n" + "-" * 64)
    print("4) MONTE CARLO RISK-OF-RUIN (chance of breaching the drawdown cap)")
    mc_rows = {}
    for book, res in results.items():
        mc = montecarlo.risk_of_ruin(res.oos_returns, dd_limit=0.20)
        mc_rows[book] = mc
        if not mc["ok"]:
            print(f"   {book:<12} {mc['message']}")
            continue
        print(f"   {book:<12} P(breach 20% drawdown) = "
              f"{mc['prob_breach'] * 100:.1f}%   "
              f"median worst-drop {mc['median_max_dd'] * 100:.0f}%   "
              f"1-in-100 worst {mc['worst_1pct_max_dd'] * 100:.0f}%")

    # ---- 5. High-risk small-cap sleeve ----
    print("\n" + "-" * 64)
    print("5) HIGH-RISK SMALL-CAP SLEEVE — screener backtest (losers included)")
    print("   Screening ~30 volatile small/mid-caps for the runner pattern")
    print("   (3x volume + 20-day breakout + gap-up catalyst)...")
    sc = smallcap.backtest(progress=lambda t: print(f"      {t}", flush=True,
                                                    end="\r"))
    print(" " * 30, end="\r")
    if sc["ok"]:
        print(f"   Signals found: {sc['signals']}   "
              f"Win rate (up after 20 days): {sc['win_rate'] * 100:.0f}%")
        print(f"   Avg win {sc['avg_win'] * 100:+.1f}%   "
              f"Avg loss {-sc['avg_loss'] * 100:+.1f}%   "
              f"Profit factor "
              f"{sc['profit_factor'] if sc['profit_factor'] else '∞'}")
        print(f"   Expectancy per signal: {sc['expectancy'] * 100:+.1f}%   "
              f"Median: {sc['median'] * 100:+.1f}%")
        print(f"   Best: {sc['best']['ticker']} {sc['best']['return'] * 100:+.0f}% "
              f"| Worst: {sc['worst']['ticker']} "
              f"{sc['worst']['return'] * 100:+.0f}%")
        print(f"\n   VERDICT: {sc['verdict']}")
    else:
        print(f"   {sc['message']}")

    # ---- Write the HTML report ----
    _write_html(label, info, regime_perf, kelly_rows, mc_rows, sc, results)
    print("\n" + "=" * 64)
    print(f"Visual report written to:\n  {RISK_HTML}")
    print("Open it in any browser for the charts and full detail.")
    from trading.audit_log import log_event
    log_event("system", "risk-report",
              f"Phase 6 risk report generated. Regime: {label}. "
              f"Small-cap sleeve justified: {sc.get('justified')}.")
    return 0


def _demo_prices(tickers):
    """Small helper: fetch a few tickers' closes for the correlation demo."""
    import pandas as pd

    from trading.data.prices import get_daily_prices
    cols = {}
    for t in tickers:
        df, _ = get_daily_prices(t)
        cols[t] = df["Close"]
    return pd.DataFrame(cols).dropna()


def _write_html(regime_label, regime_info, regime_perf, kelly_rows, mc_rows,
                sc, results):
    import html

    from trading.dashboard.build import _CSS

    def sec(title, body):
        return f"<h2>{html.escape(title)}</h2><div class='card'>{body}</div>"

    # regime table
    rt = "<table class='metrics'><tr><th>Book</th><th>Regime</th><th>Days</th>" \
         "<th>Total return</th><th>Sharpe</th></tr>"
    for book, perf in regime_perf.items():
        for reg in ("bull", "choppy", "bear"):
            c = perf[reg]
            tot = "—" if c["total"] is None else f"{c['total'] * 100:+.0f}%"
            sh = "—" if c["sharpe"] is None else f"{c['sharpe']:.2f}"
            rt += (f"<tr><td>{book}</td><td>{reg}</td><td>{c['days']}</td>"
                   f"<td>{tot}</td><td>{sh}</td></tr>")
    rt += "</table>"
    regime_body = (
        f"<p><b>Today: {regime_label.upper()}.</b> "
        f"{html.escape(regime_info.get('explain', ''))}</p>" + rt +
        "<p class='sub'>Agents weight signals by regime: trend/momentum "
        "signals count more in a bull market, less when it's choppy or "
        "bearish.</p>")

    # kelly table
    kt = ("<table class='metrics'><tr><th>Book</th><th>Trades</th>"
          "<th>Win rate</th><th>Payoff</th><th>Half-Kelly size</th></tr>")
    for book, (stats, frac, reason) in kelly_rows.items():
        wr = "—" if stats["win_rate"] is None else f"{stats['win_rate'] * 100:.0f}%"
        pay = "—" if stats["payoff"] is None else f"{stats['payoff']}x"
        kt += (f"<tr><td>{book}</td><td>{stats['n']}</td><td>{wr}</td>"
               f"<td>{pay}</td><td><b>{frac * 100:.1f}%</b></td></tr>")
    kt += ("</table><p class='sub'>Live trading uses each book's REAL closed "
           "trades; the flat 5% cap applies until a book has 20+ of them. "
           "Numbers here are bootstrapped from the backtest for illustration.</p>")

    # monte carlo table
    mt = ("<table class='metrics'><tr><th>Book</th>"
          "<th>Chance of breaching 20% drawdown</th>"
          "<th>Median worst drop</th><th>1-in-100 worst drop</th></tr>")
    for book, mc in mc_rows.items():
        if not mc.get("ok"):
            mt += f"<tr><td>{book}</td><td colspan='3'>{mc['message']}</td></tr>"
            continue
        rag = ("green" if mc["prob_breach"] < 0.1 else
               "amber" if mc["prob_breach"] < 0.3 else "red")
        mt += (f"<tr><td>{book}</td>"
               f"<td><span class='chip {rag}'>{mc['prob_breach'] * 100:.1f}%</span></td>"
               f"<td>{mc['median_max_dd'] * 100:.0f}%</td>"
               f"<td>{mc['worst_1pct_max_dd'] * 100:.0f}%</td></tr>")
    mt += ("</table><p class='sub'>Each book's real trades are reshuffled "
           "thousands of times; this is the share of those alternate histories "
           "that fell past the 20% drawdown limit. Lower is safer.</p>")

    # small-cap
    if sc.get("ok"):
        hist = _histogram(sc["returns"])
        sc_body = (
            f"<p>{hist}</p>"
            f"<table class='metrics'>"
            f"<tr><td>Signals found (losers included)</td><td><b>{sc['signals']}</b></td></tr>"
            f"<tr><td>Win rate (up after 20 days)</td><td>{sc['win_rate'] * 100:.0f}%</td></tr>"
            f"<tr><td>Average win / average loss</td><td>{sc['avg_win'] * 100:+.1f}% / {-sc['avg_loss'] * 100:+.1f}%</td></tr>"
            f"<tr><td>Median signal (the typical one)</td><td>{sc['median'] * 100:+.1f}%</td></tr>"
            f"<tr><td>Profit factor</td><td>{sc['profit_factor'] if sc['profit_factor'] else '∞'}</td></tr>"
            f"<tr><td>Expectancy per signal</td><td>{sc['expectancy'] * 100:+.1f}%</td></tr>"
            f"<tr><td>Best / worst single signal</td><td>{sc['best']['return'] * 100:+.0f}% ({sc['best']['ticker']}) / {sc['worst']['return'] * 100:+.0f}% ({sc['worst']['ticker']})</td></tr>"
            f"</table>"
            f"<div class='banner {'crit' if not sc['justified'] else ''}' "
            f"style='margin-top:12px'><b>Verdict:</b> {html.escape(sc['verdict'])}</div>")
    else:
        sc_body = f"<p>{html.escape(sc.get('message', 'No data.'))}</p>"

    banner = (
        "This page reports the system's downside controls. The honest headline: "
        "controlling risk means accepting lower headline returns — that trade is "
        "the whole point. Small-cap-sleeve results especially are optimistic "
        "because free data omits companies that went bankrupt (survivorship "
        "bias) and the 'catalyst' is proxied by a price gap.")

    body = (
        f"<div class='banner'>⚠️ {banner}</div>"
        + sec("1 · Market regime & per-regime performance", regime_body)
        + sec("2 · Kelly-criterion position sizing (half-Kelly)", kt)
        + sec("3 · Monte Carlo risk-of-ruin", mt)
        + sec("4 · High-risk small-cap sleeve (screener, losers included)", sc_body))

    RISK_HTML.parent.mkdir(parents=True, exist_ok=True)
    RISK_HTML.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Risk Calibration Report</title><style>{_CSS}</style></head>"
        f"<body><div class='wrap'><h1>Risk Calibration Report</h1>"
        f"<p class='sub'>Generated {datetime.now():%Y-%m-%d %H:%M}. "
        f"Phase 6: regime detection, correlation limits, Kelly sizing, Monte "
        f"Carlo risk-of-ruin, and the high-risk small-cap sleeve.</p>"
        + body + "</div></body></html>", encoding="utf-8")


def _histogram(returns: list[float]) -> str:
    """A tiny text-free SVG histogram of signal returns."""
    import numpy as np
    arr = np.array(returns)
    bins = np.linspace(-0.5, 0.5, 21)
    counts, edges = np.histogram(np.clip(arr, -0.5, 0.5), bins=bins)
    W, H, B = 900, 140, 24
    bw = (W - 40) / len(counts)
    mx = max(counts.max(), 1)
    bars = ""
    for i, c in enumerate(counts):
        h = (H - B - 6) * c / mx
        x = 20 + i * bw
        mid = (edges[i] + edges[i + 1]) / 2
        color = "var(--good)" if mid > 0 else "var(--crit)" if mid < 0 else "var(--muted)"
        bars += (f"<rect x='{x:.1f}' y='{H - B - h:.1f}' width='{bw - 2:.1f}' "
                 f"height='{h:.1f}' fill='{color}' rx='2'/>")
    zero_x = 20 + (0.5) * (W - 40)
    return (f"<svg viewBox='0 0 {W} {H}' width='100%'>{bars}"
            f"<line x1='{zero_x}' y1='6' x2='{zero_x}' y2='{H - B}' "
            f"stroke='var(--axis)' stroke-dasharray='3 3'/>"
            f"<text x='20' y='{H - 6}' font-size='11' fill='var(--muted)'>-50%</text>"
            f"<text x='{zero_x - 6}' y='{H - 6}' font-size='11' fill='var(--muted)'>0</text>"
            f"<text x='{W - 20}' y='{H - 6}' text-anchor='end' font-size='11' "
            f"fill='var(--muted)'>+50%</text></svg>"
            "<p class='sub'>Distribution of every signal's 20-day result "
            "(clipped at ±50%). Red bars left of zero are losers — the ones a "
            "cherry-picked backtest would hide.</p>")


if __name__ == "__main__":
    sys.exit(main())
