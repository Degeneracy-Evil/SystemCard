"""Command line entry point."""

import argparse
from typing import List, Optional, Tuple

from rich.console import Console

from systemcard import __version__
from systemcard.collector import CollectionError, collect
from systemcard.model import build
from systemcard.render import render
from systemcard.schema import SECTIONS, normalize_snapshot, resolve_sections


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Display a concise system information card.")
    result.add_argument("--compact", action="store_true", help="show only the system summary")
    result.add_argument("--no-color", action="store_true", help="disable terminal colors")
    result.add_argument(
        "--section",
        action="append",
        default=None,
        metavar="SECTIONS",
        help="only show the given sections (comma- or colon-separated, repeatable)",
    )
    result.add_argument("--list-sections", action="store_true", help="list available sections and exit")
    result.add_argument("--version", action="version", version=f"systemcard {__version__}")
    return result


def _requested_sections(raw: Optional[List[str]]) -> Tuple[Optional[List[str]], List[str]]:
    if not raw:
        return None, []
    tokens = []
    for group in raw:
        for token in group.replace(":", ",").split(","):
            cleaned = token.strip().lower().replace(" ", "-")
            if cleaned:
                tokens.append(cleaned)
    unknown = sorted({token for token in tokens if token not in SECTIONS})
    valid = resolve_sections(tokens)
    return [section for section in SECTIONS if section in valid], unknown


def main(argv: Optional[List[str]] = None) -> int:
    args = parser().parse_args(argv)
    console = Console(no_color=args.no_color)

    if args.list_sections:
        console.print(" ".join(SECTIONS))
        return 0

    try:
        snapshot = collect()
    except CollectionError as error:
        console.print(f"[red]SystemCard collection failed:[/] {error}")
        return 1

    sections, unknown = _requested_sections(args.section)
    if unknown:
        console.print(f"[red]Unknown section(s):[/] {', '.join(unknown)}")
        console.print(f"Available: {' '.join(SECTIONS)}. Try --list-sections.")
        return 2

    render(build(snapshot=normalize_snapshot(snapshot), compact=args.compact, sections=sections), console)
    return 0
