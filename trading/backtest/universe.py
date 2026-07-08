"""The set of stocks the backtester trades, plus their sectors.

⚠️ SURVIVORSHIP BIAS — read this once, it matters:
This universe is 20 large US companies that are still successful TODAY.
Companies that collapsed along the way (Enron-style) aren't in free data
feeds, so a backtest over this list looks better than real life would have.
Every results page this system produces repeats this warning. Treat backtest
numbers as "how the RULES behave", not "what you would have earned".

The universe is deliberately liquid large-caps across sectors so the three
core strategy books have variety to choose from. The High-Risk Small-Cap
Sleeve (Phase 6) uses its own separate screener, not this list.
"""

# ticker -> sector (used for the concentration metric on the dashboard)
UNIVERSE: dict[str, str] = {
    "AAPL": "Technology",
    "MSFT": "Technology",
    "NVDA": "Technology",
    "GOOGL": "Communication",
    "META": "Communication",
    "DIS": "Communication",
    "AMZN": "Consumer",
    "HD": "Consumer",
    "MCD": "Consumer",
    "WMT": "Consumer Staples",
    "KO": "Consumer Staples",
    "PG": "Consumer Staples",
    "JPM": "Financials",
    "V": "Financials",
    "JNJ": "Healthcare",
    "UNH": "Healthcare",
    "XOM": "Energy",
    "CVX": "Energy",
    "CAT": "Industrials",
    "UPS": "Industrials",
}

BENCHMARK = "SPY"  # the S&P 500 fund every result is compared against
