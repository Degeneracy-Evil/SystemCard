"""Present execution facts from a public Sysal snapshot."""

from typing import Any, Mapping, Optional

from systemcard.formatters import (
    bytes_value,
    enum_text,
    text,
    yes_no,
)
from systemcard.presentation_types import Card
from systemcard.resource_limits import cpu_quota, memory_limit
from systemcard.schema import (
    mapping_value as _mapping,
)


def execution_card(
    execution: Mapping[str, Any], visible_cpu_count: Optional[int], visible_accelerator_count: Optional[int]
) -> Card:
    process = _mapping(execution.get("process"))
    permission = _mapping(execution.get("permission"))
    cgroup = _mapping(execution.get("cgroup"))
    cpuset = _mapping(execution.get("cpuset"))
    cgroup_version = enum_text({0: "v1", 1: "v2"}, cgroup.get("version") if cgroup.get("path") else None)
    return Card(
        "execution",
        "Execution context",
        (
            (
                "Process",
                f"{text(process.get('comm'))} · PID {text(process.get('pid'))} · PPID {text(process.get('ppid'))}",
            ),
            (
                "Identity",
                f"UID {text(process.get('uid'))} · GID {text(process.get('gid'))} · root {yes_no(permission.get('is_root'))}",
            ),
            ("Cgroup", f"{cgroup_version} · {text(cgroup.get('path'))}"),
            ("CPU quota", cpu_quota(cgroup)),
            ("Memory limit", memory_limit(cgroup)),
            ("Memory current", bytes_value(cgroup.get("memory_current"))),
            ("CPU set", text(cpuset.get("cpus_effective"))),
            ("Memory nodes", text(cpuset.get("mems_effective"))),
            ("Visible resources", f"{text(visible_cpu_count)} CPUs · {text(visible_accelerator_count)} accelerators"),
        ),
    )
