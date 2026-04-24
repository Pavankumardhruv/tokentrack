# tokentrack

[![tests](https://github.com/Pavankumardhruv/tokentrack/actions/workflows/test.yml/badge.svg)](https://github.com/Pavankumardhruv/tokentrack/actions/workflows/test.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Know exactly what your AI costs.**

tokentrack is a terminal-native tool that counts LLM tokens and tracks your API spend across OpenAI, Anthropic, and Google — all from the command line. No dashboards to log into, no spreadsheets to maintain.

---

## The Problem

You're building with LLMs and have no idea what you're spending. API bills surprise you at the end of the month. You switch between GPT-4o, Claude, and Gemini but can't compare costs. There's no single place to see:

- How many tokens you've used today
- Which model is eating your budget
- Whether you're on track to blow past your monthly limit

tokentrack fixes that — right in your terminal, where you already work.

---

## Install

```bash
pip install tokentrack
```

For accurate OpenAI token counting (optional):
```bash
pip install tokentrack[openai]
```

Requires Python 3.10+.

---

## Quick Start

```bash
# Count tokens in a string
tokentrack count "Explain quantum computing in simple terms"

# Count tokens in a file
tokentrack count main.py

# Log an API call
tokentrack log -p openai -m gpt-4o -i 1500 -o 800

# See your dashboard
tokentrack dash

# Check the pricing table
tokentrack prices
```

---

## Commands

### `tokentrack count` — Count tokens

```bash
# Count tokens in text
tokentrack count "Your text here"

# Count tokens in a file
tokentrack count src/app.py

# Specify a model for the tokenizer
tokentrack count README.md --model claude-sonnet
```

Output:
```
╭──────── Token Count ────────╮
│ File:    app.py              │
│ Lines:   142                 │
│ Tokens:  1,847               │
│ Model:   gpt-4o              │
╰──────────────────────────────╯
Estimated input cost: $0.0046
```

### `tokentrack log` — Log usage

```bash
# Basic logging
tokentrack log -p openai -m gpt-4o -i 1500 -o 800

# With cache hits
tokentrack log -p anthropic -m sonnet -i 3000 -o 1200 --cached 500

# With a note
tokentrack log -p openai -m gpt-4o -i 2000 -o 600 --note "summarize docs"

# With a session tag
tokentrack log -p google -m gemini-pro -i 5000 -o 2000 --session "batch-1"
```

Cost is calculated automatically from built-in pricing. Model names are flexible — you can use short aliases:

| You type | Resolves to |
|---|---|
| `gpt-4o`, `4o` | openai/gpt-4o |
| `sonnet`, `claude-sonnet` | anthropic/claude-sonnet-4-20250514 |
| `opus`, `claude-opus` | anthropic/claude-opus-4-20250514 |
| `haiku`, `claude-haiku` | anthropic/claude-haiku-3.5 |
| `gemini-pro` | google/gemini-2.5-pro |
| `gemini-flash` | google/gemini-2.5-flash |
| `o3`, `o3-mini`, `o4-mini` | openai/o3, o3-mini, o4-mini |
| `4.1`, `4.1-mini`, `4.1-nano` | openai/gpt-4.1 family |

### `tokentrack dash` — Terminal dashboard

```bash
tokentrack dash
```

Shows:
- **Spend summary** — today, this week, this month, all time
- **Daily sparkline** — 30-day spend visualized with Unicode bars
- **Top models** — ranked by cost with percentage breakdown
- **Provider breakdown** — OpenAI vs Anthropic vs Google
- **Budget status** — color-coded progress bars

### `tokentrack report` — Usage reports

```bash
# Daily report (last 30 days)
tokentrack report

# Weekly report
tokentrack report --period weekly

# Monthly report, last 12 months
tokentrack report --period monthly --last 12
```

### `tokentrack budget` — Spending alerts

```bash
# Set budgets
tokentrack budget --daily 5.00 --monthly 100.00

# View current budgets
tokentrack budget --show

# Clear all budgets
tokentrack budget --clear
```

When you `tokentrack log` an entry, it automatically checks your budgets and warns you:
- **Yellow warning** at 80% of budget
- **Red alert** when exceeded

### `tokentrack prices` — Pricing table

```bash
# All providers
tokentrack prices

# Filter by provider
tokentrack prices --provider anthropic
```

Shows input, output, and cached token prices per 1M tokens for every supported model.

### `tokentrack export` — Export data

```bash
# Export to CSV
tokentrack export --format csv

# Export to JSON
tokentrack export --format json --output usage.json

# Export a date range
tokentrack export --format csv --start 2026-04-01 --end 2026-04-30
```

---

## Supported Models

### OpenAI
| Model | Input | Output | Cached |
|---|---|---|---|
| gpt-4o | $2.50 | $10.00 | $1.25 |
| gpt-4o-mini | $0.15 | $0.60 | $0.075 |
| gpt-4.1 | $2.00 | $8.00 | $0.50 |
| gpt-4.1-mini | $0.40 | $1.60 | $0.10 |
| gpt-4.1-nano | $0.10 | $0.40 | $0.025 |
| o3 | $2.00 | $8.00 | $0.50 |
| o3-mini | $1.10 | $4.40 | $0.275 |
| o4-mini | $1.10 | $4.40 | $0.275 |

### Anthropic
| Model | Input | Output | Cached |
|---|---|---|---|
| claude-sonnet-4-20250514 | $3.00 | $15.00 | $0.30 |
| claude-opus-4-20250514 | $15.00 | $75.00 | $1.50 |
| claude-haiku-3.5 | $0.80 | $4.00 | $0.08 |

### Google
| Model | Input | Output |
|---|---|---|
| gemini-2.5-pro | $1.25 | $10.00 |
| gemini-2.5-flash | $0.15 | $0.60 |
| gemini-2.0-flash | $0.10 | $0.40 |

*Prices are per 1M tokens in USD.*

---

## Storage

All data is stored locally in a SQLite database:

```
~/.tokentrack/tokentrack.db
```

Override with the `TOKENTRACK_DB` environment variable:

```bash
export TOKENTRACK_DB=/path/to/custom.db
```

The database is human-readable with any SQLite client:

```bash
sqlite3 ~/.tokentrack/tokentrack.db "SELECT * FROM usage ORDER BY timestamp DESC LIMIT 10"
```

---

## Use as a Library

tokentrack can be imported directly in your Python code:

```python
from tokentrack.counter import count_tokens
from tokentrack.pricing import calculate_cost
from tokentrack.db import get_db, log_usage
from tokentrack.models import UsageEntry

# Count tokens
tokens = count_tokens("Hello, world!", model="gpt-4o")

# Calculate cost
cost = calculate_cost("openai", "gpt-4o", input_tokens=1500, output_tokens=800)

# Log usage after an API call
conn = get_db()
entry = UsageEntry(
    provider="openai",
    model="gpt-4o",
    input_tokens=1500,
    output_tokens=800,
    cost=cost,
    note="summarize docs",
)
log_usage(conn, entry)
conn.close()
```

---

## How It Works

```
tokentrack count "text"     →  Counts tokens (tiktoken or estimator)
tokentrack log ...          →  Writes to SQLite with auto-calculated cost
tokentrack dash             →  Reads SQLite, renders rich terminal dashboard
tokentrack report           →  Aggregates by day/week/month
tokentrack budget           →  Stores limits, checks on every log
tokentrack export           →  Dumps to CSV or JSON
```

Everything is local. No API keys needed (unless you want accurate OpenAI token counts via tiktoken). No cloud. No accounts.

---

## License

MIT
