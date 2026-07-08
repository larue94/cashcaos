"""The institutional metric set, computed from daily returns + trades.

Every metric comes with:
- a plain-English one-line explanation (shown on the dashboard)
- the institutional benchmark it is judged against
- a red/amber/green flag

Fine print that applies everywhere: risk-free rate treated as 0 for
simplicity; "days" means trading days (~252 per year).
"""

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Metric:
    name: str
    display: str          # formatted value, e.g. "1.34" or "12.5%"
    benchmark: str        # e.g. ">1 good, >2 elite"
    rag: str              # "green" | "amber" | "red" | "info"
    explain: str          # one plain-English line
    value: float | None = None


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _cagr(returns: pd.Series) -> float:
    total = float((1 + returns).prod())
    years = len(returns) / TRADING_DAYS
    if years <= 0 or total <= 0:
        return 0.0
    return total ** (1 / years) - 1


def _sharpe(returns: pd.Series) -> float:
    sd = returns.std()
    return 0.0 if sd == 0 or np.isnan(sd) else float(returns.mean() / sd * np.sqrt(TRADING_DAYS))


def _sortino(returns: pd.Series) -> float:
    downside = returns[returns < 0]
    dd = downside.std()
    return 0.0 if dd == 0 or np.isnan(dd) else float(returns.mean() / dd * np.sqrt(TRADING_DAYS))


def _drawdown_stats(returns: pd.Series) -> tuple[float, int, int | None]:
    """(max depth as positive fraction, peak-to-trough days, recovery days or None)."""
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    dd = equity / peak - 1
    if dd.min() >= 0:
        return 0.0, 0, 0
    trough_i = int(dd.to_numpy().argmin())
    depth = float(-dd.iloc[trough_i])
    peak_value = peak.iloc[trough_i]
    peak_i = int((equity.iloc[:trough_i + 1] >= peak_value).to_numpy().nonzero()[0][-1])
    after = equity.iloc[trough_i:]
    recovered = after[after >= peak_value]
    recovery = int((after.index.get_loc(recovered.index[0]))) if len(recovered) else None
    return depth, trough_i - peak_i, recovery


def _alpha_beta_pvalue(returns: pd.Series, spy: pd.Series) -> tuple[float, float, float]:
    """Jensen's alpha (annualized), beta, and the alpha's p-value."""
    df = pd.concat([returns, spy], axis=1, keys=["r", "m"]).dropna()
    r, m = df["r"].to_numpy(), df["m"].to_numpy()
    n = len(r)
    if n < 30:
        return 0.0, 1.0, 1.0
    var_m = m.var()
    beta = float(np.cov(r, m)[0, 1] / var_m) if var_m > 0 else 1.0
    alpha_daily = float(r.mean() - beta * m.mean())
    resid = r - (alpha_daily + beta * m)
    se2 = resid.var(ddof=2)
    se_alpha = math.sqrt(se2 * (1 / n + m.mean() ** 2 / (n * var_m))) if var_m > 0 else 0.0
    if se_alpha == 0:
        return alpha_daily * TRADING_DAYS, beta, 1.0
    t = alpha_daily / se_alpha
    # two-sided p-value via the normal approximation (fine for n > 250)
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return alpha_daily * TRADING_DAYS, beta, p


def rolling_alpha_90d(returns: pd.Series, spy: pd.Series) -> pd.Series:
    """Rolling 90-day Jensen's alpha, annualized — is the edge persistent?"""
    df = pd.concat([returns, spy], axis=1, keys=["r", "m"]).dropna()
    cov = df["r"].rolling(90).cov(df["m"])
    var = df["m"].rolling(90).var()
    beta = cov / var.replace(0, np.nan)
    alpha = (df["r"].rolling(90).mean() - beta * df["m"].rolling(90).mean()) * TRADING_DAYS
    return alpha.dropna()


def monthly_table(returns: pd.Series) -> pd.DataFrame:
    """The classic PM grid: one row per year, one column per month, plus YTD."""
    monthly = (1 + returns).groupby(
        [returns.index.year, returns.index.month]).prod() - 1
    table = monthly.unstack(level=1)
    table.columns = [pd.Timestamp(2000, int(m), 1).strftime("%b") for m in table.columns]
    table["Year"] = [(1 + returns[returns.index.year == y]).prod() - 1
                     for y in table.index]
    return table


def compute_metrics(returns: pd.Series, spy: pd.Series,
                    trades: pd.DataFrame | None = None,
                    weights: pd.DataFrame | None = None,
                    sectors: dict[str, str] | None = None,
                    book_style: str = "momentum") -> list[Metric]:
    """The full metric list for one strategy book (or the whole portfolio).

    book_style: "mean-reversion" (swing) or "momentum" — sets which win-rate
    benchmark applies, per the risk framework.
    """
    m: list[Metric] = []
    spy = spy.reindex(returns.index).fillna(0.0)

    # ---------- Returns ----------
    total = float((1 + returns).prod() - 1)
    m.append(Metric("Total return", _fmt_pct(total), "beat SPY over the same span",
                    "info", "How much $1 grew over the whole test, after costs.",
                    total))
    cagr = _cagr(returns)
    m.append(Metric("CAGR", _fmt_pct(cagr), "beat SPY's CAGR", "info",
                    "The equivalent steady yearly growth rate.", cagr))
    last = returns.index[-1]
    for label, mask in [
        ("MTD", (returns.index.year == last.year) & (returns.index.month == last.month)),
        ("QTD", (returns.index.year == last.year) & (returns.index.quarter == last.quarter)),
        ("YTD", returns.index.year == last.year),
    ]:
        val = float((1 + returns[mask]).prod() - 1)
        m.append(Metric(label, _fmt_pct(val), "—", "info",
                        f"Return so far this {'month' if label == 'MTD' else 'quarter' if label == 'QTD' else 'year'}.",
                        val))

    # ---------- Risk-adjusted ----------
    sharpe = _sharpe(returns)
    m.append(Metric("Sharpe ratio", f"{sharpe:.2f}", ">1 good, >2 elite",
                    "green" if sharpe > 1 else "amber" if sharpe > 0.5 else "red",
                    "Reward earned per unit of rockiness in the ride; the "
                    "single most-quoted skill number.", sharpe))
    sortino = _sortino(returns)
    m.append(Metric("Sortino ratio", f"{sortino:.2f}", ">2 elite",
                    "green" if sortino > 2 else "amber" if sortino > 1 else "red",
                    "Like Sharpe, but only counts DOWNWARD rockiness — "
                    "upside surprises aren't punished.", sortino))
    depth, dd_days, recovery = _drawdown_stats(returns)
    calmar = cagr / depth if depth > 0 else 0.0
    m.append(Metric("Calmar ratio", f"{calmar:.2f}", ">1 good, >3 elite",
                    "green" if calmar > 1 else "amber" if calmar > 0.5 else "red",
                    "Yearly growth divided by the worst peak-to-bottom fall — "
                    "growth per unit of worst pain.", calmar))
    excess = returns - spy
    ir = _sharpe(excess)
    m.append(Metric("Information ratio vs SPY", f"{ir:.2f}", ">0.5 good",
                    "green" if ir > 0.5 else "amber" if ir > 0 else "red",
                    "How consistently the strategy beats simply holding the "
                    "S&P 500 fund.", ir))

    # ---------- Risk ----------
    m.append(Metric("Max drawdown", _fmt_pct(depth), "<20% (core books)",
                    "green" if depth < 0.20 else "amber" if depth < 0.30 else "red",
                    "The deepest peak-to-bottom fall — the worst moment to "
                    "have checked the account.", depth))
    m.append(Metric("Drawdown length", f"{dd_days} trading days "
                    + (f"(recovered in {recovery})" if recovery is not None
                       else "(not yet recovered)"),
                    "shorter is better", "info",
                    "How long the fall took, and how long until the account "
                    "made it back.", float(dd_days)))
    vol = float(returns.std() * np.sqrt(TRADING_DAYS))
    m.append(Metric("Annualized volatility", _fmt_pct(vol), "SPY is ~15-20%",
                    "info", "Typical size of the yearly swings — the "
                    "bumpiness of the ride.", vol))
    var95 = float(-np.percentile(returns.dropna(), 5))
    var99 = float(-np.percentile(returns.dropna(), 1))
    m.append(Metric("1-day VaR 95%", _fmt_pct(var95), "context, not pass/fail",
                    "info", "On 19 days out of 20, a single day's loss stayed "
                    "smaller than this.", var95))
    m.append(Metric("1-day VaR 99%", _fmt_pct(var99), "context, not pass/fail",
                    "info", "On 99 days out of 100, a single day's loss stayed "
                    "smaller than this.", var99))
    tail = returns[returns <= -var95]
    cvar = float(-tail.mean()) if len(tail) else 0.0
    m.append(Metric("CVaR (expected shortfall)", _fmt_pct(cvar),
                    "context, not pass/fail", "info",
                    "When one of those worst-5% days DID happen, this was the "
                    "average size of the hit.", cvar))
    alpha, beta, pval = _alpha_beta_pvalue(returns, spy)
    m.append(Metric("Beta to SPY", f"{beta:.2f}", "1 = moves with the market",
                    "info", "How much the strategy moves when the market moves "
                    "1% — below 1 means calmer than the market.", beta))
    downside = returns[returns < 0].std() * np.sqrt(TRADING_DAYS)
    m.append(Metric("Downside deviation", _fmt_pct(float(downside or 0)),
                    "lower is better", "info",
                    "Volatility counting only the bad days.", float(downside or 0)))

    # ---------- Alpha ----------
    alpha_rag = ("green" if alpha > 0 and pval < 0.05
                 else "amber" if alpha > 0 else "red")
    m.append(Metric("Jensen's alpha (annualized)",
                    f"{_fmt_pct(alpha)} (p-value {pval:.2f})",
                    "positive AND p-value < 0.05",
                    alpha_rag,
                    "Skill-based return beyond what market exposure explains. "
                    "The p-value asks: could this just be luck? Below 0.05 "
                    "means probably not. Don't celebrate noise.", alpha))

    # ---------- Trade quality ----------
    if trades is not None and len(trades) > 0:
        wins = trades[trades["return"] > 0]
        losses = trades[trades["return"] <= 0]
        wr = len(wins) / len(trades)
        pf = (wins["return"].sum() / -losses["return"].sum()
              if len(losses) and losses["return"].sum() < 0 else float("inf"))
        pf_display = "∞ (no losses — suspicious!)" if pf == float("inf") else f"{pf:.2f}"
        if book_style == "mean-reversion":
            wr_bench, wr_green = ">50% for mean-reversion books", wr > 0.50
        else:
            wr_bench = ">40% acceptable for momentum if profit factor >1.75"
            wr_green = wr > 0.40 and (pf > 1.75 or pf == float("inf"))
        m.append(Metric("Win rate", _fmt_pct(wr), wr_bench,
                        "green" if wr_green else "amber" if wr > 0.35 else "red",
                        "Share of completed trades that made money.", wr))
        m.append(Metric("Profit factor", pf_display, ">1.5 good, >2 elite",
                        "green" if pf > 1.5 else "amber" if pf > 1.2 else "red",
                        "Total $ won divided by total $ lost — above 1 means "
                        "the wins outweigh the losses.",
                        None if pf == float("inf") else pf))
        avg_win = float(wins["return"].mean()) if len(wins) else 0.0
        avg_loss = float(-losses["return"].mean()) if len(losses) else 0.0
        ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")
        m.append(Metric("Avg win / avg loss",
                        f"{ratio:.2f}" if ratio != float("inf") else "∞",
                        ">1 preferred", "info",
                        "Size of the typical win vs the typical loss.",
                        None if ratio == float("inf") else ratio))
        expectancy = float(trades["return"].mean())
        m.append(Metric("Expectancy per trade", _fmt_pct(expectancy),
                        "positive", "green" if expectancy > 0 else "red",
                        "Average profit per trade — what one more typical "
                        "trade is 'worth'.", expectancy))
        m.append(Metric("Avg holding period",
                        f"{trades['days'].mean():.0f} trading days",
                        "matches the book's timeframe", "info",
                        "How long a typical position was held.",
                        float(trades["days"].mean())))
        m.append(Metric("Completed trades", f"{len(trades)}",
                        "more = more trustworthy stats", "info",
                        "Sample size behind the trade-quality numbers above.",
                        float(len(trades))))

    # ---------- Portfolio health ----------
    if weights is not None and len(weights) > 0:
        gross = float(weights.abs().sum(axis=1).mean())
        m.append(Metric("Gross exposure", _fmt_pct(gross), "≤100% (no leverage)",
                        "info", "Average share of capital invested (the rest "
                        "sat safely in cash).", gross))
        turnover = float(weights.diff().abs().sum(axis=1).mean() / 2 * TRADING_DAYS)
        m.append(Metric("Turnover (annualized)", f"{turnover:.1f}x",
                        "lower = fewer costs", "info",
                        "How many times per year the whole portfolio is "
                        "replaced — each turn costs 0.1% per side.", turnover))
        top5 = float(weights.apply(lambda row: row.nlargest(5).sum(), axis=1).mean())
        m.append(Metric("Top-5 position weight", _fmt_pct(top5),
                        "context, not pass/fail", "info",
                        "Average share of capital in the 5 largest holdings — "
                        "concentration cuts both ways.", top5))
        if sectors:
            sector_weights: dict[str, float] = {}
            for t in weights.columns:
                sector = sectors.get(t, "Other")
                sector_weights[sector] = sector_weights.get(sector, 0.0) + \
                    float(weights[t].mean())
            top_sector = max(sector_weights, key=sector_weights.get)
            m.append(Metric("Largest sector",
                            f"{top_sector} ({_fmt_pct(sector_weights[top_sector])})",
                            "diversification check", "info",
                            "The industry the portfolio leaned on most, on "
                            "average.", sector_weights[top_sector]))
    return m


def overfit_warning(all_metrics: dict[str, list[Metric]]) -> str | None:
    """If everything is green across every book, say the quiet part out loud."""
    graded = [mm for metrics in all_metrics.values() for mm in metrics
              if mm.rag in ("green", "amber", "red")]
    if graded and all(mm.rag == "green" for mm in graded):
        return ("Every graded metric is green across every book. In real "
                "quantitative work this almost never happens honestly — it "
                "usually means the rules have memorized the past "
                "(overfitting). Treat these results as too good to be true "
                "until live paper trading confirms them.")
    return None
