from systemcard import cli


def test_cli_returns_success_when_collection_succeeds(monkeypatch) -> None:
    monkeypatch.setattr(cli, "collect", lambda: {"info": {}, "warnings": []})

    assert cli.main(["--compact", "--no-color"]) == 0


def test_cli_returns_failure_when_collection_fails(monkeypatch) -> None:
    def fail():
        raise cli.CollectionError("unavailable")

    monkeypatch.setattr(cli, "collect", fail)

    assert cli.main(["--no-color"]) == 1
