"""The approval workflow — the ONLY path from recommendation to broker.

    python -m trading.approve

Shows each pending recommendation and asks you, one at a time:
  y = approve  -> the order is sent to Alpaca PAPER trading right now
  n = reject   -> recorded and never sent; the reason is logged
  s = skip     -> decide later (expires after 3 days)

Design guarantee: this file contains the system's only call that submits
orders. Every submission is preceded, in the same breath, by your typed
"y" — there is no autonomous path.
"""

import sys

from trading.audit_log import log_event
from trading.broker import OrderTicket, get_broker
from trading.learning import store


def _show(r) -> None:
    size = (f"{r['shares']} shares (~${r['dollars']:,.0f})"
            if r["dollars"] else f"{r['shares']} shares")
    print("-" * 62)
    print(f"  #{r['id']}: {r['action'].upper()} {r['ticker']} — {size}"
          + (f" — {r['book']} book" if r["book"] else ""))
    print(f"  Why: {r['thesis']}")
    if r["risks"]:
        print(f"  What could go wrong: {r['risks']}")
    if r["exit_plan"] and r["exit_plan"] != "—":
        print(f"  Exit plan: {r['exit_plan']}")


def main() -> int:
    print()
    print("Approval desk — paper trading")
    print("=" * 62)
    with store.connect() as conn:
        rows = store.pending(conn)
        if not rows:
            print("Nothing is awaiting approval. Run `python -m trading.digest`")
            print("to generate today's recommendations first.")
            return 0

        if not sys.stdin.isatty():
            # Non-interactive (e.g. a script): never guess an approval.
            print(f"{len(rows)} recommendation(s) pending, but approval needs "
                  "a real keyboard session — run this in a terminal.")
            for r in rows:
                _show(r)
            return 0

        broker = get_broker()
        for r in rows:
            _show(r)
            while True:
                answer = input(f"  Approve this {r['action']}? [y]es / [n]o / "
                               "[s]kip for now: ").strip().lower()
                if answer in ("y", "n", "s"):
                    break
                print("  Please type y, n, or s.")
            if answer == "s":
                print("  Skipped — will ask again next time.")
                continue
            if answer == "n":
                store.set_status(conn, r["id"], "rejected")
                log_event("human", "rejection",
                          f"You rejected: {r['action']} {r['shares']} "
                          f"{r['ticker']}.")
                print("  Rejected and recorded. Nothing was sent.")
                continue

            # Approved — this is the moment an order goes to PAPER trading.
            log_event("human", "approval",
                      f"You approved: {r['action']} {r['shares']} {r['ticker']} "
                      f"({r['book']} book).")
            try:
                order_id = broker.submit_order(OrderTicket(
                    symbol=r["ticker"], side=r["action"],
                    quantity=int(r["shares"]), time_in_force="day"))
            except Exception as e:  # noqa: BLE001
                print(f"  ⚠️ The broker rejected the order: {e}")
                print("     The recommendation stays pending — fix the issue "
                      "and run approve again.")
                log_event("system", "order-error",
                          f"Broker rejected {r['action']} {r['ticker']}: {e}")
                continue
            store.set_status(conn, r["id"], "submitted", order_id=order_id)
            log_event("system", "order-submitted",
                      f"Sent to Alpaca paper: {r['action']} {r['shares']} "
                      f"{r['ticker']} (market order, id {order_id}).")
            print(f"  ✅ Sent to Alpaca paper trading (order {order_id[:8]}...).")
            print("     If the market is closed it will execute at the next "
                  "open. Tomorrow's digest will confirm the fill.")
    print("=" * 62)
    print("Done. Full record: trading/logs/ and the live dashboard.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
