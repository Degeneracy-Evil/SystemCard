"""Whole-disk identity, main configuration and associated mounts."""

from typing import Any, List, Mapping, Optional, Tuple

from systemcard.collection_status import inventory_complete, inventory_count, inventory_known
from systemcard.filesystems import filesystem_summary, filesystem_tables
from systemcard.formatters import UNKNOWN, bytes_value, enum_text, pci_address, text, yes_no
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, integer_value, list_value, mapping_items, mapping_value
from systemcard.storage_mounts import mount_table

BLOCK_LAYERS = {1: "Device", 2: "Partition", 3: "Device mapper", 4: "RAID", 5: "Loop", 6: "Virtual"}
STORAGE_PURPOSES = {1: "Disk", 2: "Optical", 3: "Other"}
STORAGE_PROTOCOLS = {1: "NVMe", 2: "ATA", 3: "SCSI"}
STORAGE_TRANSPORTS = {
    1: "PCIe",
    2: "SATA",
    3: "SAS",
    4: "USB",
    5: "TCP",
    6: "RDMA",
    7: "FC",
    8: "iSCSI",
    9: "Parallel SCSI",
}


def _classification(device: Mapping[str, Any]) -> Mapping[str, Any]:
    return mapping_value(device.get("classification"))


def _whole_disk(device: Mapping[str, Any]) -> bool:
    classification = _classification(device)
    return integer_or(classification.get("layer")) == 1 and integer_or(classification.get("purpose")) == 1


def _unclassified(device: Mapping[str, Any]) -> bool:
    classification = _classification(device)
    layer = integer_or(classification.get("layer"))
    return layer not in BLOCK_LAYERS or (
        layer == 1 and integer_or(classification.get("purpose")) not in STORAGE_PURPOSES
    )


def _medium(device: Mapping[str, Any]) -> str:
    rotational = device.get("rotational")
    return "Rotating" if rotational is True else "Non-rotating" if rotational is False else UNKNOWN


def _protocol(device: Mapping[str, Any]) -> str:
    return enum_text(STORAGE_PROTOCOLS, _classification(device).get("protocol"))


def _transports(device: Mapping[str, Any]) -> str:
    return (
        " / ".join(
            dict.fromkeys(
                enum_text(STORAGE_TRANSPORTS, item) for item in list_value(_classification(device).get("transports"))
            )
        )
        or UNKNOWN
    )


def _devices(title: str, devices: List[Mapping[str, Any]]) -> DetailTable:
    return DetailTable(
        title,
        ("Name", "Layer / purpose", "Rotation", "Protocol", "Transport", "Capacity", "Model", "PCI"),
        tuple(
            (
                text(item.get("name")),
                enum_text(BLOCK_LAYERS, _classification(item).get("layer"))
                + " / "
                + enum_text(STORAGE_PURPOSES, _classification(item).get("purpose")),
                _medium(item),
                _protocol(item),
                _transports(item),
                bytes_value(item.get("capacity")),
                text(item.get("model")),
                pci_address(item.get("pci_address")),
            )
            for item in devices
        ),
    )


def storage_card(storage: Mapping[str, Any], detailed: bool, meta: Optional[Mapping[str, Any]] = None) -> Card:
    devices = mapping_items(storage.get("devices"))
    disks = [item for item in devices if _whole_disk(item)]
    unknown = [item for item in devices if _unclassified(item)]
    other = [item for item in devices if not _whole_disk(item) and not _unclassified(item)]
    capacities = [integer_value(item.get("capacity")) for item in disks]
    known = [value for value in capacities if value is not None and value >= 0]
    capacity = bytes_value(sum(known)) if known else UNKNOWN
    if known and (len(known) != len(disks) or not inventory_complete(meta or {}, "storage.devices")):
        capacity += f" (known portion: {len(known)}/{len(disks)} disks)"
    confirmed = inventory_known(meta or {}, "storage.devices", storage.get("devices"))
    disk_count = inventory_count(meta or {}, "storage.devices", storage.get("devices"), len(disks))
    other_count = inventory_count(meta or {}, "storage.devices", storage.get("devices"), len(other))
    if unknown:
        disk_count = f"{len(disks)} (known portion)" if disks else UNKNOWN
        other_count = f"{len(other)} (known portion)" if other else UNKNOWN
        if capacity != UNKNOWN:
            capacity += "; block classification incomplete"
    models = list(dict.fromkeys(str(item["model"]) for item in disks if item.get("model")))
    rows: Tuple[Tuple[str, str], ...] = (
        ("Disk devices", disk_count),
        ("Device capacity (sum)", capacity),
        ("Models", joined(models[:3], " / ") + ("; more in --section storage" if len(models) > 3 else "")),
        ("Other block devices", other_count),
    )
    if confirmed and (not unknown or disks):
        solid = sum(item.get("rotational") is False for item in disks)
        rotating = sum(item.get("rotational") is True for item in disks)
        media_scope = (
            "kernel report; known disks"
            if unknown or not inventory_complete(meta or {}, "storage.devices")
            else "kernel report"
        )
        rows += (
            (
                "Rotation (yes / no / unknown)",
                f"{rotating} / {solid} / {len(disks) - solid - rotating} ({media_scope})",
            ),
        )
        protocols: List[str] = [_protocol(item) for item in disks]
        rows += (
            (
                "Protocols",
                " · ".join(
                    f"{protocol if protocol != UNKNOWN else 'Unknown'}: {protocols.count(protocol)}"
                    for protocol in dict.fromkeys(protocols)
                )
                or UNKNOWN,
            ),
        )
        rows += (("Transports", joined(list(dict.fromkeys(_transports(item) for item in disks)), " · ")),)
        removable = [item.get("removable") for item in disks]
        known_removable = [value for value in removable if isinstance(value, bool)]
        removable_count = UNKNOWN
        if len(known_removable) == len(disks):
            count = sum(value is True for value in known_removable)
            removable_count = (
                f"{count} (known disks)"
                if unknown
                else inventory_count(meta or {}, "storage.devices", storage.get("devices"), count)
            )
        rows += (("Removable whole disks", removable_count),)
    rows += filesystem_summary(storage)
    if unknown:
        rows += (
            (
                "Unclassified block devices",
                inventory_count(meta or {}, "storage.devices", storage.get("devices"), len(unknown)),
            ),
        )
    if not detailed:
        return Card("storage", "Storage", rows)
    tables: List[DetailTable] = [_devices("Whole disk devices (kernel inventory)", disks)]
    if other or unknown:
        tables.append(_devices("Other and unclassified block devices", other + unknown))
    fields = (
        ("vendor", "Vendor"),
        ("serial", "Serial"),
        ("firmware_revision", "Firmware"),
        ("wwid", "WWID"),
        ("transport", "Reported transport"),
        ("driver", "Driver"),
        ("controller_name", "PCI controller"),
        ("numa_node", "NUMA node"),
        ("scheduler", "I/O scheduler"),
        ("mapper_name", "Mapper name"),
        ("mapper_uuid", "Mapper UUID"),
        ("raid_level", "RAID level"),
        ("raid_state", "RAID state"),
        ("raid_disks", "RAID members"),
        ("raid_degraded", "RAID degraded count"),
        ("logical_block_size", "Logical block (bytes)"),
        ("physical_block_size", "Physical block (bytes)"),
        ("minimum_io_size", "Minimum I/O (bytes)"),
        ("optimal_io_size", "Optimal I/O (bytes)"),
    )
    hardware = [
        item
        for item in devices
        if _whole_disk(item) or _unclassified(item) or integer_or(_classification(item).get("layer")) in {3, 4}
    ]
    values = tuple(
        (text(item.get("name")), label, text(item.get(key)))
        for item in hardware
        for key, label in fields
        if text(item.get(key)) != UNKNOWN
    ) + tuple(
        (text(item.get("name")), label, yes_no(item.get(key)))
        for item in hardware
        for key, label in (("rotational", "Rotational"), ("read_only", "Read only"), ("removable", "Removable"))
        if key in item
    )
    if values:
        tables.append(
            DetailTable("Storage hardware and configuration", ("Device", "Field", "Value"), values, group_by=0)
        )
    mounts = mount_table(storage, block_only=True)
    if mounts is not None:
        tables.append(mounts)
    tables.extend(filesystem_tables(storage))
    return Card("storage", "Storage", rows, tuple(tables))
