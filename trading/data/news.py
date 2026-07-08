"""Recent news headlines via Finnhub's free tier.

The Sentiment agent (Phase 3) reads these headlines to gauge the mood around
a stock. The free tier allows 60 requests per minute — plenty for a daily
routine — so we pause briefly between calls to stay polite.

If no Finnhub key is set, functions raise MissingNewsKey with instructions;
callers treat news as "unavailable" rather than crashing.
"""

import time
from datetime import date, timedelta

import requests

from trading.config import get_settings

_BASE = "https://finnhub.io/api/v1"


class MissingNewsKey(Exception):
    """Raised when FINNHUB_API_KEY is blank in .env."""

    def __init__(self):
        super().__init__(
            "No Finnhub key set. Get a free one at https://finnhub.io (sign up, "
            "the key is shown on your dashboard), then paste it into trading/.env "
            "on the FINNHUB_API_KEY= line."
        )


def _get(path: str, params: dict) -> list | dict:
    settings = get_settings()
    if not settings.finnhub_api_key.strip():
        raise MissingNewsKey()
    time.sleep(1.1)  # free tier: stay comfortably under the rate limit
    params = {**params, "token": settings.finnhub_api_key}
    resp = requests.get(f"{_BASE}/{path}", params=params, timeout=30)
    if resp.status_code == 401:
        raise ValueError(
            "Finnhub rejected the key — re-check the FINNHUB_API_KEY line in "
            "trading/.env for typos or extra spaces."
        )
    resp.raise_for_status()
    return resp.json()


def get_company_news(symbol: str, days: int = 7, limit: int = 25) -> list[dict]:
    """Recent headlines about one company.

    Returns up to `limit` items, newest first, each with: date, headline,
    source, summary, url.
    """
    today = date.today()
    raw = _get(
        "company-news",
        {
            "symbol": symbol.upper(),
            "from": (today - timedelta(days=days)).isoformat(),
            "to": today.isoformat(),
        },
    )
    items = []
    for r in sorted(raw, key=lambda r: r.get("datetime", 0), reverse=True)[:limit]:
        items.append(
            {
                "date": date.fromtimestamp(r["datetime"]).isoformat() if r.get("datetime") else None,
                "headline": r.get("headline", ""),
                "source": r.get("source", ""),
                "summary": r.get("summary", ""),
                "url": r.get("url", ""),
            }
        )
    return items
