"""Risk agent — the safety officer. Sizes every position and can VETO.

Pure rules, no AI, no exceptions:
1. Circuit breaker: if the account has fallen 20%+ from its all-time peak,
   ALL new buying is vetoed until you review the situation.
2. Position cap: no single position may exceed 5% of the account (the flat
   cap that applies until Phase 6 adds Kelly sizing from real trade history).
3. Sanity checks: refuses to size a trade with a stale/absent price.

Phase 6 adds: sector/factor correlation limits, Kelly-criterion sizing,
Monte Carlo risk-of-ruin. The veto mechanism built here is what they'll
plug into.

The account's all-time peak (the "high-water mark") is remembered in a small
local file so drawdown is measured across sessions.
"""

import json
from dataclasses import dataclass

from trading.audit_log import log_event
from trading.broker.base import AccountSnapshot
from trading.config import get_settings


@dataclass
class RiskVerdict:
    approved: bool
    ticker: str
    dollars: float          # approved position size in $ (0 if vetoed)
    shares: int             # whole shares at the reference price
    reasons: list[str]      # plain-English explanation either way


def _high_water_mark(current_equity: float) -> float:
    """Remember the account's all-time peak value across sessions."""
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    path = settings.cache_dir / "account_state.json"
    state = {}
    if path.exists():
        try:
            state = json.loads(path.read_text())
        except json.JSONDecodeError:
            state = {}
    hwm = max(float(state.get("high_water_mark", 0.0)), current_equity)
    state["high_water_mark"] = hwm
    path.write_text(json.dumps(state))
    return hwm


def assess(account: AccountSnapshot, ticker: str, price: float) -> RiskVerdict:
    settings = get_settings()
    reasons: list[str] = []

    # Rule 1: the 20% drawdown circuit breaker.
    hwm = _high_water_mark(account.equity)
    drawdown = 1 - account.equity / hwm if hwm > 0 else 0.0
    if drawdown >= settings.max_drawdown_core:
        reasons.append(
            f"VETO — circuit breaker: the account is down "
            f"{drawdown * 100:.1f}% from its peak of ${hwm:,.0f}, beyond the "
            f"{settings.max_drawdown_core * 100:.0f}% limit. No new buying "
            "until you review."
        )
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict
    reasons.append(
        f"Circuit breaker OK: account is {drawdown * 100:.1f}% below its peak "
        f"(limit {settings.max_drawdown_core * 100:.0f}%)."
    )

    # Rule 3: sanity check the price before doing math with it.
    if not price or price <= 0:
        reasons.append(f"VETO — no reliable current price for {ticker}.")
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict

    # Rule 2: the 5% position cap.
    cap_dollars = account.equity * settings.max_position_fraction
    shares = int(cap_dollars // price)
    if shares < 1:
        reasons.append(
            f"VETO — even the {settings.max_position_fraction * 100:.0f}% cap "
            f"(${cap_dollars:,.0f}) doesn't buy one share at ${price:,.2f}."
        )
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict
    dollars = round(shares * price, 2)
    reasons.append(
        f"Sized at the flat {settings.max_position_fraction * 100:.0f}% cap: "
        f"{shares} shares x ${price:,.2f} = ${dollars:,.0f} "
        f"({dollars / account.equity * 100:.1f}% of the account). "
        "(Kelly-based sizing arrives in Phase 6 once there is real trade history.)"
    )

    verdict = RiskVerdict(True, ticker, dollars, shares, reasons)
    _log(verdict)
    return verdict


def _log(v: RiskVerdict) -> None:
    log_event(
        actor="risk-agent",
        event="approval" if v.approved else "veto",
        detail=f"{v.ticker}: " + " ".join(v.reasons),
        data={"ticker": v.ticker, "approved": v.approved,
              "dollars": v.dollars, "shares": v.shares},
    )
