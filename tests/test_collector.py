"""Tests for the native collection boundary."""

from collections.abc import Mapping
from typing import Any

import pytest

import systemcard
from systemcard.collector import CollectionError, collect


class SuccessfulNative:
    """Small native-module stand-in that records the requested scope."""

    scope: str | None = None

    @classmethod
    def collect(cls, scope: str) -> Mapping[str, Any]:
        cls.scope = scope
        return {"info": {}, "warnings": []}


class FailingNative:
    """Native-module stand-in that reports a collection failure."""

    @staticmethod
    def collect(scope: str) -> dict[str, Any]:
        raise RuntimeError(f"failed: {scope}")


class InvalidNative:
    """Native-module stand-in with an invalid return value."""

    @staticmethod
    def collect(scope: str) -> str:
        return scope


def test_collect_forwards_scope_and_copies_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", SuccessfulNative, raising=False)

    snapshot = collect("full")

    assert SuccessfulNative.scope == "full"
    assert snapshot == {"info": {}, "warnings": []}


def test_collect_wraps_native_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", FailingNative, raising=False)

    with pytest.raises(CollectionError, match="failed: basic"):
        collect("basic")


def test_collect_rejects_invalid_native_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(systemcard, "_native", InvalidNative, raising=False)

    with pytest.raises(CollectionError, match="invalid snapshot"):
        collect()
