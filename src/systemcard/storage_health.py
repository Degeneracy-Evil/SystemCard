"""Display protocol-specific drive reports without interpreting vendor attributes."""

from typing import Any, Dict, List, Mapping, Tuple

from systemcard.collection_status import READ_FAILURES, collection_result
from systemcard.formatters import UNKNOWN, temperature, text, yes_no
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_or, integer_value, list_value, mapping_items, mapping_value

PROTOCOLS = {0: "Unknown", 1: "NVMe controller", 2: "ATA disk", 3: "SCSI disk"}
DRIVE_FINDINGS = {
    0: "Device reports SMART failure",
    1: "NVMe critical warning asserted",
    2: "Available spare below reported threshold",
    3: "Estimated endurance used reached 100% (not an immediate failure prediction)",
    4: "ATA attribute currently below reported threshold",
    5: "ATA attribute was below threshold in the past",
    6: "NVMe historical media/data integrity errors",
    7: "SCSI historical uncorrected errors",
}
HISTORICAL_FINDINGS = {5, 6, 7}


def query_summary(storage: Mapping[str, Any]) -> str:
    reports = mapping_items(storage.get("health"))
    if not reports:
        return "No drive query reports"
    complete = sum(integer_or(report.get("status"), -1) == 0 for report in reports)
    counts: Dict[str, int] = {}
    for report in reports:
        if integer_or(report.get("status"), -1) == 0:
            continue
        reason = READ_FAILURES.get(integer_or(report.get("failure"), -1), "Partial/unknown query result")
        counts[reason] = counts.get(reason, 0) + 1
    summary = f"{complete} / {len(reports)} queries complete"
    if counts:
        summary += " · " + "; ".join(f"{reason} ({count})" for reason, count in counts.items())
    return summary


def _percent(value: object) -> str:
    number = integer_value(value)
    return UNKNOWN if number is None else f"{number}%"


def _warning(value: object) -> str:
    number = integer_value(value)
    if number is None or not 0 <= number <= 255:
        return UNKNOWN
    meanings = (
        "spare below threshold",
        "temperature outside limits",
        "reliability degraded",
        "media read only",
        "volatile memory backup failed",
        "persistent memory region unreliable/read only",
    )
    flags = [name for bit, name in enumerate(meanings) if number & (1 << bit)]
    if number & ~0x3F:
        flags.append(f"unknown bits 0x{number & ~0x3F:02x}")
    return "0x{:02x}{}".format(number, " · " + "; ".join(flags) if flags else " · no bits asserted")


def storage_health_tables(storage: Mapping[str, Any], detailed: bool) -> List[DetailTable]:
    reports = mapping_items(storage.get("health"))
    if not reports:
        return []
    tables = [
        DetailTable(
            "Drive health queries (read only)",
            ("Target / scope", "Block devices", "Collection", "SMART overall report"),
            tuple(
                (
                    "{} · {}".format(
                        text(report.get("target")), PROTOCOLS.get(integer_or(report.get("protocol")), "Unknown")
                    ),
                    ", ".join(str(device) for device in list_value(report.get("devices")) if isinstance(device, str))
                    or UNKNOWN,
                    collection_result(report),
                    "Passed"
                    if report.get("passed") is True
                    else "Failed"
                    if report.get("passed") is False
                    else UNKNOWN,
                )
                for report in reports
            ),
        )
    ]
    if not detailed:
        return tables
    values: List[Tuple[str, str, str]] = []
    for report in reports:
        target = text(report.get("target"))
        values.append((target, "Evidence", text(report.get("origin"))))
        for key, label in (("smart_available", "SMART supported"), ("smart_enabled", "SMART enabled")):
            if key in report:
                values.append((target, label, yes_no(report.get(key))))
        nvme = mapping_value(report.get("nvme"))
        fields = (
            ("critical_warning", "Critical warning", _warning),
            ("temperature", "Composite temperature", temperature),
            ("available_spare", "Available spare", _percent),
            ("spare_threshold", "Reported spare threshold", _percent),
            ("percentage_used", "Estimated endurance used", _percent),
            ("power_on_hours", "Power on hours (cumulative)", text),
            ("power_cycles", "Power cycles (cumulative)", text),
            ("unsafe_shutdowns", "Unsafe shutdowns (cumulative)", text),
            ("media_errors", "Media/data integrity errors (cumulative)", text),
            ("error_log_entries", "Error log entries (not all are hardware faults)", text),
            ("data_units_read", "Data units read (1000 x 512 bytes per unit)", text),
            ("data_units_written", "Data units written (1000 x 512 bytes per unit)", text),
        )
        for key, label, formatter in fields:
            if key in nvme:
                values.append((target, label, formatter(nvme.get(key))))
        for key, label in (
            ("read_uncorrected", "Read uncorrected errors (cumulative)"),
            ("write_uncorrected", "Write uncorrected errors (cumulative)"),
            ("verify_uncorrected", "Verify uncorrected errors (cumulative)"),
        ):
            scsi = mapping_value(report.get("scsi"))
            if key in scsi:
                values.append((target, label, text(scsi.get(key))))
        attributes = mapping_items(report.get("ata_attributes"))
        if attributes:
            tables.append(
                DetailTable(
                    f"{target} · ATA attributes (vendor raw text)",
                    ("ID", "Name", "Value", "Worst", "Threshold", "When failed", "Raw report"),
                    tuple(
                        tuple(
                            text(attribute.get(key))
                            for key in ("id", "name", "value", "worst", "threshold", "when_failed", "raw")
                        )
                        for attribute in attributes
                    ),
                )
            )
    if values:
        tables.append(
            DetailTable(
                "Drive reports and cumulative counters", ("Target", "Field", "Report"), tuple(values), group_by=0
            )
        )
    return tables


def drive_finding_tables(health: Mapping[str, Any]) -> List[DetailTable]:
    findings = mapping_items(health.get("drive_findings"))
    tables: List[DetailTable] = []
    groups = (
        ({0, 1, 2, 4}, "Current drive findings"),
        ({3}, "Drive endurance estimates"),
        (HISTORICAL_FINDINGS, "Drive historical error reports"),
    )
    for kinds, title in groups:
        rows = tuple(
            (
                text(finding.get("target")),
                {0: "Information", 1: "Warning", 2: "Critical"}.get(integer_or(finding.get("severity"), -1), "Unknown"),
                DRIVE_FINDINGS.get(integer_or(finding.get("kind"), -1), "Unknown finding"),
                text(finding.get("attribute_id")),
                text(finding.get("origin")),
            )
            for finding in sorted(findings, key=lambda item: -integer_or(item.get("severity"), -1))
            if integer_or(finding.get("kind"), -1) in kinds
        )
        if rows:
            tables.append(DetailTable(title, ("Target", "Level", "Finding", "ATA ID", "Evidence"), rows))
    return tables
