"""Data models for tokentrack."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class UsageEntry:
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    cost: Optional[float] = None
    note: str = ""
    session: str = ""
    timestamp: str = ""
    id: Optional[int] = None


@dataclass
class Budget:
    period: str
    amount: float
    active: bool = True
    id: Optional[int] = None


@dataclass
class PriceTier:
    provider: str
    model: str
    input_price: float
    output_price: float
    cached_price: float = 0.0
