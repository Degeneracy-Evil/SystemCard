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


def frequency(value: object | None) -> str:
    """Format a hertz value as a human frequency."""
    if not isinstance(value, Real) or value < 0:
        return UNKNOWN
    hertz = float(value)
    if hertz >= 1e9:
        return f"{hertz / 1e9:.2f} GHz"
    if hertz >= 1e6:
        return f"{hertz / 1e6:.0f} MHz"
    return UNKNOWN


def percent(value: object | None) -> str:
    """Format a 0-100 ratio as a percentage string."""
    if not isinstance(value, Real) or not 0 <= value <= 100:
        return UNKNOWN
    return f"{float(value):.1f}%"


def enum_text(mapping: dict[int, str], value: object | None, fallback: str = UNKNOWN) -> str:
    """Map an integer enum value to a display string."""
    try:
        return mapping.get(int(value), fallback)
    except (TypeError, ValueError):
        return fallback
