"""Data pipeline (built in Phase 2).

Fetches and caches prices (yfinance), fundamentals (yfinance + SEC EDGAR),
and news (Finnhub free tier). All free data sources — their survivorship-bias
limitations are flagged in backtest results.
"""
