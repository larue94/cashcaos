"""Market discovery — how the system finds NEW stock ideas every day.

Three engines, cheapest first:
1. Wide screen  (screens.py)   — mechanical quality+trend screen over the
                                 S&P 500; pure math, no AI cost.
2. Movers scan  (screens.py)   — the whole market's biggest gainers and
                                 most-active names today (Alpaca screener),
                                 filtered through the small-cap runner
                                 pattern for the high-risk sleeve.
3. News scan    (news_scan.py) — market-wide headlines read by the FREE
                                 open-source model to spot catalysts (FDA,
                                 contracts, earnings surprises) and the
                                 tickers behind them.

Everything discovered still passes the same gauntlet: fundamentals gate,
agent scoring, Claude's final judgment, the Risk agent's veto, and YOUR
approval. Discovery widens the funnel — it never bypasses the checks.
"""
