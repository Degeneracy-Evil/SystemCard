"""Tests for the native collection boundary."""

from collections.abc import Mapping
from typing import Any, ClassVar

import pytest

import systemcard
from systemcard._native import Domain, FilesystemQuery, SensorDevices
from systemcard.collector import CollectionError, collect


class SuccessfulNative:
    """Small native-module stand-in that records the requested domains."""

    domains: ClassVar[list[Domain]] = []

    @classmethod
    def collect(
        cls, domains: list[Domain], _filesystems: FilesystemQuery, _sensors: SensorDevices
    ) -> Mapping[str, Any]:
        cls.domains = domains
        return {"info": {}, "warnings": []}


class FailingNative:
    """Native-module stand-in that reports a collection failure."""

    @staticmethod
    def collect(_domains: list[Domain], _filesystems: FilesystemQuery, _sensors: SensorDevices) -> dict[str, Any]:
        raise RuntimeError("failed: native")


class InvalidNative:
    """Native-module stand-in with an invalid return value."""

    @staticmethod
    def collect(domains: list[Domain], _filesystems: FilesystemQuery, _sensors: SensorDevices) -> str:
        return str(domains)


def test_collect_forwards_scope_and_copies_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", SuccessfulNative, raising=False)

    snapshot = collect("full")

    assert Domain.RAW in SuccessfulNative.domains
    assert snapshot == {"info": {}, "warnings": []}


def test_collect_wraps_native_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", FailingNative, raising=False)

    with pytest.raises(CollectionError, match="failed: native"):
        collect("basic")


def test_collect_rejects_invalid_native_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", InvalidNative, raising=False)

    with pytest.raises(CollectionError, match="invalid snapshot"):
        collect()
