"""Tests for token counter."""

from pathlib import Path

from tokentrack.counter import count_tokens, count_file, _estimate_tokens


def test_estimate_tokens():
    text = "Hello world, this is a test."
    tokens = _estimate_tokens(text)
    assert tokens == len(text) // 4


def test_estimate_minimum():
    assert _estimate_tokens("") == 1
    assert _estimate_tokens("hi") == 1


def test_count_tokens_returns_positive():
    tokens = count_tokens("The quick brown fox jumps over the lazy dog.")
    assert tokens > 0


def test_count_tokens_longer_text_more_tokens():
    short = count_tokens("Hello")
    long = count_tokens("Hello world, this is a much longer piece of text that should have more tokens.")
    assert long > short


def test_count_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Line one\nLine two\nLine three\n")
    tokens, lines = count_file(f)
    assert tokens > 0
    assert lines == 3


def test_count_tokens_claude_model():
    tokens = count_tokens("Test text for Claude model", model="claude-sonnet-4-20250514")
    assert tokens > 0
