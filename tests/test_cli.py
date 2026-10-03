import sys
from io import BytesIO, TextIOWrapper
from typing import Never

import pytest

from systemcard import cli
from systemcard.collector import CollectionError


def test_cli_renders_on_ascii_output(monkeypatch: pytest.MonkeyPatch) -> None:
    output = BytesIO()
    stream = TextIOWrapper(output, encoding="ascii")
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(cli, "collect", lambda **_kwargs: {"info": {}, "warnings": ["temperature: 75 °C"]})

    assert cli.main(["--no-color"]) == 0
    stream.flush()
    assert b"SystemCard" in output.getvalue()
    assert b"75 ?C" in output.getvalue()


def test_cli_returns_success_when_collection_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "collect", lambda **_kwargs: {"info": {}, "warnings": []})

    assert cli.main(["--compact", "--no-color"]) == 0


def test_cli_returns_failure_when_collection_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(**_kwargs: object) -> Never:
        raise CollectionError("unavailable")

    monkeypatch.setattr(cli, "collect", fail)

    assert cli.main(["--no-color"]) == 1


def test_cli_lists_sections_without_collecting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(**_kwargs: object) -> Never:
        raise AssertionError("must not collect for --list-sections")

    monkeypatch.setattr(cli, "collect", fail)

    assert cli.main(["--list-sections"]) == 0
    out = capsys.readouterr().out
    assert "cpu" in out
    assert "accelerators" in out


def test_cli_rejects_unknown_section(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(**_kwargs: object) -> Never:
        raise AssertionError("invalid sections must not trigger collection")

    monkeypatch.setattr(cli, "collect", fail)
    assert cli.main(["--section", "bogus,memory", "--no-color"]) == 2


def test_cli_section_filters_output(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(cli, "collect", lambda **_kwargs: {"info": {}, "warnings": []})

    assert cli.main(["--section", "memory", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "Memory" in out
    assert "CPU" not in out


def test_cli_only_requests_selected_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    requested = []

    def collect_sections(*, sections: object = None) -> dict[str, object]:
        requested.append(sections)
        return {"info": {}}

    monkeypatch.setattr(cli, "collect", collect_sections)
    assert cli.main(["--section", "memory:cpu", "--section", "memory", "--no-color"]) == 0
    assert requested == [["cpu", "memory"]]
    requested.clear()
    assert cli.main(["--compact", "--no-color"]) == 0
    assert requested == [["system", "cpu", "memory", "accelerators"]]
