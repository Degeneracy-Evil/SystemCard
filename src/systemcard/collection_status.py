"""Labels for reported collection outcomes; never infer failure causes."""

from typing import Any, Mapping

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
COLLECT_STATUSES = {0: "Read succeeded", 1: "Partial result", 2: "Failed", 3: "Not collected"}


def collection_result(report: Mapping[str, Any]) -> str:
    status = COLLECT_STATUSES.get(integer_or(report.get("status"), -1), "Unknown status")
    reason = READ_FAILURES.get(integer_or(report.get("failure"), -1))
    if reason is not None:
        return f"{status}: {reason}"
    return status if integer_or(report.get("status"), -1) == 0 else status + "; reason unknown"


def inventory_known(meta: Mapping[str, Any], domain: str, entries: object) -> bool:
    """An empty inventory needs a successful collector report to mean zero."""
    if not isinstance(entries, list) or domain in list_value(meta.get("failed_collectors")):
        return False
    if entries:
        return True
    if any(
        item.get("domain") == domain and integer_or(item.get("status"), -1) != 0
        for item in mapping_items(meta.get("observations"))
    ):
        return False
    return domain in list_value(meta.get("succeeded_collectors"))


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
