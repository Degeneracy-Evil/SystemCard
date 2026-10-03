"""Whole-disk summaries with separate block layers, mounts and health reports."""

from typing import Any, List, Mapping, Tuple

from systemcard.formatters import UNKNOWN, bytes_value, enum_text, pci_address, text, yes_no
from systemcard.presentation_helpers import joined
from systemcard.presentation_types import Card, DetailTable
from systemcard.schema import integer_or, mapping_items
from systemcard.storage_health import query_summary, storage_health_tables

STORAGE_KINDS = {0: "NVMe", 1: "SSD", 2: "HDD", 3: "Other"}


def _whole_disk(device: Mapping[str, Any]) -> bool:
    if "layer" in device:
        return device.get("layer") == "disk"
    return integer_or(device.get("kind"), 3) in {0, 1, 2} and not device.get("partition_number")


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


def storage_card(storage: Mapping[str, Any], detailed: bool) -> Card:
    devices = mapping_items(storage.get("devices"))
    disks = [item for item in devices if _whole_disk(item)]
    other = [item for item in devices if not _whole_disk(item)]
    total = sum(integer_or(item.get("capacity")) for item in disks)
    models = list(dict.fromkeys(str(item["model"]) for item in disks if item.get("model")))
    rows: Tuple[Tuple[str, str], ...] = (
        ("Whole disks", str(len(disks)) if "devices" in storage else UNKNOWN),
        ("Disk capacity", bytes_value(total) if disks else UNKNOWN),
        ("Models", joined(models[:3], " / ") + ("; more in --section storage" if len(models) > 3 else "")),
        ("Other block devices", str(len(other)) if "devices" in storage else UNKNOWN),
    )
    if storage.get("health"):
        rows += (("Health queries", query_summary(storage)),)
    if not detailed:
        return Card("storage", "Storage", rows)
    tables: List[DetailTable] = [_devices("Whole disks (kernel inventory)", disks)]
    if other:
        tables.append(_devices("Partitions and other block layers", other))
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
    relations = tuple(
        (
            text(item.get("name")),
            text(item.get("layer")),
            text(item.get("parent")),
            text(item.get("partition_number")),
            joined(item.get("slaves")),
        )
        for item in devices
        if item.get("parent") or item.get("slaves") or item.get("mapper_name") or item.get("raid_level")
    )
    if relations:
        tables.append(
            DetailTable(
                "Block topology", ("Device", "Layer", "Partition parent", "Partition", "Lower devices"), relations
            )
        )
    mounts = mapping_items(storage.get("mounts"))
    if mounts:
        mount_rows = tuple(
            (
                text(item.get("mount_id")),
                text(item.get("block_device") or item.get("source")),
                text(item.get("filesystem")),
                text(item.get("path")),
                text(item.get("root")),
                yes_no(item.get("read_only")),
            )
            for item in mounts
        )
    else:
        # Earlier snapshots retain only a representative mount per block device.
        mount_rows = tuple(
            (
                UNKNOWN,
                text(item.get("name")),
                text(item.get("fs_type")),
                text(item.get("mount_point")),
                UNKNOWN,
                UNKNOWN,
            )
            for item in devices
            if item.get("mount_point")
        )
    if mount_rows:
        tables.append(
            DetailTable(
                "Mounts (current namespace)" if mounts else "Reported mounts (partial inventory)",
                ("ID", "Device/source", "Filesystem", "Mount point", "FS root", "Read only"),
                mount_rows,
            )
        )
    tables.extend(storage_health_tables(storage, detailed=True))
    return Card("storage", "Storage", rows, tuple(tables))
