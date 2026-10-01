"""Tests for Rich rendering."""

import re
from io import StringIO

import pytest
from rich.console import Console

from systemcard.model import Card, DetailTable, DisplayModel
from systemcard.render import render


def test_render_rejects_mismatched_detail_rows() -> None:
    model = DisplayModel(
        title="SystemCard",
        subtitle="node-1",
        cards=(Card("system", "System", (), (DetailTable("Devices", ("Name", "State"), (("GPU",),)),)),),
        warnings=(),
    )
    with pytest.raises(ValueError, match="row does not match"):
        render(model, Console(file=StringIO()))


def test_render_prints_cards_and_warnings() -> None:
    output = StringIO()
    console = Console(file=output, no_color=True, force_terminal=False, width=60)
    model = DisplayModel(
        title="SystemCard",
        subtitle="node-1",
        cards=(
            Card(
                "system",
                "System",
                (("Host", "node-1"),),
                (DetailTable("Devices", ("Name",), (("GPU",),), omitted=2),),
            ),
        ),
        warnings=("partial collection",),
        footer="Sysal 0.0.8",
    )

    render(model, console)

    rendered = output.getvalue()
    assert "SystemCard" in rendered
    assert "node-1" in rendered
    assert "partial collection" in rendered
    assert "2 more" in rendered
    assert "Sysal 0.0.8" in rendered
    assert "\x1b[" not in rendered


def test_render_emits_semantic_colors_when_enabled() -> None:
    output = StringIO()
    console = Console(file=output, color_system="standard", force_terminal=True, no_color=False, width=80)
    model = DisplayModel(
        title="SystemCard",
        subtitle="node-1",
        cards=(
            Card(
                "network",
                "Network",
                (("Temperature", "75.0 °C"),),
                (DetailTable("Interfaces", ("Name", "State"), (("eth0", "UP"), ("eth1", "DOWN"))),),
            ),
        ),
        warnings=(),
    )

    render(model, console)

    rendered = output.getvalue()
    assert "\x1b[" in rendered
    assert re.search(r"\x1b\[[0-9;]*32m", rendered)
    assert re.search(r"\x1b\[[0-9;]*31m", rendered)
