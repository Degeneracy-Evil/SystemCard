"""PCI links and paths from explicit Sysal addresses, with no hardware guesses."""

from typing import Any, Callable, Dict, List, Mapping, Optional, Set, Tuple

from systemcard.formatters import UNKNOWN, cpu_list, pci_address, text
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_value, mapping_items


def _link(device: Mapping[str, Any], prefix: str) -> str:
    speed = text(device.get(prefix + "_link_speed"))
    width = integer_value(device.get(prefix + "_link_width"))
    parts = []
    if speed != UNKNOWN:
        parts.append(speed)
    if width is not None and width > 0 and width != 255:
        parts.append(f"x{width}")
    return " · ".join(parts) or UNKNOWN


def _path(address: str, devices: Mapping[str, Mapping[str, Any]]) -> Tuple[List[str], str]:
    path: List[str] = []
    seen: Set[str] = set()
    while address != UNKNOWN:
        if address in seen:
            return path, "cycle in reported relationships"
        seen.add(address)
        path.append(address)
        device = devices.get(address)
        if device is None:
            return path, "device report missing"
        address = pci_address(device.get("upstream_address"))
    return path, "no further upstream report"


def pci_tables(pci: Mapping[str, Any], addresses: Optional[Set[str]] = None) -> List[DetailTable]:
    """Show connection reports, or selected controllers and their reported ancestors."""
    devices: Dict[str, Mapping[str, Any]] = {
        pci_address(item.get("address")): item
        for item in mapping_items(pci.get("devices"))
        if pci_address(item.get("address")) != UNKNOWN
    }
    selected = (
        {
            address
            for address, item in devices.items()
            if _link(item, "current") != UNKNOWN
            or _link(item, "max") != UNKNOWN
            or "maximum_virtual_functions" in item
            or any(
                item.get(key)
                for key in (
                    "upstream_address",
                    "physical_function",
                    "physical_slot",
                    "firmware_label",
                )
            )
        }
        if addresses is None
        else addresses - {UNKNOWN}
    )
    paths: List[Tuple[str, ...]] = []
    shown = set(selected)
    if addresses is not None:
        for address in sorted(selected):
            path, boundary = _path(address, devices)
            shown.update(path)
            paths.append((address, " → ".join(path), boundary))
    inventory = tuple(
        (
            address,
            pci_address(devices[address].get("upstream_address")),
            text(devices[address].get("device_name")),
            _link(devices[address], "current"),
            _link(devices[address], "max"),
            text(devices[address].get("numa_node")),
        )
        for address in sorted(shown)
        if address in devices
    )
    tables: List[DetailTable] = []
    if inventory:
        tables.append(
            DetailTable(
                "PCI links (device reports)",
                ("PCI", "Direct upstream", "Device", "Current link", "Maximum link", "NUMA"),
                inventory,
            )
        )
    if paths:
        tables.append(
            DetailTable("PCI paths (endpoint → upstream)", ("Endpoint", "Reported path", "Boundary"), tuple(paths))
        )
    fields: Tuple[Tuple[str, Callable[[Mapping[str, Any]], str]], ...] = (
        ("Driver", lambda item: text(item.get("driver_name"))),
        ("Kernel local CPUs", lambda item: cpu_list(item.get("local_cpus"))),
        ("Physical function", lambda item: pci_address(item.get("physical_function"))),
        ("Maximum VFs (driver report)", lambda item: text(item.get("maximum_virtual_functions"))),
        ("Enabled VFs", lambda item: text(item.get("enabled_virtual_functions"))),
        ("Physical slot", lambda item: text(item.get("physical_slot"))),
        ("Firmware label", lambda item: text(item.get("firmware_label"))),
    )
    details = tuple(
        (address, label, value)
        for address in sorted(selected)
        if address in devices
        for label, formatter in fields
        for value in (formatter(devices[address]),)
        if value != UNKNOWN
    )
    if details:
        tables.append(DetailTable("PCI affinity and identity", ("PCI", "Field", "Value"), details, group_by=0))
    return tables
