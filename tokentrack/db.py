"""SQLite database - schema, connection, and all data access."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .models import UsageEntry, Budget

SCHEMA_VERSION = "1"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS usage (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    provider       TEXT    NOT NULL,
    model          TEXT    NOT NULL,
    input_tokens   INTEGER NOT NULL DEFAULT 0,
    output_tokens  INTEGER NOT NULL DEFAULT 0,
    cached_tokens  INTEGER NOT NULL DEFAULT 0,
    cost           REAL,
    note           TEXT    DEFAULT '',
    session        TEXT    DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage(timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_provider  ON usage(provider);

CREATE TABLE IF NOT EXISTS budgets (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    period TEXT    NOT NULL UNIQUE,
    amount REAL    NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);
"""


def get_db(path: Optional[Path] = None) -> sqlite3.Connection:
    if path is None:
        env = os.environ.get("TOKENTRACK_DB")
        if env:
            path = Path(env)
        else:
            path = Path.home() / ".tokentrack" / "tokentrack.db"

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _init_schema(conn)
    return conn


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    if not row:
        conn.execute("INSERT INTO meta (key, value) VALUES ('schema_version', ?)", (SCHEMA_VERSION,))
        conn.commit()


def log_usage(conn: sqlite3.Connection, entry: UsageEntry) -> int:
    ts = entry.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cur = conn.execute(
        """INSERT INTO usage (timestamp, provider, model, input_tokens, output_tokens,
                              cached_tokens, cost, note, session)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ts, entry.provider, entry.model, entry.input_tokens, entry.output_tokens,
         entry.cached_tokens, entry.cost, entry.note, entry.session),
    )
    conn.commit()
    return cur.lastrowid


def query_usage(
    conn: sqlite3.Connection,
    start: Optional[str] = None,
    end: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    limit: int = 1000,
) -> list[UsageEntry]:
    clauses = []
    params: list = []

    if start:
        clauses.append("timestamp >= ?")
        params.append(start)
    if end:
        clauses.append("timestamp <= ?")
        params.append(end)
    if provider:
        clauses.append("provider = ?")
        params.append(provider)
    if model:
        clauses.append("model = ?")
        params.append(model)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM usage {where} ORDER BY timestamp DESC LIMIT ?",
        params + [limit],
    ).fetchall()

    return [UsageEntry(
        id=r["id"], timestamp=r["timestamp"], provider=r["provider"],
        model=r["model"], input_tokens=r["input_tokens"],
        output_tokens=r["output_tokens"], cached_tokens=r["cached_tokens"],
        cost=r["cost"], note=r["note"], session=r["session"],
    ) for r in rows]


def get_totals(
    conn: sqlite3.Connection,
    start: str,
    end: str,
    group_by: str = "day",
) -> list[dict]:
    fmt_map = {"day": "%Y-%m-%d", "week": "%Y-W%W", "month": "%Y-%m"}
    fmt = fmt_map.get(group_by, "%Y-%m-%d")

    rows = conn.execute(
        f"""SELECT strftime('{fmt}', timestamp) as period,
                   provider,
                   model,
                   SUM(input_tokens) as total_input,
                   SUM(output_tokens) as total_output,
                   SUM(cached_tokens) as total_cached,
                   SUM(cost) as total_cost,
                   COUNT(*) as calls
            FROM usage
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY period, provider, model
            ORDER BY period DESC, total_cost DESC""",
        (start, end),
    ).fetchall()

    return [dict(r) for r in rows]


def get_summary(conn: sqlite3.Connection) -> dict:
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    month_start = now.strftime("%Y-%m-01")

    def _sum(start: str) -> dict:
        row = conn.execute(
            """SELECT COALESCE(SUM(cost), 0) as cost,
                      COALESCE(SUM(input_tokens + output_tokens), 0) as tokens,
                      COUNT(*) as calls
               FROM usage WHERE timestamp >= ?""",
            (start,),
        ).fetchone()
        return dict(row)

    return {
        "today": _sum(today),
        "week": _sum(week_start),
        "month": _sum(month_start),
        "all_time": _sum("2000-01-01"),
    }


def get_daily_costs(conn: sqlite3.Connection, days: int = 30) -> list[tuple[str, float]]:
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT strftime('%Y-%m-%d', timestamp) as day,
                  COALESCE(SUM(cost), 0) as cost
           FROM usage
           WHERE timestamp >= ?
           GROUP BY day
           ORDER BY day""",
        (start,),
    ).fetchall()
    return [(r["day"], r["cost"]) for r in rows]


def get_top_models(conn: sqlite3.Connection, start: str = "2000-01-01", limit: int = 10) -> list[dict]:
    rows = conn.execute(
        """SELECT provider, model,
                  SUM(input_tokens + output_tokens) as total_tokens,
                  SUM(cost) as total_cost,
                  COUNT(*) as calls
           FROM usage
           WHERE timestamp >= ?
           GROUP BY provider, model
           ORDER BY total_cost DESC
           LIMIT ?""",
        (start, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_provider_breakdown(conn: sqlite3.Connection, start: str = "2000-01-01") -> list[dict]:
    rows = conn.execute(
        """SELECT provider,
                  SUM(input_tokens + output_tokens) as total_tokens,
                  SUM(cost) as total_cost,
                  COUNT(*) as calls
           FROM usage
           WHERE timestamp >= ?
           GROUP BY provider
           ORDER BY total_cost DESC""",
        (start,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Budgets ─────────────────────────────────────────────────────────

def set_budget(conn: sqlite3.Connection, period: str, amount: float) -> Budget:
    conn.execute(
        """INSERT INTO budgets (period, amount, active) VALUES (?, ?, 1)
           ON CONFLICT(period) DO UPDATE SET amount = excluded.amount, active = 1""",
        (period, amount),
    )
    conn.commit()
    return Budget(period=period, amount=amount, active=True)


def get_budgets(conn: sqlite3.Connection) -> list[Budget]:
    rows = conn.execute("SELECT * FROM budgets WHERE active = 1").fetchall()
    return [Budget(id=r["id"], period=r["period"], amount=r["amount"], active=bool(r["active"])) for r in rows]


def clear_budgets(conn: sqlite3.Connection) -> int:
    cur = conn.execute("UPDATE budgets SET active = 0 WHERE active = 1")
    conn.commit()
    return cur.rowcount


def check_budgets(conn: sqlite3.Connection) -> list[tuple[Budget, float, bool]]:
    budgets = get_budgets(conn)
    if not budgets:
        return []

    now = datetime.now(timezone.utc)
    results = []

    for b in budgets:
        if b.period == "daily":
            start = now.strftime("%Y-%m-%d")
        elif b.period == "weekly":
            start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        elif b.period == "monthly":
            start = now.strftime("%Y-%m-01")
        else:
            continue

        row = conn.execute(
            "SELECT COALESCE(SUM(cost), 0) as spent FROM usage WHERE timestamp >= ?",
            (start,),
        ).fetchone()
        spent = row["spent"]
        exceeded = spent >= b.amount
        results.append((b, spent, exceeded))

    return results
