"""The system's permanent memory — a small local database (SQLite).

Everything the learning loop needs survives here across sessions:
- every recommendation ever made (and what you decided about it)
- every completed trade's outcome vs. what was predicted
- daily account-value snapshots (feeds the live dashboard)
- weekly self-reviews (so "red two weeks running" can be detected)

The file lives at trading/data/cache/journal.db (kept out of GitHub).
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from trading.config import get_settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  ticker TEXT NOT NULL,
  action TEXT NOT NULL,              -- 'buy' or 'sell'
  book TEXT,
  shares INTEGER,
  dollars REAL,
  ref_price REAL,                    -- price when recommended
  confidence TEXT,
  thesis TEXT,
  risks TEXT,
  exit_plan TEXT,
  research_score INTEGER,
  technical_score INTEGER,
  sentiment_score INTEGER,
  status TEXT NOT NULL DEFAULT 'pending',
    -- pending -> approved/rejected/expired; approved -> submitted -> filled
  decided_at TEXT,
  order_id TEXT,
  fill_price REAL,
  fill_qty REAL,
  filled_at TEXT,
  closes_rec_id INTEGER              -- for sells: the buy this closes
);
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  buy_rec_id INTEGER NOT NULL,
  sell_rec_id INTEGER NOT NULL,
  ticker TEXT, book TEXT,
  entry_price REAL, exit_price REAL,
  entry_at TEXT, exit_at TEXT,
  return_pct REAL,                   -- realized, e.g. 0.05 = +5%
  holding_days REAL,
  research_score INTEGER, technical_score INTEGER, sentiment_score INTEGER
);
CREATE TABLE IF NOT EXISTS equity_snapshots (
  date TEXT PRIMARY KEY,             -- YYYY-MM-DD
  equity REAL, cash REAL
);
CREATE TABLE IF NOT EXISTS reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  text TEXT,
  red_metrics TEXT                   -- comma-separated names flagged red
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    db_path: Path = settings.cache_dir / "journal.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the first DB was created."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(recommendations)")}
    if "agent_details" not in cols:
        # JSON: [{"agent","score","stance","notes":[...]}] — the full per-agent
        # rationale, so the web UI can show WHY without re-running the team.
        conn.execute("ALTER TABLE recommendations ADD COLUMN agent_details TEXT")
        conn.commit()
    if "telegram_message_id" not in cols:
        # Set once a recommendation has been pushed to Telegram, so the bot
        # doesn't send the same card twice (survives restarts).
        conn.execute("ALTER TABLE recommendations ADD COLUMN telegram_message_id TEXT")
        conn.commit()


# ---------- recommendations ----------

def save_recommendation(conn, *, ticker, action, book, shares, dollars,
                        ref_price, confidence, thesis, risks, exit_plan,
                        scores: dict, closes_rec_id=None,
                        agent_details=None) -> int:
    import json as _json
    cur = conn.execute(
        """INSERT INTO recommendations
           (created_at, ticker, action, book, shares, dollars, ref_price,
            confidence, thesis, risks, exit_plan, research_score,
            technical_score, sentiment_score, closes_rec_id, agent_details)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (_now(), ticker, action, book, shares, dollars, ref_price, confidence,
         thesis, risks, exit_plan, scores.get("research"),
         scores.get("technical"), scores.get("sentiment"), closes_rec_id,
         _json.dumps(agent_details) if agent_details else None))
    conn.commit()
    return cur.lastrowid


def pending(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM recommendations WHERE status='pending' ORDER BY id").fetchall()


def set_status(conn, rec_id: int, status: str, order_id: str | None = None) -> None:
    conn.execute(
        "UPDATE recommendations SET status=?, decided_at=?, "
        "order_id=COALESCE(?, order_id) WHERE id=?",
        (status, _now(), order_id, rec_id))
    conn.commit()


def mark_filled(conn, rec_id: int, price: float, qty: float) -> None:
    conn.execute(
        "UPDATE recommendations SET status='filled', fill_price=?, fill_qty=?, "
        "filled_at=? WHERE id=?", (price, qty, _now(), rec_id))
    conn.commit()


def expire_stale_pending(conn, max_age_days: int = 3) -> int:
    """A recommendation is a view of ONE day's evidence — it goes stale."""
    rows = conn.execute(
        "UPDATE recommendations SET status='expired', decided_at=? "
        "WHERE status='pending' AND julianday(?) - julianday(created_at) > ?",
        (_now(), _now(), max_age_days))
    conn.commit()
    return rows.rowcount


def submitted(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM recommendations WHERE status='submitted'").fetchall()


def open_positions(conn) -> list[sqlite3.Row]:
    """Buy recs that filled and have no completed outcome yet — live holdings."""
    return conn.execute(
        """SELECT r.* FROM recommendations r
           WHERE r.action='buy' AND r.status='filled'
             AND NOT EXISTS (SELECT 1 FROM outcomes o WHERE o.buy_rec_id=r.id)
             AND NOT EXISTS (SELECT 1 FROM recommendations s
                             WHERE s.closes_rec_id=r.id
                               AND s.status IN ('pending','approved','submitted'))
        """).fetchall()


def open_positions_including_pending_sells(conn) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT r.* FROM recommendations r
           WHERE r.action='buy' AND r.status='filled'
             AND NOT EXISTS (SELECT 1 FROM outcomes o WHERE o.buy_rec_id=r.id)
        """).fetchall()


# ---------- outcomes & snapshots ----------

def record_outcome(conn, buy: sqlite3.Row, sell: sqlite3.Row) -> int:
    ret = sell["fill_price"] / buy["fill_price"] - 1 if buy["fill_price"] else 0.0
    days = (datetime.fromisoformat(sell["filled_at"])
            - datetime.fromisoformat(buy["filled_at"])).total_seconds() / 86400
    cur = conn.execute(
        """INSERT INTO outcomes (created_at, buy_rec_id, sell_rec_id, ticker,
           book, entry_price, exit_price, entry_at, exit_at, return_pct,
           holding_days, research_score, technical_score, sentiment_score)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (_now(), buy["id"], sell["id"], buy["ticker"], buy["book"],
         buy["fill_price"], sell["fill_price"], buy["filled_at"],
         sell["filled_at"], ret, round(days, 1), buy["research_score"],
         buy["technical_score"], buy["sentiment_score"]))
    conn.commit()
    return cur.lastrowid


def outcomes(conn, limit: int | None = None) -> list[sqlite3.Row]:
    q = "SELECT * FROM outcomes ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    return conn.execute(q).fetchall()


def snapshot_equity(conn, equity: float, cash: float) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO equity_snapshots (date, equity, cash) VALUES (?,?,?)",
        (datetime.now(timezone.utc).strftime("%Y-%m-%d"), equity, cash))
    conn.commit()


def equity_history(conn) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM equity_snapshots ORDER BY date").fetchall()


def save_review(conn, text: str, red_metrics: list[str]) -> None:
    conn.execute("INSERT INTO reviews (created_at, text, red_metrics) VALUES (?,?,?)",
                 (_now(), text, ",".join(red_metrics)))
    conn.commit()


def last_reviews(conn, n: int = 2) -> list[sqlite3.Row]:
    return conn.execute(
        f"SELECT * FROM reviews ORDER BY id DESC LIMIT {int(n)}").fetchall()
