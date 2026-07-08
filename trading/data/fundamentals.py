"""Company fundamentals — the numbers behind the business.

Two sources, both free:
- Yahoo Finance (yfinance): a convenient snapshot of today's key stats
  (market value, profit margins, debt, valuation ratios).
- SEC EDGAR: the US government database of official company filings. This is
  the ground truth — audited annual revenue and profit as the company itself
  reported them. Slower and rawer than Yahoo, but authoritative.

The Research agent (Phase 3) uses these numbers to decide WHAT is worth buying.
"""

import json
import time
from datetime import datetime, timedelta

import requests
import yfinance as yf

from trading.config import get_settings

_EDGAR_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_EDGAR_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


class SnapshotUnavailable(Exception):
    """Yahoo's stats service couldn't be reached right now.

    This happens when Yahoo temporarily rate-limits the network we're on
    (common in shared cloud environments, rare on a home computer). The
    official SEC EDGAR numbers keep working regardless.
    """


def get_snapshot(symbol: str) -> dict:
    """Today's key stats for one company, with plain-English field names.

    Missing values come back as None — small or foreign companies often
    don't have every number.
    """
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception as e:  # noqa: BLE001 — translate to a plain-English error
        raise SnapshotUnavailable(
            "Yahoo's company-stats service refused the connection (usually "
            "temporary rate-limiting of this network). Official SEC EDGAR "
            f"data is unaffected. Technical detail: {e}"
        ) from e
    if not info or info.get("marketCap") is None and info.get("longName") is None:
        raise SnapshotUnavailable(
            f"Yahoo returned an empty stats page for '{symbol}' — either the "
            "ticker is misspelled or Yahoo is temporarily rate-limiting."
        )

    def num(key):
        v = info.get(key)
        return float(v) if isinstance(v, (int, float)) else None

    return {
        "symbol": symbol.upper(),
        "company_name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": num("marketCap"),                # total company value, $
        "trailing_pe": num("trailingPE"),              # price vs last year's profit
        "forward_pe": num("forwardPE"),                # price vs expected profit
        "profit_margin": num("profitMargins"),         # profit kept per $1 of sales
        "revenue_growth": num("revenueGrowth"),        # sales growth vs year ago
        "debt_to_equity": num("debtToEquity"),         # borrowed money vs owned money
        "free_cash_flow": num("freeCashflow"),         # real cash generated, $
        "return_on_equity": num("returnOnEquity"),     # profit per $1 shareholders own
        "avg_volume_10d": num("averageDailyVolume10Day"),
    }


class EdgarClient:
    """Fetches official filed numbers from SEC EDGAR.

    EDGAR is free but asks tools to identify themselves and stay under
    10 requests/second — we send a contact header and pause briefly
    between calls.
    """

    def __init__(self):
        settings = get_settings()
        self._headers = {"User-Agent": settings.edgar_contact}
        self._cache_dir = settings.cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ticker_to_cik: dict[str, int] | None = None

    def _get_json(self, url: str, cache_name: str, max_age_days: int) -> dict:
        cache_file = self._cache_dir / cache_name
        if cache_file.exists():
            age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if age <= timedelta(days=max_age_days):
                return json.loads(cache_file.read_text())
        time.sleep(0.15)  # stay well under EDGAR's rate limit
        resp = requests.get(url, headers=self._headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        cache_file.write_text(json.dumps(data))
        return data

    def cik_for(self, symbol: str) -> int | None:
        """EDGAR identifies companies by a CIK number, not ticker; look it up."""
        if self._ticker_to_cik is None:
            data = self._get_json(_EDGAR_TICKERS_URL, "edgar_tickers.json", max_age_days=30)
            self._ticker_to_cik = {
                row["ticker"].upper(): int(row["cik_str"]) for row in data.values()
            }
        return self._ticker_to_cik.get(symbol.upper())

    def annual_series(self, symbol: str) -> dict:
        """Officially filed annual revenue and net profit, most recent years.

        Returns {"revenue": [(fiscal_year, dollars), ...],
                 "net_income": [...]} — newest first, up to 5 years each.
        """
        cik = self.cik_for(symbol)
        if cik is None:
            raise ValueError(
                f"'{symbol}' was not found in SEC EDGAR — it may be a fund/ETF "
                "or a non-US company (those don't file with the SEC this way)."
            )
        facts = self._get_json(
            _EDGAR_FACTS_URL.format(cik=cik), f"edgar_facts_{symbol.upper()}.json",
            max_age_days=7,
        )
        gaap = facts.get("facts", {}).get("us-gaap", {})

        def yearly(tag_options: list[str]) -> list[tuple[int, float]]:
            for tag in tag_options:
                units = gaap.get(tag, {}).get("units", {}).get("USD", [])
                # Keep only full-year figures from annual reports (10-K filings).
                rows = {}
                for u in units:
                    if u.get("form") == "10-K" and u.get("fp") == "FY" and u.get("fy"):
                        rows[int(u["fy"])] = float(u["val"])
                if rows:
                    return sorted(rows.items(), reverse=True)[:5]
            return []

        return {
            "revenue": yearly([
                "RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues",
                "SalesRevenueNet",
            ]),
            "net_income": yearly(["NetIncomeLoss"]),
        }

    def financial_statements(self, symbol: str) -> dict:
        """Officially filed income statement + balance sheet, recent years.

        Returns a dict of {line_item: [(fiscal_year, dollars), ...]} pulled
        straight from the company's own SEC filings — the authoritative source
        an analyst would review. Newest first, up to 4 years each.
        """
        cik = self.cik_for(symbol)
        if cik is None:
            raise ValueError(f"'{symbol}' isn't in SEC EDGAR (fund/ETF or "
                             "non-US company).")
        facts = self._get_json(
            _EDGAR_FACTS_URL.format(cik=cik), f"edgar_facts_{symbol.upper()}.json",
            max_age_days=7)
        gaap = facts.get("facts", {}).get("us-gaap", {})

        def yearly(tags, unit="USD"):
            for tag in tags:
                units = gaap.get(tag, {}).get("units", {}).get(unit, [])
                rows = {}
                for u in units:
                    if u.get("form") == "10-K" and u.get("fp") == "FY" and u.get("fy"):
                        rows[int(u["fy"])] = float(u["val"])
                if rows:
                    return sorted(rows.items(), reverse=True)[:4]
            return []

        return {
            "company": facts.get("entityName", symbol.upper()),
            # Income statement
            "revenue": yearly(["RevenueFromContractWithCustomerExcludingAssessedTax",
                               "Revenues", "SalesRevenueNet"]),
            "gross_profit": yearly(["GrossProfit"]),
            "operating_income": yearly(["OperatingIncomeLoss"]),
            "net_income": yearly(["NetIncomeLoss"]),
            "eps_diluted": yearly(["EarningsPerShareDiluted"], unit="USD/shares"),
            # Balance sheet
            "total_assets": yearly(["Assets"]),
            "total_liabilities": yearly(["Liabilities"]),
            "equity": yearly(["StockholdersEquity",
                              "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]),
            "cash": yearly(["CashAndCashEquivalentsAtCarryingValue",
                            "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]),
            "long_term_debt": yearly(["LongTermDebtNoncurrent", "LongTermDebt"]),
            # Cash flow
            "operating_cash_flow": yearly(
                ["NetCashProvidedByUsedInOperatingActivities"]),
        }
