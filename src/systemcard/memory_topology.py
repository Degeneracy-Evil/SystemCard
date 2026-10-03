"""Present EDAC hierarchy without interpreting firmware slot names."""

from typing import Any, List, Mapping

from systemcard.formatters import UNKNOWN, bytes_value, enum_text, pci_address, text
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_value, mapping_items, mapping_value

LAYERS = {0: "Unknown", 1: "branch", 2: "channel", 3: "slot", 4: "csrow", 5: "memory"}
KINDS = {0: "Unknown", 1: "DIMM", 2: "rank"}
ASSOCIATIONS = {0: "Unknown", 1: "EDAC inventory", 2: "Unique label + capacity match"}


def location_text(value: object) -> str:
    location = mapping_value(value)
    coordinates = mapping_items(location.get("coordinates"))
    if coordinates and all(
        integer_value(item.get("layer")) in LAYERS and integer_value(item.get("index")) is not None
        for item in coordinates
    ):
        return " / ".join(f"{enum_text(LAYERS, item.get('layer'))} {item['index']}" for item in coordinates)
    return text(location.get("report"))


def device_name(item: Mapping[str, Any]) -> str:
    kind = enum_text(KINDS, item.get("kind"))
    return f"mc{text(item.get('controller_index'))} / {kind} {text(item.get('index'))}"


def memory_topology_tables(memory: Mapping[str, Any], detailed: bool = False) -> List[DetailTable]:
    tables: List[DetailTable] = []
    controllers = mapping_items(memory.get("controllers"))
    if detailed and controllers:
        tables.append(
            DetailTable(
                "EDAC controllers (counters since reset)",
                ("ID", "Name", "Capacity", "NUMA", "PCI", "Corrected", "Uncorrected"),
                tuple(
                    (
                        text(item.get("index")),
                        text(item.get("name")),
                        bytes_value(item.get("capacity")),
                        text(item.get("numa_node")),
                        pci_address(item.get("pci_address")),
                        text(item.get("corrected_errors")),
                        text(item.get("uncorrected_errors")),
                    )
                    for item in controllers
                ),
            )
        )
    limits = tuple(
        (f"mc{text(item.get('index'))}", report)
        for item in controllers
        for report in (location_text(item.get("max_location")),)
        if report != UNKNOWN
    )
    if limits:
        tables.append(DetailTable("EDAC layer maximum indices (not population)", ("Controller", "Maxima"), limits))
    devices = mapping_items(memory.get("edac_devices"))
    if devices:
        tables.append(
            DetailTable(
                "EDAC memory locations (rank capacity is per rank)",
                ("EDAC device", "Driver label", "Location", "Capacity", "NUMA"),
                tuple(
                    (
                        device_name(item),
                        text(item.get("label")),
                        location_text(item.get("location")),
                        bytes_value(item.get("size")),
                        text(item.get("numa_node")),
                    )
                    for item in devices
                ),
            )
        )
    relations = tuple(
        (
            text(item.get("locator")),
            f"mc{text(item.get('controller_index'))} / DIMM {text(item.get('edac_device_index'))}",
            enum_text(ASSOCIATIONS, item.get("edac_association")),
        )
        for item in mapping_items(memory.get("dimms"))
        if item.get("controller_index") is not None
    )
    if relations:
        tables.append(DetailTable("DIMM / EDAC association", ("Slot", "EDAC device", "Basis"), relations))
    if detailed and devices:
        fields = (("memory_type", "Technology"), ("edac_mode", "EDAC mode"), ("device_width", "DRAM device width"))
        rows = tuple(
            (device_name(item), label, report)
            for item in devices
            for key, label in fields
            for report in (text(item.get(key)),)
            if report != UNKNOWN
        )
        if rows:
            tables.append(DetailTable("EDAC device reports", ("EDAC device", "Field", "Value"), rows, group_by=0))
    return tables
