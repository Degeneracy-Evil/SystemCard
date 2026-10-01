"""Tests for snapshot validation and normalization."""

import pytest

from systemcard.schema import normalize_snapshot, resolve_sections, validate_snapshot


def test_validate_snapshot_rejects_unusable_values() -> None:
    with pytest.raises(TypeError, match="mapping"):
        validate_snapshot([])  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="'info'"):
        validate_snapshot({})


def test_normalize_snapshot_degrades_bad_domains_to_empty_mappings() -> None:
    snapshot = normalize_snapshot({"info": {"cpu": "bad", "memory": {"total_memory": 1024}}})

    assert snapshot["info"]["cpu"] == {}
    assert snapshot["info"]["memory"] == {"total_memory": 1024}
    assert snapshot["info"]["platform"] == {}


def test_resolve_sections_keeps_only_canonical_names() -> None:
    assert resolve_sections(["memory", "bogus", "cpu"]) == {"cpu", "memory"}
