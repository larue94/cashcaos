"""The "coiled spring" scanner — the $OSCR pattern, found systematically.

The setup: a business getting measurably BETTER while its stock does NOTHING,
with insiders — the people who know most — buying with their own money. When
the market notices, the repricing can be fast. Three conditions:

1. INSIDER BUYING (the trigger): significant recent open-market purchases by
   executives (CEO/CFO/President/directors), from OpenInsider's free feed of
   SEC Form 4 filings. Cluster buys (several insiders) count extra.
2. PRICE ASLEEP: the stock hasn't already run — 6-month move within a band.
3. BUSINESS IMPROVING: latest filed quarterly revenue up vs the same quarter
   a year ago (straight from SEC EDGAR).

Honesty notes: insiders are early and often 6-18 months early — springs need
patience, which is why they get trend-based exits, not timers. And insiders
are sometimes just wrong. The stop-loss applies like everywhere else.
"""

import io
import re

import pandas as pd
import requests

from trading.audit_log import log_event
from trading.discovery.market_data import market_cap_millions

_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
# Purchases >= $25k in the last 2 weeks, biggest first (OpenInsider free feed)
_URL = ("http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=14&fdr=&td=0"
        "&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=100&vh=&ocl=&och=&sic1=-1"
        "&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h="
        "&oc2l=&oc2h=&sortcol=8&cnt=100&page=1")
_KEY_TITLES = re.compile(r"CEO|CFO|Pres|COO|10%|Dir", re.I)
MAX_CAP_MILLIONS = 10_000    # up to $10B — OSCR-sized springs included
FLAT_BAND = (-0.30, 0.35)    # 6-month move that still counts as "asleep"
MIN_REV_GROWTH = 0.10        # quarterly revenue up 10%+ year over year


def _insider_purchases() -> pd.DataFrame:
    """Recent significant open-market insider buys, market-wide."""
    r = requests.get(_URL, headers=_UA, timeout=30)
    r.raise_for_status()
    tables = pd.read_html(io.StringIO(r.text))
    table = next((t for t in tables if "Ticker" in "".join(map(str, t.columns))), None)
    if table is None:
        return pd.DataFrame()
    table.columns = [str(c).strip().replace("\xa0", " ") for c in table.columns]
    return table


def quarterly_revenue_yoy(symbol: str) -> float | None:
    """Latest filed quarter's revenue vs the same quarter last year (EDGAR)."""
    from trading.data.fundamentals import EdgarClient
    try:
        client = EdgarClient()
        cik = client.cik_for(symbol)
        if cik is None:
            return None
        facts = client._get_json(  # noqa: SLF001 — same package family
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
            f"edgar_facts_{symbol.upper()}.json", max_age_days=7)
        gaap = facts.get("facts", {}).get("us-gaap", {})
        for tag in ("RevenueFromContractWithCustomerExcludingAssessedTax",
                    "Revenues", "SalesRevenueNet"):
            units = gaap.get(tag, {}).get("units", {}).get("USD", [])
            frames = {}
            for u in units:
                frame = u.get("frame", "")
                if re.fullmatch(r"CY\d{4}Q\d", frame):
                    frames[frame] = float(u["val"])
            if len(frames) >= 5:
                latest = sorted(frames)[-1]
                year_ago = f"CY{int(latest[2:6]) - 1}{latest[6:]}"
                if year_ago in frames and frames[year_ago] > 0:
                    return frames[latest] / frames[year_ago] - 1
        return None
    except Exception:  # noqa: BLE001
        return None


def coiled_springs(limit: int = 3) -> list[dict]:
    """Candidates matching insider-buying + flat price + improving revenue."""
    try:
        table = _insider_purchases()
    except Exception as e:  # noqa: BLE001
        log_event("discovery", "spring-scan-error", f"OpenInsider unavailable: {e}")
        return []
    if table.empty:
        return []

    tick_col = next((c for c in table.columns if "Ticker" in c), None)
    title_col = next((c for c in table.columns if "Title" in c), None)
    value_col = next((c for c in table.columns if "Value" in c), None)
    if not (tick_col and title_col and value_col):
        return []

    # Aggregate buys per ticker; keep key-insider purchases only.
    buys: dict[str, dict] = {}
    for _, row in table.iterrows():
        sym = str(row[tick_col]).strip().upper()
        title = str(row[title_col])
        if not sym or len(sym) > 5 or not _KEY_TITLES.search(title):
            continue
        value = float(re.sub(r"[^0-9.]", "", str(row[value_col])) or 0)
        b = buys.setdefault(sym, {"symbol": sym, "insider_buys": 0,
                                  "insider_value": 0.0, "titles": set()})
        b["insider_buys"] += 1
        b["insider_value"] += value
        b["titles"].add(title.split(",")[0].strip()[:20])

    # Rank by conviction: total dollars, cluster size.
    ranked = sorted(buys.values(),
                    key=lambda b: (b["insider_buys"] >= 2, b["insider_value"]),
                    reverse=True)

    out = []
    from trading.data.prices import get_daily_prices
    for b in ranked[:15]:                     # cap the expensive checks
        if len(out) >= limit:
            break
        sym = b["symbol"]
        # Condition 2: price asleep (not already run)
        try:
            df, _ = get_daily_prices(sym)
            close = df["Close"]
            if len(close) < 130:
                continue
            mom6 = float(close.iloc[-1] / close.iloc[-126] - 1)
            if not (FLAT_BAND[0] <= mom6 <= FLAT_BAND[1]):
                continue
            b["mom_6m"] = round(mom6, 3)
            b["price"] = round(float(close.iloc[-1]), 2)
        except Exception:  # noqa: BLE001
            continue
        # Size check
        cap = market_cap_millions(sym)
        b["market_cap_m"] = cap
        if cap is not None and cap >= MAX_CAP_MILLIONS:
            continue
        # Condition 3: business improving (SEC-filed quarterly revenue)
        yoy = quarterly_revenue_yoy(sym)
        b["rev_yoy_q"] = None if yoy is None else round(yoy, 3)
        if yoy is not None and yoy < MIN_REV_GROWTH:
            continue
        b["titles"] = sorted(b["titles"])
        out.append(b)

    if out:
        log_event("discovery", "coiled-springs",
                  "Coiled-spring candidates (insider buying + flat price + "
                  "improving revenue): " + ", ".join(
                      f"{c['symbol']} ({c['insider_buys']} buys, "
                      f"${c['insider_value']:,.0f})" for c in out),
                  data={"hits": [{k: (sorted(v) if isinstance(v, set) else v)
                                  for k, v in c.items()} for c in out]})
    return out
