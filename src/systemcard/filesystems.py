"""Filesystem views and usage; shared storage is never summed as disk capacity."""

from typing import Any, Dict, List, Mapping, Optional, Tuple

from systemcard.collection_status import collection_result
from systemcard.formatters import UNKNOWN, bytes_value, enum_text, percent, text
from systemcard.presentation_types import DetailTable
from systemcard.schema import integer_value, mapping_items, mapping_value

FILESYSTEM_KINDS = {0: "Local", 1: "Network", 2: "Memory", 3: "Pseudo", 4: "Userspace", 5: "Unknown"}


def _mounts(storage: Mapping[str, Any]) -> Dict[int, Mapping[str, Any]]:
    return {
        identity: mount
        for mount in mapping_items(storage.get("mounts"))
        for identity in [integer_value(mount.get("mount_id"))]
        if identity is not None
    }


def _aliases(report: Mapping[str, Any], mounts: Mapping[int, Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    ids = report.get("mount_ids")
    if not isinstance(ids, list):
        return []
    return [
        mounts[identity]
        for item in ids
        for identity in [integer_value(item)]
        if identity is not None and identity in mounts
    ]


def _used(usage: Mapping[str, Any], total_key: str, free_key: str) -> Optional[int]:
    total = integer_value(usage.get(total_key))
    free = integer_value(usage.get(free_key))
    return total - free if total is not None and free is not None and 0 <= free <= total else None


def filesystem_summary(storage: Mapping[str, Any]) -> Tuple[Tuple[str, str], ...]:
    mounts = _mounts(storage)
    reports = mapping_items(storage.get("filesystems"))
    if not reports:
        return (("Filesystem statistics", UNKNOWN),)
    counts = {kind: sum(integer_value(report.get("kind")) == kind for report in reports) for kind in range(6)}
    counts[5] += len(reports) - sum(counts.values())
    inventory = " · ".join(f"{counts[kind]} {FILESYSTEM_KINDS[kind].lower()}" for kind in range(6) if counts[kind])
    rows = [("Filesystem views", inventory)]
    for report in reports:
        if not any(mount.get("path") == "/" for mount in _aliases(report, mounts)):
            continue
        usage = mapping_value(report.get("usage"))
        rows.extend(
            (
                (
                    "Root used / total",
                    f"{bytes_value(_used(usage, 'total', 'free'))} / {bytes_value(usage.get('total'))}",
                ),
                ("Root available", bytes_value(usage.get("available"))),
            )
        )
        break
    return tuple(rows)


def filesystem_tables(storage: Mapping[str, Any]) -> Tuple[DetailTable, ...]:
    mounts = _mounts(storage)
    reports = [item for item in mapping_items(storage.get("filesystems")) if item.get("kind") != 3]
    if not reports:
        return ()
    space: List[Tuple[str, ...]] = []
    inodes: List[Tuple[str, ...]] = []
    notes: List[Tuple[str, ...]] = []
    for report in reports:
        aliases = _aliases(report, mounts)
        paths = "\n".join(text(mount.get("path")) for mount in aliases) or UNKNOWN
        filesystems = " / ".join(dict.fromkeys(text(mount.get("filesystem")) for mount in aliases)) or UNKNOWN
        usage = mapping_value(report.get("usage"))
        used = _used(usage, "total", "free")
        total = integer_value(usage.get("total"))
        space.append(
            (
                paths,
                enum_text(FILESYSTEM_KINDS, report.get("kind")),
                filesystems,
                bytes_value(total),
                bytes_value(used),
                bytes_value(usage.get("available")),
                percent(100 * used / total) if total and used is not None else UNKNOWN,
                "Not queried" if report.get("status") == 3 and report.get("note") else collection_result(report),
            )
        )
        total_inodes = integer_value(usage.get("inodes"))
        used_inodes = _used(usage, "inodes", "free_inodes")
        if total_inodes is not None:
            inodes.append(
                (
                    paths,
                    text(total_inodes),
                    text(used_inodes),
                    text(usage.get("available_inodes")),
                    percent(100 * used_inodes / total_inodes) if total_inodes and used_inodes is not None else UNKNOWN,
                )
            )
        if usage and total_inodes is None:
            notes.append((paths, "Inode capacity not reported"))
        if report.get("note"):
            notes.append((paths, text(report.get("note"))))
    tables = [
        DetailTable(
            "Filesystem space (aliases grouped; shared pools not summed)",
            ("Mounts", "Kind", "Filesystem", "Total", "Used", "Available", "Used %", "Query"),
            tuple(space),
        )
    ]
    if inodes:
        tables.append(
            DetailTable("Filesystem inodes", ("Mounts", "Total", "Used", "Available", "Used %"), tuple(inodes))
        )
    if notes:
        tables.append(DetailTable("Filesystem query notes", ("Mounts", "Note"), tuple(notes)))
    return tuple(tables)
