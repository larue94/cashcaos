"""Bulk daily price data for the whole S&P 500 in a few batched requests.

Alpaca allows many symbols per request, so ~1 year of daily bars for 500
stocks takes seconds, not hours. Cached once per day.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from trading.config import get_settings

_SP500_CSV = Path(__file__).resolve().parent / "sp500.csv"


def sp500() -> pd.DataFrame:
    """The S&P 500 constituent list (symbol, name, sector)."""
    df = pd.read_csv(_SP500_CSV)
    df = df.rename(columns={"Symbol": "symbol", "Security": "name",
                            "GICS Sector": "sector"})
    # Alpaca uses dots for share classes (BRK.B); the dataset already does too.
    return df[["symbol", "name", "sector"]]


def sp500_sectors() -> dict[str, str]:
    return dict(zip(sp500()["symbol"], sp500()["sector"]))


def bulk_daily_bars(symbols: list[str], days: int = 320,
                    progress=None) -> dict[str, pd.DataFrame]:
    """Daily OHLCV for many symbols at once. Returns {symbol: DataFrame}.

    Cached to one file per calendar day so repeat runs are instant.
    """
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    cache = settings.cache_dir / f"bulk_bars_{datetime.now():%Y%m%d}.pkl"
    if cache.exists():
        data = pd.read_pickle(cache)
        if set(symbols) <= set(data.keys()):
            return {s: data[s] for s in symbols}

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame

    client = StockHistoricalDataClient(settings.alpaca_api_key,
                                       settings.alpaca_secret_key)
    start = datetime.now() - timedelta(days=int(days * 1.6))
    out: dict[str, pd.DataFrame] = {}
    CHUNK = 100
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        if progress:
            progress(f"bars {i + 1}-{min(i + CHUNK, len(symbols))} of {len(symbols)}")
        try:
            bars = client.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=chunk, timeframe=TimeFrame.Day,
                start=start, adjustment="all")).df
        except Exception:  # noqa: BLE001 — a bad chunk shouldn't kill the scan
            continue
        if bars is None or bars.empty:
            continue
        for sym in bars.index.get_level_values(0).unique():
            d = bars.xs(sym, level=0).reset_index()
            df = pd.DataFrame({
                "Open": d["open"].values, "High": d["high"].values,
                "Low": d["low"].values, "Close": d["close"].values,
                "Volume": d["volume"].values,
            }, index=pd.to_datetime(d["timestamp"]).dt.tz_localize(None).dt.normalize())
            out[sym] = df

    try:
        pd.to_pickle(out, cache)
        # tidy older bulk caches
        for old in settings.cache_dir.glob("bulk_bars_*.pkl"):
            if old != cache:
                old.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    return out


def market_cap_millions(symbol: str) -> float | None:
    """Company size in $ millions, via Finnhub's free profile endpoint."""
    import requests
    settings = get_settings()
    if not settings.finnhub_api_key.strip():
        return None
    try:
        r = requests.get("https://finnhub.io/api/v1/stock/profile2",
                         params={"symbol": symbol,
                                 "token": settings.finnhub_api_key},
                         timeout=20)
        if r.ok:
            mc = r.json().get("marketCapitalization")
            return float(mc) if mc else None
    except Exception:  # noqa: BLE001
        return None
    return None
