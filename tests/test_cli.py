from systemcard import cli


def test_cli_returns_success_when_collection_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(cli, "collect", lambda: {"info": {}, "warnings": []})

    assert cli.main(["--compact", "--no-color"]) == 0


def test_cli_returns_failure_when_collection_fails(monkeypatch) -> None:
    def fail():
        raise cli.CollectionError("unavailable")

    monkeypatch.setattr(cli, "collect", fail)

    assert cli.main(["--no-color"]) == 1


def test_cli_lists_sections_without_collecting(monkeypatch, capsys) -> None:
    def fail():
        raise AssertionError("must not collect for --list-sections")

    monkeypatch.setattr(cli, "collect", fail)

    assert cli.main(["--list-sections"]) == 0
    out = capsys.readouterr().out
    assert "cpu" in out
    assert "accelerators" in out


def test_cli_rejects_unknown_section(monkeypatch) -> None:
    monkeypatch.setattr(cli, "collect", lambda: {"info": {}, "warnings": []})

    assert cli.main(["--section", "bogus,memory", "--no-color"]) == 2


def test_cli_section_filters_output(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "collect", lambda: {"info": {}, "warnings": []})

    assert cli.main(["--section", "memory", "--no-color"]) == 0
    out = capsys.readouterr().out
    assert "Memory" in out
    assert "CPU" not in out
