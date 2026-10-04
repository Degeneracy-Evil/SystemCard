"""Present accelerators facts from a public Sysal snapshot."""

from typing import Any, Counter, Mapping, Optional

from systemcard.collection_status import inventory_known
from systemcard.formatters import (
    UNKNOWN,
    bytes_value,
    enum_text,
    pci_address,
    text,
    yes_no,
)
from systemcard.presentation_helpers import boolean_count
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import (
    mapping_items as _mappings,
)

ACCELERATOR_KINDS = {0: "GPU", 1: "NPU", 2: "FPGA", 3: "Other"}


def accelerator_card(
    accelerators: Mapping[str, Any], show_tables: bool, meta: Optional[Mapping[str, Any]] = None
) -> Card:
    devices = _mappings(accelerators.get("devices"))
    confirmed = inventory_known(meta or {}, "accelerator", accelerators.get("devices"))
    visible = boolean_count(devices, "visible_to_current_process")
    physical = [item for item in devices if not item.get("parent_uuid")]
    kinds = Counter(enum_text(ACCELERATOR_KINDS, item.get("kind")) for item in physical)
    breakdown = " · ".join(f"{count} {kind}" for kind, count in kinds.items()) or (
        "No accelerators detected" if confirmed else UNKNOWN
    )
    if len(physical) < len(devices):
        breakdown += f" · {len(devices) - len(physical)} MIG instances"
    rows = tuple(
        (
            str(item.get("id", index)),
            enum_text(ACCELERATOR_KINDS, item.get("kind")),
            text(item.get("name")) + (" (MIG)" if item.get("parent_uuid") else ""),
            bytes_value(item.get("memory_size")),
            pci_address(item.get("pci_address")),
            text(item.get("nearest_numa_node")),
            yes_no(item.get("visible_to_current_process")),
        )
        for index, item in enumerate(devices)
    )
    tables = (
        (DetailTable("Devices", ("ID", "Kind", "Name", "Memory", "PCI", "NUMA", "Visible"), rows),)
        if rows and show_tables
        else ()
    )
    return Card(
        "accelerators",
        "Accelerators",
        (
            ("Summary", breakdown),
            ("Process visibility", f"{text(visible)} of {len(devices)} observed devices" if confirmed else UNKNOWN),
        ),
        tables,
    )
