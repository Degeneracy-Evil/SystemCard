"""Rich terminal rendering for SystemCard display models."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from systemcard.model import DisplayModel


def render(model: DisplayModel, console: Console) -> None:
    """Render a display model using panels that gracefully fit narrow terminals."""
    console.print(Panel.fit(Text(model.title, style="bold cyan"), subtitle=model.subtitle))
    for card in model.cards:
        table = Table.grid(padding=(0, 1))
        table.add_column(style="dim", justify="right")
        table.add_column()
        for label, value in card.rows:
            table.add_row(label, value)
        console.print(Panel(table, title=card.title, expand=False))

    if model.warnings:
        console.print(Panel("\n".join(model.warnings), title="Warnings", style="yellow"))
