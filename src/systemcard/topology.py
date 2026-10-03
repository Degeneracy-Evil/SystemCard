"""Hardware relationships expressed by explicit IDs in a Sysal snapshot."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import UNKNOWN, bytes_value, cpu_list, pci_address, text
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_value, list_value, mapping_items, mapping_value


def topology_card(info: Mapping[str, Any]) -> Card:
    cpu = mapping_value(info.get("cpu"))
    memory = mapping_value(info.get("memory"))
    network = mapping_items(mapping_value(info.get("network")).get("interfaces"))
    devices = mapping_items(mapping_value(info.get("storage")).get("devices"))
    controllers = mapping_items(memory.get("controllers"))
    tables: List[DetailTable] = []
    numa_rows: List[Tuple[str, ...]] = []
    for node in mapping_items(memory.get("numa_memory")):
        number = integer_value(node.get("node"))
        if number is None:
            continue
        logical = [item for item in mapping_items(cpu.get("logical_cpus")) if item.get("numa_node") == number]
        packages = sorted(
            {str(item["package_id"]) for item in logical if integer_value(item.get("package_id")) is not None}
        )
        numa_rows.append(
            (
                str(number),
                cpu_list([item.get("id") for item in logical]),
                ", ".join(packages) or UNKNOWN,
                bytes_value(node.get("total")),
                bytes_value(node.get("free")),
            )
        )
    if numa_rows:
        tables.append(DetailTable("NUMA domains", ("Node", "CPUs", "Packages", "Memory", "Free"), tuple(numa_rows)))
    attachments: List[Tuple[str, ...]] = []
    for device in mapping_items(mapping_value(info.get("pci")).get("devices")):
        address = pci_address(device.get("address"))
        if address == UNKNOWN:
            continue
        interfaces = [
            str(item["name"])
            for item in network
            if pci_address(item.get("pci_address")) == address and item.get("name")
        ]
        blocks = [
            str(item["name"])
            for item in devices
            if pci_address(item.get("pci_address")) == address and item.get("name") and not item.get("parent")
        ]
        memory_controllers = [
            str(item.get("index")) for item in controllers if pci_address(item.get("pci_address")) == address
        ]
        if interfaces or blocks or memory_controllers:
            attachments.append(
                (
                    address,
                    text(device.get("device_name")),
                    text(device.get("numa_node")),
                    ", ".join(interfaces) or UNKNOWN,
                    ", ".join(blocks) or UNKNOWN,
                    ", ".join(memory_controllers) or UNKNOWN,
                )
            )
    if attachments:
        tables.append(
            DetailTable(
                "PCI attachments",
                ("PCI", "Device", "NUMA", "Interfaces", "Block devices", "Memory controllers"),
                tuple(attachments),
            )
        )
    blocks_rows: List[Tuple[str, ...]] = []
    for item in devices:
        if item.get("parent"):
            blocks_rows.append((text(item.get("name")), "partition of", text(item.get("parent"))))
        blocks_rows.extend(
            (text(item.get("name")), "uses block device", text(slave)) for slave in list_value(item.get("slaves"))
        )
    if blocks_rows:
        tables.append(
            DetailTable(
                "Block device dependencies", ("Device", "Relationship", "Parent/lower device"), tuple(blocks_rows)
            )
        )
    net_rows: List[Tuple[str, ...]] = []
    for item in network:
        if item.get("master"):
            net_rows.append((text(item.get("name")), "member of", text(item.get("master"))))
        if item.get("vlan_parent"):
            net_rows.append((text(item.get("name")), "VLAN parent", text(item.get("vlan_parent"))))
        net_rows.extend(
            (text(item.get("name")), "uses interface", text(lower))
            for lower in list_value(item.get("lower_interfaces"))
        )
    if net_rows:
        tables.append(
            DetailTable("Interface dependencies", ("Interface", "Relationship", "Related interface"), tuple(net_rows))
        )
    return Card(
        "topology",
        "Hardware topology",
        (("View", "Explicit relationships reported by the current system"),),
        tuple(tables),
    )
