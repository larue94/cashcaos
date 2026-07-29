"""The High-Risk Small-Cap Sleeve's live decision flow.

Candidates arrive from discovery (the runner-pattern scanner and the social
buzz scanner). For each, we gather the evidence — pattern stats, buzz stats,
news mood (free model), and whatever fundamentals exist — then Claude judges
whether ANY deserves a small speculative position today.

Sleeve discipline (this is the walled-off risky money):
- max ~3% of the account per position (then confidence-scaled)
- at most 3 sleeve positions open at once
- 30% stop-loss, and a time exit after ~20 trading days (the pattern the
  backtest validated is a 20-day hold, not a marriage)
- everything still requires YOUR approval
"""

import json
import re

from trading.agents import risk_agent, sentiment_agent
from trading.audit_log import log_event
from trading.broker import get_broker
from trading.data.prices import get_daily_prices

SLEEVE_POSITION_FRACTION = 0.03   # ~3% per sleeve position before scaling
MAX_SLEEVE_POSITIONS = 3

_SYSTEM = """You run the HIGH-RISK small-cap sleeve of a paper-trading
portfolio for a beginner. Candidates come in two archetypes:
- RUNNERS: volume/breakout spikes already moving — momentum lottery tickets;
  most fail, rare monsters pay for the rest. Exits: trailing stop.
- COILED SPRINGS: insiders buying with their own money while the business
  improves and the price sleeps — patient re-rating plays that may need
  months (the $OSCR pattern). Exits: thesis/trend based.
Your job is to pick AT MOST ONE candidate worth a SMALL speculative position
today — or "none", which is often correct. Springs with real insider
conviction may deserve preference over already-extended runners. Be suspicious of: pumps with no substance,
stocks that already gapped so far the entry is terrible, and buzz with no
catalyst. Reply ONLY a JSON object:
{
  "action": "buy" or "none",
  "ticker": "...",
  "confidence": "low" | "medium" | "high",
  "thesis": "2-3 sentences, plain English, why this one and why now",
  "what_could_go_wrong": "1-2 sentences — be blunt, these are lottery tickets",
  "exit_plan": "1 sentence"
}"""


def _candidate_evidence(cand: dict) -> str:
    sym = cand["symbol"]
    lines = [f"=== {sym} (found by: {cand['source']}) ==="]
    if "volume_x" in cand:
        lines.append(f"- Runner pattern: volume {cand['volume_x']}x its 50-day "
                     f"average, gapped {cand.get('gap_pct', '?')}% on the last "
                     "session, broke its 20-day high.")
    if "spike_x" in cand:
        lines.append(f"- Social buzz: Reddit mentions up {cand['spike_x']}x in "
                     f"24h ({cand['mentions']} mentions).")
    if "insider_buys" in cand:
        titles = ", ".join(cand.get("titles", [])) or "insiders"
        lines.append(f"- INSIDER BUYING: {cand['insider_buys']} open-market "
                     f"purchase(s) totaling ${cand['insider_value']:,.0f} in "
                     f"the last 2 weeks by {titles} (SEC Form 4 filings).")
        mom = cand.get("mom_6m")
        if mom is not None:
            lines.append(f"- Price asleep: {mom:+.0%} over 6 months — the "
                         "market hasn't reacted yet.")
        yoy = cand.get("rev_yoy_q")
        lines.append("- Latest quarterly revenue vs a year ago: "
                     + (f"{yoy:+.0%} (SEC-filed)." if yoy is not None else
                        "unknown (no US quarterly filings — discount accordingly)."))
    if cand.get("market_cap_m"):
        lines.append(f"- Market cap: ${cand['market_cap_m']:,.0f} million.")
    try:
        df, _ = get_daily_prices(cand["symbol"])
        close = df["Close"]
        price = float(close.iloc[-1])
        cand["price"] = price
        month_ago = float(close.iloc[-21]) if len(close) > 21 else price
        lines.append(f"- Price ${price:,.2f}; {price / month_ago - 1:+.0%} over "
                     "the last month.")
    except Exception:  # noqa: BLE001
        lines.append("- (price history unavailable)")
    try:
        news_op = sentiment_agent.form_opinion(sym)   # free model reads the news
        if news_op.stance != "unavailable":
            lines.append(f"- News mood ({news_op.stance}, {news_op.score}/100): "
                         + (news_op.notes[0] if news_op.notes else ""))
            cand["sentiment_score"] = news_op.score
    except Exception:  # noqa: BLE001
        pass
    return "\n".join(lines)


def open_sleeve_count(conn) -> int:
    from trading.learning import store
    return sum(1 for p in store.open_positions_including_pending_sells(conn)
               if p["book"] in ("smallcap", "spring"))


def consider(candidates: list[dict], conn, say=print) -> dict | None:
    """Judge sleeve candidates; return a saved recommendation dict or None."""
    from trading.llm import ask
    from trading.learning import store

    if not candidates:
        return None
    if open_sleeve_count(conn) >= MAX_SLEEVE_POSITIONS:
        say("  Sleeve is full (3 positions) — not adding more risk.")
        return None
    has_pending = any(r["action"] == "buy" and r["book"] in ("smallcap", "spring")
                      for r in store.pending(conn))
    if has_pending:
        say("  A sleeve idea is already awaiting your decision.")
        return None

    say(f"  Sleeve candidates: {', '.join(c['symbol'] for c in candidates)}")
    evidence = "\n\n".join(_candidate_evidence(c) for c in candidates[:4])
    reply = ask("high", _SYSTEM,
                "Today's high-risk sleeve candidates. Pick at most ONE (or "
                "none):\n\n" + evidence)
    m = re.search(r"\{.*\}", reply, re.S)
    if not m:
        return None
    parsed = json.loads(m.group(0))
    if parsed.get("action") != "buy" or not parsed.get("ticker"):
        log_event("orchestrator", "sleeve-pass",
                  f"Sleeve: no candidate worth even a small position today. "
                  f"{parsed.get('thesis', '')}")
        say("  Sleeve verdict: none worth it today.")
        return None

    ticker = parsed["ticker"].upper()
    cand = next((c for c in candidates if c["symbol"] == ticker), {})
    book = cand.get("book", "smallcap")
    price = float(cand.get("price") or 0)
    broker = get_broker()
    account = broker.get_account()
    verdict = risk_agent.assess(
        account, ticker, price, book=book,
        max_position_fraction=SLEEVE_POSITION_FRACTION,
        confidence=parsed.get("confidence"))
    if not verdict.approved:
        log_event("orchestrator", "sleeve-veto",
                  f"Sleeve pick {ticker} was vetoed: {' '.join(verdict.reasons)}")
        say(f"  Sleeve pick {ticker} was vetoed by the risk agent.")
        return None

    source = cand.get("source", "discovery")
    rec_id = store.save_recommendation(
        conn, ticker=ticker, action="buy", book=book,
        shares=verdict.shares, dollars=verdict.dollars, ref_price=price,
        confidence=parsed.get("confidence"),
        thesis=f"[HIGH-RISK SLEEVE — found by {source}] " + parsed.get("thesis", ""),
        risks=parsed.get("what_could_go_wrong", "") +
              (" Sleeve rules: ~3% position, 30% stop-loss, trailing exit when "
               "the run breaks (close below the 20-day low). Most runner picks "
               "lose; rare big winners carry it."
               if book == "smallcap" else
               " Spring rules: ~3% position, 30% stop-loss, patient trend exit "
               "(sell if it breaks below the 200-day average). Insiders are "
               "often 6-18 months early — this needs patience."),
        exit_plan=parsed.get("exit_plan",
                             "Trailing 20-day-low exit or the -30% stop."
                             if book == "smallcap" else
                             "Hold while the thesis builds; exit on a 200-day "
                             "trend break or the -30% stop."),
        scores={"sentiment": cand.get("sentiment_score")},
        agent_details=[{"agent": "discovery", "score": None, "stance": source,
                        "notes": [_candidate_evidence(c) for c in candidates
                                  if c["symbol"] == ticker]}])
    log_event("orchestrator", "recommendation",
              f"SLEEVE RECOMMENDATION (awaiting approval): buy {verdict.shares} "
              f"{ticker} (~${verdict.dollars:,.0f}, found by {source}). "
              f"{parsed.get('thesis', '')}",
              data={"ticker": ticker, "source": source, "rec_id": rec_id})
    say(f"  Sleeve recommendation created: {ticker} "
        f"({verdict.shares} shares, ~${verdict.dollars:,.0f}).")
    return parsed
