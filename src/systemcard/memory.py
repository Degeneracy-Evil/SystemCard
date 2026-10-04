"""Present memory facts from a public Sysal snapshot."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import (
    UNKNOWN,
    bytes_value,
    text,
)
from systemcard.presentation_helpers import boolean_count
from systemcard.presentation_helpers import joined as _joined
from systemcard.presentation_helpers import limited as _limited
from systemcard.presentation_types import Card, DetailTable
from systemcard.resource_limits import memory_limit
from systemcard.schema import (
    integer_value,
    number_value,
)
from systemcard.schema import (
    mapping_items as _mappings,
)


def memory_card(memory: Mapping[str, Any], detailed: bool, cgroup: Mapping[str, Any]) -> Card:
    total = number_value(memory.get("total_memory"))
    available = number_value(memory.get("available_memory"))
    used = total - available if total is not None and available is not None else None
    dimms = _mappings(memory.get("dimms"))
    population = integer_value(memory.get("populated_dimms"))
    if population is None:
        population = boolean_count(dimms, "present") if dimms else None
    entries = integer_value(memory.get("dimm_count"))
    if entries is None:
        entries = len(dimms) if dimms else None
    populated = [item for item in dimms if item.get("present") is True]
    shown = _limited(populated, detailed, 8)
    dimm_rows = tuple(
        (
            text(item.get("locator")),
            text(item.get("bank_locator")),
            bytes_value(item.get("size")),
            f"{item['speed_mts']} MT/s" if integer_value(item.get("speed_mts")) is not None else UNKNOWN,
            text(item.get("manufacturer")),
            text(item.get("part_number")),
        )
        for item in shown
    )
    tables: Tuple[DetailTable, ...] = ()
    if dimm_rows and detailed:
        tables = (
            DetailTable(
                "Populated DIMMs",
                ("Slot", "Bank", "Size", "Speed", "Vendor", "Part number"),
                dimm_rows,
                len(populated) - len(shown),
            ),
        )
    if detailed:
        module_rows = tuple(
            (
                text(item.get("locator")),
                text(item.get("memory_type")),
                text(item.get("form_factor")),
                text(item.get("rank")),
                f"{text(item.get('data_width'))} / {text(item.get('total_width'))}"
                if item.get("data_width") is not None or item.get("total_width") is not None
                else UNKNOWN,
                f"{item['configured_speed_mts']} MT/s" if item.get("configured_speed_mts") is not None else UNKNOWN,
                f"{item['configured_voltage_mv']} mV" if item.get("configured_voltage_mv") is not None else UNKNOWN,
                _joined([item.get("type_detail"), item.get("edac_mode"), item.get("device_width")], " · "),
            )
            for item in populated
        )
        if module_rows:
            tables += (
                DetailTable(
                    "DIMM configuration",
                    ("Slot", "Type", "Form", "Ranks", "Data / total bits", "Configured", "Voltage", "Mode"),
                    module_rows,
                ),
            )
        identifiers = tuple(
            (text(item.get("locator")), text(item.get("serial")), text(item.get("asset_tag")))
            for item in populated
            if item.get("serial") or item.get("asset_tag")
        )
        if identifiers:
            tables += (DetailTable("DIMM identity", ("Slot", "Serial", "Asset tag"), identifiers),)
        numa = _mappings(memory.get("numa_memory"))
        if numa:
            tables += (
                DetailTable(
                    "NUMA memory",
                    ("Node", "Total", "Free", "Available"),
                    tuple(
                        (
                            text(item.get("node")),
                            bytes_value(item.get("total")),
                            bytes_value(item.get("free")),
                            bytes_value(item.get("available")),
                        )
                        for item in numa
                    ),
                ),
            )
        empty = [item for item in dimms if item.get("present") is False]
        if empty:
            tables += (
                DetailTable(
                    "Unpopulated slots",
                    ("Slot", "Bank"),
                    tuple((text(item.get("locator")), text(item.get("bank_locator"))) for item in empty),
                ),
            )
    inventory_rows: List[Tuple[str, str]] = []
    inventory_source = memory.get("dimm_inventory_source")
    if inventory_source:
        expected = text(memory.get("reported_slot_count"))
        complete = memory.get("reported_slots_complete")
        coverage = (
            "complete against firmware report"
            if complete is True
            else "partial"
            if complete is False
            else "completeness unknown"
        )
        inventory_rows.append(
            ("Slot inventory", f"{inventory_source} · {len(dimms)} observed · {expected} reported · {coverage}")
        )
    if memory.get("reported_array_error_correction"):
        inventory_rows.append(("Firmware ECC report", text(memory.get("reported_array_error_correction"))))
    if detailed and (memory.get("reported_array_location") or memory.get("reported_array_max_capacity") is not None):
        tables += (
            DetailTable(
                "Firmware memory array report",
                ("Location", "Maximum capacity", "Error correction"),
                (
                    (
                        text(memory.get("reported_array_location")),
                        bytes_value(memory.get("reported_array_max_capacity")),
                        text(memory.get("reported_array_error_correction")),
                    ),
                ),
            ),
        )
    return Card(
        "memory",
        "Memory",
        (
            ("Host total", bytes_value(total)),
            ("Cgroup limit", memory_limit(cgroup)),
            ("Cgroup current", bytes_value(cgroup.get("memory_current"))),
            ("Used / available", f"{bytes_value(used)} / {bytes_value(available)}"),
            ("Technology", text(memory.get("memory_type"))),
            (
                "Configured speed",
                f"{memory['configured_speed_mts']} MT/s"
                if integer_value(memory.get("configured_speed_mts")) is not None
                else UNKNOWN,
            ),
            (
                "DIMM population",
                f"{text(population if population is not None and population >= 0 else None)} of {text(entries if entries is not None and entries >= 0 else None)} observed entries"
                if entries is not None
                else UNKNOWN,
            ),
            *inventory_rows,
        ),
        tables,
    )
