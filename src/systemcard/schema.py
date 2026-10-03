"""Snapshot validation, normalization, and canonical display sections.

Python modules treat every field other than the top-level mapping as optional
(see docs/binding-contract.md). This module centralizes the minimal structural
guarantees the presentation side can rely on, without coupling to Sysal's C++
internals.
"""

from math import isfinite
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

SECTIONS: Tuple[str, ...] = (
    "system",
    "cpu",
    "memory",
    "accelerators",
    "network",
    "storage",
    "software",
    "execution",
    "topology",
    "sensors",
    "health",
)

_INFO_DOMAINS: Tuple[str, ...] = (
    "platform",
    "cpu",
    "memory",
    "accelerators",
    "network",
    "storage",
    "pci",
    "software",
    "execution",
    "sensors",
    "hardware_health",
)


def mapping_value(value: object) -> Mapping[str, Any]:
    """Read a mapping without inventing values for malformed or missing data."""
    return value if isinstance(value, Mapping) else {}


def list_value(value: object) -> List[Any]:
    """Read the JSON list shape used by Sysal."""
    return list(value) if isinstance(value, list) else []


def mapping_items(value: object) -> List[Mapping[str, Any]]:
    """Read objects in a JSON list; preserve malformed positions as empty objects."""
    return [mapping_value(item) for item in list_value(value)]


def integer_value(value: object) -> Optional[int]:
    """Booleans are not quantities or enum ordinals."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def integer_or(value: object, default: int = 0) -> int:
    result = integer_value(value)
    return default if result is None else result


def number_value(value: object) -> Optional[Union[int, float]]:
    """Only finite JSON numbers are usable measurements."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return None if isinstance(value, float) and not isfinite(value) else value


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Raise on structurally unusable snapshots that presentation cannot build from."""
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a mapping")
    info = snapshot.get("info")
    if not isinstance(info, Mapping):
        raise ValueError("snapshot is missing a mapping 'info'")


def normalize_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a copy with guaranteed dict domains.

    Non-structural bad data (e.g. a string where a domain mapping was expected)
    degrades to empty containers instead of raising, matching the contract that
    presentation must degrade gracefully on absent optional fields.
    """
    validate_snapshot(snapshot)

    result = dict(snapshot)
    info = dict(mapping_value(snapshot.get("info")))
    result["info"] = info

    for domain in _INFO_DOMAINS:
        info[domain] = dict(mapping_value(info.get(domain)))

    return result


def is_valid_section(name: str) -> bool:
    """Whether ``name`` is one of the canonical display sections."""
    return name in SECTIONS


def resolve_sections(tokens: Iterable[str]) -> Set[str]:
    """Return the subset of ``tokens`` that are valid canonical sections."""
    return {token for token in tokens if is_valid_section(token)}
