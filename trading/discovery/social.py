"""Social buzz scanner — what retail traders are suddenly talking about.

This is the "$OSCR effect": small caps often start their run when chatter
explodes on social platforms before the mainstream notices. We use ApeWisdom
(free), which aggregates ticker mentions across Reddit's trading communities
(wallstreetbets and others) — the closest free proxy for X/Twitter buzz,
which no longer has an affordable public feed.

What matters is not the absolute mention count (SPY/NVDA are always loud)
but the SPIKE: mentions up sharply vs the previous 24h, on a name that isn't
a mega-cap. Those are surfaced as buzz candidates.

Honesty note: buzz-chasing is crowd momentum. By the time something trends,
part of the move has happened, and crowds are wrong a lot — OSCR worked,
many don't. That's why buzz names still pass the full gauntlet (pattern
check, fundamentals gate where applicable, Risk agent, your approval) and
live in the capped high-risk sleeve, never the core books.
"""

import requests

from trading.audit_log import log_event

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
_MEGA_CAPS = {"SPY", "QQQ", "IWM", "NVDA", "MSFT", "AAPL", "GOOGL", "GOOG",
              "AMZN", "META", "TSLA", "AMD", "NFLX", "AVGO", "BRK.B", "VOO",
              "GLD", "TLT", "COIN", "MSTR", "PLTR", "INTC", "MU"}


def buzzing_stocks(min_mentions: int = 30, min_spike: float = 2.0,
                   limit: int = 5) -> list[dict]:
    """Names whose social chatter is SPIKING (not just loud).

    min_spike: today's mentions vs yesterday's, e.g. 2.0 = doubled.
    Mega-caps and index funds are excluded — they're always chatty.
    """
    try:
        r = requests.get("https://apewisdom.io/api/v1.0/filter/all-stocks/page/1",
                         headers=_UA, timeout=25)
        r.raise_for_status()
        rows = r.json().get("results", [])
    except Exception as e:  # noqa: BLE001
        log_event("discovery", "social-scan-error", f"ApeWisdom unavailable: {e}")
        return []

    hits = []
    for row in rows:
        ticker = (row.get("ticker") or "").upper()
        mentions = int(row.get("mentions") or 0)
        prev = int(row.get("mentions_24h_ago") or 0)
        if (not ticker or ticker in _MEGA_CAPS or mentions < min_mentions
                or not ticker.replace(".", "").isalpha() or len(ticker) > 5):
            continue
        spike = mentions / prev if prev > 0 else float(mentions)
        if spike >= min_spike:
            hits.append({"symbol": ticker, "mentions": mentions,
                         "mentions_prev": prev, "spike_x": round(spike, 1),
                         "rank": int(row.get("rank") or 0),
                         "upvotes": int(row.get("upvotes") or 0)})
    hits.sort(key=lambda h: h["spike_x"], reverse=True)
    top = hits[:limit]
    if top:
        log_event("discovery", "social-buzz",
                  "Social chatter spiking on: " + ", ".join(
                      f"{h['symbol']} ({h['spike_x']}x, {h['mentions']} mentions)"
                      for h in top),
                  data={"hits": top})
    return top
