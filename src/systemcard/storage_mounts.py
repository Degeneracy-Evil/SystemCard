"""Mount tables for ordinary block storage and complete namespace topology."""

from typing import Any, Mapping, Optional

from systemcard.formatters import UNKNOWN, text, yes_no
from systemcard.presentation_types import DetailTable
from systemcard.schema import mapping_items


def mount_table(storage: Mapping[str, Any], block_only: bool = False) -> Optional[DetailTable]:
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
            if not block_only or item.get("block_device")
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
            for item in mapping_items(storage.get("devices"))
            if item.get("mount_point")
        )
    if not mount_rows:
        return None
    return DetailTable(
        "Block device mounts (current namespace)"
        if block_only and mounts
        else "Mounts (current namespace)"
        if mounts
        else "Reported mounts (partial inventory)",
        ("ID", "Device/source", "Filesystem", "Mount point", "FS root", "Read only"),
        mount_rows,
    )
