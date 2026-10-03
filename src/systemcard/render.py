"""Rich terminal rendering for SystemCard display models."""

from typing import Dict, List, Sequence, Tuple, Union

from rich.cells import cell_len
from rich.console import Console, ConsoleRenderable, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from systemcard.formatters import UNKNOWN
from systemcard.presentation_types import Card, DetailTable, DisplayModel
from systemcard.theme import cell_text, section_style, value_text

CARD_MIN_WIDTH = 54
COLUMN_GAP = 2
MAX_COLUMNS = 3


def _fields(rows: Sequence[Tuple[str, Text]], accent: str, width: int) -> Table:
    """Keep labels readable and give values room before choosing two columns."""
    label_width = max((cell_len(label) for label, _ in rows), default=0)
    stacked = width - 4 - label_width - 1 < 24
    fields = Table.grid(padding=(0, 1), expand=True)
    fields.add_column(overflow="fold")
    if not stacked:
        fields.add_column(ratio=1, overflow="fold")
    for label, value in rows:
        heading = Text(label, style=f"bold {accent}")
        if stacked:
            fields.add_row(heading)
            fields.add_row(value)
        else:
            fields.add_row(heading, value)
    return fields


def _summary(card: Card, width: int) -> Table:
    return _fields(
        [(label, value_text(label, value)) for label, value in card.rows], section_style(card.section), width
    )


def _visible_columns(detail: DetailTable) -> DetailTable:
    for row in detail.rows:
        if len(detail.columns) != len(row):
            raise ValueError("Detail row does not match table columns")
    if detail.group_by is not None and not 0 <= detail.group_by < len(detail.columns):
        raise ValueError("Detail grouping column is out of range")
    keep = tuple(
        index
        for index in range(len(detail.columns))
        if index == 0
        or index == detail.group_by
        or not detail.rows
        or any(row[index] not in {UNKNOWN, ""} for row in detail.rows)
    )
    return DetailTable(
        detail.title,
        tuple(detail.columns[index] for index in keep),
        tuple(tuple(row[index] for index in keep) for row in detail.rows),
        detail.omitted,
        keep.index(detail.group_by) if detail.group_by is not None else None,
    )


def _grouped_fields(detail: DetailTable, accent: str, width: int) -> List[ConsoleRenderable]:
    if detail.group_by is None:
        return []
    index = detail.group_by
    groups: Dict[str, List[Tuple[str, Text]]] = {}
    for row in detail.rows:
        values = [(column, value) for number, (column, value) in enumerate(zip(detail.columns, row)) if number != index]
        # Field/value records have an actual field name in the first remaining cell.
        fields = (
            [(values[0][1], cell_text(values[0][1], values[1][1]))]
            if len(values) == 2 and values[0][0] == "Field"
            else [(column, cell_text(column, value)) for column, value in values if value not in {UNKNOWN, ""}]
        )
        groups.setdefault(row[index], []).extend(fields)
    result: List[ConsoleRenderable] = []
    for identity, fields in groups.items():
        table = _fields(fields, accent, width)
        table.title = Text(f"{detail.title} · {identity}", style=f"bold {accent}")
        result.append(table)
    return result


def _details(card: Card, width: int) -> List[ConsoleRenderable]:
    accent = section_style(card.section)
    details: List[ConsoleRenderable] = []
    for original in card.tables:
        detail = _visible_columns(original)
        column_widths = [
            max(cell_len(column), min(max((cell_len(row[index]) for row in detail.rows), default=0), 24), 8)
            for index, column in enumerate(detail.columns)
        ]
        if detail.group_by is not None:
            details.extend(_grouped_fields(detail, accent, width))
        elif sum(column_widths) + 3 * len(detail.columns) + 1 > width - 4 and detail.rows:
            for index, row in enumerate(detail.rows, start=1):
                values = [
                    (column, cell_text(column, value))
                    for column, value in zip(detail.columns, row)
                    if value not in {UNKNOWN, ""}
                ]
                fields = _fields(values, accent, width)
                fields.title = Text(f"{detail.title} · {index}", style=f"bold {accent}")
                details.append(fields)
        else:
            table = Table(
                title=Text(detail.title, style=f"bold {accent}"),
                header_style=f"bold {accent}",
                border_style=accent,
                expand=True,
            )
            for column, minimum in zip(detail.columns, column_widths):
                table.add_column(column, overflow="fold", min_width=minimum if detail.rows else None)
            for row in detail.rows:
                table.add_row(*(cell_text(column, value) for column, value in zip(detail.columns, row)))
            details.append(table)
        if detail.omitted:
            details.append(Text(f"… {detail.omitted} more; use --section {card.section} for all", style="dim"))
    return details


def _panel(card: Card, content: Group) -> Panel:
    accent = section_style(card.section)
    return Panel(content, title=Text(card.title, style=f"bold {accent}"), border_style=accent, expand=True)


def _summary_row(cards: Sequence[Card], columns: int, console: Console, width: int) -> Table:
    """Use fixed column widths and measured heights to align every border."""
    available = width - COLUMN_GAP * (columns - 1)
    widths = [available // columns + (index < available % columns) for index in range(columns)]
    panels = [_panel(card, Group(_summary(card, column_width))) for card, column_width in zip(cards, widths)]
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
    return row


def render(model: DisplayModel, console: Console) -> None:
    """Show a responsive summary grid, keeping detailed tables at full width."""
    width = console.width
    content: List[ConsoleRenderable] = []
    heading = Text(model.title, style="bold bright_cyan")
    if model.subtitle:
        heading.append(" · ", style="dim blue")
        heading.append(model.subtitle, style="blue")
    content.append(Rule(heading, style="bright_blue"))
    columns = min(MAX_COLUMNS, (width + COLUMN_GAP) // (CARD_MIN_WIDTH + COLUMN_GAP), len(model.cards))
    if columns > 1:
        content.extend(
            _summary_row(model.cards[start : start + columns], columns, console, width)
            for start in range(0, len(model.cards), columns)
        )
        content.extend(_panel(card, Group(*_details(card, width))) for card in model.cards if card.tables)
    else:
        content.extend(_panel(card, Group(_summary(card, width), *_details(card, width))) for card in model.cards)

    if model.warnings:
        content.append(
            Panel(
                Text("\n".join(model.warnings), style="yellow"),
                title=Text("Warnings", style="bold yellow"),
                border_style="yellow",
            )
        )
    if model.footer:
        content.append(Text(model.footer, style="dim blue", justify="right"))
    console.print(Group(*content), width=width)
