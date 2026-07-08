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

    # --- AI reasoning layer (two tiers; see trading/llm.py) ---
    # HIGH tier: judgment calls — final trade reasoning, the daily digest,
    # risk narratives, the weekly self-review.
    llm_high_model: str = field(default_factory=lambda: os.getenv("LLM_HIGH_MODEL", "claude-opus-4-8"))
    # LOW tier: grunt work — summarizing headlines, extracting catalysts,
    # formatting. Cheap and fast.
    llm_low_model: str = field(default_factory=lambda: os.getenv("LLM_LOW_MODEL", "claude-haiku-4-5"))
    # The LOW tier can be pointed at an open-source model server instead of
    # Claude: set LLM_LOW_PROVIDER=openai-compatible plus LLM_LOW_BASE_URL
    # (e.g. http://localhost:11434/v1 for Ollama) and optionally LLM_LOW_API_KEY.
    llm_low_provider: str = field(default_factory=lambda: os.getenv("LLM_LOW_PROVIDER", "anthropic"))
    llm_low_base_url: str = field(default_factory=lambda: os.getenv("LLM_LOW_BASE_URL", ""))
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
