"""Snapshot validation, normalization, and canonical display sections.

Python modules treat every field other than the top-level mapping as optional
(see docs/binding-contract.md). This module centralizes the minimal structural
guarantees the presentation side can rely on, without coupling to Sysal's C++
internals.
"""

from typing import Any, Dict, Iterable, Mapping, Set, Tuple

SECTIONS: Tuple[str, ...] = (
    "system",
    "cpu",
    "memory",
    "accelerators",
    "network",
    "storage",
    "software",
    "execution",
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
)


def _as_mapping(value: object) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    """Raise on structurally unusable snapshots that presentation cannot build from."""
    if not isinstance(snapshot, Mapping):
        raise TypeError("snapshot must be a mapping")
    info = snapshot.get("info")
    if not isinstance(info, Mapping):
        raise ValueError("snapshot is missing a mapping 'info'")


def normalize_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a copy with guaranteed dict domains and list-valued fields.

    Non-structural bad data (e.g. a string where a domain mapping was expected)
    degrades to empty containers instead of raising, matching the contract that
    presentation must degrade gracefully on absent optional fields.
    """
    validate_snapshot(snapshot)

    result = dict(snapshot)
    info = _as_mapping(snapshot.get("info"))
    result["info"] = info

    for domain in _INFO_DOMAINS:
        info[domain] = _as_mapping(info.get(domain))

    return result


def is_valid_section(name: str) -> bool:
    """Whether ``name`` is one of the canonical display sections."""
    return name in SECTIONS


def resolve_sections(tokens: Iterable[str]) -> Set[str]:
    """Return the subset of ``tokens`` that are valid canonical sections."""
    return {token for token in tokens if is_valid_section(token)}
