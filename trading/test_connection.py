"""Phase 1 test: can we reach your Alpaca paper-trading account?

Run it with:

    python -m trading.test_connection

It checks, in order:
  1. Your keys are present in the .env file
  2. Alpaca accepts them and returns your paper account
  3. The account is healthy (not blocked) and shows a cash balance
  4. We can read market status (open/closed) and current holdings

Every step prints a plain-English pass/fail line. This test only READS from
your account — it never places an order.
"""

import sys

PASS = "  ✅ "
FAIL = "  ❌ "


def main() -> int:
    print()
    print("Alpaca paper-trading connection test")
    print("=" * 52)

    # Step 1: keys present?
    from trading.config import get_settings

    settings = get_settings()
    missing = settings.missing_alpaca_keys()
    if missing:
        print(FAIL + "Your Alpaca keys are not set up yet.")
        print(f"     Missing: {', '.join(missing)}")
        print("     Fix: copy trading/.env.example to a file named trading/.env")
        print("     and paste in the keys from your Alpaca *Paper* dashboard.")
        print("     Full walkthrough: trading/README.md, 'Setting up', Steps 1-2.")
        return 1
    print(PASS + "Keys found in your .env file.")

    # Step 2: does Alpaca accept them?
    from trading.broker import get_broker

    try:
        broker = get_broker(settings)
        account = broker.get_account()
    except Exception as e:  # noqa: BLE001 — we want to translate ANY failure
        msg = str(e).lower()
        print(FAIL + "Could not connect to Alpaca.")
        if "40110000" in msg or "unauthorized" in msg or "forbidden" in msg or "401" in msg:
            print("     Alpaca rejected the keys. Most common causes:")
            print("     - Key ID and Secret swapped, or a copy/paste typo")
            print("     - Keys generated from the LIVE dashboard instead of Paper")
            print("     Fix: regenerate keys on the *Paper* dashboard and re-paste them.")
        else:
            print("     This looks like a network problem (no internet, firewall,")
            print("     or Alpaca briefly down). The exact error was:")
            print(f"     {e}")
        return 1
    print(PASS + f"Connected to {broker.name()} — account {account.account_id}.")

    # Step 3: account healthy?
    if account.blocked:
        print(FAIL + "Alpaca reports this account is blocked from trading.")
        print("     Fix: log in to alpaca.markets and check for notices on the account.")
        return 1
    print(PASS + "Account is active and allowed to trade.")
    print(f"     Simulated cash:        ${account.cash:,.2f}")
    print(f"     Total account value:   ${account.equity:,.2f}")
    print(f"     Buying power:          ${account.buying_power:,.2f}")

    # Step 4: market status + holdings
    try:
        market = "OPEN" if broker.is_market_open() else "CLOSED"
        print(PASS + f"US stock market is currently {market}.")
        positions = broker.get_positions()
        if positions:
            print(PASS + f"You hold {len(positions)} position(s):")
            for p in positions:
                sign = "+" if p.unrealized_pl >= 0 else ""
                print(f"     {p.symbol}: {p.quantity:g} shares, "
                      f"worth ${p.market_value:,.2f} "
                      f"({sign}{p.unrealized_pl_pct * 100:.1f}% since entry)")
        else:
            print(PASS + "No positions yet — the account is all cash, as expected "
                         "for a fresh paper account.")
    except Exception as e:  # noqa: BLE001
        print(FAIL + f"Connected, but could not read market data: {e}")
        return 1

    # Record the successful test in the audit trail.
    from trading.audit_log import log_event, latest_log_file

    log_event(
        actor="system",
        event="connection-test",
        detail=(f"Connection test passed. Account {account.account_id}, "
                f"equity ${account.equity:,.2f}, market {market.lower()}."),
        data={"equity": account.equity, "cash": account.cash},
    )
    log_path = latest_log_file()

    print()
    print("=" * 52)
    print("All checks passed. Phase 1 is working.")
    if log_path:
        print(f"This test was recorded in the audit log: {log_path}")
    print("Nothing was bought or sold — this test only reads your account.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
