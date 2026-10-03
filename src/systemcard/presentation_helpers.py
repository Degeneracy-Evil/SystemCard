"""Small helpers shared by hardware card builders."""

from typing import Any, List, Mapping

from systemcard.formatters import UNKNOWN, text
from systemcard.schema import list_value


def joined(values: object, separator: str = ", ") -> str:
    rendered = [text(value) for value in list_value(values) if text(value) != UNKNOWN]
    return separator.join(rendered) or UNKNOWN


def limited(items: List[Mapping[str, Any]], detailed: bool, limit: int) -> List[Mapping[str, Any]]:
    return items if detailed else items[:limit]
