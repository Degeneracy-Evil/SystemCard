"""Select and compose cards from a normalized Sysal snapshot."""

from typing import Any, Callable, Dict, List, Mapping, Optional

from systemcard.accelerators import accelerator_card
from systemcard.collection_status import with_collection_status
from systemcard.cpu import cpu_card
from systemcard.execution import execution_card as _execution_card
from systemcard.formatters import UNKNOWN, text
from systemcard.health import health_card
from systemcard.memory import memory_card
from systemcard.network import network_card
from systemcard.platform import system_card
from systemcard.presentation_types import Card as Card
from systemcard.presentation_types import DetailTable as DetailTable
from systemcard.presentation_types import DisplayModel as DisplayModel
from systemcard.schema import SECTIONS, number_value
from systemcard.schema import list_value as _items
from systemcard.schema import mapping_items as _mappings
from systemcard.schema import mapping_value as _mapping
from systemcard.sensors import sensors_card
from systemcard.software import software_card
from systemcard.sources import with_sources
from systemcard.storage import storage_card
from systemcard.topology import topology_card


def build(
    snapshot: Mapping[str, Any],
    compact: bool = False,
    sections: Optional[List[str]] = None,
    sources: bool = False,
) -> DisplayModel:
    """Build a resilient presentation model from a public Sysal JSON snapshot."""
    info = _mapping(snapshot.get("info"))
    platform = _mapping(info.get("platform"))
    hostname = text(_mapping(platform.get("host")).get("hostname"))
    detailed = bool(sections)
    meta = _mapping(snapshot.get("meta"))
    cgroup = _mapping(_mapping(info.get("execution")).get("cgroup"))

    def execution_card() -> Card:
        visible_cpu_count = sum(
            item.get("visible_to_current_process") is True
            for item in _mappings(_mapping(info.get("cpu")).get("logical_cpus"))
        )
        visible_accelerator_count = sum(
            item.get("visible_to_current_process") is True
            for item in _mappings(_mapping(info.get("accelerators")).get("devices"))
        )
        return _execution_card(_mapping(info.get("execution")), visible_cpu_count, visible_accelerator_count)

    builders: Dict[str, Callable[[], Card]] = {
        "system": lambda: system_card(platform, _mapping(info.get("pci")), detailed),
        "cpu": lambda: cpu_card(
            _mapping(info.get("cpu")),
            detailed,
            cgroup,
            text(_mapping(platform.get("architecture")).get("name")),
            meta=meta,
        ),
        "memory": lambda: memory_card(_mapping(info.get("memory")), detailed, cgroup),
        "accelerators": lambda: accelerator_card(_mapping(info.get("accelerators")), detailed, meta=meta),
        "network": lambda: network_card(_mapping(info.get("network")), detailed, meta=meta),
        "storage": lambda: storage_card(_mapping(info.get("storage")), detailed, meta=meta),
        "software": lambda: software_card(_mapping(info.get("software"))),
        "execution": execution_card,
        "topology": lambda: topology_card(info),
        "sensors": lambda: sensors_card(info),
        "health": lambda: health_card(info),
    }
    wanted = (
        tuple(section for section in SECTIONS if section in sections)
        if sections
        else (
            SECTIONS[:4] if compact else ("system", "cpu", "memory", "storage", "network", "accelerators", "execution")
        )
    )
    cards = tuple(with_collection_status(builders[section](), meta) for section in wanted)
    if not detailed:
        cards = tuple(Card(card.section, card.title, card.rows) for card in cards)
    if sources:
        cards = tuple(with_sources(card, _mapping(snapshot.get("meta")), info) for card in cards)
    warnings = tuple(str(item) for item in _items(snapshot.get("warnings")) if item)
    footer_parts = []
    if text(meta.get("sysal_version")) != UNKNOWN:
        footer_parts.append(f"Sysal {text(meta.get('sysal_version'))}")
    duration = number_value(meta.get("collect_duration"))
    if duration is not None:
        footer_parts.append(f"collected in {duration * 1000:.0f} ms")
    return DisplayModel("SystemCard", hostname, tuple(cards), warnings, " · ".join(footer_parts))
