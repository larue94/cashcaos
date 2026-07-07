"""Backtesting harness (built in Phase 4).

Walk-forward windows (train 3 years, test 1, rolling 2010-2026), benchmarked
against buy-and-hold SPY, with 0.1% per-trade cost simulated. Reports
performance decay across windows and flags survivorship bias of free data.
"""
