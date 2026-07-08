"""Market regime detection — is the market trending up, choppy, or falling?

Agents should not treat a raging bull market and a scary bear market the
same way. This classifies each day into one of three regimes using the
S&P 500 (SPY):

- BULL   : durable uptrend and calm — price above its 200-day average, the
           50-day above the 200-day, and volatility not elevated.
- BEAR   : downtrend — price below its 200-day average and the 50-day below
           the 200-day.
- CHOPPY : everything in between — mixed signals or high volatility, the
           whipsaw conditions where trend-following gets chopped up.

It also reports how each strategy book actually performed in each regime, so
you can see (not guess) which book earns its keep when.
"""

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def classify_series(spy_close: pd.Series) -> pd.Series:
    """Label every day 'bull' / 'choppy' / 'bear' from SPY's own behavior."""
    sma50 = spy_close.rolling(50).mean()
    sma200 = spy_close.rolling(200).mean()
    daily = spy_close.pct_change(fill_method=None)
    vol20 = daily.rolling(20).std() * np.sqrt(TRADING_DAYS)
    vol_median = vol20.expanding(min_periods=60).median()

    trend_up = (spy_close > sma200) & (sma50 > sma200)
    trend_down = (spy_close < sma200) & (sma50 < sma200)
    high_vol = vol20 > vol_median * 1.3

    regime = pd.Series("choppy", index=spy_close.index)
    regime[trend_up & ~high_vol] = "bull"
    regime[trend_down] = "bear"
    return regime.where(sma200.notna(), other=np.nan)


def current_regime(spy_close: pd.Series) -> tuple[str, dict]:
    """Today's regime plus the supporting numbers, in plain terms."""
    regime = classify_series(spy_close)
    label = regime.dropna().iloc[-1] if regime.notna().any() else "unknown"
    sma200 = float(spy_close.rolling(200).mean().iloc[-1])
    price = float(spy_close.iloc[-1])
    vol20 = float(spy_close.pct_change(fill_method=None).rolling(20).std().iloc[-1]
                  * np.sqrt(TRADING_DAYS))
    explain = {
        "bull": "The market is in a calm uptrend — trend-following and "
                "momentum books tend to do best here.",
        "bear": "The market is in a downtrend — the safest move is often to "
                "hold more cash; the circuit breaker guards the downside.",
        "choppy": "The market is choppy or volatile — whipsaws are common, so "
                  "be more selective and expect trend signals to misfire.",
        "unknown": "Not enough history yet to classify the market.",
    }[label]
    return label, {
        "price": round(price, 2), "sma200": round(sma200, 2),
        "above_200day": price > sma200,
        "volatility": round(vol20, 3), "explain": explain}


def performance_by_regime(book_returns: pd.Series,
                          regime_series: pd.Series) -> dict:
    """How one book did in each regime: return, annualized Sharpe, day count."""
    aligned = pd.concat([book_returns, regime_series.reindex(book_returns.index)],
                        axis=1, keys=["r", "regime"]).dropna()
    out = {}
    for label in ("bull", "choppy", "bear"):
        seg = aligned[aligned["regime"] == label]["r"]
        if len(seg) < 5:
            out[label] = {"days": len(seg), "total": None, "sharpe": None,
                          "annualized": None}
            continue
        total = float((1 + seg).prod() - 1)
        sd = seg.std()
        sharpe = 0.0 if sd == 0 else float(seg.mean() / sd * np.sqrt(TRADING_DAYS))
        ann = (1 + total) ** (TRADING_DAYS / len(seg)) - 1
        out[label] = {"days": len(seg), "total": round(total, 4),
                      "sharpe": round(sharpe, 2), "annualized": round(ann, 4)}
    return out
