"""Immutable terminal presentation types shared by card builders."""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class DetailTable:
    title: str
    columns: Tuple[str, ...]
    rows: Tuple[Tuple[str, ...], ...]
    omitted: int = 0
    group_by: Optional[int] = None


@dataclass(frozen=True)
class Card:
    section: str
    title: str
    rows: Tuple[Tuple[str, str], ...]
    tables: Tuple[DetailTable, ...] = ()


@dataclass(frozen=True)
class DisplayModel:
    title: str
    subtitle: str
    cards: Tuple[Card, ...]
    warnings: Tuple[str, ...]
    footer: str = ""
