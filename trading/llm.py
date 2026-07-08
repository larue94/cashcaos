"""The AI reasoning layer — two tiers of "brain", routed by task difficulty.

HIGH tier (judgment calls; default: Claude Opus, Anthropic's most capable
widely available model tier for this kind of reasoning):
  - weighing the four agents' evidence into a final recommendation
  - writing the daily digest you approve or reject
  - the Risk agent's veto narratives and the weekly self-review

LOW tier (grunt work; default: Claude Haiku, ~5x cheaper):
  - summarizing news headlines into one-line sentiment notes
  - extracting catalysts ("FDA approval", "contract win") from articles
  - reformatting text

Important honesty note: most of this system's number-crunching (indicators,
screeners, portfolio metrics, backtests) uses NO AI model at all — it's plain
math, which is free, instant, and never hallucinates. The AI tiers are only
used where actual reading and reasoning is required.

Open-source models: the LOW tier can be pointed at any server that speaks the
common "OpenAI-compatible" protocol (Ollama running Llama/Qwen on your own
computer, or hosted services like OpenRouter). Set in .env:
    LLM_LOW_PROVIDER=openai-compatible
    LLM_LOW_BASE_URL=http://localhost:11434/v1   (Ollama example)
    LLM_LOW_MODEL=llama3.1:8b
The HIGH tier stays on Claude — final trade reasoning is exactly where model
quality pays for itself.

Every call's token usage and estimated cost is written to the audit log, so
you can always see what the AI layer is costing you.
"""

import requests as _requests

from trading.audit_log import log_event
from trading.config import Settings, get_settings

# US dollars per 1 million tokens (input, output) — used for the cost line in
# the audit log. Models not listed just log token counts without a $ figure.
_PRICES_PER_MTOK = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


class MissingClaudeKey(Exception):
    def __init__(self):
        super().__init__(
            "No Claude API key set. Get one at https://console.anthropic.com "
            "(API Keys -> Create Key), then paste it into trading/.env on the "
            "ANTHROPIC_API_KEY= line."
        )


def _estimated_cost(model: str, tokens_in: int, tokens_out: int) -> float | None:
    prices = _PRICES_PER_MTOK.get(model)
    if not prices:
        return None
    return tokens_in / 1e6 * prices[0] + tokens_out / 1e6 * prices[1]


def _ask_anthropic(settings: Settings, model: str, system: str, prompt: str,
                   max_tokens: int) -> str:
    if not settings.anthropic_api_key.strip():
        raise MissingClaudeKey()
    import anthropic

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
        detail=(f"Called {model}: {response.usage.input_tokens} tokens in, "
                f"{response.usage.output_tokens} out"
                + (f", estimated cost ${cost:.4f}" if cost is not None else "")),
        data={"model": model, "tokens_in": response.usage.input_tokens,
              "tokens_out": response.usage.output_tokens, "est_cost_usd": cost},
    )
    return text


def _ask_openai_compatible(settings: Settings, system: str, prompt: str,
                           max_tokens: int) -> str:
    """Talk to an open-source model server (Ollama, OpenRouter, LM Studio...)."""
    if not settings.llm_low_base_url.strip():
        raise ValueError(
            "LLM_LOW_PROVIDER is 'openai-compatible' but LLM_LOW_BASE_URL is "
            "blank in trading/.env — set it to your model server's address "
            "(e.g. http://localhost:11434/v1 for Ollama)."
        )
    headers = {"Content-Type": "application/json"}
    if settings.llm_low_api_key.strip():
        headers["Authorization"] = f"Bearer {settings.llm_low_api_key}"
    resp = _requests.post(
        settings.llm_low_base_url.rstrip("/") + "/chat/completions",
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
    resp.raise_for_status()
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    log_event(
        actor="llm",
        event="model-call",
        detail=(f"Called open-source model {settings.llm_low_model} via "
                f"{settings.llm_low_base_url}: "
                f"{usage.get('prompt_tokens', '?')} tokens in, "
                f"{usage.get('completion_tokens', '?')} out"),
        data={"model": settings.llm_low_model, "provider": "openai-compatible",
              "tokens_in": usage.get("prompt_tokens"),
              "tokens_out": usage.get("completion_tokens")},
    )
    return text


def ask(tier: str, system: str, prompt: str, max_tokens: int | None = None) -> str:
    """Ask the AI a question, routed by tier.

    tier: "high" for judgment calls, "low" for grunt work.
    system: standing instructions (who the model is, rules it must follow).
    prompt: the actual question/material.
    """
    settings = get_settings()
    if tier == "high":
        return _ask_anthropic(settings, settings.llm_high_model, system, prompt,
                              max_tokens or 8000)
    if tier == "low":
        if settings.llm_low_provider == "openai-compatible":
            return _ask_openai_compatible(settings, system, prompt, max_tokens or 2000)
        return _ask_anthropic(settings, settings.llm_low_model, system, prompt,
                              max_tokens or 2000)
    raise ValueError(f"tier must be 'high' or 'low', got {tier!r}")
