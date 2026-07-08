"""Sentiment agent — reads recent headlines, gauges the mood.

The only agent that uses the LOW (open-source, free) AI tier: it hands the
raw headlines to the model and asks for a stance, a score, and a one-line
summary in a fixed format that's easy to double-check.

If news isn't available (no key, quiet week, service down) the agent says
"unavailable" rather than guessing — a missing opinion is handled honestly
by the orchestrator, never silently made up.
"""

import re

from trading.agents.opinion import Opinion
from trading.data.news import MissingNewsKey, get_company_news
from trading.llm import LowTierNotConfigured, ask

_SYSTEM = """You are a financial news analyst. You will be given recent
headlines about one company. Judge the overall news mood for its stock over
the next weeks. Watch for traps: "beat estimates but lowered guidance" is
negative; legal/regulatory losses matter; routine index/ETF mentions are
noise. Reply in EXACTLY this format, three lines, nothing else:
STANCE: bullish | neutral | bearish
SCORE: <integer 0-100, 50 = neutral>
SUMMARY: <one plain-English sentence a beginner understands>"""


def form_opinion(ticker: str) -> Opinion:
    try:
        items = get_company_news(ticker, days=7, limit=15)
    except MissingNewsKey as e:
        opinion = Opinion(agent="sentiment", ticker=ticker, score=50,
                          stance="unavailable", notes=[str(e)])
        opinion.log()
        return opinion

    if not items:
        opinion = Opinion(agent="sentiment", ticker=ticker, score=50,
                          stance="unavailable",
                          notes=["No news found in the last 7 days."])
        opinion.log()
        return opinion

    headlines = "\n".join(
        f"- [{i['date']}] {i['headline']} ({i['source']})" for i in items
    )
    try:
        reply = ask("low", _SYSTEM,
                    f"Company: {ticker}\nRecent headlines:\n{headlines}")
    except LowTierNotConfigured as e:
        opinion = Opinion(agent="sentiment", ticker=ticker, score=50,
                          stance="unavailable", notes=[str(e)])
        opinion.log()
        return opinion

    # Parse the fixed 3-line format leniently.
    stance_m = re.search(r"STANCE:\s*(bullish|neutral|bearish)", reply, re.I)
    score_m = re.search(r"SCORE:\s*(\d{1,3})", reply)
    summary_m = re.search(r"SUMMARY:\s*(.+)", reply)
    stance = stance_m.group(1).lower() if stance_m else "neutral"
    score = max(0, min(100, int(score_m.group(1)))) if score_m else 50
    summary = summary_m.group(1).strip() if summary_m else reply.strip()[:200]

    opinion = Opinion(
        agent="sentiment", ticker=ticker, score=score, stance=stance,
        notes=[summary, f"(Based on {len(items)} headlines from the last 7 days.)"],
        data={"headline_count": len(items),
              "newest_headline": items[0]["headline"]})
    opinion.log()
    return opinion
