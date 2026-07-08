"""Daily price history, with a local cache and two independent sources.

Source 1 — Yahoo Finance (via yfinance): free, history back to 2010+.
Source 2 — Alpaca's own market data (free with your paper keys): used
automatically whenever Yahoo is unreachable or rate-limits us. Alpaca's
history starts around 2016, which is plenty for day-to-day operation;
long-range backtests prefer Yahoo when it's available.

The first request for a stock downloads its daily history and saves it in
trading/data/cache/. Later requests reuse the saved copy and only re-download
when it is more than a few days stale, so the system stays fast and polite to
the free services.

Honesty note (flagged again wherever backtests are shown): free sources
mainly carry companies that still exist today. Stocks that went bankrupt or
were delisted are missing, which makes historical results look somewhat
better than reality ("survivorship bias").
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

from trading.config import get_settings

# yfinance prints alarming technical errors when Yahoo is briefly down; we
# handle those failures ourselves (with a fallback), so keep its noise quiet.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _cache_path(symbol: str) -> Path:
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings.cache_dir / f"prices_{symbol.upper()}.csv"


def _from_yfinance(symbol: str) -> pd.DataFrame:
    settings = get_settings()
    df = yf.download(
        symbol,
        start=settings.price_history_start,
        auto_adjust=True,   # adjusted for splits/dividends — the honest series
        progress=False,
        multi_level_index=False,
    )
    if df is None or df.empty:
        raise ValueError(f"yfinance returned no data for '{symbol}'")
    df.index.name = "Date"
    return df[_COLUMNS]


def _from_yahoo_direct(symbol: str) -> pd.DataFrame:
    """Yahoo's chart service via a plain web request.

    Some networks (including this cloud environment) break the specialized
    connection style the yfinance library uses; a plain request often still
    gets through.
    """
    settings = get_settings()
    start = int(datetime.strptime(settings.price_history_start, "%Y-%m-%d").timestamp())
    resp = requests.get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}",
        params={"period1": start, "period2": int(datetime.now().timestamp()),
                "interval": "1d", "events": "div,split"},
        headers={"User-Agent": _BROWSER_UA},
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    adjclose = result["indicators"]["adjclose"][0]["adjclose"]
    df = pd.DataFrame(
        {
            "Open": quote["open"], "High": quote["high"], "Low": quote["low"],
            "Close": adjclose, "Volume": quote["volume"],
        },
        index=pd.to_datetime(result["timestamp"], unit="s").normalize(),
    ).dropna()
    if df.empty:
        raise ValueError(f"Yahoo chart service returned no data for '{symbol}'")
    df.index.name = "Date"
    # Scale Open/High/Low by the same split/dividend adjustment as Close.
    raw_close = pd.Series(quote["close"], index=df.index[:0].union(df.index)).reindex(df.index)
    factor = (df["Close"] / raw_close).fillna(1.0)
    for col in ("Open", "High", "Low"):
        df[col] = df[col] * factor
    return df[_COLUMNS]


def _from_alpaca(symbol: str) -> pd.DataFrame:
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    settings = get_settings()
    client = StockHistoricalDataClient(settings.alpaca_api_key, settings.alpaca_secret_key)
    bars = client.get_stock_bars(
        StockBarsRequest(
            symbol_or_symbols=symbol.upper(),
            timeframe=TimeFrame.Day,
            start=datetime(2016, 1, 1),   # roughly where Alpaca's history begins
            adjustment="all",             # adjusted for splits/dividends
        )
    ).df
    if bars is None or bars.empty:
        raise ValueError(f"Alpaca returned no data for '{symbol}'")
    bars = bars.reset_index()
    df = pd.DataFrame(
        {
            "Open": bars["open"].values, "High": bars["high"].values,
            "Low": bars["low"].values, "Close": bars["close"].values,
            "Volume": bars["volume"].values,
        },
        # Alpaca stamps each daily bar at midnight New York time; in UTC that
        # is 04:00/05:00 the same calendar day, so the UTC date is the trading date.
        index=pd.to_datetime(bars["timestamp"]).dt.tz_localize(None).dt.normalize(),
    )
    df.index.name = "Date"
    return df[_COLUMNS]


def get_daily_prices(symbol: str, refresh: bool = False) -> tuple[pd.DataFrame, str]:
    """Daily prices for one stock, plus which source supplied them.

    Returns (table, source). The table has one row per trading day: Open,
    High, Low, Close (split/dividend-adjusted) and Volume (shares traded).
    Source is 'cache', 'yahoo', or 'alpaca'.
    """
    path = _cache_path(symbol)
    if not refresh and path.exists():
        df = pd.read_csv(path, index_col="Date", parse_dates=True)
        if not df.empty:
            # Weekends/holidays produce no new data, so "fresh enough" means
            # the newest row is within the last 4 calendar days.
            age = datetime.now() - df.index[-1].to_pydatetime()
            if age <= timedelta(days=4):
                return df, "cache"

    errors = []
    for source, fetch in (("yahoo", _from_yfinance),
                          ("yahoo", _from_yahoo_direct),
                          ("alpaca", _from_alpaca)):
        try:
            df = fetch(symbol)
            df.to_csv(path)
            return df, source
        except Exception as e:  # noqa: BLE001 — try the next source
            errors.append(f"{fetch.__name__}: {e}")

    raise RuntimeError(
        f"All price sources failed for '{symbol}'. If the ticker is spelled "
        "correctly (e.g. AAPL, not Apple), this is a temporary network issue — "
        "wait a few minutes and retry. Details: " + " | ".join(errors)
    )


def latest_close(symbol: str) -> float:
    """Most recent end-of-day price for one stock."""
    df, _ = get_daily_prices(symbol)
    return float(df["Close"].iloc[-1])
