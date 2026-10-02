"""Rich terminal rendering for SystemCard display models."""

from typing import List, Sequence, Union

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from systemcard.model import Card, DisplayModel
from systemcard.theme import cell_text, section_style, value_text

CARD_MIN_WIDTH = 54
COLUMN_GAP = 2
MAX_COLUMNS = 3


def _summary(card: Card) -> Table:
    accent = section_style(card.section)
    summary = Table.grid(padding=(0, 1), expand=True)
    summary.add_column(style=accent, no_wrap=True)
    summary.add_column(ratio=1, overflow="fold")
    for label, value in card.rows:
        summary.add_row(Text(label, style=f"bold {accent}"), value_text(label, value))
    return summary


def _details(card: Card) -> List[Table]:
    accent = section_style(card.section)
    details: List[Table] = []
    for detail in card.tables:
        table = Table(
            title=Text(detail.title, style=f"bold {accent}"),
            header_style=f"bold {accent}",
            border_style=accent,
            expand=True,
        )
        for column in detail.columns:
            table.add_column(column, overflow="fold")
        for row in detail.rows:
            if len(detail.columns) != len(row):
                raise ValueError("Detail row does not match table columns")
            table.add_row(*(cell_text(column, value) for column, value in zip(detail.columns, row)))
        if detail.omitted:
            table.caption = f"… {detail.omitted} more; use --section {card.section} for all"
            table.caption_style = "dim"
        details.append(table)
    return details


def _panel(card: Card, content: Group) -> Panel:
    accent = section_style(card.section)
    return Panel(content, title=Text(card.title, style=f"bold {accent}"), border_style=accent, expand=True)


def _summary_row(cards: Sequence[Card], columns: int, console: Console) -> None:
    """Use fixed column widths and measured heights to align every border."""
    available = console.width - COLUMN_GAP * (columns - 1)
    widths = [available // columns + (index < available % columns) for index in range(columns)]
    panels = [_panel(card, Group(_summary(card))) for card in cards]
    for panel, width in zip(panels, widths):
        panel.width = width
    height = max(
        len(console.render_lines(panel, console.options.update(width=width), pad=False))
        for panel, width in zip(panels, widths)
    )
    # An incomplete row keeps the same widths without stretching its cards.
    row = Table.grid(padding=0)
    row.width = sum(widths[: len(panels)]) + COLUMN_GAP * (len(panels) - 1)
    values: List[Union[Panel, str]] = []
    for index, (panel, width) in enumerate(zip(panels, widths)):
        if index:
            row.add_column(width=COLUMN_GAP)
            values.append("")
        row.add_column(width=width)
        panel.height = height
        values.append(panel)
    row.add_row(*values)
    console.print(row)


def render(model: DisplayModel, console: Console) -> None:
    """Show a responsive summary grid, keeping detailed tables at full width."""
    heading = Text(model.title, style="bold bright_cyan")
    if model.subtitle:
        heading.append(" · ", style="dim blue")
        heading.append(model.subtitle, style="blue")
    console.rule(heading, style="bright_blue")
    columns = min(MAX_COLUMNS, (console.width + COLUMN_GAP) // (CARD_MIN_WIDTH + COLUMN_GAP), len(model.cards))
    if columns > 1:
        for start in range(0, len(model.cards), columns):
            _summary_row(model.cards[start : start + columns], columns, console)
        for card in model.cards:
            if card.tables:
                console.print(_panel(card, Group(*_details(card))))
    else:
        for card in model.cards:
            console.print(_panel(card, Group(_summary(card), *_details(card))))

    if model.warnings:
        console.print(
            Panel(
                Text("\n".join(model.warnings), style="yellow"),
                title=Text("Warnings", style="bold yellow"),
                border_style="yellow",
            )
        )
    if model.footer:
        console.print(Text(model.footer, style="dim blue", justify="right"))
