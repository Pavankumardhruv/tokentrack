"""Rich terminal dashboard - summary, sparklines, tables."""

from __future__ import annotations

import sqlite3

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

from . import db


SPARK_CHARS = " ▁▂▃▄▅▆▇█"


def _sparkline(values: list[float]) -> str:
    if not values:
        return ""
    mx = max(values) or 1
    return "".join(SPARK_CHARS[min(int(v / mx * 8), 8)] for v in values)


def _format_cost(cost: float) -> str:
    if cost >= 1.0:
        return f"${cost:.2f}"
    if cost >= 0.01:
        return f"${cost:.3f}"
    return f"${cost:.4f}"


def _format_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def render_dashboard(conn: sqlite3.Connection, console: Console) -> None:
    summary = db.get_summary(conn)
    daily = db.get_daily_costs(conn, days=30)
    top = db.get_top_models(conn)
    providers = db.get_provider_breakdown(conn)
    budget_status = db.check_budgets(conn)

    panels = []

    today = summary["today"]
    week = summary["week"]
    month = summary["month"]
    all_time = summary["all_time"]

    summary_text = (
        f"[bold]Today[/bold]      {_format_cost(today['cost'])}  ({_format_tokens(today['tokens'])} tokens, {today['calls']} calls)\n"
        f"[bold]This week[/bold]  {_format_cost(week['cost'])}  ({_format_tokens(week['tokens'])} tokens, {week['calls']} calls)\n"
        f"[bold]This month[/bold] {_format_cost(month['cost'])}  ({_format_tokens(month['tokens'])} tokens, {month['calls']} calls)\n"
        f"[bold]All time[/bold]   {_format_cost(all_time['cost'])}  ({_format_tokens(all_time['tokens'])} tokens, {all_time['calls']} calls)"
    )
    panels.append(Panel(summary_text, title="Spend Summary", border_style="cyan"))

    if daily:
        costs = [c for _, c in daily]
        spark = _sparkline(costs)
        date_range = f"{daily[0][0]} → {daily[-1][0]}"
        spark_text = f"{spark}\n[dim]{date_range}  |  peak: {_format_cost(max(costs))}[/dim]"
        panels.append(Panel(spark_text, title="Daily Spend (30 days)", border_style="green"))

    for p in panels:
        console.print(p)

    if top:
        table = Table(title="Top Models", border_style="cyan", show_lines=False)
        table.add_column("Provider", style="yellow")
        table.add_column("Model")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Calls", justify="right", style="dim")

        total_cost = sum(r["total_cost"] or 0 for r in top)
        for r in top:
            cost = r["total_cost"] or 0
            pct = f" ({cost / total_cost * 100:.0f}%)" if total_cost else ""
            table.add_row(
                r["provider"], r["model"],
                _format_tokens(r["total_tokens"]),
                _format_cost(cost) + pct,
                str(r["calls"]),
            )
        console.print(table)

    if providers and len(providers) > 1:
        table = Table(title="By Provider", border_style="cyan", show_lines=False)
        table.add_column("Provider", style="yellow")
        table.add_column("Tokens", justify="right")
        table.add_column("Cost", justify="right", style="green")
        table.add_column("Calls", justify="right", style="dim")

        for r in providers:
            table.add_row(
                r["provider"],
                _format_tokens(r["total_tokens"]),
                _format_cost(r["total_cost"] or 0),
                str(r["calls"]),
            )
        console.print(table)

    if budget_status:
        lines = []
        for budget, spent, exceeded in budget_status:
            pct = (spent / budget.amount * 100) if budget.amount else 0
            bar_len = 20
            filled = min(int(pct / 100 * bar_len), bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

            if exceeded:
                color = "red"
                status = "EXCEEDED"
            elif pct >= 80:
                color = "yellow"
                status = "WARNING"
            else:
                color = "green"
                status = "OK"

            lines.append(
                f"[bold]{budget.period.title()}[/bold]  "
                f"[{color}]{bar}[/{color}]  "
                f"{_format_cost(spent)} / {_format_cost(budget.amount)}  "
                f"[{color}]{status}[/{color}]"
            )

        console.print(Panel("\n".join(lines), title="Budgets", border_style="cyan"))
