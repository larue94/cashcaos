"""The per-agent performance ledger and adaptive confidence weights.

After every closed trade, each agent's original call is graded:
- an agent that was bullish (score >= 60) is RIGHT if the trade made money
- an agent that was bearish (score <= 40) is RIGHT if the trade lost money
- near-neutral calls (41-59) aren't graded — the agent didn't commit

From those grades, rolling accuracy over the last 30 / 90 / 365 closed
trades sets each agent's CONFIDENCE WEIGHT in future decisions:

    weight = 2 x accuracy, kept between 0.3 and 1.2
    (fewer than 5 graded calls -> weight stays at the neutral 1.0)

Example from the spec: an agent wrong 70% of the time lately (accuracy
0.30) gets weight 0.6 — its voice literally counts for half. This is
pattern-reinforcement and adaptive weighting, NOT model retraining: the AI
models themselves never change; only how much each agent's opinion counts.
"""

import sqlite3

AGENTS = ("research", "technical", "sentiment")
WINDOWS = (30, 90, 365)


def _grade(score: int | None, ret: float) -> bool | None:
    """True=right, False=wrong, None=didn't commit / no data."""
    if score is None:
        return None
    if score >= 60:
        return ret > 0
    if score <= 40:
        return ret <= 0
    return None


def accuracy_table(conn: sqlite3.Connection) -> dict:
    """{agent: {window: {'graded': n, 'right': n, 'accuracy': float|None}}}"""
    rows = conn.execute(
        "SELECT research_score, technical_score, sentiment_score, return_pct "
        "FROM outcomes ORDER BY id DESC LIMIT 365").fetchall()
    table: dict = {}
    for agent in AGENTS:
        table[agent] = {}
        for window in WINDOWS:
            graded = right = 0
            for row in rows[:window]:
                g = _grade(row[f"{agent}_score"], row["return_pct"])
                if g is not None:
                    graded += 1
                    right += int(g)
            table[agent][window] = {
                "graded": graded, "right": right,
                "accuracy": round(right / graded, 2) if graded else None}
    return table


def weights(conn: sqlite3.Connection, window: int = 90) -> dict[str, float]:
    """Current confidence weight per agent (neutral 1.0 until 5+ graded calls)."""
    table = accuracy_table(conn)
    out = {}
    for agent in AGENTS:
        cell = table[agent][window]
        if cell["graded"] < 5:
            out[agent] = 1.0
        else:
            out[agent] = round(max(0.3, min(1.2, 2 * cell["accuracy"])), 2)
    return out


def weights_note(w: dict[str, float]) -> str:
    """One plain-English line describing the current weighting."""
    if all(v == 1.0 for v in w.values()):
        return ("All agents at neutral weight 1.0 — fewer than 5 graded "
                "closed trades so far; weights adapt as history builds.")
    parts = [f"{a} {v}x" for a, v in w.items()]
    return ("Adaptive weights from recent accuracy (90-trade window): "
            + ", ".join(parts) + ".")
