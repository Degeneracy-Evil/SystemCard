"""Present platform facts from a public Sysal snapshot."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import (
    UNKNOWN,
    pci_address,
    text,
)
from systemcard.presentation_helpers import joined as _joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import (
    integer_value,
)
from systemcard.schema import (
    mapping_items as _mappings,
)
from systemcard.schema import (
    mapping_value as _mapping,
)


def system_card(platform: Mapping[str, Any], pci: Mapping[str, Any], detailed: bool) -> Card:
    host = _mapping(platform.get("host"))
    os_info = _mapping(platform.get("os"))
    kernel = _mapping(platform.get("kernel"))
    architecture = _mapping(platform.get("architecture"))
    firmware = _mapping(platform.get("firmware"))
    distribution = text(os_info.get("distribution_version"))
    if distribution == UNKNOWN:
        distribution = (
            " ".join(part for part in (text(os_info.get("name")), text(os_info.get("version"))) if part != UNKNOWN)
            or UNKNOWN
        )
    else:
        os_name = text(os_info.get("name"))
        if os_name != UNKNOWN and not distribution.lower().startswith(os_name.lower()):
            distribution = f"{os_name} {distribution}"
    hardware = (
        " ".join(part for part in (text(host.get("vendor")), text(host.get("product_name"))) if part != UNKNOWN)
        or UNKNOWN
    )
    bios = (
        " ".join(
            part for part in (text(firmware.get("bios_vendor")), text(firmware.get("bios_version"))) if part != UNKNOWN
        )
        or UNKNOWN
    )
    arch = text(architecture.get("name"))
    bits = integer_value(architecture.get("bits"))
    if bits is not None and bits > 0:
        arch = f"{arch} ({bits}-bit, {text(architecture.get('byte_order'))}-endian)"
    rows: List[Tuple[str, str]] = [
        ("Host", text(host.get("hostname"))),
        ("Operating system", distribution),
        ("Kernel", text(kernel.get("release"))),
        ("Architecture", arch),
        ("Hardware", hardware),
        ("Firmware", f"{bios} · {'UEFI' if firmware.get('uefi') is True else 'Legacy/unknown'}"),
    ]
    board = _mapping(platform.get("baseboard"))
    chassis = _mapping(platform.get("chassis"))
    if board:
        rows.append(("Motherboard", _joined([board.get("vendor"), board.get("name"), board.get("version")], " ")))
    if chassis:
        rows.append(
            (
                "Chassis",
                _joined(
                    [
                        chassis.get("vendor"),
                        f"SMBIOS type {chassis['type']}" if chassis.get("type") is not None else None,
                    ],
                    " · ",
                ),
            )
        )
    tables: List[DetailTable] = []
    if detailed:
        groups = (
            (
                "Machine identity",
                host,
                (
                    ("vendor", "Vendor"),
                    ("product_name", "Model"),
                    ("product_family", "Family"),
                    ("product_version", "Product version"),
                    ("product_sku", "SKU"),
                    ("serial", "Serial"),
                    ("product_uuid", "Product UUID"),
                    ("machine_id", "OS machine-id"),
                ),
            ),
            (
                "Motherboard identity",
                board,
                (
                    ("vendor", "Vendor"),
                    ("name", "Model"),
                    ("version", "Version"),
                    ("serial", "Serial"),
                    ("asset_tag", "Asset tag"),
                ),
            ),
            (
                "Chassis identity",
                chassis,
                (
                    ("vendor", "Vendor"),
                    ("type", "SMBIOS type code"),
                    ("version", "Version"),
                    ("serial", "Serial"),
                    ("asset_tag", "Asset tag"),
                ),
            ),
            (
                "Firmware identity",
                firmware,
                (
                    ("bios_vendor", "Vendor"),
                    ("bios_version", "Version"),
                    ("bios_date", "Date"),
                    ("bios_release", "BIOS revision"),
                    ("ec_firmware_release", "EC firmware revision"),
                ),
            ),
        )
        for title, source, fields in groups:
            values = tuple((label, text(source.get(key))) for key, label in fields if text(source.get(key)) != UNKNOWN)
            if values:
                tables.append(DetailTable(title, ("Field", "Value"), values))
    if detailed:
        slots = [
            item for item in _mappings(pci.get("devices")) if item.get("physical_slot") or item.get("firmware_label")
        ]
        if slots:
            tables.append(
                DetailTable(
                    "PCI slots and firmware labels",
                    ("Slot", "PCI", "Device", "Label", "Current link", "Maximum link"),
                    tuple(
                        (
                            text(item.get("physical_slot")),
                            pci_address(item.get("address")),
                            text(item.get("device_name")),
                            text(item.get("firmware_label")),
                            f"{text(item.get('current_link_speed'))} · x{text(item.get('current_link_width'))}",
                            f"{text(item.get('max_link_speed'))} · x{text(item.get('max_link_width'))}",
                        )
                        for item in slots
                    ),
                )
            )
    return Card("system", "System", tuple(rows), tuple(tables))
