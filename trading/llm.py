"""The AI reasoning layer — two tiers of "brain", routed by task difficulty.

HIGH tier (judgment calls; Claude — default Claude Opus):
  - weighing the four agents' evidence into a final recommendation
  - writing the daily digest you approve or reject
  - the Risk agent's veto narratives and the weekly self-review

LOW tier (grunt work; ALWAYS an open-source model, never Claude):
  - summarizing news headlines into one-line sentiment notes
  - extracting catalysts ("FDA approval", "contract win") from articles
  - reformatting text

The LOW tier speaks the standard "OpenAI-compatible" protocol, which nearly
every open-source model service understands. Two free ways to run it:

  1. Groq (hosted, free tier, no computer requirements — the default):
     get a free key at https://console.groq.com and put it in trading/.env
     as LLM_LOW_API_KEY. Default model: Llama 3.3 70B.
  2. Ollama (runs on YOUR computer, fully free and private):
     install from https://ollama.com, run `ollama pull llama3.1:8b`, then in
     trading/.env set LLM_LOW_BASE_URL=http://localhost:11434/v1 and
     LLM_LOW_MODEL=llama3.1:8b (no API key needed).

Honesty note: most of this system's number-crunching (indicators, screeners,
portfolio metrics, backtests) uses NO AI model at all — plain math, free and
never hallucinating. The AI tiers only handle actual reading and reasoning.

Every call's token usage (and estimated cost, where it has one) is written to
the audit log, so you can always see what the AI layer is costing you.
"""

import requests as _requests

from trading.audit_log import log_event
from trading.config import Settings, get_settings

# US dollars per 1 million tokens (input, output) — used for the cost line in
# the audit log. Models not listed just log token counts without a $ figure.
_PRICES_PER_MTOK = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
}


class MissingClaudeKey(Exception):
    def __init__(self):
        super().__init__(
            "No Claude API key set. Get one at https://console.anthropic.com "
            "(API Keys -> Create Key), then paste it into trading/.env on the "
            "ANTHROPIC_API_KEY= line."
        )


class LowTierNotConfigured(Exception):
    """The open-source model for grunt-work tasks isn't set up yet."""

    def __init__(self):
        super().__init__(
            "The open-source model (LOW tier) isn't set up yet. Two free "
            "options:\n"
            "  1. Groq (hosted, easiest): free key from https://console.groq.com"
            " -> paste into trading/.env as LLM_LOW_API_KEY=\n"
            "  2. Ollama (on your own computer): install from https://ollama.com,"
            " run `ollama pull llama3.1:8b`, then set in trading/.env:\n"
            "     LLM_LOW_BASE_URL=http://localhost:11434/v1\n"
            "     LLM_LOW_MODEL=llama3.1:8b"
        )


def _estimated_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    prices = _PRICES_PER_MTOK.get(model)
    if not prices:
        return None
    return tokens_in / 1e6 * prices[0] + tokens_out / 1e6 * prices[1]


def _ask_claude(settings: Settings, system: str, prompt: str, max_tokens: int) -> str:
    """HIGH tier: judgment calls go to Claude."""
    if not settings.anthropic_api_key.strip():
        raise MissingClaudeKey()
    import anthropic

    model = settings.llm_high_model
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"The model declined this request ({model}).")
    text = "".join(b.text for b in response.content if b.type == "text")
    cost = _estimated_cost(model, response.usage.input_tokens, response.usage.output_tokens)
    log_event(
        actor="llm",
        event="model-call",
        detail=(f"HIGH tier ({model}): {response.usage.input_tokens} tokens in, "
                f"{response.usage.output_tokens} out"
                + (f", estimated cost ${cost:.4f}" if cost is not None else "")),
        data={"tier": "high", "model": model,
              "tokens_in": response.usage.input_tokens,
              "tokens_out": response.usage.output_tokens, "est_cost_usd": cost},
    )
    return text


def _is_local_server(base_url: str) -> bool:
    return "localhost" in base_url or "127.0.0.1" in base_url


def _ask_open_source(settings: Settings, system: str, prompt: str, max_tokens: int) -> str:
    """LOW tier: grunt work goes to an open-source model."""
    base_url = settings.llm_low_base_url.strip()
    # A hosted service needs a key; a local Ollama server doesn't.
    if not base_url or (not settings.llm_low_api_key.strip()
                        and not _is_local_server(base_url)):
        raise LowTierNotConfigured()
    headers = {"Content-Type": "application/json"}
    if settings.llm_low_api_key.strip():
        headers["Authorization"] = f"Bearer {settings.llm_low_api_key}"
    try:
        resp = _requests.post(
            base_url.rstrip("/") + "/chat/completions",
            headers=headers,
            json={
                "model": settings.llm_low_model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=120,
        )
    except _requests.exceptions.ConnectionError as e:
        if _is_local_server(base_url):
            raise RuntimeError(
                "Could not reach your local model server at "
                f"{base_url}. Is Ollama running? (Open the Ollama app, or run "
                "`ollama serve` in a terminal.)"
            ) from e
        raise
    if resp.status_code == 401:
        raise ValueError(
            "The open-source model service rejected the key — re-check the "
            "LLM_LOW_API_KEY line in trading/.env for typos."
        )
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    log_event(
        actor="llm",
        event="model-call",
        detail=(f"LOW tier (open-source {settings.llm_low_model} via {base_url}): "
                f"{usage.get('prompt_tokens', '?')} tokens in, "
                f"{usage.get('completion_tokens', '?')} out, cost $0 (free tier)"),
        data={"tier": "low", "model": settings.llm_low_model,
              "provider": base_url,
              "tokens_in": usage.get("prompt_tokens"),
              "tokens_out": usage.get("completion_tokens")},
    )
    return text


def ask(tier: str, system: str, prompt: str, max_tokens: int | None = None) -> str:
    """Ask the AI a question, routed by tier.

    tier: "high" for judgment calls (Claude), "low" for grunt work
          (open-source model).
    system: standing instructions (who the model is, rules it must follow).
    prompt: the actual question/material.
    """
    settings = get_settings()
    if tier == "high":
        return _ask_claude(settings, system, prompt, max_tokens or 8000)
    if tier == "low":
        return _ask_open_source(settings, system, prompt, max_tokens or 2000)
    raise ValueError(f"tier must be 'high' or 'low', got {tier!r}")
