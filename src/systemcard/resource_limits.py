"""Format reported cgroup limits, preserving unknown and partial results."""

from typing import Any, Mapping

from systemcard.formatters import UNKNOWN, bytes_value
from systemcard.schema import integer_value


def cpu_quota(cgroup: Mapping[str, Any]) -> str:
    raw_quota = cgroup.get("cpu_quota_us")
    if raw_quota is None:
        return "Unlimited" if cgroup.get("cpu_limit_known") is True else UNKNOWN
    quota = integer_value(raw_quota)
    period = integer_value(cgroup.get("cpu_period_us"))
    if quota is None or period is None or quota <= 0 or period <= 0:
        return UNKNOWN
    rendered = f"{quota / period:g} CPUs"
    return rendered if cgroup.get("cpu_limit_known") is True else f"≤ {rendered} (partial)"


def memory_limit(cgroup: Mapping[str, Any]) -> str:
    raw_limit = cgroup.get("memory_limit")
    if raw_limit is None:
        return "Unlimited" if cgroup.get("memory_limit_known") is True else UNKNOWN
    limit = integer_value(raw_limit)
    if limit is None or limit < 0:
        return UNKNOWN
    rendered = bytes_value(limit)
    return rendered if cgroup.get("memory_limit_known") is True else f"≤ {rendered} (partial)"
