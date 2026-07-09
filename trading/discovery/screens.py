"""The mechanical market screens — pure math over the whole universe.

core_screen():     rank all 500 S&P names by quality-trend; the top handful
                   become the day's watchlist for the core books.
movers():          the whole market's top gainers + most active (Alpaca).
smallcap_screen(): apply the sleeve's runner pattern (3x volume + breakout +
                   gap catalyst) to today's movers, then verify market cap
                   < $2B — candidates for the high-risk sleeve.
"""

import numpy as np
import pandas as pd

from trading.discovery.market_data import (bulk_daily_bars, market_cap_millions,
                                           sp500)

# The sleeve pattern (mirrors strategies/smallcap.py backtest thresholds)
VOLUME_SPIKE = 3.0
BREAKOUT_LOOKBACK = 20
GAP_CATALYST = 0.05
MAX_MARKET_CAP_MILLIONS = 2000  # < $2B


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    val = (100 - 100 / (1 + rs)).iloc[-1]
    return float(val) if pd.notna(val) else 50.0


def core_screen(top_n: int = 6, progress=None) -> list[dict]:
    """Rank the S&P 500 mechanically; return the strongest candidates.

    Score per stock (0-100): durable uptrend, 6-month momentum, healthy RSI,
    proximity to highs. No AI, no cost — this only decides who gets the full
    (more expensive) agent treatment.
    """
    constituents = sp500()
    bars = bulk_daily_bars(list(constituents["symbol"]), progress=progress)
    rows = []
    for sym, df in bars.items():
        if len(df) < 220:
            continue
        close = df["Close"]
        price = float(close.iloc[-1])
        sma50 = float(close.rolling(50).mean().iloc[-1])
        sma200 = float(close.rolling(200).mean().iloc[-1])
        mom126 = float(close.iloc[-1] / close.iloc[-126] - 1) if len(close) > 126 else 0
        rsi = _rsi(close)
        hi52 = float(close.tail(252).max())

        score = 50
        if sma50 > sma200:
            score += 15
        if price > sma50:
            score += 10
        score += max(-10, min(15, mom126 * 50))       # momentum, capped
        if 40 <= rsi <= 70:
            score += 8
        elif rsi > 78:
            score -= 8
        if price >= hi52 * 0.95:
            score += 5                                  # near 52-week high
        rows.append({"symbol": sym, "score": round(min(100, score), 1),
                     "price": round(price, 2), "mom_6m": round(mom126, 3),
                     "rsi": round(rsi, 0)})
    ranked = sorted(rows, key=lambda r: r["score"], reverse=True)
    return ranked[:top_n]


def movers(top: int = 25) -> dict:
    """Today's market-wide biggest gainers and most-active stocks."""
    from alpaca.data.historical.screener import ScreenerClient
    from alpaca.data.requests import MarketMoversRequest, MostActivesRequest

    from trading.config import get_settings
    s = get_settings()
    sc = ScreenerClient(s.alpaca_api_key, s.alpaca_secret_key)
    gainers = sc.get_market_movers(MarketMoversRequest(top=top)).gainers
    actives = sc.get_most_actives(MostActivesRequest(top=top)).most_actives
    return {
        "gainers": [{"symbol": g.symbol, "pct": round(float(g.percent_change), 1),
                     "price": float(g.price)} for g in gainers],
        "actives": [{"symbol": a.symbol} for a in actives],
    }


def smallcap_screen(progress=None, max_candidates: int = 3) -> list[dict]:
    """Live small-cap runner candidates: the sleeve pattern on today's movers.

    Pattern (same as the honest backtest): volume >= 3x its 50-day average,
    close above the prior 20-day high, gap up >= 5% — then confirm the
    company is actually small (< $2B) via Finnhub. Returns at most a few,
    strongest first. Uses the last COMPLETED day's bar, matching the backtest.
    """
    try:
        mv = movers()
    except Exception:  # noqa: BLE001
        return []
    # candidates = gainers + actives, de-duplicated, skipping obvious non-stocks
    symbols = []
    for row in mv["gainers"] + mv["actives"]:
        sym = row["symbol"]
        if sym not in symbols and sym.isalpha() and len(sym) <= 5:
            symbols.append(sym)
    if not symbols:
        return []
    if progress:
        progress(f"checking {len(symbols)} movers against the runner pattern")
    bars = bulk_daily_bars(symbols, days=90)

    hits = []
    for sym, df in bars.items():
        if len(df) < 55:
            continue
        close, high, vol, open_ = df["Close"], df["High"], df["Volume"], df["Open"]
        vol_avg = float(vol.rolling(50).mean().iloc[-1])
        prior_high = float(high.iloc[-(BREAKOUT_LOOKBACK + 1):-1].max())
        gap = float(open_.iloc[-1] / close.iloc[-2] - 1)
        v_ratio = float(vol.iloc[-1] / vol_avg) if vol_avg else 0
        price = float(close.iloc[-1])
        if (v_ratio >= VOLUME_SPIKE and price > prior_high
                and gap >= GAP_CATALYST and price >= 1.0):
            hits.append({"symbol": sym, "price": round(price, 2),
                         "volume_x": round(v_ratio, 1),
                         "gap_pct": round(gap * 100, 1)})
    # strongest volume signals first; then the (rate-limited) market-cap check
    hits.sort(key=lambda h: h["volume_x"], reverse=True)
    confirmed = []
    for h in hits:
        if len(confirmed) >= max_candidates:
            break
        mc = market_cap_millions(h["symbol"])
        h["market_cap_m"] = mc
        if mc is not None and mc >= MAX_MARKET_CAP_MILLIONS:
            continue  # too big for the small-cap sleeve
        confirmed.append(h)
    return confirmed
