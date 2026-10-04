"""Explain collection status without exposing raw payloads or inferring causes."""

from typing import Any, Dict, List, Mapping, Set, Tuple

from systemcard.collection_status import COLLECT_STATUSES, READ_FAILURES, collector_domain
from systemcard.formatters import UNKNOWN, pci_address
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, mapping_items, mapping_value


def _source(origin: str) -> str:
    if origin.startswith(("smartctl/", "nvme-smart-log/")):
        return "Device health report"
    if origin.startswith("ethtool/"):
        return "Driver (ethtool)"
    if origin.startswith("/sys/class/dmi/"):
        return "Firmware (DMI)"
    if origin.startswith("/sys/"):
        return "Kernel/driver (sysfs)"
    if origin.startswith("/proc/"):
        return "Kernel (procfs)"
    if origin.startswith("udevadm"):
        return "Firmware via udev"
    if origin.startswith("lspci"):
        return "PCI system database"
    return "System query"


def _observations(card: Card, meta: Mapping[str, Any], info: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    domains = {collector_domain(card.section)}
    if card.section == "cpu":
        domains.add("sensors")
    if card.section == "health":
        domains = {"sensors", "memory", "storage", "storage_health", "pci"}
    elif card.section == "topology":
        domains = {"cpu", "memory", "network", "storage", "pci"}
    elif card.section in {"system", "memory", "network", "storage"}:
        domains.add("pci")
    references: Set[str] = set()
    groups = (
        ("network", "storage", "memory")
        if card.section == "topology"
        else ("storage", "memory")
        if card.section == "health"
        else (card.section,)
    )
    for group in groups:
        data = mapping_value(info.get(group))
        key = "interfaces" if group == "network" else "controllers" if group == "memory" else "devices"
        references.update(pci_address(item.get("pci_address")) for item in mapping_items(data.get(key)))
        if group == "storage":
            for key in ("controllers", "nvme_controllers", "scsi_hosts"):
                references.update(pci_address(item.get("pci_address")) for item in mapping_items(data.get(key)))
        if group == "network":
            references.update(
                pci_address(item.get("pci_address"))
                for item in mapping_items(mapping_value(data.get("rdma")).get("devices"))
            )
    if card.section == "system":
        references.update(
            pci_address(item.get("address"))
            for item in mapping_items(mapping_value(info.get("pci")).get("devices"))
            if item.get("physical_slot") or item.get("firmware_label")
        )
    references.discard(UNKNOWN)
    observations = []
    for item in mapping_items(meta.get("observations")):
        if item.get("domain") not in domains:
            continue
        origin = str(item.get("origin", ""))
        if card.section == "cpu" and item.get("domain") == "sensors" and not origin.startswith("/sys/class/thermal/"):
            continue
        if item.get("domain") == "pci" and origin.startswith("/sys/bus/pci/devices/"):
            parts = origin.split("/")
            if len(parts) < 6 or parts[5] not in references:
                continue
        observations.append(item)
    return observations


def with_source_gaps(card: Card, meta: Mapping[str, Any], info: Mapping[str, Any]) -> Card:
    """Summarize actual source gaps without treating every missing file as a failed domain."""
    counts: Dict[str, int] = {}
    for item in _observations(card, meta, info):
        status = integer_or(item.get("status"), -1)
        if status == 0:
            continue
        reason = READ_FAILURES.get(integer_or(item.get("failure"), -1))
        label = reason or COLLECT_STATUSES.get(status, "Unknown source status") + " (reason unknown)"
        counts[label] = counts.get(label, 0) + 1
    if not counts:
        return card
    reasons = list(counts.items())
    summary = "; ".join(f"{label} ({count})" for label, count in reasons[:3])
    if len(reasons) > 3:
        summary += f"; {len(reasons) - 3} other reasons"
    summary += "; --sources for details"
    return Card(card.section, card.title, (*card.rows, ("Source gaps", summary)), card.tables)


def with_sources(card: Card, meta: Mapping[str, Any], info: Mapping[str, Any]) -> Card:
    observations = _observations(card, meta, info)
    rows: Tuple[Tuple[str, ...], ...] = tuple(
        (
            _source(str(item.get("origin", ""))),
            str(item.get("origin", "—")),
            COLLECT_STATUSES.get(integer_or(item.get("status"), -1), "Unknown status"),
            READ_FAILURES.get(
                integer_or(item.get("failure"), -1),
                UNKNOWN if integer_or(item.get("status"), -1) == 0 else "Reason unknown",
            ),
        )
        for item in observations
    )
    if not rows:
        rows = (("—", "—", "No source observations in this snapshot", "Reason unknown"),)
    table = DetailTable("Collection sources", ("Source", "Origin", "Result", "Missing/partial reason"), rows)
    return Card(card.section, card.title, card.rows, (*card.tables, table))
