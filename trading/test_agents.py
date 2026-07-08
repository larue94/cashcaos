"""Phase 3 test: run the full agent team once and show a real recommendation.

Run it with:

    python -m trading.test_agents

It analyzes a small demo watchlist of well-known stocks, prints each agent's
view, and ends with ONE recommendation in plain English — or an honest "do
nothing today".

IMPORTANT: this is analysis only. Nothing is bought or sold, and nothing
ever will be without your explicit per-trade approval (built in Phase 5).
"""

import sys

# A small starter watchlist of large, liquid US stocks for the demo.
# You can change this list freely — any US ticker works.
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "JNJ", "XOM"]


def main() -> int:
    print()
    print("Agent team — full analysis run")
    print("=" * 60)
    print(f"Watchlist: {', '.join(WATCHLIST)}")
    print("(This takes a couple of minutes: real data is fetched for each")
    print(" stock and both AI tiers do real reasoning.)")
    print()

    from trading.agents.orchestrator import run
    from trading.audit_log import latest_log_file

    try:
        rec = run(WATCHLIST)
    except Exception as e:  # noqa: BLE001
        print(f"\n  ❌ The run failed: {e}")
        print("     If this mentions a key, check trading/.env. Otherwise wait")
        print("     a minute and retry — free data services sometimes hiccup.")
        return 1

    print()
    print("=" * 60)
    if rec.action == "buy":
        print(f"RECOMMENDATION  (paper trading — awaiting YOUR approval)")
        print("-" * 60)
        print(f"  Buy {rec.shares} shares of {rec.ticker} "
              f"(~${rec.dollars:,.0f} at ${rec.price:,.2f})")
        print(f"  Strategy book: {rec.strategy_book}   "
              f"Confidence: {rec.confidence}")
        print()
        print(f"  Why: {rec.thesis}")
        print()
        print(f"  What could go wrong: {rec.what_could_go_wrong}")
        print()
        print(f"  Exit plan: {rec.exit_plan}")
        print()
        print("  Risk agent's sizing:")
        for r in rec.risk_notes:
            print(f"    - {r}")
    elif rec.action == "vetoed":
        print(f"The team wanted to buy {rec.ticker}, but the RISK AGENT VETOED it:")
        for r in rec.risk_notes:
            print(f"    - {r}")
    else:
        print("RECOMMENDATION: do nothing today.")
        print(f"  {rec.thesis}")
    print("=" * 60)
    print()
    print("Nothing was executed. No order was sent to Alpaca.")
    log_path = latest_log_file()
    if log_path:
        print(f"Every agent's full reasoning was recorded in: {log_path}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
