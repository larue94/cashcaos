"""Deep analysis — the full fundamentals + technicals report for one stock.

This is what the "Full analysis" button shows. It goes well beyond the short
agent summary: every fundamental number we have, a fuller technical picture,
Fibonacci retracement levels, and a tentative Elliott-Wave read.

Honesty, stated up front and repeated in the output:
- Fibonacci levels are objective arithmetic once you pick the swing — but
  WHICH swing high/low to measure from is a judgement call, so treat the
  levels as "zones of interest", not magic numbers.
- Elliott Wave is INHERENTLY SUBJECTIVE. Expert practitioners routinely
  disagree on the wave count for the same chart, and no algorithm can label
  waves authoritatively. What we produce is a tentative, mechanical read of
  the recent swings — a talking point, not a forecast. It is clearly flagged
  as experimental everywhere it appears.
"""

import io

import numpy as np
import pandas as pd

from trading.data.fundamentals import EdgarClient, SnapshotUnavailable, get_snapshot
from trading.data.prices import get_daily_prices


# ---------------- technical indicators ----------------

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal, macd - signal


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df["High"], df["Low"], df["Close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ---------------- Fibonacci ----------------

def fibonacci(df: pd.DataFrame, lookback: int = 120) -> dict:
    """Retracement levels between the recent swing low and high."""
    window = df.tail(lookback)
    hi = float(window["High"].max())
    lo = float(window["Low"].min())
    hi_date = window["High"].idxmax()
    lo_date = window["Low"].idxmin()
    price = float(df["Close"].iloc[-1])
    up_move = hi_date > lo_date  # low came first -> measuring an up-swing
    span = hi - lo
    if span <= 0:
        return {"ok": False}
    ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
    # In an up-swing, retracements come DOWN from the high; flip for down-swing.
    levels = {}
    for r in ratios:
        levels[r] = hi - span * r if up_move else lo + span * r
    # where does price sit? find the two bracketing levels
    ordered = sorted(levels.items(), key=lambda kv: kv[1])
    position = "below all levels"
    for i in range(len(ordered) - 1):
        if ordered[i][1] <= price <= ordered[i + 1][1]:
            position = (f"between the {ordered[i][0] * 100:.1f}% and "
                        f"{ordered[i + 1][0] * 100:.1f}% levels")
            break
    return {"ok": True, "high": hi, "low": lo, "up_move": up_move,
            "price": price, "levels": levels, "position": position,
            "hi_date": hi_date.strftime("%Y-%m-%d"),
            "lo_date": lo_date.strftime("%Y-%m-%d")}


# ---------------- swing pivots + tentative Elliott Wave ----------------

def swing_pivots(close: pd.Series, pct: float = 0.06) -> list[dict]:
    """Zigzag: alternating highs/lows separated by at least `pct` moves."""
    prices = close.to_numpy()
    dates = close.index
    if len(prices) < 10:
        return []
    pivots = [{"i": 0, "price": float(prices[0]), "date": dates[0]}]
    direction = 0  # 1 up, -1 down
    last = prices[0]
    last_i = 0
    for i in range(1, len(prices)):
        change = prices[i] / last - 1
        if direction >= 0 and prices[i] > last:
            last, last_i = prices[i], i
        elif direction <= 0 and prices[i] < last:
            last, last_i = prices[i], i
        if direction >= 0 and change <= -pct:
            pivots.append({"i": last_i, "price": float(prices[last_i]),
                           "date": dates[last_i], "kind": "high"})
            direction, last, last_i = -1, prices[i], i
        elif direction <= 0 and change >= pct:
            pivots.append({"i": last_i, "price": float(prices[last_i]),
                           "date": dates[last_i], "kind": "low"})
            direction, last, last_i = 1, prices[i], i
    return pivots[-9:]  # keep the most recent swings


def elliott_read(pivots: list[dict]) -> dict:
    """A TENTATIVE, mechanical Elliott-Wave-style read. Not a forecast."""
    if len(pivots) < 4:
        return {"ok": False,
                "note": "Not enough clean swings recently to attempt a wave count."}
    # Look at the last up to 6 pivots and describe the alternating structure.
    recent = pivots[-6:]
    legs = []
    for a, b in zip(recent, recent[1:]):
        move = b["price"] / a["price"] - 1
        legs.append((b.get("kind", "?"), move))
    up_legs = [m for k, m in legs if m > 0]
    down_legs = [m for k, m in legs if m < 0]
    # Very rough impulse-vs-correction heuristic.
    if len(legs) >= 5 and len([m for _, m in legs if m > 0]) >= 3:
        label = ("The recent structure LOOKS like a 5-swing impulse sequence "
                 "(the classic 1-2-3-4-5 shape), which Elliott theory reads as "
                 "a trend in force. If so, a corrective A-B-C pullback often "
                 "follows.")
    elif len(legs) >= 3 and down_legs and up_legs:
        label = ("The recent structure looks corrective (a choppy A-B-C style "
                 "pullback) rather than a clean trending impulse.")
    else:
        label = ("The swings are too few or too irregular to suggest a clear "
                 "impulse or corrective pattern.")
    last_dir = "up" if legs and legs[-1][1] > 0 else "down"
    return {"ok": True, "label": label, "last_leg": last_dir,
            "swings": [(p.get("kind", "?"), round(p["price"], 2)) for p in recent]}


# ---------------- fundamentals ----------------

def fundamentals_block(ticker: str) -> list[str]:
    out = []
    try:
        s = get_snapshot(ticker)
        if s.get("company_name"):
            out.append(f"{s['company_name']} — {s.get('sector') or '?'}"
                       + (f" / {s['industry']}" if s.get("industry") else ""))
        def pct(x): return f"{x * 100:.1f}%" if x is not None else "n/a"
        if s.get("market_cap"):
            out.append(f"Market value: ${s['market_cap'] / 1e9:,.1f}B")
        pe = s.get("forward_pe") or s.get("trailing_pe")
        if pe:
            out.append(f"Valuation: {pe:.1f}x earnings"
                       + (" (forward)" if s.get("forward_pe") else " (trailing)"))
        if s.get("profit_margin") is not None:
            out.append(f"Profit margin: {pct(s['profit_margin'])} "
                       "(kept per $1 of sales)")
        if s.get("revenue_growth") is not None:
            out.append(f"Revenue growth: {pct(s['revenue_growth'])} year/year")
        if s.get("return_on_equity") is not None:
            out.append(f"Return on equity: {pct(s['return_on_equity'])}")
        if s.get("debt_to_equity") is not None:
            out.append(f"Debt vs equity: {s['debt_to_equity']:.0f}% "
                       + ("(heavy)" if s["debt_to_equity"] > 200 else "(moderate)"
                          if s["debt_to_equity"] > 80 else "(conservative)"))
        if s.get("free_cash_flow"):
            out.append(f"Free cash flow: ${s['free_cash_flow'] / 1e9:,.1f}B")
    except SnapshotUnavailable:
        out.append("(Live stats snapshot temporarily unavailable — showing "
                   "official filings only.)")
    # EDGAR official multi-year trend
    try:
        series = EdgarClient().annual_series(ticker)
        revs = series["revenue"][:4]
        incs = dict(series["net_income"])
        if revs:
            out.append("Officially filed results (SEC):")
            for year, rev in revs:
                ni = incs.get(year)
                line = f"  {year}: revenue ${rev / 1e9:,.0f}B"
                if ni is not None:
                    line += f", net {'profit' if ni >= 0 else 'loss'} ${abs(ni) / 1e9:,.1f}B"
                out.append(line)
    except Exception:  # noqa: BLE001
        pass
    return out or ["No fundamentals available for this symbol."]


# ---------------- the assembled report ----------------

def deep_report(ticker: str) -> dict:
    """Structured deep analysis for one ticker."""
    df, _src = get_daily_prices(ticker)
    close = df["Close"]
    price = float(close.iloc[-1])
    sma20 = float(close.rolling(20).mean().iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    weekly = close.resample("W").last().dropna()
    sma200w = (float(weekly.rolling(200).mean().iloc[-1])
               if len(weekly) >= 200 else None)
    rsi = float(_rsi(close).iloc[-1])
    macd, signal, hist = _macd(close)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = float((bb_mid + 2 * bb_std).iloc[-1])
    bb_lo = float((bb_mid - 2 * bb_std).iloc[-1])
    atr = float(_atr(df).iloc[-1])
    hi52 = float(df["High"].tail(252).max())
    lo52 = float(df["Low"].tail(252).min())

    try:
        statements = EdgarClient().financial_statements(ticker)
    except Exception:  # noqa: BLE001
        statements = None

    return {
        "ticker": ticker.upper(), "price": price,
        "fundamentals": fundamentals_block(ticker),
        "statements": statements,
        "tech": {
            "price": price, "sma20": sma20, "sma50": sma50, "sma200": sma200,
            "sma200w": sma200w,
            "rsi": rsi, "macd": float(macd.iloc[-1]),
            "macd_signal": float(signal.iloc[-1]), "macd_hist": float(hist.iloc[-1]),
            "bb_up": bb_up, "bb_lo": bb_lo, "atr": atr,
            "hi52": hi52, "lo52": lo52,
            "pct_of_52w_range": (price - lo52) / (hi52 - lo52) if hi52 > lo52 else 0.5,
        },
        "fibonacci": fibonacci(df),
        "elliott": elliott_read(swing_pivots(close)),
    }


def chart_image(ticker: str, days: int = 300) -> bytes:
    """Draw a real technical chart (price + moving averages + Fibonacci + RSI)
    as a PNG, returned as bytes — for sending to Telegram or saving."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    df, _ = get_daily_prices(ticker)
    hist = df.tail(days + 200)
    close = hist["Close"]
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    rsi = _rsi(close)
    view = hist.tail(days)
    fib = fibonacci(df)

    plt.style.use("dark_background")
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(10, 6.4), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    fig.patch.set_facecolor("#171a19")
    for a in (ax, axr):
        a.set_facecolor("#171a19")
        a.grid(color="#2a2f2c", linewidth=0.6)
        for s in a.spines.values():
            s.set_color("#2a2f2c")
        a.tick_params(colors="#aeb6b0", labelsize=8)

    idx = view.index
    ax.plot(idx, view["Close"], color="#4a95e8", linewidth=1.8, label="Price")
    ax.plot(idx, sma50.tail(days), color="#22b985", linewidth=1.1,
            linestyle="--", label="50-day avg")
    ax.plot(idx, sma200.tail(days), color="#e0a542", linewidth=1.1,
            linestyle="--", label="200-day avg")
    # Fibonacci levels as faint horizontal lines
    if fib.get("ok"):
        for r, lvl in fib["levels"].items():
            if view["Low"].min() * 0.97 <= lvl <= view["High"].max() * 1.03:
                ax.axhline(lvl, color="#8b877c", linewidth=0.6, alpha=0.5)
                ax.text(idx[-1], lvl, f" {r * 100:.1f}%", color="#8b877c",
                        fontsize=7, va="center")
    ax.set_title(f"{ticker.upper()} — price, moving averages & Fibonacci levels",
                 color="#eef1ee", fontsize=12, loc="left")
    ax.legend(loc="upper left", fontsize=8, facecolor="#1c201e",
              edgecolor="#2a2f2c", labelcolor="#eef1ee")
    ax.set_ylabel("Price ($)", color="#aeb6b0", fontsize=9)

    axr.plot(idx, rsi.tail(days), color="#c58af0", linewidth=1.2)
    axr.axhline(70, color="#e26b5d", linewidth=0.7, linestyle=":")
    axr.axhline(30, color="#3fbf62", linewidth=0.7, linestyle=":")
    axr.set_ylim(0, 100)
    axr.set_ylabel("RSI", color="#aeb6b0", fontsize=9)
    axr.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axr.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                facecolor="#171a19")
    plt.close(fig)
    return buf.getvalue()


def format_report(rep: dict) -> str:
    """Plain-English multi-section text (for Telegram / the web app)."""
    t = rep["tech"]
    lines = [f"📊 DEEP ANALYSIS — {rep['ticker']}  (${rep['price']:,.2f})", ""]

    lines.append("— FUNDAMENTALS (what the business is worth) —")
    lines += rep["fundamentals"]
    lines.append("")

    st = rep.get("statements")
    if st:
        def row(label, key, unit="B"):
            vals = st.get(key) or []
            if not vals:
                return None
            years = [str(y) for y, _ in vals]
            if unit == "$":  # per-share
                nums = [f"${v:,.2f}" for _, v in vals]
            else:
                nums = [f"${v / 1e9:,.1f}B" for _, v in vals]
            return f"  {label:<20} " + "  ".join(
                f"{y}:{n}" for y, n in zip(years, nums))

        lines.append("— INCOME STATEMENT (SEC-filed, annual) —")
        for lbl, key in [("Revenue", "revenue"), ("Gross profit", "gross_profit"),
                         ("Operating income", "operating_income"),
                         ("Net income", "net_income")]:
            r = row(lbl, key)
            if r:
                lines.append(r)
        eps = row("Diluted EPS", "eps_diluted", unit="$")
        if eps:
            lines.append(eps)
        lines.append("")
        lines.append("— BALANCE SHEET (SEC-filed, annual) —")
        for lbl, key in [("Total assets", "total_assets"),
                         ("Total liabilities", "total_liabilities"),
                         ("Shareholder equity", "equity"), ("Cash", "cash"),
                         ("Long-term debt", "long_term_debt")]:
            r = row(lbl, key)
            if r:
                lines.append(r)
        ocf = row("Operating cash flow", "operating_cash_flow")
        if ocf:
            lines.append("— CASH FLOW —")
            lines.append(ocf)
        lines.append("")

    lines.append("— TECHNICALS (what the chart is doing) —")
    trend = ("uptrend" if t["sma50"] > t["sma200"] else "downtrend")
    lines.append(f"Trend: {trend} (50-day ${t['sma50']:,.2f} vs 200-day "
                 f"${t['sma200']:,.2f}); price is "
                 f"{'above' if t['price'] > t['sma50'] else 'below'} the 50-day.")
    if t.get("sma200w") is not None:
        above = t["price"] > t["sma200w"]
        lines.append(f"Secular trend: 200-WEEK average ${t['sma200w']:,.2f} — "
                     f"price is {'ABOVE' if above else 'BELOW'} it, "
                     + ("a multi-year bull backdrop (strongest long-term signal)."
                        if above else
                        "meaning the multi-year trend has broken — a major "
                        "long-term caution."))
    lines.append(f"Momentum: RSI {t['rsi']:.0f} "
                 + ("(overbought — stretched)" if t["rsi"] >= 70
                    else "(oversold — washed out)" if t["rsi"] <= 30
                    else "(neutral)") + ".")
    macd_state = ("bullish (MACD above its signal)" if t["macd"] > t["macd_signal"]
                  else "bearish (MACD below its signal)")
    lines.append(f"MACD: {macd_state} — a trend-momentum gauge.")
    lines.append(f"Bollinger band: ${t['bb_lo']:,.2f} … ${t['bb_up']:,.2f} "
                 "(price near the top = stretched high, near the bottom = "
                 "stretched low).")
    lines.append(f"Volatility (ATR): ±${t['atr']:,.2f}/day of typical swing.")
    lines.append(f"52-week range: ${t['lo52']:,.2f} … ${t['hi52']:,.2f} "
                 f"(price is {t['pct_of_52w_range'] * 100:.0f}% up that range).")
    lines.append("")

    fib = rep["fibonacci"]
    lines.append("— FIBONACCI RETRACEMENT (support/resistance zones) —")
    if fib.get("ok"):
        lines.append(f"Measured from the swing low ${fib['low']:,.2f} "
                     f"({fib['lo_date']}) to the high ${fib['high']:,.2f} "
                     f"({fib['hi_date']}).")
        for r, lvl in sorted(fib["levels"].items()):
            mark = "  ← price here" if abs(lvl - fib["price"]) < fib["price"] * 0.01 else ""
            lines.append(f"  {r * 100:5.1f}% : ${lvl:,.2f}{mark}")
        lines.append(f"Price is currently {fib['position']}.")
        lines.append("(These are zones where price often pauses or reverses — "
                     "treat as areas of interest, not exact triggers.)")
    else:
        lines.append("Not enough of a clean swing to draw Fibonacci levels.")
    lines.append("")

    ell = rep["elliott"]
    lines.append("— ELLIOTT WAVE (⚠️ experimental & subjective) —")
    if ell.get("ok"):
        lines.append(ell["label"])
        lines.append(f"Most recent swing direction: {ell['last_leg']}.")
    else:
        lines.append(ell.get("note", "No read available."))
    lines.append("⚠️ Elliott Wave counts are subjective — experts disagree on "
                 "the same chart, and no tool labels them authoritatively. This "
                 "is a mechanical talking point, NOT a prediction. Do not size a "
                 "trade on it.")
    lines.append("")
    lines.append("— SOURCES (review them yourself) —")
    st = rep.get("statements")
    if st:
        cik = st.get("cik")
        lines.append(f"Financials: {st.get('company', rep['ticker'])} official "
                     "SEC 10-K filings, via data.sec.gov (EDGAR).")
        lines.append(f"  Filings: https://www.sec.gov/cgi-bin/browse-edgar?"
                     f"action=getcompany&company={rep['ticker']}&type=10-K")
    lines.append("Prices/technicals: daily price history (Yahoo Finance / "
                 "Alpaca), computed in-house.")
    lines.append("Live stats (P/E, margins): Yahoo Finance. "
                 "News mood: Finnhub.")
    return "\n".join(lines)
