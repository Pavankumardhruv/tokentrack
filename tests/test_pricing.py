"""Tests for pricing module."""

from tokentrack.pricing import resolve_model, calculate_cost, get_pricing_table


def test_resolve_exact_key():
    tier = resolve_model("openai/gpt-4o")
    assert tier is not None
    assert tier.model == "gpt-4o"


def test_resolve_alias():
    tier = resolve_model("sonnet")
    assert tier is not None
    assert tier.provider == "anthropic"

    tier = resolve_model("4o")
    assert tier is not None
    assert tier.model == "gpt-4o"


def test_resolve_partial():
    tier = resolve_model("haiku")
    assert tier is not None
    assert tier.provider == "anthropic"


def test_resolve_unknown():
    assert resolve_model("nonexistent-model-xyz") is None


def test_calculate_cost():
    cost = calculate_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=500)
    assert cost is not None
    expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00
    assert abs(cost - expected) < 0.000001


def test_calculate_cost_with_cache():
    cost = calculate_cost("openai", "gpt-4o", input_tokens=1000, output_tokens=500, cached_tokens=200)
    assert cost is not None
    expected = (1000 / 1_000_000) * 2.50 + (500 / 1_000_000) * 10.00 + (200 / 1_000_000) * 1.25
    assert abs(cost - expected) < 0.000001


def test_calculate_cost_unknown():
    cost = calculate_cost("unknown", "nonexistent", input_tokens=100, output_tokens=50)
    assert cost is None


def test_pricing_table():
    all_tiers = get_pricing_table()
    assert len(all_tiers) > 10

    openai_tiers = get_pricing_table("openai")
    assert all(t.provider == "openai" for t in openai_tiers)


def test_pricing_table_sorted():
    tiers = get_pricing_table()
    providers = [t.provider for t in tiers]
    assert providers == sorted(providers)
