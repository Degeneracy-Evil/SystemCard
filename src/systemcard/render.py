"""Rich terminal rendering for SystemCard display models."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from systemcard.model import DisplayModel
from systemcard.theme import cell_text, section_style, value_text


def render(model: DisplayModel, console: Console) -> None:
    """Render a display model using panels that gracefully fit narrow terminals."""
    console.print(
        Panel.fit(
            Text(model.title, style="bold bright_cyan"),
            subtitle=Text(model.subtitle, style="blue"),
            border_style="bright_blue",
        )
    )
    for card in model.cards:
        accent = section_style(card.section)
        summary = Table.grid(padding=(0, 1), expand=True)
        summary.add_column(style=accent, justify="right", no_wrap=True)
        summary.add_column(ratio=1, overflow="fold")
        for label, value in card.rows:
            summary.add_row(Text(label, style=f"bold {accent}"), value_text(label, value))

        details: list[Table] = []
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
                table.add_row(*(cell_text(column, value) for column, value in zip(detail.columns, row, strict=True)))
            if detail.omitted:
                table.caption = f"… {detail.omitted} more; use --section {card.section} for all"
                table.caption_style = "dim"
            details.append(table)
        console.print(
            Panel(
                Group(summary, *details),
                title=Text(card.title, style=f"bold {accent}"),
                border_style=accent,
                expand=True,
            )
        )

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
