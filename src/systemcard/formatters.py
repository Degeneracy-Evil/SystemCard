"""Formatting helpers shared by presentation models and renderers."""

from __future__ import annotations

UNKNOWN = "—"


def text(value: object | None) -> str:
    """Return a consistent display value for optional strings and scalars."""
    if value is None or value == "":
        return UNKNOWN
    return str(value)


def bytes_value(value: object | None) -> str:
    """Format a byte count using binary units."""
    if not isinstance(value, (int, float)) or value < 0:
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
    if not isinstance(value, (int, float)) or value < 0:
        return UNKNOWN
    hertz = float(value)
    if hertz >= 1e9:
        return f"{hertz / 1e9:.2f} GHz"
    if hertz >= 1e6:
        return f"{hertz / 1e6:.0f} MHz"
    return UNKNOWN


def bit_rate(value: object | None) -> str:
    """Format a bit-per-second value using decimal network units."""
    if not isinstance(value, (int, float)) or value <= 0:
        return UNKNOWN
    rate = float(value)
    if rate >= 1e9:
        return f"{rate / 1e9:g} Gbps"
    if rate >= 1e6:
        return f"{rate / 1e6:g} Mbps"
    if rate >= 1e3:
        return f"{rate / 1e3:g} Kbps"
    return f"{rate:g} bps"


def temperature(value: object | None) -> str:
    """Format a millidegree Celsius value."""
    if not isinstance(value, (int, float)):
        return UNKNOWN
    return f"{float(value) / 1000:.1f} °C"


def yes_no(value: object | None) -> str:
    """Format an optional boolean."""
    if not isinstance(value, bool):
        return UNKNOWN
    return "Yes" if value else "No"


def pci_address(value: object | None) -> str:
    """Format a serialized PCI address."""
    if not isinstance(value, dict):
        return UNKNOWN
    parts = (value.get("domain"), value.get("bus"), value.get("device"), value.get("function"))
    if not all(isinstance(part, int) for part in parts):
        return UNKNOWN
    domain, bus, device, function = parts
    return f"{domain:04x}:{bus:02x}:{device:02x}.{function:x}"


def percent(value: object | None) -> str:
    """Format a 0-100 ratio as a percentage string."""
    if not isinstance(value, (int, float)) or not 0 <= value <= 100:
        return UNKNOWN
    return f"{float(value):.1f}%"


def enum_text(mapping: dict[int, str], value: object | None, fallback: str = UNKNOWN) -> str:
    """Map an integer enum value to a display string."""
    if not isinstance(value, (int, str)):
        return fallback
    try:
        return mapping.get(int(value), fallback)
    except (TypeError, ValueError):
        return fallback
