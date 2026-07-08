"""The LIVE dashboard — your paper account and learning loop, right now.

Rebuilt automatically at the end of every daily digest run. Open
trading/dashboard/output/live.html in any browser. (The backtest dashboard,
dashboard.html, is its historical sibling.)
"""

import html
from datetime import datetime
from pathlib import Path

from trading.dashboard.build import _CSS
from trading.learning import ledger, store

OUTPUT = Path(__file__).resolve().parent / "output" / "live.html"


def _card(title: str, body: str, sub: str = "") -> str:
    return (f"<h2>{html.escape(title)}</h2>"
            + (f"<p class='sub'>{html.escape(sub)}</p>" if sub else "")
            + f"<div class='card'>{body}</div>")


def _table(headers: list[str], rows: list[list[str]], empty: str) -> str:
    if not rows:
        return f"<p class='sub'>{html.escape(empty)}</p>"
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>"
                   for row in rows)
    return f"<table class='metrics'><tr>{head}</tr>{body}</table>"


def _sparkline(history) -> str:
    if len(history) < 2:
        return ("<p class='sub'>The account-value chart appears after a few "
                "daily digest runs (one dot per day).</p>")
    values = [row["equity"] for row in history]
    lo, hi = min(values) * 0.999, max(values) * 1.001
    W, H = 700, 120
    pts = " ".join(
        f"{20 + (W - 40) * i / (len(values) - 1):.1f},"
        f"{10 + (H - 30) * (1 - (v - lo) / (hi - lo or 1)):.1f}"
        for i, v in enumerate(values))
    return (f"<svg viewBox='0 0 {W} {H}' width='100%'>"
            f"<polyline points='{pts}' fill='none' stroke='var(--series1)' "
            f"stroke-width='2'/>"
            f"<text x='{W - 18}' y='14' text-anchor='end' font-size='12' "
            f"fill='var(--series1)' font-weight='600'>${values[-1]:,.0f}</text>"
            f"<text x='20' y='{H - 4}' font-size='11' fill='var(--muted)'>"
            f"{history[0]['date']}</text>"
            f"<text x='{W - 18}' y='{H - 4}' text-anchor='end' font-size='11' "
            f"fill='var(--muted)'>{history[-1]['date']}</text></svg>")


def build_live(conn, broker, account) -> Path:
    sections = []

    # --- Account ---
    positions = broker.get_positions()
    history = store.equity_history(conn)
    start_equity = history[0]["equity"] if history else account.equity
    change = account.equity / start_equity - 1 if start_equity else 0.0
    body = (f"<p style='font-size:22px;margin:4px 0'><b>${account.equity:,.2f}</b>"
            f" <span class='sub'>({change * 100:+.2f}% since tracking began; "
            f"${account.cash:,.2f} uninvested cash)</span></p>"
            + _sparkline(history))
    pos_rows = [[html.escape(p.symbol), f"{p.quantity:g}",
                 f"${p.avg_entry_price:,.2f}", f"${p.current_price:,.2f}",
                 f"${p.market_value:,.2f}",
                 f"<b style='color:var(--{ 'good' if p.unrealized_pl >= 0 else 'crit'})'>"
                 f"{p.unrealized_pl_pct * 100:+.1f}%</b>"]
                for p in positions]
    body += "<div style='height:10px'></div>" + _table(
        ["Stock", "Shares", "Bought at", "Now", "Worth", "P/L"],
        pos_rows, "No positions held yet — the account is all cash.")
    sections.append(_card("Paper account (simulated money)", body,
                          "Live view of the Alpaca paper account."))

    # --- Pending approvals ---
    pend = store.pending(conn)
    rows = [[f"#{r['id']}", r["action"].upper(), html.escape(r["ticker"]),
             f"{r['shares']}", html.escape(r["book"] or "—"),
             html.escape((r["thesis"] or "")[:160])] for r in pend]
    sections.append(_card(
        "Awaiting your approval", _table(
            ["#", "Action", "Stock", "Shares", "Book", "Why (short)"], rows,
            "Nothing pending. Run `python -m trading.digest` for today's ideas."),
        "Nothing here executes until you approve it in "
        "`python -m trading.approve`. Pending items expire after 3 days."))

    # --- Learning ledger ---
    table = ledger.accuracy_table(conn)
    weights = ledger.weights(conn)
    rows = []
    for agent in ledger.AGENTS:
        cells = [agent.capitalize()]
        for window in ledger.WINDOWS:
            cell = table[agent][window]
            cells.append("—" if cell["accuracy"] is None
                         else f"{cell['accuracy'] * 100:.0f}% "
                              f"({cell['right']}/{cell['graded']})")
        cells.append(f"<b>{weights[agent]}x</b>")
        rows.append(cells)
    sections.append(_card(
        "Agent report card (the learning loop)",
        _table(["Agent", "Last 30 trades", "Last 90", "Last 365",
                "Current weight"], rows, "")
        + f"<p class='sub'>{html.escape(ledger.weights_note(weights))} "
          "An agent that keeps being wrong automatically counts for less in "
          "future decisions (down to 0.3x); one that keeps being right counts "
          "up to 1.2x. This is adaptive weighting, not AI retraining.</p>",
        "Graded only on trades that have actually closed."))

    # --- Closed trades ---
    outs = store.outcomes(conn, limit=15)
    rows = [[html.escape(o["ticker"]), html.escape(o["book"] or "—"),
             f"${o['entry_price']:,.2f}", f"${o['exit_price']:,.2f}",
             f"{o['holding_days']:.0f}d",
             f"<b style='color:var(--{ 'good' if o['return_pct'] >= 0 else 'crit'})'>"
             f"{o['return_pct'] * 100:+.1f}%</b>"] for o in outs]
    sections.append(_card(
        "Completed round-trips",
        _table(["Stock", "Book", "In at", "Out at", "Held", "Result"], rows,
               "No completed trades yet — results appear once a position has "
               "been bought AND sold."),
        "Every one of these graded the agents and fed the report card above."))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Live Paper-Trading Dashboard</title><style>{_CSS}</style></head>"
        f"<body><div class='wrap'><h1>Live Paper-Trading Dashboard</h1>"
        f"<p class='sub'>Updated {datetime.now():%Y-%m-%d %H:%M} by the daily "
        f"digest. Simulated money only; every action requires your approval.</p>"
        + "".join(sections) + "</div></body></html>",
        encoding="utf-8")
    return OUTPUT
