"""Labels for reported collection outcomes; never infer failure causes."""

from typing import Any, Mapping, Optional

from systemcard.presentation_types import Card
from systemcard.schema import integer_or, list_value, mapping_items

READ_FAILURES = {
    0: "Interface/file not present",
    1: "Permission denied",
    2: "Query unsupported",
    3: "Read/query failed",
    4: "Optional tool unavailable",
    5: "Query timed out",
    6: "Source did not provide a value",
    7: "Skipped in low power mode",
}
SKIP_REASONS = {
    0: "Skip reason unknown",
    1: "Not requested",
    2: "Excluded by policy",
    3: "Query budget exhausted",
    4: "Query not applicable",
}
COLLECT_STATUSES = {0: "Read succeeded", 1: "Partial result", 2: "Failed", 3: "Not collected"}


def collection_result(report: Mapping[str, Any]) -> str:
    status = COLLECT_STATUSES.get(integer_or(report.get("status"), -1), "Unknown status")
    reason = READ_FAILURES.get(integer_or(report.get("failure"), -1)) or SKIP_REASONS.get(
        integer_or(report.get("skip"), -1)
    )
    if reason is not None:
        return f"{status}: {reason}"
    return status if integer_or(report.get("status"), -1) == 0 else status + "; reason unknown"


# Public Sysal InventoryKind values, centralized at the JSON boundary.
INVENTORIES = {
    "cpu.packages": 0,
    "cpu.cores": 1,
    "cpu.logical_cpus": 2,
    "cpu.numa_nodes": 3,
    "cpu.caches": 4,
    "network.interfaces": 5,
    "storage.devices": 6,
    "pci.devices": 7,
    "accelerators.devices": 8,
}


def inventory_complete(meta: Mapping[str, Any], inventory: str) -> bool:
    """Only an explicit, unique library report can establish completeness."""
    kind = INVENTORIES[inventory]
    reports = [item for item in mapping_items(meta.get("inventories")) if integer_or(item.get("inventory"), -1) == kind]
    return len(reports) == 1 and integer_or(reports[0].get("completeness"), -1) == 2


def inventory_known(meta: Mapping[str, Any], inventory: str, entries: object) -> bool:
    """Observed entries are usable; an empty list needs explicit completeness."""
    return (
        isinstance(entries, list)
        and all(isinstance(item, Mapping) for item in entries)
        and (bool(entries) or inventory_complete(meta, inventory))
    )


def inventory_count(meta: Mapping[str, Any], inventory: str, entries: object, count: Optional[int] = None) -> str:
    """Format a count within the scope established by the library."""
    if not isinstance(entries, list) or any(not isinstance(item, Mapping) for item in entries):
        return "—"
    value = len(entries) if count is None else count
    if inventory_complete(meta, inventory):
        return str(value)
    return f"{value} (known portion)" if entries and value else "—"


def collector_domain(section: str) -> str:
    """Translate presentation section names to native collector names."""
    return {"system": "platform", "accelerators": "accelerator"}.get(section, section)


def with_collection_status(card: Card, meta: Mapping[str, Any]) -> Card:
    """Do not present default model values as results of a failed collector."""
    if card.section in {"topology", "health"}:
        return card
    domain = collector_domain(card.section)
    if domain in list_value(meta.get("failed_collectors")):
        return Card(card.section, card.title, (("Collection", "Failed; inventory unknown"),))
    if (
        isinstance(meta.get("succeeded_collectors"), list)
        and isinstance(meta.get("failed_collectors"), list)
        and domain not in list_value(meta.get("succeeded_collectors"))
    ):
        return Card(card.section, card.title, (("Collection", "Not collected; inventory unknown"),))
    return card
