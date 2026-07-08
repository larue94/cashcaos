"""A tiny Telegram Bot API wrapper over plain HTTP (no heavy dependencies).

Only the handful of calls this bot needs: send a message (with tappable
buttons), edit a message after a decision, acknowledge a button tap, and
long-poll for new taps/commands.
"""

import html

import requests

_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramClient:
    def __init__(self, token: str):
        self._token = token

    def _call(self, method: str, **params) -> dict:
        resp = requests.post(_BASE.format(token=self._token, method=method),
                             json=params, timeout=70)
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"Telegram API error on {method}: "
                               f"{data.get('description', data)}")
        return data.get("result", {})

    @staticmethod
    def esc(text: str) -> str:
        """Escape text for Telegram's HTML parse mode."""
        return html.escape(text or "", quote=False)

    @staticmethod
    def buttons(rows: list[list[tuple[str, str]]]) -> dict:
        """Build an inline keyboard from [[(label, callback_data), ...], ...]."""
        return {"inline_keyboard": [
            [{"text": label, "callback_data": data} for label, data in row]
            for row in rows]}

    def send(self, chat_id, text: str, buttons: dict | None = None) -> dict:
        params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True}
        if buttons:
            params["reply_markup"] = buttons
        return self._call("sendMessage", **params)

    def send_photo(self, chat_id, photo: bytes, caption: str = "") -> dict:
        """Send an image (e.g. a chart PNG) with an optional caption."""
        resp = requests.post(
            _BASE.format(token=self._token, method="sendPhoto"),
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": ("chart.png", photo, "image/png")},
            timeout=70)
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"sendPhoto failed: {data.get('description', data)}")
        return data.get("result", {})

    def edit(self, chat_id, message_id, text: str,
             buttons: dict | None = None) -> dict:
        params = {"chat_id": chat_id, "message_id": message_id, "text": text,
                  "parse_mode": "HTML", "disable_web_page_preview": True}
        if buttons is not None:
            params["reply_markup"] = buttons
        try:
            return self._call("editMessageText", **params)
        except RuntimeError:
            return {}  # "message is not modified" etc. — harmless

    def answer_callback(self, callback_query_id, text: str = "") -> None:
        try:
            self._call("answerCallbackQuery", callback_query_id=callback_query_id,
                       text=text)
        except RuntimeError:
            pass

    def get_me(self) -> dict:
        return self._call("getMe")

    def get_updates(self, offset: int | None, timeout: int = 50) -> list[dict]:
        params = {"timeout": timeout,
                  "allowed_updates": ["message", "callback_query"]}
        if offset is not None:
            params["offset"] = offset
        return self._call("getUpdates", **params)
