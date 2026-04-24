"""Tests for database layer."""

import os
import tempfile
from pathlib import Path

import pytest

from tokentrack.models import UsageEntry, Budget
from tokentrack import db


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    c = db.get_db(path)
    yield c
    c.close()


def test_schema_created(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r["name"] for r in tables}
    assert "usage" in names
    assert "budgets" in names
    assert "meta" in names


def test_log_and_query(conn):
    entry = UsageEntry(
        provider="openai", model="gpt-4o",
        input_tokens=1000, output_tokens=500,
        cost=0.0075,
    )
    row_id = db.log_usage(conn, entry)
    assert row_id == 1

    results = db.query_usage(conn)
    assert len(results) == 1
    assert results[0].provider == "openai"
    assert results[0].input_tokens == 1000
    assert results[0].cost == 0.0075


def test_query_with_filters(conn):
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=100, output_tokens=50))
    db.log_usage(conn, UsageEntry(provider="anthropic", model="sonnet", input_tokens=200, output_tokens=100))

    openai_only = db.query_usage(conn, provider="openai")
    assert len(openai_only) == 1
    assert openai_only[0].provider == "openai"


def test_summary(conn):
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500, cost=0.01))
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=2000, output_tokens=1000, cost=0.02))

    summary = db.get_summary(conn)
    assert summary["today"]["cost"] == pytest.approx(0.03)
    assert summary["today"]["tokens"] == 4500
    assert summary["today"]["calls"] == 2


def test_budget_lifecycle(conn):
    b = db.set_budget(conn, "daily", 5.00)
    assert b.period == "daily"
    assert b.amount == 5.00

    budgets = db.get_budgets(conn)
    assert len(budgets) == 1

    db.set_budget(conn, "daily", 10.00)
    budgets = db.get_budgets(conn)
    assert len(budgets) == 1
    assert budgets[0].amount == 10.00

    count = db.clear_budgets(conn)
    assert count == 1
    assert db.get_budgets(conn) == []


def test_check_budgets(conn):
    db.set_budget(conn, "daily", 1.00)
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=100000, output_tokens=50000, cost=1.50))

    results = db.check_budgets(conn)
    assert len(results) == 1
    budget, spent, exceeded = results[0]
    assert exceeded is True
    assert spent == pytest.approx(1.50)


def test_top_models(conn):
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500, cost=0.01))
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500, cost=0.01))
    db.log_usage(conn, UsageEntry(provider="anthropic", model="sonnet", input_tokens=500, output_tokens=250, cost=0.005))

    top = db.get_top_models(conn)
    assert len(top) == 2
    assert top[0]["model"] == "gpt-4o"
    assert top[0]["calls"] == 2


def test_env_var_db_path(tmp_path):
    db_path = tmp_path / "custom.db"
    os.environ["TOKENTRACK_DB"] = str(db_path)
    try:
        c = db.get_db()
        assert db_path.exists()
        c.close()
    finally:
        del os.environ["TOKENTRACK_DB"]
