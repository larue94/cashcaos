"""The weekly self-review — run once a week (e.g. Saturday morning):

    python -m trading.review

The orchestrator looks back at the week USING NUMBERS, not vibes:
- account value change and the week's closed trades
- each agent's rolling accuracy from the learning ledger
- anything currently red-flagged

It writes a plain-English review, PROPOSES rule adjustments, and explicitly
calls out any metric that has been red two reviews running. Proposals are
just words — no rule changes ever go live without you changing them
yourself (or asking me to in a future session).
"""

import sys
from datetime import datetime, timedelta, timezone

from trading.audit_log import log_event
from trading.broker import get_broker
from trading.learning import ledger, store
from trading.llm import ask

_SYSTEM = """You are the head of a small paper-trading team writing your
weekly self-review for the (beginner) owner. Rules:
- Reference the numbers you are given; never invent numbers or use vibes.
- Be honest about what went wrong. If there's too little data to judge,
  say exactly that — do not fill silence with false insight.
- If you propose rule adjustments, list them under 'PROPOSALS' as bullet
  points and state plainly that nothing changes without the owner's
  sign-off. If no change is warranted, say 'No changes proposed this week.'
Write at most ~300 words, plain English, no headers except PROPOSALS."""


def _red_flags(conn, account, week_outcomes) -> list[str]:
    """Simple weekly red flags, computed from real numbers."""
    flags = []
    history = store.equity_history(conn)
    if history:
        peak = max(row["equity"] for row in history)
        dd = 1 - account.equity / peak if peak else 0
        if dd >= 0.20:
            flags.append("drawdown-circuit-breaker")
        elif dd >= 0.10:
            flags.append("drawdown-over-10pct")
    if week_outcomes:
        losses = [o for o in week_outcomes if o["return_pct"] < 0]
        if len(losses) / len(week_outcomes) > 0.6:
            flags.append("weekly-win-rate-below-40pct")
    weights = ledger.weights(conn)
    for agent, weight in weights.items():
        if weight <= 0.6:
            flags.append(f"{agent}-agent-accuracy-low")
    return flags


def main() -> int:
    print()
    print("Weekly self-review")
    print("=" * 62)
    broker = get_broker()
    account = broker.get_account()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    with store.connect() as conn:
        history = store.equity_history(conn)
        week_hist = [r for r in history if r["date"] >= week_ago[:10]]
        wtd = (account.equity / week_hist[0]["equity"] - 1) if week_hist else 0.0
        outs = [o for o in store.outcomes(conn) if o["created_at"] >= week_ago]
        acc = ledger.accuracy_table(conn)
        weights = ledger.weights(conn)
        open_pos = store.open_positions_including_pending_sells(conn)
        flags = _red_flags(conn, account, outs)

        prev = store.last_reviews(conn, 1)
        prev_flags = set((prev[0]["red_metrics"] or "").split(",")) if prev else set()
        repeat_flags = [f for f in flags if f in prev_flags and f]

        facts = [
            f"Account value: ${account.equity:,.2f} "
            f"({wtd * 100:+.2f}% over the review period).",
            f"Open positions: {len(open_pos)} "
            f"({', '.join(p['ticker'] for p in open_pos) or 'none'}).",
            f"Trades closed this week: {len(outs)}"
            + ("" if not outs else " — " + ", ".join(
                f"{o['ticker']} {o['return_pct'] * 100:+.1f}%" for o in outs)) + ".",
            "Agent accuracy (last 90 closed trades): " + "; ".join(
                f"{a}: " + (f"{c['accuracy'] * 100:.0f}% of {c['graded']} calls"
                            if (c := acc[a][90])["accuracy"] is not None
                            else "not enough graded calls yet")
                for a in ledger.AGENTS) + ".",
            f"Current adaptive weights: {weights}.",
            f"Red flags this week: {', '.join(flags) or 'none'}.",
            f"Red flags ALSO red last week (call these out): "
            f"{', '.join(repeat_flags) or 'none'}.",
        ]
        print("Facts handed to the reviewer:")
        for f in facts:
            print(f"  - {f}")
        print("\nWriting the review (HIGH reasoning tier)...\n")
        review = ask("high", _SYSTEM, "This week's numbers:\n- "
                     + "\n- ".join(facts))
        print("-" * 62)
        print(review)
        print("-" * 62)
        if repeat_flags:
            print(f"⚠️ RED TWO WEEKS RUNNING: {', '.join(repeat_flags)}")
        print("Reminder: proposals above change NOTHING until you approve them.")

        store.save_review(conn, review, flags)
        log_event("orchestrator", "weekly-review",
                  f"Weekly self-review written. Red flags: "
                  f"{', '.join(flags) or 'none'}. "
                  f"Repeat flags: {', '.join(repeat_flags) or 'none'}.",
                  data={"equity": account.equity, "flags": flags})
    return 0


if __name__ == "__main__":
    sys.exit(main())
