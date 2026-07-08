"""Research agent — reads the business, decides WHAT is worth buying.

Uses plain arithmetic on real filed numbers (no AI needed here):
- Yahoo snapshot: profit margin, revenue growth, debt load, valuation
- SEC EDGAR: the officially filed multi-year revenue and profit trend

If Yahoo is temporarily rate-limiting (common on cloud networks), the agent
degrades gracefully to EDGAR-only mode and says so in its notes.
"""

from trading.agents.opinion import Opinion, stance_from_score
from trading.data.fundamentals import EdgarClient, SnapshotUnavailable, get_snapshot


def form_opinion(ticker: str, edgar: EdgarClient | None = None) -> Opinion:
    score = 50  # start neutral, move with evidence
    notes: list[str] = []
    data: dict = {}
    edgar = edgar or EdgarClient()

    # --- Layer 1: today's snapshot (Yahoo) ---
    snap = None
    try:
        snap = get_snapshot(ticker)
    except SnapshotUnavailable:
        notes.append("Today's stats snapshot was unavailable (Yahoo rate-limit); "
                     "judged on official SEC filings only.")

    if snap:
        data["snapshot"] = {k: v for k, v in snap.items() if v is not None}
        pm = snap.get("profit_margin")
        if pm is not None:
            if pm >= 0.15:
                score += 10
                notes.append(f"Strong profitability: keeps {pm * 100:.0f} cents "
                             "of every sales dollar.")
            elif pm < 0:
                score -= 15
                notes.append("Currently unprofitable.")
        rg = snap.get("revenue_growth")
        if rg is not None:
            if rg >= 0.10:
                score += 10
                notes.append(f"Sales growing {rg * 100:.0f}% year over year.")
            elif rg < 0:
                score -= 10
                notes.append(f"Sales shrinking ({rg * 100:.0f}% year over year).")
        de = snap.get("debt_to_equity")
        if de is not None:
            if de > 200:
                score -= 10
                notes.append("Heavy debt load (over 2x shareholders' equity).")
            elif de < 80:
                score += 5
                notes.append("Conservative debt load.")
        pe = snap.get("forward_pe") or snap.get("trailing_pe")
        if pe is not None:
            if 8 <= pe <= 30:
                score += 5
                notes.append(f"Reasonably valued ({pe:.0f}x expected earnings).")
            elif pe > 50:
                score -= 10
                notes.append(f"Expensive ({pe:.0f}x earnings — a lot of optimism "
                             "already in the price).")

    # --- Layer 2: the official multi-year trend (SEC EDGAR) ---
    try:
        series = edgar.annual_series(ticker)
        revs = series["revenue"]
        incomes = series["net_income"]
        if len(revs) >= 3:
            newest, oldest = revs[0][1], revs[2][1]
            data["revenue_3y"] = {str(y): v for y, v in revs[:3]}
            if newest > oldest * 1.15:
                score += 10
                notes.append(f"Officially filed revenue up "
                             f"{(newest / oldest - 1) * 100:.0f}% over 3 years.")
            elif newest < oldest * 0.95:
                score -= 10
                notes.append("Officially filed revenue has been shrinking over "
                             "3 years.")
        if len(incomes) >= 2:
            if incomes[0][1] > 0 and incomes[1][1] > 0:
                score += 5
                notes.append("Profitable in each of the last two filed years.")
            elif incomes[0][1] < 0:
                score -= 10
                notes.append("Lost money in the most recent filed year.")
    except Exception as e:  # noqa: BLE001 — ETFs/foreign names aren't in EDGAR
        notes.append(f"No SEC filings found ({e})")

    score = max(0, min(100, score))
    opinion = Opinion(agent="research", ticker=ticker, score=score,
                      stance=stance_from_score(score), notes=notes, data=data)
    opinion.log()
    return opinion
