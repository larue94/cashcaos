"""The Telegram bot: pushes recommendations to your phone with Approve/Reject
buttons, answers a few commands, and runs the daily analysis on a schedule.

Run it with:   python -m trading.telegram

Safety: the SAME approve path as everywhere else (trading/webapp/actions.py),
so a tap goes through the identical rules and broker path. Approving asks for
a second confirming tap first. Only the owner chat may act on trades.
"""

import json
import threading
import time
from datetime import datetime

from trading.audit_log import log_event
from trading.config import get_settings
from trading.learning import store
from trading.telegram.client import TelegramClient
from trading.webapp import actions


# ---------- owner (who is allowed to approve trades) ----------

def _owner_path():
    return get_settings().cache_dir / "telegram_owner.json"


def _load_owner() -> str | None:
    settings = get_settings()
    if settings.telegram_chat_id.strip():
        return settings.telegram_chat_id.strip()
    path = _owner_path()
    if path.exists():
        try:
            return str(json.loads(path.read_text()).get("chat_id") or "") or None
        except json.JSONDecodeError:
            return None
    return None


def _save_owner(chat_id) -> None:
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    _owner_path().write_text(json.dumps({"chat_id": str(chat_id)}))


# ---------- message formatting ----------

def _rec_text(r) -> str:
    e = TelegramClient.esc
    action = r["action"].upper()
    emoji = "🟢" if r["action"] == "buy" else "🟡"
    size = (f"{r['shares']} shares (~${r['dollars']:,.0f})"
            if r["dollars"] else f"{r['shares']} shares")
    lines = [f"{emoji} <b>{action} {e(r['ticker'])}</b> — {e(size)}"]
    if r["book"]:
        lines.append(f"Book: {e(r['book'])}"
                     + (f" · confidence {e(r['confidence'])}"
                        if r["confidence"] else ""))
    lines.append("")
    lines.append(e(r["thesis"] or ""))
    if r["risks"]:
        lines.append(f"\n⚠️ <i>{e(r['risks'])}</i>")
    return "\n".join(lines)


def _detail_text(r) -> str:
    e = TelegramClient.esc
    out = [f"<b>Full analysis — {e(r['ticker'])}</b>", ""]
    details = json.loads(r["agent_details"]) if r["agent_details"] else []
    if details:
        for a in details:
            out.append(f"<b>{e(a['agent'].capitalize())}</b>: "
                       f"{a['score']}/100 ({e(a['stance'])})")
            for note in a.get("notes", [])[:3]:
                out.append(f"  • {e(note)}")
    else:
        out.append(f"Research {r['research_score']} · "
                   f"Technical {r['technical_score']} · "
                   f"Sentiment {r['sentiment_score']}")
    if r["exit_plan"] and r["exit_plan"] != "—":
        out.append(f"\n<b>Exit plan:</b> {e(r['exit_plan'])}")
    return "\n".join(out)


def _decision_buttons(rec_id: int) -> dict:
    return TelegramClient.buttons([
        [("✅ Approve", f"ap:{rec_id}"), ("❌ Reject", f"rj:{rec_id}")],
        [("🔎 Full analysis", f"dt:{rec_id}")],
    ])


def _confirm_buttons(rec_id: int) -> dict:
    return TelegramClient.buttons([
        [("✅ Yes, send the order", f"apc:{rec_id}")],
        [("↩️ Cancel", f"cx:{rec_id}")],
    ])


# ---------- the bot ----------

class Bot:
    def __init__(self):
        settings = get_settings()
        if not settings.telegram_bot_token.strip():
            raise RuntimeError(
                "No Telegram bot token set. Create a bot with @BotFather in "
                "Telegram (send it /newbot), then paste the token into "
                "trading/.env on the TELEGRAM_BOT_TOKEN= line. Full steps are "
                "in trading/README.md.")
        self.tg = TelegramClient(settings.telegram_bot_token)
        self.owner = _load_owner()
        self._offset = None
        self._last_digest_date = None
        self._digest_lock = threading.Lock()

    # --- authorization ---
    def _is_owner(self, chat_id) -> bool:
        return self.owner is not None and str(chat_id) == str(self.owner)

    def _send_long(self, chat_id, text: str) -> None:
        """Send text as HTML, split into Telegram-sized chunks at line breaks."""
        esc = TelegramClient.esc(text)
        limit = 3800
        chunk = ""
        for line in esc.split("\n"):
            if len(chunk) + len(line) + 1 > limit:
                self.tg.send(chat_id, f"<pre>{chunk}</pre>")
                chunk = ""
            chunk += line + "\n"
        if chunk.strip():
            self.tg.send(chat_id, f"<pre>{chunk}</pre>")

    def _send_deep(self, chat_id, ticker: str, r=None) -> None:
        """Compute and send the full fundamentals + technicals + Fib + Elliott."""
        # A quick one-line agent verdict header, then the deep report.
        if r is not None:
            header = (f"Agent scores — research {r['research_score']}, "
                      f"technical {r['technical_score']}, "
                      f"sentiment {r['sentiment_score']} (0-100, 50=neutral).")
            self.tg.send(chat_id, TelegramClient.esc(header))
        try:
            from trading.agents.deep_analysis import (chart_image, deep_report,
                                                      format_report)
            self.tg.send(chat_id, "⏳ Crunching fundamentals, technicals, "
                         "Fibonacci and wave structure…")
            # Draw and send the technical chart image first.
            try:
                png = chart_image(ticker)
                self.tg.send_photo(chat_id, png,
                                   f"{ticker.upper()} — price, moving averages, "
                                   "Fibonacci levels and RSI")
            except Exception:  # noqa: BLE001 — chart is a bonus, keep going
                pass
            report = format_report(deep_report(ticker))
            self._send_long(chat_id, report)
        except Exception as e:  # noqa: BLE001
            self.tg.send(chat_id, "Couldn't build the deep analysis right now "
                         f"({TelegramClient.esc(str(e))}). Price data services "
                         "sometimes rate-limit — try again in a minute.")

    # --- pushing recommendations ---
    def push_pending(self) -> int:
        if not self.owner:
            return 0
        sent = 0
        with store.connect() as conn:
            for r in store.pending(conn):
                if r["telegram_message_id"]:
                    continue
                msg = self.tg.send(self.owner, _rec_text(r),
                                   _decision_buttons(r["id"]))
                conn.execute("UPDATE recommendations SET telegram_message_id=? "
                             "WHERE id=?", (str(msg.get("message_id", "")), r["id"]))
                conn.commit()
                sent += 1
        return sent

    # --- the daily analysis ---
    def run_digest(self, announce_chat=None) -> None:
        with self._digest_lock:
            if announce_chat:
                self.tg.send(announce_chat, "🔎 Running today's analysis — this "
                             "takes a minute or two…")
            try:
                from trading.digest import main as digest_main
                digest_main()
            except Exception as e:  # noqa: BLE001
                log_event("system", "telegram-digest-error", str(e))
                if announce_chat:
                    self.tg.send(announce_chat, f"⚠️ The analysis hit an error: "
                                 f"{TelegramClient.esc(str(e))}")
                return
            n = self.push_pending()
            if announce_chat and n == 0:
                self.tg.send(announce_chat, "✅ Done — nothing new to approve "
                             "today.")

    # --- scheduler (weekday, at the configured local time) ---
    def _scheduler(self) -> None:
        target = get_settings().telegram_digest_time
        while True:
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            is_weekday = now.weekday() < 5
            if (is_weekday and now.strftime("%H:%M") == target
                    and self._last_digest_date != today):
                self._last_digest_date = today
                log_event("system", "telegram-scheduled-digest",
                          f"Scheduled daily digest firing at {target}.")
                if self.owner:
                    self.tg.send(self.owner, f"⏰ Daily check ({target}) — running "
                                 "the analysis…")
                self.run_digest()
            time.sleep(30)

    # --- handling taps and commands ---
    def _handle_callback(self, cq) -> None:
        chat_id = cq["message"]["chat"]["id"]
        cq_id = cq["id"]
        data = cq.get("data", "")
        if not self._is_owner(chat_id):
            self.tg.answer_callback(cq_id, "Not authorized.")
            return
        action, _, rid = data.partition(":")
        rec_id = int(rid) if rid.isdigit() else None
        msg_id = cq["message"]["message_id"]

        if action == "dt" and rec_id:
            with store.connect() as conn:
                r = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                 (rec_id,)).fetchone()
            self.tg.answer_callback(cq_id, "Building the deep analysis…")
            if r:
                self._send_deep(chat_id, r["ticker"], r)
        elif action == "ap" and rec_id:
            # Ask for a confirming second tap before sending a real order.
            with store.connect() as conn:
                r = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                 (rec_id,)).fetchone()
            if r and r["status"] == "pending":
                self.tg.edit(chat_id, msg_id,
                             _rec_text(r) + "\n\n<b>Send this order to Alpaca "
                             "paper trading?</b>", _confirm_buttons(rec_id))
            self.tg.answer_callback(cq_id)
        elif action == "cx" and rec_id:
            with store.connect() as conn:
                r = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                 (rec_id,)).fetchone()
            if r and r["status"] == "pending":
                self.tg.edit(chat_id, msg_id, _rec_text(r),
                             _decision_buttons(rec_id))
            self.tg.answer_callback(cq_id, "Cancelled.")
        elif action == "apc" and rec_id:
            result = actions.approve(rec_id)  # the real, shared approve path
            with store.connect() as conn:
                r = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                 (rec_id,)).fetchone()
            tag = "✅ APPROVED" if result["ok"] else "⚠️"
            self.tg.edit(chat_id, msg_id,
                         _rec_text(r) + f"\n\n{tag} {TelegramClient.esc(result['message'])}",
                         None)
            self.tg.answer_callback(cq_id, "Sent." if result["ok"] else "Not sent.")
        elif action == "rj" and rec_id:
            result = actions.reject(rec_id)
            with store.connect() as conn:
                r = conn.execute("SELECT * FROM recommendations WHERE id=?",
                                 (rec_id,)).fetchone()
            self.tg.edit(chat_id, msg_id,
                         _rec_text(r) + f"\n\n❌ Rejected. {TelegramClient.esc(result['message'])}",
                         None)
            self.tg.answer_callback(cq_id, "Rejected.")
        else:
            self.tg.answer_callback(cq_id)

    def _handle_message(self, msg) -> None:
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.startswith("/start"):
            if self.owner is None:
                self.owner = str(chat_id)
                _save_owner(chat_id)
                self.tg.send(chat_id,
                             "👋 You're now the owner of this trading bot. I'll "
                             "send you each recommendation with Approve/Reject "
                             "buttons, and run the analysis automatically every "
                             "weekday.\n\nCommands: /pending /status /digest /help")
                log_event("system", "telegram-owner-set",
                          f"Telegram owner set to chat {chat_id}.")
            elif self._is_owner(chat_id):
                self.tg.send(chat_id, "✅ You're the owner. Commands: /pending "
                             "/status /digest /help")
            else:
                self.tg.send(chat_id, "This bot already has an owner and is "
                             "private.")
            return

        if not self._is_owner(chat_id):
            self.tg.send(chat_id, "This bot is private.")
            return

        if text.startswith("/help"):
            self.tg.send(chat_id,
                         "<b>Commands</b>\n"
                         "/pending — show trades awaiting your approval\n"
                         "/status — account value &amp; open positions\n"
                         "/digest — run the analysis right now\n"
                         "/analyze TICKER — deep analysis of any stock "
                         "(e.g. /analyze AAPL): full fundamentals, technicals, "
                         "Fibonacci levels and a tentative Elliott-Wave read\n"
                         "Every recommendation arrives with Approve/Reject "
                         "buttons. Nothing trades without your tap.")
        elif text.startswith("/analyze"):
            parts = text.split()
            if len(parts) < 2:
                self.tg.send(chat_id, "Give me a ticker, e.g. /analyze AAPL")
            else:
                ticker = parts[1].upper().lstrip("$")
                threading.Thread(target=self._send_deep,
                                 args=(chat_id, ticker), daemon=True).start()
        elif text.startswith("/pending"):
            n = self.push_pending()
            with store.connect() as conn:
                total = len(store.pending(conn))
            if total == 0:
                self.tg.send(chat_id, "Nothing awaits approval right now. "
                             "Send /digest to look for a new idea.")
            elif n == 0:
                self.tg.send(chat_id, f"{total} item(s) already sent above — "
                             "scroll up to the cards with buttons.")
        elif text.startswith("/status"):
            self._send_status(chat_id)
        elif text.startswith("/digest"):
            threading.Thread(target=self.run_digest, args=(chat_id,),
                             daemon=True).start()
        else:
            self.tg.send(chat_id, "Unrecognized. Send /help for commands.")

    def _send_status(self, chat_id) -> None:
        try:
            state = actions.full_state()
        except Exception as e:  # noqa: BLE001
            self.tg.send(chat_id, f"Couldn't read the account: "
                         f"{TelegramClient.esc(str(e))}")
            return
        a = state["account"]
        lines = [f"💼 <b>${a['equity']:,.2f}</b> "
                 f"({a['change'] * 100:+.2f}% since start)",
                 f"Cash: ${a['cash']:,.2f}"]
        if state["positions"]:
            lines.append("\n<b>Positions</b>")
            for p in state["positions"]:
                lines.append(f"• {TelegramClient.esc(p['symbol'])}: "
                             f"{p['qty']:g} sh, {p['pl_pct'] * 100:+.1f}%")
        else:
            lines.append("\nNo positions — all cash.")
        self.tg.send(chat_id, "\n".join(lines))

    # --- main loop ---
    def run(self) -> None:
        me = self.tg.get_me()
        print(f"Bot @{me.get('username')} is live. Owner: "
              f"{self.owner or 'not set — send /start to the bot to claim it'}.")
        threading.Thread(target=self._scheduler, daemon=True).start()
        if self.owner:
            try:
                self.tg.send(self.owner, "🤖 Trading bot restarted and watching. "
                             "Send /help for commands.")
                self.push_pending()
            except Exception:  # noqa: BLE001
                pass
        while True:
            try:
                updates = self.tg.get_updates(self._offset)
            except Exception as e:  # noqa: BLE001 — keep the bot alive on blips
                print("poll error:", e)
                time.sleep(5)
                continue
            for u in updates:
                self._offset = u["update_id"] + 1
                try:
                    if "callback_query" in u:
                        self._handle_callback(u["callback_query"])
                    elif "message" in u:
                        self._handle_message(u["message"])
                except Exception as e:  # noqa: BLE001
                    print("handler error:", e)


def main() -> int:
    print()
    print("=" * 60)
    print("  Telegram trading bot")
    print("=" * 60)
    bot = Bot()
    bot.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
