"""Loads settings (API keys, risk limits) from the .env file.

Every other part of the system gets its configuration from here, so there is
exactly one place to look when something is misconfigured.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# The trading/ folder itself — used to locate .env and logs regardless of
# which directory the user runs commands from.
PACKAGE_DIR = Path(__file__).resolve().parent

# Look for .env in trading/ first, then in the repository root.
load_dotenv(PACKAGE_DIR / ".env")
load_dotenv(PACKAGE_DIR.parent / ".env")


@dataclass
class Settings:
    """All system settings in one place."""

    # --- Broker (Alpaca paper trading) ---
    alpaca_api_key: str = field(default_factory=lambda: os.getenv("ALPACA_API_KEY", ""))
    alpaca_secret_key: str = field(default_factory=lambda: os.getenv("ALPACA_SECRET_KEY", ""))
    # Hard-wired to paper trading. There is deliberately no switch for live
    # trading anywhere in this codebase.
    alpaca_paper: bool = True

    # --- Data & AI keys (used from Phase 2/3) ---
    finnhub_api_key: str = field(default_factory=lambda: os.getenv("FINNHUB_API_KEY", ""))
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))

    # --- Risk budget (governs everything; see README) ---
    max_drawdown_core: float = 0.20        # 20% circuit breaker on core books
    max_drawdown_smallcap: float = 0.35    # accepted budget for the sleeve
    smallcap_sleeve_fraction: float = 0.15 # 10–20% of capital; default 15%
    max_position_fraction: float = 0.05    # flat 5% cap until Kelly has data
    # Hard per-position stop-loss: sell if a holding falls this far below its
    # entry price, regardless of the trend rules. A safety net, not a strategy.
    # 0 disables it. Small-cap sleeve gets its own wider stop (see below).
    stop_loss_pct: float = field(
        default_factory=lambda: float(os.getenv("STOP_LOSS_PCT", "0.15")))
    stop_loss_pct_smallcap: float = field(
        default_factory=lambda: float(os.getenv("STOP_LOSS_PCT_SMALLCAP", "0.30")))

    # --- Telegram bot (phone alerts + Approve/Reject buttons) ---
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    # If set, only this chat may approve/reject. If blank, the first person to
    # send /start becomes the owner (saved locally so it survives restarts).
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    # Local time (24h HH:MM) to auto-run the daily digest on weekdays.
    telegram_digest_time: str = field(default_factory=lambda: os.getenv("TELEGRAM_DIGEST_TIME", "09:45"))

    # --- AI reasoning layer (two tiers; see trading/llm.py) ---
    # HIGH tier: judgment calls — final trade reasoning, the daily digest,
    # risk narratives, the weekly self-review.
    llm_high_model: str = field(default_factory=lambda: os.getenv("LLM_HIGH_MODEL", "claude-opus-4-8"))
    # LOW tier: grunt work — summarizing headlines, extracting catalysts,
    # formatting. Always an OPEN-SOURCE model (never Claude), reached through
    # the standard "OpenAI-compatible" protocol. Defaults target Groq's free
    # hosted tier; point LLM_LOW_BASE_URL at http://localhost:11434/v1 to use
    # Ollama running on your own computer instead.
    llm_low_model: str = field(default_factory=lambda: os.getenv("LLM_LOW_MODEL", "llama-3.3-70b-versatile"))
    llm_low_base_url: str = field(
        default_factory=lambda: os.getenv("LLM_LOW_BASE_URL", "https://api.groq.com/openai/v1")
    )
    llm_low_api_key: str = field(default_factory=lambda: os.getenv("LLM_LOW_API_KEY", ""))

    # --- Data pipeline ---
    # SEC EDGAR asks automated tools to identify themselves with a contact.
    edgar_contact: str = field(
        default_factory=lambda: os.getenv("EDGAR_CONTACT", "cashcaos-trading research@example.com")
    )
    # Backtests run 2010-2026, so price history is fetched from here onward.
    price_history_start: str = "2010-01-01"

    # --- Files ---
    logs_dir: Path = PACKAGE_DIR / "logs"
    cache_dir: Path = PACKAGE_DIR / "data" / "cache"

    def missing_alpaca_keys(self) -> list[str]:
        """Names of the Alpaca settings that are still blank."""
        missing = []
        if not self.alpaca_api_key.strip():
            missing.append("ALPACA_API_KEY")
        if not self.alpaca_secret_key.strip():
            missing.append("ALPACA_SECRET_KEY")
        return missing


def get_settings() -> Settings:
    return Settings()
