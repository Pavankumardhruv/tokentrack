"""Built-in LLM pricing tables and cost calculation."""

from __future__ import annotations

from typing import Optional

from .models import PriceTier

PRICING: dict[str, PriceTier] = {
    # OpenAI
    "openai/gpt-4o": PriceTier("openai", "gpt-4o", 2.50, 10.00, 1.25),
    "openai/gpt-4o-mini": PriceTier("openai", "gpt-4o-mini", 0.15, 0.60, 0.075),
    "openai/gpt-4.1": PriceTier("openai", "gpt-4.1", 2.00, 8.00, 0.50),
    "openai/gpt-4.1-mini": PriceTier("openai", "gpt-4.1-mini", 0.40, 1.60, 0.10),
    "openai/gpt-4.1-nano": PriceTier("openai", "gpt-4.1-nano", 0.10, 0.40, 0.025),
    "openai/o3": PriceTier("openai", "o3", 2.00, 8.00, 0.50),
    "openai/o3-mini": PriceTier("openai", "o3-mini", 1.10, 4.40, 0.275),
    "openai/o4-mini": PriceTier("openai", "o4-mini", 1.10, 4.40, 0.275),
    # Anthropic
    "anthropic/claude-sonnet-4-20250514": PriceTier("anthropic", "claude-sonnet-4-20250514", 3.00, 15.00, 0.30),
    "anthropic/claude-opus-4-20250514": PriceTier("anthropic", "claude-opus-4-20250514", 15.00, 75.00, 1.50),
    "anthropic/claude-haiku-3.5": PriceTier("anthropic", "claude-haiku-3.5", 0.80, 4.00, 0.08),
    # Google
    "google/gemini-2.5-pro": PriceTier("google", "gemini-2.5-pro", 1.25, 10.00, 0.0),
    "google/gemini-2.5-flash": PriceTier("google", "gemini-2.5-flash", 0.15, 0.60, 0.0),
    "google/gemini-2.0-flash": PriceTier("google", "gemini-2.0-flash", 0.10, 0.40, 0.0),
}

MODEL_ALIASES: dict[str, str] = {
    "gpt4o": "openai/gpt-4o",
    "gpt-4o": "openai/gpt-4o",
    "4o": "openai/gpt-4o",
    "4o-mini": "openai/gpt-4o-mini",
    "gpt4o-mini": "openai/gpt-4o-mini",
    "gpt-4.1": "openai/gpt-4.1",
    "4.1": "openai/gpt-4.1",
    "4.1-mini": "openai/gpt-4.1-mini",
    "4.1-nano": "openai/gpt-4.1-nano",
    "o3": "openai/o3",
    "o3-mini": "openai/o3-mini",
    "o4-mini": "openai/o4-mini",
    "sonnet": "anthropic/claude-sonnet-4-20250514",
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    "opus": "anthropic/claude-opus-4-20250514",
    "claude-opus": "anthropic/claude-opus-4-20250514",
    "haiku": "anthropic/claude-haiku-3.5",
    "claude-haiku": "anthropic/claude-haiku-3.5",
    "gemini-pro": "google/gemini-2.5-pro",
    "gemini-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.0-flash": "google/gemini-2.0-flash",
}


def resolve_model(model: str) -> Optional[PriceTier]:
    key = model.strip().lower()

    if key in MODEL_ALIASES:
        return PRICING[MODEL_ALIASES[key]]

    for pricing_key, tier in PRICING.items():
        if key == pricing_key.lower():
            return tier
        if key == tier.model.lower():
            return tier

    for pricing_key, tier in PRICING.items():
        if key in pricing_key.lower() or key in tier.model.lower():
            return tier

    return None


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> Optional[float]:
    key = f"{provider}/{model}"
    tier = PRICING.get(key)
    if not tier:
        tier = resolve_model(model)
    if not tier:
        return None

    input_cost = (input_tokens / 1_000_000) * tier.input_price
    output_cost = (output_tokens / 1_000_000) * tier.output_price
    cached_cost = (cached_tokens / 1_000_000) * tier.cached_price

    return round(input_cost + output_cost + cached_cost, 6)


def get_pricing_table(provider: Optional[str] = None) -> list[PriceTier]:
    tiers = list(PRICING.values())
    if provider:
        tiers = [t for t in tiers if t.provider == provider.lower()]
    return sorted(tiers, key=lambda t: (t.provider, t.model))
