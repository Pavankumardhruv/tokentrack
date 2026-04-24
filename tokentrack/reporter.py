"""Report generation — daily, weekly, monthly aggregation."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone, timedelta

from rich.console import Console
from rich.table import Table

from . import db
from .dashboard import _format_cost, _format_tokens


def print_report(
    conn: sqlite3.Connection,
    console: Console,
    period: str = "daily",
    last_n: int = 30,
) -> None:
    now = datetime.now(timezone.utc)

    if period == "daily":
        start = (now - timedelta(days=last_n)).strftime("%Y-%m-%d")
        group = "day"
    elif period == "weekly":
        start = (now - timedelta(weeks=last_n)).strftime("%Y-%m-%d")
        group = "week"
    elif period == "monthly":
        start = (now - timedelta(days=last_n * 30)).strftime("%Y-%m-%d")
        group = "month"
    else:
        start = "2000-01-01"
        group = "day"

    end = now.strftime("%Y-%m-%dT23:59:59Z")
    rows = db.get_totals(conn, start, end, group)

    if not rows:
        console.print("[dim]No usage data for this period.[/dim]")
        return

    table = Table(
        title=f"{period.title()} Report",
        border_style="cyan",
        show_lines=False,
    )
    table.add_column("Period", style="bold")
    table.add_column("Provider", style="yellow")
    table.add_column("Model")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Calls", justify="right", style="dim")

    total_cost = 0.0
    total_input = 0
    total_output = 0
    total_calls = 0

    for r in rows:
        cost = r["total_cost"] or 0
        total_cost += cost
        total_input += r["total_input"]
        total_output += r["total_output"]
        total_calls += r["calls"]

        table.add_row(
            r["period"],
            r["provider"],
            r["model"],
            _format_tokens(r["total_input"]),
            _format_tokens(r["total_output"]),
            _format_cost(cost),
            str(r["calls"]),
        )

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {_format_cost(total_cost)}  |  "
        f"{_format_tokens(total_input)} in + {_format_tokens(total_output)} out  |  "
        f"{total_calls} calls"
    )
