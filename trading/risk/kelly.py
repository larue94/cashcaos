"""Kelly-criterion position sizing — bet size from real edge, not a guess.

The Kelly formula answers: given how often a strategy wins and how big its
wins are versus its losses, what fraction of the account maximizes long-run
growth? Betting more than Kelly eventually goes broke; betting Kelly is
maximally aggressive; most professionals bet HALF-Kelly for a much smoother
ride at ~3/4 of the growth.

Rule the system follows (from your risk framework):
- Until a book has at least `min_trades` real closed trades, use the flat
  5% cap — you cannot compute a reliable edge from a handful of trades.
- After that, size at HALF-Kelly from the book's ACTUAL win rate and payoff
  ratio, still hard-capped (so one confident signal can't dominate).
"""


def kelly_stats(trade_returns: list[float]) -> dict:
    """Win rate, payoff ratio, full-Kelly and half-Kelly fractions."""
    if not trade_returns:
        return {"n": 0, "win_rate": None, "payoff": None,
                "full_kelly": None, "half_kelly": None}
    wins = [r for r in trade_returns if r > 0]
    losses = [-r for r in trade_returns if r <= 0]
    p = len(wins) / len(trade_returns)
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    if avg_loss <= 0:
        # No losing trades yet — Kelly is undefined/infinite; stay conservative.
        return {"n": len(trade_returns), "win_rate": round(p, 3),
                "payoff": None, "full_kelly": None, "half_kelly": None}
    b = avg_win / avg_loss                      # payoff ratio
    full = p - (1 - p) / b                       # Kelly fraction
    return {"n": len(trade_returns), "win_rate": round(p, 3),
            "payoff": round(b, 2), "full_kelly": round(full, 4),
            "half_kelly": round(max(0.0, full / 2), 4),
            "avg_win": round(avg_win, 4), "avg_loss": round(avg_loss, 4)}


def position_fraction(trade_returns: list[float], min_trades: int = 20,
                      flat: float = 0.05, cap: float = 0.10) -> tuple[float, str]:
    """The fraction of the account to risk on one position, with a reason."""
    stats = kelly_stats(trade_returns)
    if stats["n"] < min_trades:
        return flat, (f"Flat {flat * 100:.0f}% cap — only {stats['n']} closed "
                      f"trade(s) so far, not enough to compute a reliable Kelly "
                      f"size (need {min_trades}).")
    hk = stats["half_kelly"]
    if hk is None:
        return flat, (f"Flat {flat * 100:.0f}% cap — no losing trades yet, so "
                      "Kelly can't be computed honestly; staying conservative.")
    if hk <= 0:
        return (0.0, f"Half-Kelly is {hk * 100:.1f}% (≤0): this book's recent "
                     f"edge is negative (win rate {stats['win_rate'] * 100:.0f}%, "
                     f"payoff {stats['payoff']}x). Size ZERO until it recovers.")
    sized = min(hk, cap)
    capped = " (hard-capped)" if hk > cap else ""
    return sized, (f"Half-Kelly size {sized * 100:.1f}%{capped} from a "
                   f"{stats['win_rate'] * 100:.0f}% win rate and "
                   f"{stats['payoff']}x payoff over {stats['n']} trades.")
