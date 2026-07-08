"""Risk agent — the safety officer. Sizes every position and can VETO.

Pure rules, no AI, no exceptions:
1. Circuit breaker: if the account has fallen 20%+ from its all-time peak,
   ALL new buying is vetoed until you review the situation.
2. Correlation limit (Phase 6): vetoes a buy that would pile onto a cluster
   of holdings that all move together, or overload one sector.
3. Position sizing: Kelly-criterion (half-Kelly) from the book's ACTUAL win
   rate and payoff once it has enough closed trades; the flat 5% cap until
   then. Always hard-capped.
4. Sanity checks: refuses to size a trade with a stale/absent price.

The account's all-time peak (the "high-water mark") is remembered in a small
local file so drawdown is measured across sessions.
"""

import json
from dataclasses import dataclass

from trading.audit_log import log_event
from trading.broker.base import AccountSnapshot
from trading.config import get_settings
from trading.risk import correlation, kelly


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


def assess(account: AccountSnapshot, ticker: str, price: float,
           book: str | None = None, current_tickers: list[str] | None = None,
           prices=None, book_trade_returns: list[float] | None = None,
           max_position_fraction: float | None = None) -> RiskVerdict:
    """Judge and size a proposed BUY. Extra args (all optional) enable the
    Phase 6 rules; without them it behaves like the Phase 3 flat-cap version.

    max_position_fraction lets the small-cap sleeve pass its own wider cap.
    """
    settings = get_settings()
    reasons: list[str] = []
    cap_fraction = (max_position_fraction if max_position_fraction is not None
                    else settings.max_position_fraction)

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

    # Rule 2: correlation & sector limits (only if we know current holdings).
    if current_tickers and prices is not None:
        allowed, corr_reasons = correlation.check(ticker, current_tickers, prices)
        reasons.extend(corr_reasons)
        if not allowed:
            verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
            _log(verdict)
            return verdict

    # Rule 4: sanity check the price before doing math with it.
    if not price or price <= 0:
        reasons.append(f"VETO — no reliable current price for {ticker}.")
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict

    # Rule 3: position sizing — Kelly (half) once there's history, else flat cap.
    if book_trade_returns is not None:
        fraction, size_reason = kelly.position_fraction(
            book_trade_returns, flat=cap_fraction, cap=max(cap_fraction, 0.10))
    else:
        fraction, size_reason = cap_fraction, (
            f"Flat {cap_fraction * 100:.0f}% cap (no closed-trade history "
            "wired in for this call).")
    reasons.append(size_reason)

    if fraction <= 0:
        reasons.append(f"VETO — sizing came out at 0% for {ticker}.")
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict

    cap_dollars = account.equity * fraction
    shares = int(cap_dollars // price)
    if shares < 1:
        reasons.append(
            f"VETO — even a {fraction * 100:.1f}% position "
            f"(${cap_dollars:,.0f}) doesn't buy one share at ${price:,.2f}."
        )
        verdict = RiskVerdict(False, ticker, 0.0, 0, reasons)
        _log(verdict)
        return verdict
    dollars = round(shares * price, 2)
    reasons.append(
        f"Final size: {shares} shares x ${price:,.2f} = ${dollars:,.0f} "
        f"({dollars / account.equity * 100:.1f}% of the account)."
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
