"""Phase 2 test: can the system see prices, fundamentals, and news?

Run it with:

    python -m trading.test_data

It checks each of the three data feeds using Apple (AAPL) and the S&P 500
fund (SPY) as guinea pigs, and prints a plain-English pass/fail line per
feed. Nothing is bought or sold; this only reads public data.
"""

import sys

PASS = "  ✅ "
FAIL = "  ❌ "
WARN = "  ⚠️  "


def main() -> int:
    print()
    print("Data pipeline test")
    print("=" * 52)
    failures = 0

    # ---- Feed 1: daily prices (Yahoo Finance, Alpaca as automatic backup) ----
    try:
        from trading.data.prices import get_daily_prices

        aapl, aapl_src = get_daily_prices("AAPL")
        spy, spy_src = get_daily_prices("SPY")
        source_names = {"yahoo": "Yahoo Finance", "alpaca": "Alpaca's data feed",
                        "cache": "the local cache (saved from an earlier run)"}
        print(PASS + f"Price feed works — supplied by {source_names[aapl_src]}.")
        print(f"     AAPL: {len(aapl):,} trading days on file "
              f"({aapl.index[0].date()} to {aapl.index[-1].date()}), "
              f"latest close ${float(aapl['Close'].iloc[-1]):,.2f}")
        print(f"     SPY (the benchmark): latest close "
              f"${float(spy['Close'].iloc[-1]):,.2f}")
        print("     Downloaded data is cached locally, so this is fast next time.")
        if aapl_src == "alpaca":
            print("     Note: Yahoo was unreachable just now, so the Alpaca backup")
            print("     stepped in automatically (its history starts in 2016;")
            print("     Yahoo reaches back to 2010 and will be preferred when up).")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(FAIL + f"Price feed failed: {e}")

    # ---- Feed 2: fundamentals (Yahoo snapshot + SEC EDGAR official filings) ----
    try:
        from trading.data.fundamentals import SnapshotUnavailable, get_snapshot

        try:
            snap = get_snapshot("AAPL")
            mc = snap["market_cap"]
            pm = snap["profit_margin"]
            print(PASS + f"Fundamentals snapshot works — {snap['company_name']} "
                  f"({snap['sector']}).")
            if mc:
                print(f"     Company value: ${mc / 1e12:.2f} trillion")
            if pm is not None:
                print(f"     Profit margin: {pm * 100:.1f}% "
                      f"(keeps {pm * 100:.0f} cents of every sales dollar)")
        except SnapshotUnavailable as e:
            print(WARN + "Fundamentals snapshot temporarily unavailable (not broken):")
            print(f"     {e}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(FAIL + f"Fundamentals snapshot failed: {e}")

    try:
        from trading.data.fundamentals import EdgarClient

        series = EdgarClient().annual_series("AAPL")
        revs = series["revenue"]
        if not revs:
            raise ValueError("EDGAR responded but no annual revenue was found.")
        print(PASS + "SEC EDGAR official filings work. Apple's filed annual revenue:")
        for year, dollars in revs[:3]:
            print(f"     fiscal {year}: ${dollars / 1e9:,.0f} billion")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(FAIL + f"SEC EDGAR feed failed: {e}")
        print("     EDGAR is a government site and is occasionally slow —")
        print("     if this keeps failing, wait a few minutes and retry.")

    # ---- Feed 3: news headlines (Finnhub) ----
    try:
        from trading.data.news import MissingNewsKey, get_company_news

        try:
            news = get_company_news("AAPL", days=7, limit=3)
            if news:
                print(PASS + f"News feed works — {len(news)} recent AAPL headlines, e.g.:")
                for item in news:
                    print(f"     [{item['date']}] {item['headline'][:70]}")
            else:
                print(WARN + "News feed connected but returned no headlines "
                             "(unusual for AAPL — may be a quiet news window).")
        except MissingNewsKey as e:
            print(WARN + "News feed SKIPPED — not an error, just not set up yet.")
            print(f"     {e}")
    except Exception as e:  # noqa: BLE001
        failures += 1
        print(FAIL + f"News feed failed: {e}")

    # ---- Verdict ----
    from trading.audit_log import log_event

    print()
    print("=" * 52)
    if failures == 0:
        print("Data pipeline is working. (News stays optional until you add a")
        print("free Finnhub key — the Sentiment agent in Phase 3 will need it.)")
        log_event("system", "data-test", "Data pipeline test passed.")
    else:
        print(f"{failures} feed(s) failed — see the ❌ lines above for fixes.")
        log_event("system", "data-test", f"Data pipeline test had {failures} failure(s).")
    print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
