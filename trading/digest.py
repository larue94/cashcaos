"""The daily digest — run this once a day (market mornings work best):

    python -m trading.digest

What one run does, in order:
1. SYNC   — checks whether previously approved orders filled; any completed
            round-trip is graded and added to the learning ledger
2. EXITS  — reviews every open position against its book's exit rules; a
            triggered exit becomes a SELL recommendation awaiting approval
3. IDEAS  — runs the full agent team on the watchlist for today's best new
            BUY recommendation (if any deserves it)
4. RECORD — snapshots account value and rebuilds the live dashboard
5. PRINTS the digest: everything pending YOUR decision

NOTHING IS EXECUTED by this command. Approving or rejecting each pending
trade happens in `python -m trading.approve` — that is the only path to the
broker, and it asks you per trade.
"""

import sys

from trading.agents import technical_agent
from trading.audit_log import log_event
from trading.broker import get_broker
from trading.learning import ledger, store

# Fallback watchlist if market-wide discovery is unreachable.
FALLBACK_WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "JNJ", "XOM"]


def build_watchlist(say) -> list[str]:
    """Today's core-book watchlist, discovered from the whole market:
    the S&P 500 quality-trend screen (pure math) + any S&P names with a
    concrete news catalyst (spotted by the free open-source model)."""
    watchlist: list[str] = []
    try:
        from trading.discovery.screens import core_screen
        top = core_screen(top_n=6)
        watchlist = [r["symbol"] for r in top]
        say(f"  Market screen (S&P 500): leaders by quality-trend -> "
            f"{', '.join(watchlist)}")
        log_event("discovery", "core-screen",
                  "S&P 500 screen leaders: " + ", ".join(
                      f"{r['symbol']} (score {r['score']})" for r in top))
    except Exception as e:  # noqa: BLE001
        say(f"  Market screen unavailable ({e}) — using fallback list.")
        return list(FALLBACK_WATCHLIST)
    try:
        from trading.discovery.market_data import sp500
        from trading.discovery.news_scan import catalyst_candidates
        sp = set(sp500()["symbol"])
        for c in catalyst_candidates():
            if c["symbol"] in sp and c["symbol"] not in watchlist:
                watchlist.append(c["symbol"])
                say(f"  + news catalyst: {c['symbol']} ({c['catalyst']})")
    except Exception:  # noqa: BLE001
        pass
    return watchlist[:8]


def sleeve_candidates(say) -> list[dict]:
    """High-risk sleeve candidates: the runner-pattern scan over the whole
    market's movers, plus social-buzz spikes (the '$OSCR effect')."""
    out: list[dict] = []
    try:
        from trading.discovery.screens import smallcap_screen
        for h in smallcap_screen():
            h["source"] = "runner-pattern scan"
            out.append(h)
    except Exception as e:  # noqa: BLE001
        say(f"  (runner scan unavailable: {e})")
    try:
        from trading.discovery.social import buzzing_stocks
        seen = {c["symbol"] for c in out}
        for b in buzzing_stocks():
            if b["symbol"] not in seen:
                b["source"] = "social buzz (Reddit)"
                out.append(b)
    except Exception as e:  # noqa: BLE001
        say(f"  (buzz scan unavailable: {e})")
    return out


def sync_fills(conn, broker, say) -> None:
    """Update submitted orders; grade any completed round-trips."""
    for rec in store.submitted(conn):
        info = broker.get_order_status(rec["order_id"])
        if info["status"] == "filled":
            store.mark_filled(conn, rec["id"], info["filled_avg_price"],
                              info["filled_qty"])
            say(f"  Filled: {rec['action']} {info['filled_qty']:g} "
                f"{rec['ticker']} @ ${info['filled_avg_price']:,.2f}")
            log_event("system", "fill",
                      f"Order filled: {rec['action']} {info['filled_qty']:g} "
                      f"{rec['ticker']} at ${info['filled_avg_price']:,.2f}.")
            if rec["action"] == "sell" and rec["closes_rec_id"]:
                buy = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                   (rec["closes_rec_id"],)).fetchone()
                sell = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                    (rec["id"],)).fetchone()
                if buy and buy["fill_price"]:
                    store.record_outcome(conn, buy, sell)
                    ret = sell["fill_price"] / buy["fill_price"] - 1
                    say(f"  Round-trip closed: {rec['ticker']} "
                        f"{ret * 100:+.1f}% — graded into the learning ledger.")
                    log_event("learning", "outcome",
                              f"Closed {rec['ticker']}: {ret * 100:+.1f}%. "
                              "Each agent's original call was graded against "
                              "this result.")
        elif info["status"] == "cancelled":
            store.set_status(conn, rec["id"], "cancelled")
            say(f"  Order for {rec['ticker']} was cancelled/expired at the broker.")


# Exit rules per book — the mechanical guardrails behind each exit plan.
def _exit_check(book: str, ticker: str, entry_price: float | None,
                held_days: float | None = None) -> tuple[bool, str]:
    from trading.config import get_settings
    settings = get_settings()
    op = technical_agent.form_opinion(ticker)
    price = op.data.get("price", 0)
    sma50 = op.data.get("sma50", 0)
    sma200 = op.data.get("sma200", 0)
    rsi = op.data.get("rsi", 50)

    # SAFETY FIRST: hard stop-loss, checked before any trend rule. This is a
    # protective net that the backtest did not include — it can sell earlier
    # than the trend rules would, on purpose, to cap a single loss.
    stop = (settings.stop_loss_pct_smallcap if book == "smallcap"
            else settings.stop_loss_pct)
    if stop > 0 and entry_price and price:
        drop = price / entry_price - 1
        if drop <= -stop:
            return True, (f"STOP-LOSS: {ticker} is {drop * 100:.1f}% below your "
                          f"entry (${entry_price:,.2f} → ${price:,.2f}), past the "
                          f"{stop * 100:.0f}% safety stop. Selling to cap the loss "
                          "regardless of the trend.")

    if book == "swing":
        if rsi >= 65:
            return True, (f"Swing exit: the bounce has played out (RSI {rsi:.0f} "
                          "is above 65).")
        if price < sma200:
            return True, "Swing exit: the long-term uptrend broke (price fell below its 200-day average)."
    elif book == "monthly":
        if price < sma50:
            return True, "Monthly exit: momentum faded (price fell below its 50-day average)."
    elif book == "smallcap":
        # The backtested pattern is a ~20-trading-day hold (≈28 calendar days):
        # take what the run gave and move on — runners that keep running will
        # show up in the scanner again.
        if held_days is not None and held_days >= 28:
            return True, (f"Sleeve time exit: held ~{held_days:.0f} calendar days "
                          "(the pattern's validated window is ~20 trading days). "
                          "Time to take the result and recycle the risk budget.")
    else:  # long-term
        if sma50 < sma200:
            return True, "Long-term exit: the durable uptrend ended (50-day average fell below the 200-day)."
    return False, ""


def check_exits(conn, say) -> int:
    """Turn triggered exit rules into SELL recommendations needing approval."""
    created = 0
    from datetime import datetime, timezone
    for pos in store.open_positions(conn):
        entry = pos["fill_price"] or pos["ref_price"]
        held_days = None
        if pos["filled_at"]:
            held_days = (datetime.now(timezone.utc)
                         - datetime.fromisoformat(pos["filled_at"])
                         ).total_seconds() / 86400
        should_exit, why = _exit_check(pos["book"], pos["ticker"], entry,
                                       held_days)
        if should_exit:
            store.save_recommendation(
                conn, ticker=pos["ticker"], action="sell", book=pos["book"],
                shares=int(pos["fill_qty"] or pos["shares"]), dollars=None,
                ref_price=None, confidence="rule",
                thesis=why + " (This is the mechanical exit rule for the "
                       f"{pos['book']} book — the same rule the backtest used.)",
                risks="Exiting locks in the current result; the stock may "
                      "recover afterwards. Rules accept that trade-off.",
                exit_plan="—", scores={}, closes_rec_id=pos["id"])
            created += 1
            say(f"  Exit triggered for {pos['ticker']}: {why}")
            log_event("orchestrator", "exit-signal",
                      f"{pos['ticker']} ({pos['book']} book): {why} "
                      "Sell recommendation created, awaiting approval.")
    return created


def print_pending(conn) -> None:
    rows = store.pending(conn)
    print()
    print("=" * 62)
    if not rows:
        print("NOTHING AWAITS YOUR APPROVAL today.")
        print("=" * 62)
        return
    print(f"AWAITING YOUR APPROVAL — {len(rows)} recommendation(s)")
    print("(Run `python -m trading.approve` to decide. Nothing happens")
    print(" until you do; recommendations expire after 3 days.)")
    for r in rows:
        print("-" * 62)
        size = (f"{r['shares']} shares (~${r['dollars']:,.0f})"
                if r["dollars"] else f"{r['shares']} shares")
        print(f"  #{r['id']}: {r['action'].upper()} {r['ticker']} — {size}"
              + (f" — {r['book']} book" if r["book"] else ""))
        print(f"  Why: {r['thesis']}")
        if r["risks"]:
            print(f"  What could go wrong: {r['risks']}")
        if r["exit_plan"] and r["exit_plan"] != "—":
            print(f"  Exit plan: {r['exit_plan']}")
    print("=" * 62)


def main() -> int:
    print()
    print("Daily digest")
    print("=" * 62)
    say = print

    broker = get_broker()
    account = broker.get_account()
    with store.connect() as conn:
        expired = store.expire_stale_pending(conn)
        if expired:
            say(f"  {expired} stale recommendation(s) expired (evidence >3 days old).")

        say("Step 1/5: syncing order fills from the broker...")
        sync_fills(conn, broker, say)

        say("Step 2/5: checking exit rules on open positions...")
        n_open = len(store.open_positions_including_pending_sells(conn))
        if n_open == 0:
            say("  No open positions yet.")
        else:
            check_exits(conn, say)

        # Core books: only look for a new buy if none is already pending.
        has_pending_core = any(r["action"] == "buy" and r["book"] != "smallcap"
                               for r in store.pending(conn))
        if has_pending_core:
            say("Step 3/5: a core-book buy is already awaiting your decision — "
                "not piling on another.")
        else:
            say("Step 3/5: discovering today's candidates across the market...")
            watchlist = build_watchlist(say)
            say("  Running the agent team on the discovered watchlist...")
            from trading.agents.orchestrator import run
            rec = run(watchlist, verbose=True)
            if rec.action == "buy":
                store.save_recommendation(
                    conn, ticker=rec.ticker, action="buy",
                    book=rec.strategy_book, shares=rec.shares,
                    dollars=rec.dollars, ref_price=rec.price,
                    confidence=rec.confidence,
                    thesis="[found by market screen] " + rec.thesis,
                    risks=rec.what_could_go_wrong, exit_plan=rec.exit_plan,
                    scores=rec.scores_for(rec.ticker),
                    agent_details=rec.details_for(rec.ticker))
            elif rec.action == "vetoed":
                say(f"  Team wanted {rec.ticker}, but the risk agent vetoed it.")
            else:
                say("  The team found nothing worth buying today — that's a "
                    "valid answer.")

        # High-risk sleeve: runner pattern + social buzz, judged separately.
        say("Step 4/5: scanning for high-risk small-cap runners + social buzz...")
        from trading.agents import sleeve
        cands = sleeve_candidates(say)
        if cands:
            sleeve.consider(cands, conn, say)
        else:
            say("  No runner-pattern or buzz-spike candidates today.")

        say("Step 5/5: snapshotting account value + rebuilding live dashboard...")
        store.snapshot_equity(conn, account.equity, account.cash)
        from trading.dashboard.live import build_live
        path = build_live(conn, broker, account)
        say(f"  Live dashboard: {path}")

        print_pending(conn)
        with store.connect() as c2:
            log_event("system", "digest", "Daily digest completed. "
                      f"Equity ${account.equity:,.2f}; "
                      f"{len(store.pending(c2))} recommendation(s) pending.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
