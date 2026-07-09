"""News catalyst scanner — market-wide headlines read by the FREE model.

Pulls the latest general market news from Finnhub, hands the headlines to
the open-source LOW tier (costs $0 on the free tier), and asks it to spot
REAL catalysts — FDA approvals, contract wins, earnings surprises, M&A —
and name the tickers. Those become discovery candidates.
"""

import re

import requests

from trading.audit_log import log_event
from trading.config import get_settings
from trading.llm import LowTierNotConfigured, ask

_SYSTEM = """You read financial news headlines and identify REAL catalysts.
A catalyst is concrete news that changes a company's prospects: FDA
approval/trial results, major contract or partnership win, earnings surprise,
acquisition, or major product launch. NOT catalysts: analyst opinions, price
targets, index moves, general market commentary, or articles about many
stocks at once.
From the headlines given, list AT MOST 5 single-company catalysts. Reply with
one line each, EXACTLY this format (nothing else):
TICKER | catalyst type | one-line summary
If there are none, reply exactly: NONE"""


def catalyst_candidates(limit_headlines: int = 40) -> list[dict]:
    """Tickers with a concrete news catalyst right now."""
    settings = get_settings()
    if not settings.finnhub_api_key.strip():
        return []
    try:
        r = requests.get("https://finnhub.io/api/v1/news",
                         params={"category": "general",
                                 "token": settings.finnhub_api_key},
                         timeout=25)
        r.raise_for_status()
        articles = r.json()[:limit_headlines]
    except Exception as e:  # noqa: BLE001
        log_event("discovery", "news-scan-error", f"Finnhub news unavailable: {e}")
        return []
    if not articles:
        return []

    headlines = "\n".join(f"- {a.get('headline', '')}" for a in articles
                          if a.get("headline"))
    try:
        reply = ask("low", _SYSTEM, "Today's market headlines:\n" + headlines)
    except LowTierNotConfigured:
        return []
    except Exception as e:  # noqa: BLE001
        log_event("discovery", "news-scan-error", f"LOW tier failed: {e}")
        return []

    hits = []
    for line in reply.splitlines():
        m = re.match(r"\s*\$?([A-Z]{1,5})\s*\|\s*([^|]+)\|\s*(.+)", line.strip())
        if m:
            hits.append({"symbol": m.group(1).upper(),
                         "catalyst": m.group(2).strip(),
                         "summary": m.group(3).strip()})
    if hits:
        log_event("discovery", "news-catalysts",
                  "News catalysts spotted (via free model): " + "; ".join(
                      f"{h['symbol']} ({h['catalyst']})" for h in hits),
                  data={"hits": hits})
    return hits[:5]
