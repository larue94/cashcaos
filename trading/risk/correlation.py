"""Portfolio correlation limits — don't accidentally make one big bet.

If you hold five stocks that all move together, you don't have five bets —
you have one bet five times, and one bad day hits all of it. The Risk agent
uses this to BLOCK a new position when it would pile onto an already-crowded
cluster of names that move in lockstep.

Two guards:
1. Correlation cluster: block if the candidate's daily moves are highly
   correlated (above `threshold`) with `max_correlated` or more current
   holdings — e.g. no more than 2 tightly-correlated momentum names at once.
2. Sector concentration: block if the candidate would push one sector past
   `max_per_sector` holdings.
"""

import pandas as pd

from trading.backtest.universe import UNIVERSE


def check(candidate: str, current_tickers: list[str], prices: pd.DataFrame,
          *, threshold: float = 0.7, max_correlated: int = 2,
          max_per_sector: int = 3, lookback: int = 90,
          sectors: dict | None = None) -> tuple[bool, list[str]]:
    """Return (allowed, reasons). allowed=False means the Risk agent vetoes."""
    sectors = sectors or UNIVERSE
    reasons: list[str] = []
    if not current_tickers:
        return True, ["No existing holdings — correlation limits not binding."]

    # --- Guard 1: correlation cluster ---
    have_cols = [t for t in [candidate] + current_tickers if t in prices.columns]
    if candidate in prices.columns and len(have_cols) > 1:
        rets = prices[have_cols].pct_change(fill_method=None).tail(lookback)
        corr = rets.corr()
        highly = []
        for t in current_tickers:
            if t in corr.columns and t != candidate:
                c = corr.loc[candidate, t]
                if pd.notna(c) and c >= threshold:
                    highly.append((t, round(float(c), 2)))
        if len(highly) >= max_correlated:
            names = ", ".join(f"{t} ({c})" for t, c in highly)
            reasons.append(
                f"VETO — correlation limit: {candidate} moves in lockstep with "
                f"{len(highly)} holding(s) already ({names}). Adding it would "
                f"make more than {max_correlated} tightly-correlated names — "
                "that concentrates risk into one hidden bet.")
            return False, reasons
        if highly:
            reasons.append(
                f"Correlation OK: {candidate} is correlated with "
                f"{len(highly)} holding(s), under the limit of {max_correlated}.")
        else:
            reasons.append("Correlation OK: not tightly correlated with current "
                           "holdings.")

    # --- Guard 2: sector concentration ---
    cand_sector = sectors.get(candidate, "Other")
    same_sector = [t for t in current_tickers
                   if sectors.get(t, "Other") == cand_sector]
    if len(same_sector) >= max_per_sector:
        reasons.append(
            f"VETO — sector limit: already {len(same_sector)} holding(s) in "
            f"{cand_sector} ({', '.join(same_sector)}); {candidate} would push "
            f"past the max of {max_per_sector} per sector.")
        return False, reasons
    reasons.append(f"Sector OK: {cand_sector} would hold {len(same_sector) + 1} "
                   f"name(s), within the max of {max_per_sector}.")
    return True, reasons
