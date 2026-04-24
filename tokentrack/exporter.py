"""Export usage data to CSV or JSON."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Optional

from . import db


def export_csv(
    conn: sqlite3.Connection,
    output: Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> int:
    entries = db.query_usage(conn, start=start, end=end, limit=100_000)

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "timestamp", "provider", "model", "input_tokens",
            "output_tokens", "cached_tokens", "cost", "note", "session",
        ])
        for e in entries:
            writer.writerow([
                e.timestamp, e.provider, e.model, e.input_tokens,
                e.output_tokens, e.cached_tokens, e.cost or 0,
                e.note, e.session,
            ])

    return len(entries)


def export_json(
    conn: sqlite3.Connection,
    output: Path,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> int:
    entries = db.query_usage(conn, start=start, end=end, limit=100_000)

    data = [{
        "timestamp": e.timestamp,
        "provider": e.provider,
        "model": e.model,
        "input_tokens": e.input_tokens,
        "output_tokens": e.output_tokens,
        "cached_tokens": e.cached_tokens,
        "cost": e.cost or 0,
        "note": e.note,
        "session": e.session,
    } for e in entries]

    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return len(entries)
