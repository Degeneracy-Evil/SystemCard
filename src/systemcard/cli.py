"""Command line entry point."""

import argparse
import sys
from contextlib import contextmanager
from io import TextIOWrapper
from typing import Iterator, List, Optional, TextIO, Tuple

from rich.console import Console

from systemcard import __version__
from systemcard.collector import CollectionError, collect
from systemcard.model import build
from systemcard.render import render
from systemcard.schema import SECTIONS, normalize_snapshot, resolve_sections


@contextmanager
def _console_output() -> Iterator[TextIO]:
    """Replace unrepresentable characters without closing the original stream."""
    stream = sys.stdout
    if not isinstance(stream, TextIOWrapper):
        yield stream
        return
    stream.flush()
    output = TextIOWrapper(stream.buffer, encoding=stream.encoding, errors="replace", line_buffering=True)
    try:
        yield output
    finally:
        output.flush()
        output.detach()


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
    result.add_argument("--sources", action="store_true", help="show collection sources and missing-data reasons")
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
    with _console_output() as output:
        return _display(args, Console(file=output, no_color=args.no_color))


def _display(args: argparse.Namespace, console: Console) -> int:

    if args.list_sections:
        console.print(" ".join(SECTIONS))
        return 0

    sections, unknown = _requested_sections(args.section)
    if args.section is not None and not sections and not unknown:
        console.print("[red]No section names given.[/] Try --list-sections.")
        return 2
    if unknown:
        console.print(f"[red]Unknown section(s):[/] {', '.join(unknown)}")
        console.print(f"Available: {' '.join(SECTIONS)}. Try --list-sections.")
        return 2

    try:
        requested = (
            sections
            if sections is not None
            else (["system", "cpu", "memory", "accelerators"] if args.compact else None)
        )
        snapshot = normalize_snapshot(collect(sections=requested))
    except (CollectionError, ValueError, TypeError) as error:
        console.print(f"[red]SystemCard collection failed:[/] {error}")
        return 1

    render(
        build(snapshot=snapshot, compact=args.compact, sections=sections, sources=args.sources),
        console,
    )
    return 0
