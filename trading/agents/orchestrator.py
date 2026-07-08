"""The orchestrator — team lead of the four agents.

For each stock on the watchlist it collects the three analyst opinions
(research = WHAT, technical = WHEN, sentiment = mood). Candidates must pass
the fundamentals gate first — a weak business is never bought just because
the chart looks good. The strongest candidates go to the HIGH reasoning tier
(Claude), which weighs the evidence and drafts ONE recommendation in plain
English. The Risk agent then sizes it — or vetoes it outright.

NOTHING IS EXECUTED. The output is a recommendation for a human to read.
The Phase 5 approval workflow is the only path that will ever send an order
to the broker, and only after you approve it.
"""

import json
import re
from dataclasses import dataclass, field

from trading.agents import research_agent, risk_agent, sentiment_agent, technical_agent
from trading.agents.opinion import Opinion
from trading.audit_log import log_event
from trading.broker import get_broker
from trading.data.fundamentals import EdgarClient
from trading.llm import ask

# Candidates must score at least this on fundamentals to be considered at all.
FUNDAMENTALS_GATE = 55

_SYSTEM = """You are the head of a small, disciplined investment team running
a PAPER (simulated money) portfolio for a beginner investor. Your team's
rules, which you must follow:
- Fundamentals decide WHAT to buy; technicals decide WHEN.
- No day trading. Strategy books: "swing" (days-weeks), "monthly" (~1-3
  months), "long-term" (6+ months).
- Be honest about weaknesses and about what could go wrong. Never hype.
- Write for a beginner: plain English, no unexplained jargon.
You will receive the team's evidence for a shortlist of candidates. Choose
the SINGLE best recommendation (or "none" if nothing is genuinely
attractive — that is a perfectly good answer).
Reply with ONLY a JSON object, no other text, in exactly this shape:
{
  "action": "buy" or "none",
  "ticker": "...",
  "strategy_book": "swing" | "monthly" | "long-term",
  "confidence": "low" | "medium" | "high",
  "thesis": "2-4 sentences: why this company, why now, in plain English",
  "what_could_go_wrong": "1-3 sentences of honest risk",
  "exit_plan": "1-2 sentences: roughly when/why you would sell"
}"""


@dataclass
class Recommendation:
    action: str                       # "buy" or "none"
    ticker: str = ""
    strategy_book: str = ""
    confidence: str = ""
    thesis: str = ""
    what_could_go_wrong: str = ""
    exit_plan: str = ""
    shares: int = 0
    dollars: float = 0.0
    price: float = 0.0
    risk_notes: list[str] = field(default_factory=list)
    opinions: dict = field(default_factory=dict)   # ticker -> [Opinion, ...]


def _opinions_text(ticker: str, opinions: list[Opinion]) -> str:
    lines = [f"=== {ticker} ==="]
    for op in opinions:
        lines.append(f"[{op.agent} agent] {op.stance}, score {op.score}/100")
        for note in op.notes:
            lines.append(f"  - {note}")
        if op.data.get("price"):
            lines.append(f"  - current price: ${op.data['price']}")
    return "\n".join(lines)


def _parse_reply(reply: str) -> dict:
    match = re.search(r"\{.*\}", reply, re.S)
    if not match:
        raise ValueError(f"Model reply had no JSON object: {reply[:200]}")
    return json.loads(match.group(0))


def run(watchlist: list[str], verbose: bool = True) -> Recommendation:
    """Analyze the watchlist and produce one human-readable recommendation."""

    def say(msg: str) -> None:
        if verbose:
            print(msg)

    log_event("orchestrator", "run-start",
              f"Analyzing watchlist: {', '.join(watchlist)}")
    edgar = EdgarClient()
    all_opinions: dict[str, list[Opinion]] = {}
    candidates: list[tuple[float, str]] = []

    for ticker in watchlist:
        say(f"  Analyzing {ticker}...")
        ops = []
        research = research_agent.form_opinion(ticker, edgar)
        ops.append(research)
        technical = technical_agent.form_opinion(ticker)
        ops.append(technical)
        sentiment = sentiment_agent.form_opinion(ticker)
        ops.append(sentiment)
        all_opinions[ticker] = ops

        if research.score < FUNDAMENTALS_GATE:
            log_event("orchestrator", "gate",
                      f"{ticker} excluded: fundamentals score {research.score} "
                      f"is below the gate of {FUNDAMENTALS_GATE}. "
                      "(Rule: fundamentals decide WHAT to buy.)")
            continue
        # Rank: fundamentals decide WHAT (60%), timing WHEN (30%), mood (10%).
        sentiment_score = sentiment.score if sentiment.stance != "unavailable" else 50
        combined = 0.6 * research.score + 0.3 * technical.score + 0.1 * sentiment_score
        candidates.append((combined, ticker))

    if not candidates:
        log_event("orchestrator", "recommendation",
                  "No candidate passed the fundamentals gate today. "
                  "Recommendation: do nothing.")
        return Recommendation(action="none",
                              thesis="No stock on the watchlist passed the "
                                     "fundamentals quality gate today. Doing "
                                     "nothing is the disciplined choice.",
                              opinions=all_opinions)

    candidates.sort(reverse=True)
    shortlist = [t for _, t in candidates[:3]]
    say(f"  Shortlist after fundamentals gate: {', '.join(shortlist)}")
    say("  Asking the HIGH reasoning tier to weigh the evidence...")

    evidence = "\n\n".join(_opinions_text(t, all_opinions[t]) for t in shortlist)
    reply = ask("high", _SYSTEM,
                "Here is your team's evidence. Choose the single best "
                "recommendation (or none):\n\n" + evidence)
    parsed = _parse_reply(reply)

    rec = Recommendation(
        action=parsed.get("action", "none"),
        ticker=parsed.get("ticker", ""),
        strategy_book=parsed.get("strategy_book", ""),
        confidence=parsed.get("confidence", ""),
        thesis=parsed.get("thesis", ""),
        what_could_go_wrong=parsed.get("what_could_go_wrong", ""),
        exit_plan=parsed.get("exit_plan", ""),
        opinions=all_opinions,
    )

    if rec.action != "buy" or not rec.ticker:
        log_event("orchestrator", "recommendation",
                  f"Head of team chose no trade today. Reasoning: {rec.thesis}")
        return rec

    # The Risk agent has the last word — veto power over everything.
    say("  Risk agent reviewing the proposal...")
    tech_data = next((o.data for o in all_opinions.get(rec.ticker, [])
                      if o.agent == "technical"), {})
    price = float(tech_data.get("price", 0))
    broker = get_broker()
    account = broker.get_account()
    verdict = risk_agent.assess(account, rec.ticker, price)
    rec.risk_notes = verdict.reasons
    if not verdict.approved:
        rec.action = "vetoed"
        log_event("orchestrator", "recommendation",
                  f"Proposal to buy {rec.ticker} was VETOED by the risk agent.")
        return rec

    rec.shares, rec.dollars, rec.price = verdict.shares, verdict.dollars, price
    log_event(
        "orchestrator", "recommendation",
        f"RECOMMENDATION (awaiting human approval): buy {rec.shares} {rec.ticker} "
        f"(~${rec.dollars:,.0f}) in the {rec.strategy_book} book. "
        f"Thesis: {rec.thesis} Risks: {rec.what_could_go_wrong} "
        f"Exit plan: {rec.exit_plan}",
        data={"ticker": rec.ticker, "shares": rec.shares, "dollars": rec.dollars,
              "book": rec.strategy_book, "confidence": rec.confidence},
    )
    return rec
