"""CLI entry point - tokentrack commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .models import UsageEntry
from .pricing import resolve_model, calculate_cost, get_pricing_table
from .dashboard import render_dashboard, _format_cost, _format_tokens
from .reporter import print_report

app = typer.Typer(
    name="tokentrack",
    help="Terminal-native LLM token counter and usage tracker.",
)
console = Console()


def _version_callback(value: bool):
    if value:
        console.print(f"tokentrack {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=_version_callback,
        is_eager=True, help="Show version",
    ),
):
    """Terminal-native LLM token counter and usage tracker."""


# ── count ───────────────────────────────────────────────────────────

@app.command()
def count(
    text: str = typer.Argument(..., help="Text string or file path to count tokens for"),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model for tokenizer selection"),
):
    """Count tokens in a text string or file."""
    from .counter import count_tokens, count_file

    path = Path(text)
    if path.exists() and path.is_file():
        tokens, lines = count_file(path, model)
        console.print(Panel(
            f"File:    [cyan]{path.name}[/cyan]\n"
            f"Lines:   {lines:,}\n"
            f"Tokens:  [bold]{tokens:,}[/bold]\n"
            f"Model:   {model}",
            title="Token Count",
            border_style="cyan",
        ))

        tier = resolve_model(model)
        if tier:
            input_cost = (tokens / 1_000_000) * tier.input_price
            console.print(f"[dim]Estimated input cost: {_format_cost(input_cost)}[/dim]")
    else:
        tokens = count_tokens(text, model)
        console.print(Panel(
            f"Tokens:  [bold]{tokens:,}[/bold]\n"
            f"Chars:   {len(text):,}\n"
            f"Model:   {model}",
            title="Token Count",
            border_style="cyan",
        ))

        tier = resolve_model(model)
        if tier:
            input_cost = (tokens / 1_000_000) * tier.input_price
            console.print(f"[dim]Estimated input cost: {_format_cost(input_cost)}[/dim]")


# ── log ─────────────────────────────────────────────────────────────

@app.command()
def log(
    provider: str = typer.Option(..., "--provider", "-p", help="Provider: openai, anthropic, google"),
    model: str = typer.Option(..., "--model", "-m", help="Model name (e.g., gpt-4o, sonnet, gemini-pro)"),
    input_tokens: int = typer.Option(..., "--input", "-i", help="Input token count"),
    output_tokens: int = typer.Option(..., "--output", "-o", help="Output token count"),
    cached: int = typer.Option(0, "--cached", help="Cached token count"),
    note: str = typer.Option("", "--note", "-n", help="Optional note"),
    session: str = typer.Option("", "--session", "-s", help="Session tag for grouping"),
):
    """Log a usage entry with token counts."""
    from . import db as database

    tier = resolve_model(model)
    if tier:
        canonical_model = tier.model
        cost = calculate_cost(tier.provider, tier.model, input_tokens, output_tokens, cached)
    else:
        canonical_model = model
        cost = None

    entry = UsageEntry(
        provider=provider.lower(),
        model=canonical_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached,
        cost=cost,
        note=note,
        session=session,
    )

    conn = database.get_db()
    row_id = database.log_usage(conn, entry)

    parts = [
        f"[bold green]Logged[/bold green]  #{row_id}\n",
        f"  Provider:  {entry.provider}",
        f"  Model:     {entry.model}",
        f"  Input:     {_format_tokens(input_tokens)}",
        f"  Output:    {_format_tokens(output_tokens)}",
    ]
    if cached:
        parts.append(f"  Cached:    {_format_tokens(cached)}")
    if cost is not None:
        parts.append(f"  Cost:      {_format_cost(cost)}")
    else:
        parts.append("  Cost:      [yellow]unknown model - price not calculated[/yellow]")
    if note:
        parts.append(f"  Note:      {note}")

    console.print(Panel("\n".join(parts), title="tokentrack log", border_style="cyan"))

    budget_results = database.check_budgets(conn)
    for budget, spent, exceeded in budget_results:
        if exceeded:
            console.print(
                f"[bold red]⚠ Budget exceeded:[/bold red] {budget.period} - "
                f"{_format_cost(spent)} / {_format_cost(budget.amount)}"
            )
        elif spent >= budget.amount * 0.8:
            console.print(
                f"[yellow]⚠ Budget warning:[/yellow] {budget.period} - "
                f"{_format_cost(spent)} / {_format_cost(budget.amount)} (80%+)"
            )

    conn.close()


# ── dash ────────────────────────────────────────────────────────────

@app.command()
def dash():
    """Show a terminal dashboard with spend breakdown."""
    from . import db as database

    conn = database.get_db()
    summary = database.get_summary(conn)

    if summary["all_time"]["calls"] == 0:
        console.print("[dim]No usage data yet.[/dim] Log your first entry:")
        console.print("  tokentrack log -p openai -m gpt-4o -i 1000 -o 500")
        conn.close()
        return

    render_dashboard(conn, console)
    conn.close()


# ── report ──────────────────────────────────────────────────────────

@app.command()
def report(
    period: str = typer.Option("daily", "--period", "-p", help="Period: daily, weekly, monthly"),
    last: int = typer.Option(30, "--last", "-l", help="Number of periods to show"),
):
    """Show a usage report grouped by period."""
    from . import db as database

    if period not in ("daily", "weekly", "monthly"):
        console.print(f"[red]Invalid period:[/red] {period}")
        console.print("Choose: daily, weekly, monthly")
        raise typer.Exit(1)

    conn = database.get_db()
    print_report(conn, console, period, last)
    conn.close()


# ── budget ──────────────────────────────────────────────────────────

@app.command()
def budget(
    daily: Optional[float] = typer.Option(None, "--daily", help="Set daily budget in USD"),
    weekly: Optional[float] = typer.Option(None, "--weekly", help="Set weekly budget in USD"),
    monthly: Optional[float] = typer.Option(None, "--monthly", help="Set monthly budget in USD"),
    clear: bool = typer.Option(False, "--clear", help="Clear all budgets"),
    show: bool = typer.Option(False, "--show", help="Show current budgets"),
):
    """Set or view spending budgets."""
    from . import db as database

    conn = database.get_db()

    if clear:
        count = database.clear_budgets(conn)
        console.print(f"[yellow]Cleared {count} budget(s)[/yellow]")
        conn.close()
        return

    set_any = False
    for period, amount in [("daily", daily), ("weekly", weekly), ("monthly", monthly)]:
        if amount is not None:
            database.set_budget(conn, period, amount)
            console.print(f"[green]Set {period} budget:[/green] {_format_cost(amount)}")
            set_any = True

    if show or not set_any:
        results = database.check_budgets(conn)
        if not results:
            console.print("[dim]No budgets set.[/dim]")
            console.print("  tokentrack budget --daily 5.00 --monthly 100.00")
        else:
            for b, spent, exceeded in results:
                pct = (spent / b.amount * 100) if b.amount else 0
                color = "red" if exceeded else ("yellow" if pct >= 80 else "green")
                console.print(
                    f"  [{color}]{b.period.title()}[/{color}]  "
                    f"{_format_cost(spent)} / {_format_cost(b.amount)}  "
                    f"({pct:.0f}%)"
                )

    conn.close()


# ── prices ──────────────────────────────────────────────────────────

@app.command()
def prices(
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="Filter by provider"),
):
    """Show the built-in pricing table."""
    tiers = get_pricing_table(provider)

    if not tiers:
        console.print(f"[red]No pricing data for provider:[/red] {provider}")
        raise typer.Exit(1)

    table = Table(title="LLM Pricing (per 1M tokens)", border_style="cyan")
    table.add_column("Provider", style="yellow")
    table.add_column("Model")
    table.add_column("Input", justify="right", style="green")
    table.add_column("Output", justify="right", style="green")
    table.add_column("Cached", justify="right", style="dim")

    for t in tiers:
        table.add_row(
            t.provider,
            t.model,
            f"${t.input_price:.2f}",
            f"${t.output_price:.2f}",
            f"${t.cached_price:.3f}" if t.cached_price else "-",
        )

    console.print(table)


# ── export ──────────────────────────────────────────────────────────

@app.command(name="export")
def export_data(
    fmt: str = typer.Option("csv", "--format", "-f", help="Format: csv or json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    start: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, "--end", help="End date (YYYY-MM-DD)"),
):
    """Export usage data to CSV or JSON."""
    from . import db as database
    from .exporter import export_csv, export_json

    conn = database.get_db()

    if fmt == "csv":
        out_path = Path(output or "tokentrack_export.csv")
        count = export_csv(conn, out_path, start, end)
    elif fmt == "json":
        out_path = Path(output or "tokentrack_export.json")
        count = export_json(conn, out_path, start, end)
    else:
        console.print(f"[red]Unknown format:[/red] {fmt}. Use csv or json.")
        conn.close()
        raise typer.Exit(1)

    console.print(f"[green]Exported {count} entries[/green] → {out_path}")
    conn.close()
