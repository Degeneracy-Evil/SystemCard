"""Small helpers shared by hardware card builders."""

from typing import Any, List, Mapping, Optional

from systemcard.formatters import UNKNOWN, text
from systemcard.schema import list_value


def joined(values: object, separator: str = ", ") -> str:
    rendered = [text(value) for value in list_value(values) if text(value) != UNKNOWN]
    return separator.join(rendered) or UNKNOWN


def limited(items: List[Mapping[str, Any]], detailed: bool, limit: int) -> List[Mapping[str, Any]]:
    return items if detailed else items[:limit]


def boolean_count(items: List[Mapping[str, Any]], field: str) -> Optional[int]:
    """Missing flags cannot be counted as false."""
    if any(not isinstance(item.get(field), bool) for item in items):
        return None
    return sum(item.get(field) is True for item in items)


def reported_count(*groups: object, partial: bool = False) -> str:
    """Count explicit report lists, labelling a sum with missing groups."""
    known = [group for group in groups if isinstance(group, list)]
    if not known:
        return UNKNOWN
    count = str(sum(len(group) for group in known))
    if len(known) != len(groups):
        return count + " (known portion)"
    return count + " (partial evidence)" if partial else count
