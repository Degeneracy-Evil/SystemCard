"""Formatting helpers shared by presentation models and renderers."""

from __future__ import annotations

from numbers import Real

UNKNOWN = "—"


def text(value: object | None) -> str:
    """Return a consistent display value for optional strings and scalars."""
    if value is None or value == "":
        return UNKNOWN
    return str(value)


def bytes_value(value: object | None) -> str:
    """Format a byte count using binary units."""
    if not isinstance(value, Real) or value < 0:
        return UNKNOWN

    amount = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return UNKNOWN
