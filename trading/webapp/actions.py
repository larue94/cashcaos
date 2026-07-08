"""Shared actions the web UI performs — the same code paths as the CLI.

Keeping these here (not duplicated in the browser) means a click in the web
app goes through EXACTLY the same broker + audit-log + database path as
`python -m trading.approve`. The browser never talks to the broker directly;
it asks this server, which enforces every rule.
"""

import json

from trading.audit_log import log_event
from trading.broker import OrderTicket, get_broker
from trading.data.prices import get_daily_prices
from trading.learning import ledger, store


def approve(rec_id: int) -> dict:
    """Approve a recommendation → submit the order to Alpaca paper trading.

    This is a real order submission — the only difference from the CLI is the
    button instead of a typed 'y'. Returns {ok, message}.
    """
    with store.connect() as conn:
        rec = conn.execute("SELECT * FROM recommendations WHERE id=?",
                           (rec_id,)).fetchone()
        if rec is None:
            return {"ok": False, "message": "Recommendation not found."}
        if rec["status"] != "pending":
            return {"ok": False,
                    "message": f"Already {rec['status']} — nothing to do."}
        log_event("human", "approval",
                  f"You approved (web): {rec['action']} {rec['shares']} "
                  f"{rec['ticker']} ({rec['book']} book).")
        try:
            broker = get_broker()
            order_id = broker.submit_order(OrderTicket(
                symbol=rec["ticker"], side=rec["action"],
                quantity=int(rec["shares"]), time_in_force="day"))
        except Exception as e:  # noqa: BLE001
            log_event("system", "order-error",
                      f"Broker rejected {rec['action']} {rec['ticker']}: {e}")
            return {"ok": False,
                    "message": f"The broker rejected the order: {e}. "
                               "The recommendation stays pending."}
        store.set_status(conn, rec_id, "submitted", order_id=order_id)
        log_event("system", "order-submitted",
                  f"Sent to Alpaca paper: {rec['action']} {rec['shares']} "
                  f"{rec['ticker']} (market order, id {order_id}).")
        return {"ok": True,
                "message": f"Order sent to Alpaca paper trading "
                           f"(#{order_id[:8]}...). If the market is closed it "
                           "executes at the next open."}


def reject(rec_id: int, reason: str = "") -> dict:
    with store.connect() as conn:
        rec = conn.execute("SELECT * FROM recommendations WHERE id=?",
                           (rec_id,)).fetchone()
        if rec is None:
            return {"ok": False, "message": "Recommendation not found."}
        if rec["status"] != "pending":
            return {"ok": False,
                    "message": f"Already {rec['status']} — nothing to do."}
        store.set_status(conn, rec_id, "rejected")
        log_event("human", "rejection",
                  f"You rejected (web): {rec['action']} {rec['shares']} "
                  f"{rec['ticker']}." + (f" Reason: {reason}" if reason else ""))
        return {"ok": True, "message": "Rejected and recorded. Nothing sent."}


def deep_analysis(ticker: str) -> dict:
    """The full fundamentals + technicals + Fibonacci + Elliott report as text."""
    from trading.agents.deep_analysis import deep_report, format_report
    return {"ticker": ticker.upper(), "text": format_report(deep_report(ticker))}


def chart_data(ticker: str, days: int = 260) -> dict:
    """Recent price history with trend overlays, for the detail chart."""
    df, source = get_daily_prices(ticker)
    df = df.tail(days + 200)  # extra for the 200-day average warm-up
    close = df["Close"]
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    tail = df.tail(days)
    return {
        "ticker": ticker.upper(), "source": source,
        "dates": [d.strftime("%Y-%m-%d") for d in tail.index],
        "close": [round(float(v), 2) for v in close.tail(days)],
        "sma50": [None if v != v else round(float(v), 2) for v in sma50.tail(days)],
        "sma200": [None if v != v else round(float(v), 2) for v in sma200.tail(days)],
    }


def full_state() -> dict:
    """Everything the main dashboard shows, as JSON."""
    broker = get_broker()
    account = broker.get_account()
    with store.connect() as conn:
        store.expire_stale_pending(conn)
        store.snapshot_equity(conn, account.equity, account.cash)
        positions = broker.get_positions()
        pend = store.pending(conn)
        history = store.equity_history(conn)
        acc_table = ledger.accuracy_table(conn)
        weights = ledger.weights(conn)
        outs = store.outcomes(conn, limit=25)
        try:
            market_open = broker.is_market_open()
        except Exception:  # noqa: BLE001
            market_open = None

        recs = []
        for r in pend:
            recs.append({
                "id": r["id"], "action": r["action"], "ticker": r["ticker"],
                "book": r["book"], "shares": r["shares"], "dollars": r["dollars"],
                "confidence": r["confidence"], "thesis": r["thesis"],
                "risks": r["risks"], "exit_plan": r["exit_plan"],
                "ref_price": r["ref_price"], "created_at": r["created_at"],
                "scores": {"research": r["research_score"],
                           "technical": r["technical_score"],
                           "sentiment": r["sentiment_score"]},
                "agent_details": json.loads(r["agent_details"])
                if r["agent_details"] else [],
            })

    # Headline backtest + risk metrics, if the reports have been generated.
    from pathlib import Path
    reports = Path(__file__).resolve().parent.parent / "dashboard" / "output"
    metrics_summary = risk_summary = None
    try:
        p = reports / "summary.json"
        if p.exists():
            metrics_summary = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        pass
    try:
        p = reports / "risk_summary.json"
        if p.exists():
            risk_summary = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        pass

    start_equity = history[0]["equity"] if history else account.equity
    return {
        "metrics_summary": metrics_summary,
        "risk_summary": risk_summary,
        "account": {
            "equity": account.equity, "cash": account.cash,
            "buying_power": account.buying_power,
            "change": account.equity / start_equity - 1 if start_equity else 0,
            "market_open": market_open,
        },
        "equity_history": [{"date": h["date"], "equity": h["equity"]}
                           for h in history],
        "positions": [{
            "symbol": p.symbol, "qty": p.quantity,
            "avg_entry": p.avg_entry_price, "current": p.current_price,
            "value": p.market_value, "pl": p.unrealized_pl,
            "pl_pct": p.unrealized_pl_pct,
        } for p in positions],
        "pending": recs,
        "report_card": [{
            "agent": a,
            "windows": {str(w): acc_table[a][w] for w in ledger.WINDOWS},
            "weight": weights[a],
        } for a in ledger.AGENTS],
        "weights_note": ledger.weights_note(weights),
        "outcomes": [{
            "ticker": o["ticker"], "book": o["book"],
            "entry": o["entry_price"], "exit": o["exit_price"],
            "days": o["holding_days"], "return": o["return_pct"],
        } for o in outs],
    }
