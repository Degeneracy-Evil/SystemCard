"""Present C++ hardware findings, keeping current and historical evidence separate."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import text
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, mapping_items, mapping_value
from systemcard.sensors import sensor_groups, sensor_name
from systemcard.storage_health import (
    DRIVE_FINDINGS,
    HISTORICAL_FINDINGS,
    drive_finding_tables,
    query_summary,
    storage_health_tables,
)

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


def health_card(info: Mapping[str, Any], detailed: bool = True) -> Card:
    health = mapping_value(info.get("hardware_health"))
    alerts = sorted(mapping_items(health.get("sensor_alerts")), key=lambda item: -integer_or(item.get("severity"), -1))
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
    drive_findings = mapping_items(health.get("drive_findings"))
    current_drives = [
        item for item in drive_findings if integer_or(item.get("kind"), -1) not in HISTORICAL_FINDINGS | {3}
    ]
    estimates = [item for item in drive_findings if integer_or(item.get("kind"), -1) == 3]
    historical = [item for item in drive_findings if integer_or(item.get("kind"), -1) in HISTORICAL_FINDINGS]
    summaries.extend(
        "{}: {}".format(
            text(item.get("target")), DRIVE_FINDINGS.get(integer_or(item.get("kind"), -1), "Unknown finding")
        )
        for item in sorted(current_drives, key=lambda item: -integer_or(item.get("severity"), -1))
    )
    if detailed:
        tables.extend(drive_finding_tables(health))
        tables.extend(storage_health_tables(mapping_value(info.get("storage")), detailed=True))
        if memory:
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
        ("Current findings", str(len(alerts) + len(storage) + len(current_drives))),
        ("Endurance estimates", str(len(estimates))),
        ("Historical reports", str(len(memory) + len(historical))),
        ("Drive queries", query_summary(mapping_value(info.get("storage")))),
        ("Scope", "Reported evidence only; missing data stays unknown"),
    )
    if not summaries:
        summaries.extend(
            "{}: {}".format(
                text(item.get("target")), DRIVE_FINDINGS.get(integer_or(item.get("kind"), -1), "Unknown finding")
            )
            for item in estimates + historical
        )
    if summaries:
        rows += (("Findings", "; ".join(summaries[:3]) + ("; more in --section health" if len(summaries) > 3 else "")),)
    return Card("health", "Hardware findings", rows, tuple(tables))
