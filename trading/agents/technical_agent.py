"""Technical agent — reads the price chart, decides WHEN to act.

Pure arithmetic on daily prices (no AI):
- Trend: 50-day vs 200-day average price ("golden" alignment = uptrend)
- Momentum: RSI, a 0-100 gauge of how stretched recent moves are
- Breakout: is price pushing to a new 20-day high?
- Volume: is today's interest unusually high vs the 3-month norm?

The system's rule: fundamentals decide WHAT to buy, this agent decides WHEN.
"""

import pandas as pd

from trading.agents.opinion import Opinion, stance_from_score
from trading.data.prices import get_daily_prices


def _rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return float((100 - 100 / (1 + rs)).iloc[-1])


def form_opinion(ticker: str) -> Opinion:
    df, _source = get_daily_prices(ticker)
    if len(df) < 220:
        opinion = Opinion(
            agent="technical", ticker=ticker, score=50, stance="unavailable",
            notes=["Not enough price history for reliable chart signals "
                   f"(need ~1 year, have {len(df)} days)."])
        opinion.log()
        return opinion

    close = df["Close"]
    price = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    # 200-WEEK moving average (~4 years): the long-term secular trend line that
    # institutions watch. Computed from weekly closes; needs enough history.
    weekly = close.resample("W").last().dropna()
    sma200w = (float(weekly.rolling(200).mean().iloc[-1])
               if len(weekly) >= 200 else None)
    rsi = _rsi(close)
    high20 = float(df["High"].iloc[-21:-1].max())
    vol_avg = float(df["Volume"].rolling(63).mean().iloc[-1])
    vol_today = float(df["Volume"].iloc[-1])
    vol_ratio = vol_today / vol_avg if vol_avg else 1.0

    score = 50
    notes: list[str] = []

    if sma50 > sma200:
        score += 15
        notes.append("Long-term uptrend intact (50-day average price is above "
                     "the 200-day).")
    else:
        score -= 15
        notes.append("Long-term trend is down (50-day average below 200-day) — "
                     "usually better to wait.")

    # Secular trend: the 200-week average is the multi-year backbone.
    if sma200w is not None:
        if price > sma200w:
            score += 8
            notes.append(f"Above its 200-WEEK average (${sma200w:,.2f}) — in a "
                         "multi-year secular uptrend, the strongest long-term "
                         "backdrop.")
        else:
            score -= 12
            notes.append(f"Below its 200-WEEK average (${sma200w:,.2f}) — the "
                         "multi-year trend has broken down; a serious caution "
                         "flag for long-term buyers.")

    if price > sma50:
        score += 10
        notes.append("Price is above its 50-day average — recent strength.")
    else:
        score -= 5
        notes.append("Price is below its 50-day average — recent weakness.")

    if rsi >= 75:
        score -= 10
        notes.append(f"Overheated short-term (RSI {rsi:.0f}) — risk of chasing; "
                     "a pullback entry would be safer.")
    elif rsi <= 30:
        score += 5
        notes.append(f"Washed-out short-term (RSI {rsi:.0f}) — potential "
                     "rebound zone, but confirm the trend first.")
    elif 40 <= rsi <= 65:
        score += 10
        notes.append(f"Healthy momentum, not overstretched (RSI {rsi:.0f}).")

    if price > high20:
        score += 10
        notes.append("Breaking out above its recent 20-day price ceiling.")

    if vol_ratio >= 2:
        score += 5
        notes.append(f"Unusual attention: volume {vol_ratio:.1f}x the 3-month norm.")

    score = max(0, min(100, score))
    opinion = Opinion(
        agent="technical", ticker=ticker, score=score,
        stance=stance_from_score(score), notes=notes,
        data={"price": round(price, 2), "sma50": round(sma50, 2),
              "sma200": round(sma200, 2),
              "sma200w": round(sma200w, 2) if sma200w is not None else None,
              "rsi": round(rsi, 1), "volume_vs_norm": round(vol_ratio, 2)})
    opinion.log()
    return opinion
