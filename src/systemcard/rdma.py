"""Present explicit RDMA reports without fabric queries or capability guesses."""

from typing import Any, List, Mapping, Tuple

from systemcard.collection_status import collection_result
from systemcard.formatters import UNKNOWN, bit_rate, enum_text, pci_address, text
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_or, integer_value, mapping_items, mapping_value

NODE_TYPES = {0: UNKNOWN, 1: "Channel adapter", 2: "Switch", 3: "Router", 4: "RNIC", 5: "usNIC", 6: "usNIC UDP"}
PORT_STATES = {0: UNKNOWN, 1: "DOWN", 2: "INIT", 3: "ARMED", 4: "ACTIVE", 5: "ACTIVE DEFERRED"}
PHYSICAL_STATES = {
    0: UNKNOWN,
    1: "Sleep",
    2: "Polling",
    3: "Disabled",
    4: "Training",
    5: "Link up",
    6: "Recovery",
    7: "PHY test",
}
LINK_LAYERS = {0: UNKNOWN, 1: "InfiniBand", 2: "Ethernet"}


def rdma_summary(network: Mapping[str, Any]) -> Tuple[Tuple[str, str], ...]:
    if "rdma" not in network:
        return ()
    inventory = mapping_value(network.get("rdma"))
    devices = mapping_items(inventory.get("devices"))
    if integer_or(inventory.get("status"), -1) != 0 and not devices:
        return (("RDMA discovery", collection_result(inventory)),)
    ports = [port for device in devices for port in mapping_items(device.get("ports"))]
    active = sum(integer_value(port.get("state")) == 4 for port in ports)
    report = f"{len(devices)} devices · {len(ports)} reported ports · {active} active"
    unknown = sum(integer_value(port.get("state")) not in {1, 2, 3, 4, 5} for port in ports)
    if unknown:
        report += f" · {unknown} states unknown"
    if integer_or(inventory.get("status"), -1) != 0:
        report += " · " + collection_result(inventory)
    return (("RDMA reports", report),)


def _hex(value: object) -> str:
    number = integer_value(value)
    return UNKNOWN if number is None or number < 0 else f"0x{number:x}"


def rdma_tables(network: Mapping[str, Any], detailed: bool = True) -> List[DetailTable]:
    devices = mapping_items(mapping_value(network.get("rdma")).get("devices"))
    if not devices:
        return []
    tables = [
        DetailTable(
            "RDMA device attachments",
            ("RDMA device", "Node type", "PCI", "NUMA", "Backing device interfaces"),
            tuple(
                (
                    text(device.get("name")),
                    enum_text(NODE_TYPES, device.get("node_type")),
                    pci_address(device.get("pci_address")),
                    text(device.get("numa_node")),
                    joined(device.get("network_interfaces")),
                )
                for device in devices
            ),
        )
    ]
    ports = [
        (f"{text(device.get('name'))} / {text(port.get('number'))}", port)
        for device in devices
        for port in mapping_items(device.get("ports"))
    ]
    if ports:
        tables.append(
            DetailTable(
                "RDMA ports (driver reports)",
                ("Device / port", "Link layer", "State", "Physical state", "Reported rate", "Interfaces (GID)"),
                tuple(
                    (
                        identity,
                        enum_text(LINK_LAYERS, port.get("link_layer")),
                        enum_text(PORT_STATES, port.get("state")),
                        enum_text(PHYSICAL_STATES, port.get("physical_state")),
                        text(port.get("rate_report")) if port.get("rate_report") else bit_rate(port.get("rate")),
                        joined(port.get("network_interfaces")),
                    )
                    for identity, port in ports
                ),
            )
        )
    if not detailed:
        return tables
    fields = (
        ("device_name", "PCI device"),
        ("vendor", "PCI vendor ID"),
        ("driver", "Driver"),
        ("firmware_version", "Firmware"),
        ("description", "Node description"),
        ("node_guid", "Node GUID"),
        ("system_image_guid", "System image GUID"),
    )
    values = tuple(
        (text(device.get("name")), label, value)
        for device in devices
        for key, label in fields
        for value in (text(device.get(key)),)
        if value != UNKNOWN
    )
    if values:
        tables.append(DetailTable("RDMA device identity", ("Device", "Field", "Value"), values, group_by=0))
    port_fields = (
        ("lid", "LID (driver report)"),
        ("subnet_manager_lid", "SM LID (driver report)"),
        ("subnet_manager_sl", "SM service level"),
        ("lid_mask_count", "LID mask count"),
        ("capability_mask", "Capability mask"),
    )
    values = tuple(
        (identity, label, value)
        for identity, port in ports
        for key, label in port_fields
        for value in (
            _hex(port.get(key)) if key in {"lid", "subnet_manager_lid", "capability_mask"} else text(port.get(key)),
        )
        if value != UNKNOWN
    )
    if values:
        tables.append(DetailTable("RDMA port fields", ("Device / port", "Field", "Value"), values, group_by=0))
    return tables
