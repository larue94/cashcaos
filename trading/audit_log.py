"""Human-readable audit trail.

Every meaningful action — agent opinions, orchestrator decisions, risk vetoes,
your approvals, orders sent — gets appended to a plain-text file in
trading/logs/, one file per day (e.g. audit_2026-07-07.log). Open it in any
text editor to see exactly why anything happened.

A machine-readable copy of each entry is kept alongside (.jsonl) so the
Phase 5 learning loop can analyze past decisions without re-parsing prose.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from trading.config import get_settings


def log_event(actor: str, event: str, detail: str, data: dict | None = None) -> None:
    """Record one event.

    actor:  who did it — e.g. "risk-agent", "orchestrator", "human", "system"
    event:  short label — e.g. "veto", "recommendation", "connection-test"
    detail: full plain-English explanation
    data:   optional structured details for later analysis
    """
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    text_line = f"[{stamp}] {actor} | {event}\n    {detail}\n"
    with open(settings.logs_dir / f"audit_{day}.log", "a", encoding="utf-8") as f:
        f.write(text_line)

    record = {"time": now.isoformat(), "actor": actor, "event": event,
              "detail": detail, "data": data or {}}
    with open(settings.logs_dir / f"audit_{day}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def latest_log_file() -> Path | None:
    """Path of today's readable log file, if it exists."""
    settings = get_settings()
    logs = sorted(settings.logs_dir.glob("audit_*.log"))
    return logs[-1] if logs else None
