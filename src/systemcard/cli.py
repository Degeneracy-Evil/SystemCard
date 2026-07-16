"""Command line entry point."""

from __future__ import annotations

import argparse

from rich.console import Console

from systemcard import __version__
from systemcard.collector import CollectionError, collect
from systemcard.model import build
from systemcard.render import render


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Display a concise system information card.")
    result.add_argument("--compact", action="store_true", help="show only the system summary")
    result.add_argument("--no-color", action="store_true", help="disable terminal colors")
    result.add_argument("--version", action="version", version=f"systemcard {__version__}")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    console = Console(no_color=args.no_color)
    try:
        snapshot = collect()
    except CollectionError as error:
        console.print(f"[red]SystemCard collection failed:[/] {error}")
        return 1

    render(build(snapshot, compact=args.compact), console)
    return 0
