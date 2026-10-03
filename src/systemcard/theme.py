"""Semantic Rich styles used by the terminal renderer."""

from typing import Dict

from rich.text import Text

SECTION_STYLES: Dict[str, str] = {
    "system": "bright_blue",
    "cpu": "bright_cyan",
    "memory": "bright_magenta",
    "accelerators": "bright_green",
    "network": "green",
    "storage": "yellow",
    "software": "blue",
    "execution": "magenta",
    "topology": "bright_cyan",
    "sensors": "bright_cyan",
    "health": "yellow",
}


def section_style(section: str) -> str:
    """Return the stable accent color for a card section."""
    return SECTION_STYLES.get(section, "cyan")


def value_text(label: str, value: str) -> Text:
    """Apply semantic styling to a summary value."""
    if value == "—":
        return Text(value, style="dim")
    lowered = label.lower()
    if "temperature" in lowered:
        return Text(value, style=_temperature_style(value))
    if "visibility" in lowered or "visible resources" in lowered:
        return Text(value, style="green")
    if lowered in {"model", "operating system", "hardware", "summary"}:
        return Text(value, style="bold")
    return Text(value)


def cell_text(column: str, value: str) -> Text:
    """Apply status-aware styling to a detail-table cell."""
    if value == "—" or value.endswith(" —"):
        return Text(value, style="dim")
    column = column.lower()
    normalized = value.upper()
    if column in {"state", "link"}:
        if normalized.startswith("UP"):
            return Text(value, style="bold green")
        if normalized.startswith("DOWN"):
            return Text(value, style="bold red")
        return Text(value, style="yellow")
    if column in {"visible", "loaded"}:
        return Text(value, style="bold green" if normalized == "YES" else "red")
    if column == "temperature":
        return Text(value, style=_temperature_style(value))
    if column in {"kind", "level"}:
        return Text(value, style="bold cyan")
    return Text(value)


def _temperature_style(value: str) -> str:
    """Color temperatures using conservative server-oriented thresholds."""
    try:
        celsius = float(value.split()[0])
    except (ValueError, IndexError):
        return "yellow"
    if celsius >= 85:
        return "bold red"
    if celsius >= 70:
        return "bold yellow"
    return "green"
