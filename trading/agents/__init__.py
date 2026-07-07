"""The AI team (built in Phase 3).

Will contain:
- research_agent.py   — fundamentals via yfinance + SEC EDGAR (decides WHAT to buy)
- sentiment_agent.py  — news mood via Finnhub's free tier
- technical_agent.py  — chart patterns and indicators (decides WHEN to buy)
- risk_agent.py       — position sizing, correlation limits, 20% drawdown
                        circuit breaker, and VETO power over every trade
- orchestrator.py     — collects all opinions and writes the daily digest
"""
