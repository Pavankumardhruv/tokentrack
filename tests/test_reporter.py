"""Tests for reporter module."""

import pytest

from tokentrack.models import UsageEntry
from tokentrack import db
from tokentrack.reporter import print_report


@pytest.fixture
def conn(tmp_path):
    path = tmp_path / "test.db"
    c = db.get_db(path)
    yield c
    c.close()


def test_report_empty(conn, capsys):
    from rich.console import Console
    console = Console(file=open("/dev/null", "w"))
    print_report(conn, console, "daily")


def test_report_with_data(conn):
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=1000, output_tokens=500, cost=0.01))
    db.log_usage(conn, UsageEntry(provider="openai", model="gpt-4o", input_tokens=2000, output_tokens=1000, cost=0.02))

    totals = db.get_totals(conn, "2000-01-01", "2099-12-31", "day")
    assert len(totals) >= 1
    assert totals[0]["total_input"] == 3000
