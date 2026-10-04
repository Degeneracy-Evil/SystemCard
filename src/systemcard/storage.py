"""Whole-disk identity, main configuration and associated mounts."""

from typing import Any, List, Mapping, Optional, Tuple

from systemcard.collection_status import inventory_known
from systemcard.formatters import UNKNOWN, bytes_value, enum_text, pci_address, text, yes_no
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, integer_value, mapping_items
from systemcard.storage_mounts import mount_table

STORAGE_KINDS = {0: "NVMe", 1: "SSD", 2: "HDD", 3: "Other"}


def _whole_disk(device: Mapping[str, Any]) -> bool:
    if "layer" in device:
        return device.get("layer") == "disk"
    return integer_or(device.get("kind"), 3) in {0, 1, 2} and not device.get("partition_number")


def _unclassified(device: Mapping[str, Any]) -> bool:
    layer = device.get("layer")
    if isinstance(layer, str) and layer not in {"", "unknown", "other"}:
        return False
    return not _whole_disk(device) and not device.get("partition_number") and not device.get("parent")


def _devices(title: str, devices: List[Mapping[str, Any]]) -> DetailTable:
    return DetailTable(
        title,
        ("Name", "Kind / layer", "Capacity", "Model", "PCI"),
        tuple(
            (
                text(item.get("name")),
                text(item.get("layer")) if not _whole_disk(item) else enum_text(STORAGE_KINDS, item.get("kind")),
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
    if known and len(known) != len(disks):
        capacity += f" (known portion: {len(known)}/{len(disks)} disks)"
    confirmed = inventory_known(meta or {}, "storage", storage.get("devices"))
    disk_count = str(len(disks)) if confirmed else UNKNOWN
    other_count = str(len(other)) if confirmed else UNKNOWN
    if unknown:
        disk_count = f"{len(disks)} (known portion)" if disks else UNKNOWN
        other_count = f"{len(other)} (known portion)" if other else UNKNOWN
        if capacity != UNKNOWN:
            capacity += "; block classification incomplete"
    models = list(dict.fromkeys(str(item["model"]) for item in disks if item.get("model")))
    rows: Tuple[Tuple[str, str], ...] = (
        ("Whole disks", disk_count),
        ("Disk capacity", capacity),
        ("Models", joined(models[:3], " / ") + ("; more in --section storage" if len(models) > 3 else "")),
        ("Other block devices", other_count),
    )
    if unknown:
        rows += (("Unclassified block devices", str(len(unknown))),)
    if not detailed:
        return Card("storage", "Storage", rows)
    tables: List[DetailTable] = [_devices("Whole disks (kernel inventory)", disks)]
    fields = (
        ("vendor", "Vendor"),
        ("serial", "Serial"),
        ("firmware_revision", "Firmware"),
        ("wwid", "WWID"),
        ("transport", "Transport"),
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
    hardware = [item for item in devices if _whole_disk(item) or item.get("layer") in {"md", "device-mapper"}]
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
    return Card("storage", "Storage", rows, tuple(tables))
