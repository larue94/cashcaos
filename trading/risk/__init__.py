"""Risk calibration (Phase 6).

- regime.py       classify the market (bull / choppy / bear) and show how
                  each book performed in each regime historically
- correlation.py  the Risk agent's correlation limit — blocks piling into
                  names that all move together
- kelly.py        Kelly-criterion position sizing (half-Kelly), from each
                  book's ACTUAL win rate and payoff once history exists
- montecarlo.py   risk-of-ruin: thousands of resampled trade sequences,
                  reporting the chance of breaching the drawdown limit
"""
