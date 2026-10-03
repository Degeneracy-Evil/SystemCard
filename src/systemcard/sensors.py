"""Display typed sensor readings without interpreting device alarm rules."""

from typing import Any, Callable, List, Mapping, Tuple

from systemcard.formatters import UNKNOWN, pci_address, temperature, text
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import mapping_items, mapping_value, number_value


def _rpm(value: object) -> str:
    number = number_value(value)
    return UNKNOWN if number is None else f"{number} RPM"


def _power(value: object) -> str:
    number = number_value(value)
    return UNKNOWN if number is None else f"{number / 1000000:.3f} W"


def sensor_groups() -> Tuple[Tuple[str, str, Callable[[object], str]], ...]:
    return (("temperatures", "Temperatures", temperature), ("fans", "Fans", _rpm), ("powers", "Power", _power))


def sensor_name(sensor: Mapping[str, Any]) -> str:
    identity = mapping_value(sensor.get("identity"))
    address = pci_address(identity.get("pci_address"))
    chip = text(identity.get("chip"))
    if address != UNKNOWN:
        chip += f" ({address})"
    return "{} · {}".format(chip, text(identity.get("label") or identity.get("channel")))


def _reported_state(sensor: Mapping[str, Any]) -> str:
    if sensor.get("unit_supported") is False:
        return "Unit unsupported"
    if sensor.get("fault") is True:
        return "Read fault"
    if sensor.get("enabled") is False:
        return "Disabled"
    asserted = [
        text(alarm.get("attribute")) for alarm in mapping_items(sensor.get("alarms")) if alarm.get("active") is True
    ]
    return ", ".join(asserted) or "No asserted flags reported"


def sensors_card(info: Mapping[str, Any]) -> Card:
    sensors = mapping_value(info.get("sensors"))
    tables: List[DetailTable] = []
    rows: List[Tuple[str, str]] = []
    for key, title, formatter in sensor_groups():
        items = mapping_items(sensors.get(key))
        rows.append((title, f"{len(items)} observed" if items else "No reports available"))
        if not items:
            continue
        fields = [("input", "Current")]
        fields.extend(
            (field, label)
            for field, label in (
                ("average", "Average"),
                ("minimum", "Minimum"),
                ("maximum", "Maximum"),
                ("critical", "Critical"),
            )
            if any(item.get(field) is not None for item in items)
        )
        values = tuple(
            (sensor_name(item), *(formatter(item.get(field)) for field, _ in fields), _reported_state(item))
            for item in items
        )
        tables.append(DetailTable(title, ("Sensor", *(label for _, label in fields), "Reported state"), values))
    identities = tuple(
        (
            sensor_name(item),
            text(mapping_value(item.get("identity")).get("channel")),
            pci_address(mapping_value(item.get("identity")).get("pci_address")),
            text(mapping_value(item.get("identity")).get("origin")),
        )
        for key, _, _ in sensor_groups()
        for item in mapping_items(sensors.get(key))
    )
    if identities:
        tables.append(DetailTable("Sensor identity", ("Sensor", "Channel", "PCI", "Origin"), identities))
    return Card("sensors", "Hardware sensors", tuple(rows), tuple(tables))
