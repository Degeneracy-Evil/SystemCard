"""Reviewable terminal snapshots use synthetic, fixed data rather than local hardware."""

import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from rich.console import Console

from systemcard.model import build
from systemcard.render import render

ROOT = Path(__file__).parent


@pytest.mark.parametrize("case,width", [("default", 80), ("compact", 80), ("narrow", 40), ("missing", 80)])
def test_display_snapshot(case: str, width: int) -> None:
    snapshot: dict[str, Any] = (
        {"info": {}} if case == "missing" else json.loads((ROOT / "fixtures/container-mig.json").read_text())
    )
    output = StringIO()
    render(
        build(snapshot, compact=case == "compact"),
        Console(file=output, width=width, no_color=True, force_terminal=False),
    )
    assert output.getvalue() == (ROOT / "snapshots" / f"{case}.txt").read_text()
