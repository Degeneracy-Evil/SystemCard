"""Formatting helpers shared by presentation models and renderers."""

from typing import Dict, Optional

from systemcard.schema import integer_value, mapping_value, number_value

UNKNOWN = "—"


def text(value: Optional[object]) -> str:
    """Return a consistent display value for optional strings and scalars."""
    if value is None or value == "":
        return UNKNOWN
    return str(value)


def bytes_value(value: Optional[object]) -> str:
    """Format a byte count using binary units."""
    value = number_value(value)
    if value is None or value < 0:
        return UNKNOWN

    amount = float(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.1f} {unit}"
        amount /= 1024
    return UNKNOWN


def frequency(value: Optional[object]) -> str:
    """Format a hertz value as a human frequency."""
    value = number_value(value)
    if value is None or value < 0:
        return UNKNOWN
    hertz = float(value)
    if hertz >= 1e9:
        return f"{hertz / 1e9:.2f} GHz"
    if hertz >= 1e6:
        return f"{hertz / 1e6:.0f} MHz"
    return UNKNOWN


def bit_rate(value: Optional[object]) -> str:
    """Format a bit-per-second value using decimal network units."""
    value = number_value(value)
    if value is None or value <= 0:
        return UNKNOWN
    rate = float(value)
    if rate >= 1e9:
        return f"{rate / 1e9:g} Gbps"
    if rate >= 1e6:
        return f"{rate / 1e6:g} Mbps"
    if rate >= 1e3:
        return f"{rate / 1e3:g} Kbps"
    return f"{rate:g} bps"


def temperature(value: Optional[object]) -> str:
    """Format a millidegree Celsius value."""
    value = number_value(value)
    if value is None:
        return UNKNOWN
    return f"{float(value) / 1000:.1f} °C"


def yes_no(value: Optional[object]) -> str:
    """Format an optional boolean."""
    if not isinstance(value, bool):
        return UNKNOWN
    return "Yes" if value else "No"


def pci_address(value: Optional[object]) -> str:
    """Format a serialized PCI address."""
    address = mapping_value(value)
    parts = tuple(integer_value(address.get(key)) for key in ("domain", "bus", "device", "function"))
    if any(part is None for part in parts):
        return UNKNOWN
    domain, bus, device, function = (int(part) for part in parts if part is not None)
    if not (0 <= domain <= 0xFFFF and 0 <= bus <= 0xFF and 0 <= device <= 0x1F and 0 <= function <= 7):
        return UNKNOWN
    return f"{domain:04x}:{bus:02x}:{device:02x}.{function:x}"


def percent(value: Optional[object]) -> str:
    """Format a 0-100 ratio as a percentage string."""
    value = number_value(value)
    if value is None or not 0 <= value <= 100:
        return UNKNOWN
    return f"{float(value):.1f}%"


def enum_text(mapping: Dict[int, str], value: Optional[object], fallback: str = UNKNOWN) -> str:
    """Map an integer enum value to a display string."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return fallback
    try:
        return mapping.get(int(value), fallback)
    except (TypeError, ValueError):
        return fallback
