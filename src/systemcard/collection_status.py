"""Labels for reported collection outcomes; never infer failure causes."""

from typing import Any, Mapping

from systemcard.schema import integer_or

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
    return status if reason is None else f"{status}: {reason}"
