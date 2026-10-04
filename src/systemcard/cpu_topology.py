"""Complete CPU cache, frequency policy and logical thread relationships."""

from typing import Any, List, Mapping, Tuple

from systemcard.cpu import CACHE_TYPES
from systemcard.formatters import bytes_value, cpu_list, enum_text, frequency, text, yes_no
from systemcard.presentation_types import DetailTable
from systemcard.schema import mapping_items as _mappings


def cpu_topology_tables(cpu: Mapping[str, Any]) -> List[DetailTable]:
    logical = _mappings(cpu.get("logical_cpus"))
    tables: List[DetailTable] = []
    rows: Tuple[Tuple[str, ...], ...]
    caches = _mappings(cpu.get("caches"))
    if any(item.get("shared_cpus") for item in caches):
        rows = tuple(
            (
                "L" + text(item.get("level")) if item.get("level") is not None else "—",
                enum_text(CACHE_TYPES, item.get("type")),
                text(item.get("cache_id")),
                bytes_value(item.get("size")),
                text(item.get("sets")),
                cpu_list(item.get("shared_cpus")),
            )
            for item in caches
        )
        tables.append(DetailTable("Cache sharing", ("Level", "Type", "ID", "Size", "Sets", "CPUs"), rows))
    policies = _mappings(cpu.get("frequency_policies"))
    if policies:
        rows = tuple(
            (
                str(item.get("index", "—")),
                cpu_list(item.get("related_cpus")),
                frequency(item.get("hardware_min_frequency")),
                frequency(item.get("hardware_max_frequency")),
                frequency(item.get("scaling_min_frequency")),
                frequency(item.get("scaling_max_frequency")),
                frequency(item.get("scaling_current_frequency")),
                text(item.get("driver")),
                text(item.get("governor")),
            )
            for item in policies
        )
        tables.append(
            DetailTable(
                "Frequency policies (kernel reports)",
                ("Policy", "CPUs", "HW min", "HW max", "Policy min", "Policy max", "Reported", "Driver", "Governor"),
                rows,
            )
        )
        rows = tuple(
            (
                str(item.get("index", "—")),
                cpu_list(item.get("affected_cpus")),
                frequency(item.get("base_frequency")),
                frequency(item.get("hardware_current_frequency")),
                text(item.get("energy_performance_preference")),
            )
            for item in policies
        )
        tables.append(
            DetailTable(
                "Frequency policy details",
                ("Policy", "Affected CPUs", "Base", "HW reported", "Energy preference"),
                rows,
            )
        )
    if "online_cpu_ids" in cpu:
        rows = tuple(
            (
                str(item.get("id", "—")),
                str(item.get("package_id", "—")),
                str(item.get("core_id", "—")),
                text(item.get("numa_node")),
                yes_no(item.get("online")),
                yes_no(item.get("visible_to_current_process")),
            )
            for item in logical
        )
        tables.append(
            DetailTable("Logical CPU topology", ("CPU", "Package", "Core", "NUMA", "Online", "Visible"), rows)
        )
    return tables
