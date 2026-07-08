"""The common format every agent uses to voice its view on a stock.

Scores run 0-100 (50 = neutral). Every opinion carries plain-English notes
explaining the score, and every opinion is written to the audit log the
moment it is formed.
"""

from dataclasses import dataclass, field

from trading.audit_log import log_event


@dataclass
class Opinion:
    agent: str              # "research", "sentiment", "technical", "risk"
    ticker: str
    score: int              # 0-100; 50 is neutral
    stance: str             # "bullish", "neutral", "bearish", or "unavailable"
    notes: list[str] = field(default_factory=list)   # plain-English reasons
    data: dict = field(default_factory=dict)         # raw numbers for the record

    def log(self) -> None:
        log_event(
            actor=f"{self.agent}-agent",
            event="opinion",
            detail=(f"{self.ticker}: {self.stance} (score {self.score}/100). "
                    + " ".join(self.notes)),
            data={"ticker": self.ticker, "score": self.score,
                  "stance": self.stance, **self.data},
        )


def stance_from_score(score: int) -> str:
    if score >= 60:
        return "bullish"
    if score <= 40:
        return "bearish"
    return "neutral"
