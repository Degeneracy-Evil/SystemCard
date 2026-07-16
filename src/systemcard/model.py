"""Transform normalized snapshots into renderer-friendly cards."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from systemcard.formatters import bytes_value, text


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _items(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


@dataclass(frozen=True)
class Card:
    title: str
    rows: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DisplayModel:
    title: str
    subtitle: str
    cards: tuple[Card, ...]
    warnings: tuple[str, ...]


def build(snapshot: Mapping[str, Any], compact: bool = False) -> DisplayModel:
    """Build a resilient presentation model from a public Sysal JSON snapshot."""
    info = _mapping(snapshot.get("info"))
    platform = _mapping(info.get("platform"))
    host = _mapping(platform.get("host"))
    os_info = _mapping(platform.get("os"))
    cpu = _mapping(info.get("cpu"))
    memory = _mapping(info.get("memory"))
    accelerators = _mapping(info.get("accelerators"))
    network = _mapping(info.get("network"))
    storage = _mapping(info.get("storage"))
    software = _mapping(info.get("software"))

    hostname = text(host.get("hostname"))
    os_name = " ".join(part for part in (text(os_info.get("name")), text(os_info.get("version"))) if part != "—")
    packages = _items(cpu.get("packages"))
    cpu_name = text(_mapping(packages[0]).get("model_name")) if packages else "—"
    visible_cpus = sum(1 for item in _items(cpu.get("logical_cpus")) if _mapping(item).get("visible_to_current_process"))
    devices = _items(accelerators.get("devices"))
    visible_devices = sum(
        1 for item in devices if _mapping(item).get("visible_to_current_process")
    )

    cards = [
        Card("System", (("Host", hostname), ("OS", os_name or "—"), ("Architecture", text(_mapping(platform.get("architecture")).get("name"))))),
        Card(
            "CPU",
            (("Model", cpu_name), ("Packages", str(len(packages))), ("Logical CPUs", str(len(_items(cpu.get("logical_cpus"))))), ("Visible to process", str(visible_cpus))),
        ),
        Card(
            "Memory",
            (("Total", bytes_value(memory.get("total_memory"))), ("Available", bytes_value(memory.get("available_memory"))), ("Type", text(memory.get("memory_type")))),
        ),
        Card("Accelerators", (("Devices", str(len(devices))), ("Visible to process", str(visible_devices)))),
    ]

    if not compact:
        interfaces = _items(network.get("interfaces"))
        disks = _items(storage.get("devices"))
        cards.extend(
            [
                Card("Network", (("Interfaces", str(len(interfaces))),)),
                Card("Storage", (("Devices", str(len(disks))),)),
                Card(
                    "Software",
                    (("Drivers", str(len(_items(software.get("drivers"))))), ("Runtimes", str(len(_items(software.get("runtimes")))))),
                ),
            ]
        )

    warnings = tuple(str(item) for item in _items(snapshot.get("warnings")) if item)
    return DisplayModel("SystemCard", hostname, tuple(cards), warnings)
