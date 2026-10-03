"""Network inventory and explicit physical-interface summaries."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import UNKNOWN, bit_rate, enum_text, pci_address, text, yes_no
from systemcard.presentation_helpers import joined as _joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import mapping_items as _mappings

INTERFACE_STATES = {0: "UP", 1: "DOWN", 2: "UNKNOWN"}


def _summary(network: Mapping[str, Any], interfaces: List[Mapping[str, Any]]) -> Tuple[Tuple[str, str], ...]:
    physical = [
        item
        for item in interfaces
        if item.get("interface_kind") == "physical" or (not item.get("interface_kind") and item.get("pci_address"))
    ]
    unclassified = sum(not item.get("interface_kind") and not item.get("pci_address") for item in interfaces)
    summary: Tuple[Tuple[str, str], ...] = (
        ("Physical interfaces", str(len(physical)) if "interfaces" in network else UNKNOWN),
        ("Links up", str(sum(item.get("state") == 0 for item in physical)) if "interfaces" in network else UNKNOWN),
        ("Other interfaces", str(len(interfaces) - len(physical)) if "interfaces" in network else UNKNOWN),
    )
    if unclassified:
        summary += (("Unclassified", str(unclassified)),)
    summary += tuple(
        (
            text(item.get("name")),
            "{} · {}".format(enum_text(INTERFACE_STATES, item.get("state")), bit_rate(item.get("speed"))),
        )
        for item in physical[:4]
    )
    if len(physical) > 4:
        summary += (("More interfaces", f"{len(physical) - 4}; --section network"),)
    return summary


def network_card(network: Mapping[str, Any], detailed: bool) -> Card:
    interfaces = _mappings(network.get("interfaces"))
    if not detailed:
        return Card("network", "Network", _summary(network, interfaces))
    up = [item for item in interfaces if item.get("state") == 0]
    visible = sum(item.get("visible_to_current_process") is True for item in interfaces)
    shown = interfaces
    columns = ("Name", "State", "Speed", "Addresses", "Hardware")
    rows: Tuple[Tuple[str, ...], ...] = tuple(
        (
            text(item.get("name")),
            enum_text(INTERFACE_STATES, item.get("state")),
            bit_rate(item.get("speed")),
            _joined(item.get("addresses"), "\n"),
            _joined(
                [
                    "MAC " + str(item["mac"]) if item.get("mac") else None,
                    "PCI " + pci_address(item.get("pci_address")) if item.get("pci_address") else None,
                ],
                "\n",
            ),
        )
        for item in shown
    )
    tables: List[DetailTable] = [DetailTable("Interfaces", columns, rows)]
    fields = (
        ("device_name", "Device"),
        ("vendor", "PCI vendor ID"),
        ("driver", "Driver"),
        ("driver_version", "Driver version"),
        ("firmware_version", "Firmware"),
        ("permanent_mac", "Permanent address"),
        ("interface_kind", "Interface kind"),
        ("bond_mode", "Bond mode"),
        ("vlan_id", "VLAN ID"),
        ("vlan_parent", "VLAN parent"),
        ("master", "Master"),
        ("mtu", "MTU (bytes)"),
        ("duplex", "Duplex"),
        ("physical_port_name", "Physical port"),
        ("numa_node", "NUMA node"),
        ("interface_index", "Interface index"),
    )
    hardware_rows = tuple(
        (text(item.get("name")), label, text(item.get(key)))
        for item in shown
        for key, label in fields
        if text(item.get(key)) != UNKNOWN
    ) + tuple((text(item.get("name")), "Carrier", yes_no(item.get("carrier"))) for item in shown if "carrier" in item)
    if hardware_rows:
        tables.append(
            DetailTable(
                "Interface hardware and configuration", ("Interface", "Field", "Value"), hardware_rows, group_by=0
            )
        )
    autoneg = tuple(
        (text(item.get("name")), "Auto-negotiation", yes_no(item.get("autonegotiation")))
        for item in shown
        if "autonegotiation" in item
    )
    if autoneg:
        tables.append(DetailTable("Link negotiation", ("Interface", "Field", "Value"), autoneg, group_by=0))
    modes = tuple(
        (
            text(item.get("name")),
            _joined(item.get("supported_link_modes"), "\n"),
            _joined(item.get("advertised_link_modes"), "\n"),
            _joined(item.get("peer_link_modes"), "\n"),
        )
        for item in shown
        if item.get("supported_link_modes") or item.get("advertised_link_modes") or item.get("peer_link_modes")
    )
    if modes:
        tables.append(
            DetailTable(
                "Link modes (capability / advertisements)",
                ("Interface", "Supported", "Advertised", "Peer advertised"),
                modes,
            )
        )
    links = tuple(
        (
            text(item.get("name")),
            text(item.get("master")),
            _joined(item.get("lower_interfaces")),
            text(item.get("vlan_parent")),
            text(item.get("vlan_id")),
        )
        for item in shown
        if item.get("master") or item.get("lower_interfaces") or item.get("vlan_parent")
    )
    if links:
        tables.append(
            DetailTable(
                "Interface topology", ("Interface", "Master", "Lower interfaces", "VLAN parent", "VLAN ID"), links
            )
        )
    return Card(
        "network",
        "Network",
        (
            ("Interfaces", f"{len(interfaces)} total · {len(up)} up"),
            ("Process visibility", f"{visible} of {len(interfaces)} interfaces"),
        ),
        tuple(tables),
    )
