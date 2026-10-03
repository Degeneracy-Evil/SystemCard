"""Present C++ hardware findings, keeping current and historical evidence separate."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import text
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, mapping_items, mapping_value
from systemcard.sensors import sensor_groups, sensor_name

_SEVERITY = {0: "Information", 1: "Warning", 2: "Critical"}
_KINDS = {
    0: "Driver alarm asserted",
    1: "Sensor read fault",
    2: "Reported critical limit reached",
    3: "Below reported minimum",
    4: "Above reported maximum",
}
_COVERAGE = {
    0: "Not requested",
    1: "No usable evidence",
    2: "Partial evidence",
    3: "Evidence available (not a completeness guarantee)",
}


def has_findings(info: Mapping[str, Any]) -> bool:
    health = mapping_value(info.get("hardware_health"))
    return any(mapping_items(health.get(key)) for key in ("sensor_alerts", "storage_alerts", "memory_events"))


def health_card(info: Mapping[str, Any], detailed: bool = True) -> Card:
    health = mapping_value(info.get("hardware_health"))
    alerts = mapping_items(health.get("sensor_alerts"))
    storage = mapping_items(health.get("storage_alerts"))
    memory = mapping_items(health.get("memory_events"))
    tables: List[DetailTable] = []
    summaries: List[str] = []
    readings = {
        str(mapping_value(item.get("identity")).get("id")): (
            sensor_name(item),
            formatter(item.get("input")),
            formatter(item.get("minimum")),
            formatter(item.get("maximum")),
            formatter(item.get("critical")),
        )
        for key, _, formatter in sensor_groups()
        for item in mapping_items(mapping_value(info.get("sensors")).get(key))
    }
    if alerts:
        values = []
        for alert in alerts:
            identity = str(alert.get("sensor"))
            name, current, minimum, maximum, critical = readings.get(identity, (identity, "—", "—", "—", "—"))
            summaries.append("{}: {}".format(name, _KINDS.get(integer_or(alert.get("kind"), -1), "Unknown finding")))
            values.append(
                (
                    _SEVERITY.get(integer_or(alert.get("severity"), -1), "Unknown"),
                    name,
                    _KINDS.get(integer_or(alert.get("kind"), -1), "Unknown finding"),
                    current,
                    f"min {minimum} / max {maximum} / critical {critical}",
                    text(alert.get("origin")),
                )
            )
        if detailed:
            tables.append(
                DetailTable(
                    "Current sensor findings",
                    ("Level", "Sensor", "Finding", "Reading", "Reported limits", "Evidence"),
                    tuple(values),
                )
            )
    summaries.extend(
        "{}: RAID degraded ({} members)".format(text(item.get("device")), text(item.get("degraded_members")))
        for item in storage
    )
    if storage and detailed:
        tables.append(
            DetailTable(
                "RAID findings",
                ("Device", "Missing members", "Evidence"),
                tuple(
                    (text(item.get("device")), text(item.get("degraded_members")), text(item.get("origin")))
                    for item in storage
                ),
            )
        )
    if memory and detailed:
        tables.append(
            DetailTable(
                "EDAC historical events (since initialization/reset)",
                ("Controller", "Corrected", "Uncorrected", "Level", "Evidence"),
                tuple(
                    (
                        text(item.get("controller_index")),
                        text(item.get("corrected")),
                        text(item.get("uncorrected")),
                        _SEVERITY.get(integer_or(item.get("severity"), -1), "Unknown"),
                        text(item.get("origin")),
                    )
                    for item in memory
                ),
            )
        )
    if detailed:
        coverage = mapping_items(health.get("coverage"))
        tables.append(
            DetailTable(
                "Evidence coverage",
                ("Domain", "Availability", "Usable readings", "Reported flags"),
                tuple(
                    (
                        text(item.get("domain")),
                        _COVERAGE.get(integer_or(item.get("status"), -1), "Unknown"),
                        text(item.get("usable_readings")),
                        text(item.get("alarm_reports")),
                    )
                    for item in coverage
                )
                or (("—", "No coverage reports in this snapshot", "—", "—"),),
            )
        )
    rows: Tuple[Tuple[str, str], ...] = (
        ("Observed sensor findings", str(len(alerts))),
        ("Reported RAID degradation", str(len(storage))),
        ("Historical memory events", str(len(memory))),
        ("Scope", "Only reported evidence; missing data does not establish normal operation"),
    )
    if summaries:
        rows += (("Findings", "; ".join(summaries[:3]) + ("; more in --section health" if len(summaries) > 3 else "")),)
    return Card("health", "Hardware findings", rows, tuple(tables))
