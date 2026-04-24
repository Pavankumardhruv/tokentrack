"""Tests for dashboard rendering."""

from tokentrack.dashboard import _sparkline, _format_cost, _format_tokens


def test_sparkline_empty():
    assert _sparkline([]) == ""


def test_sparkline_values():
    result = _sparkline([0, 5, 10, 5, 0])
    assert len(result) == 5
    assert result[2] in "█"


def test_format_cost():
    assert _format_cost(10.50) == "$10.50"
    assert _format_cost(0.05) == "$0.050"
    assert _format_cost(0.001) == "$0.0010"


def test_format_tokens():
    assert _format_tokens(500) == "500"
    assert _format_tokens(1500) == "1.5K"
    assert _format_tokens(2_500_000) == "2.5M"
