"""Native Sysal collection boundary."""

from typing import Any, Dict, List, Mapping, Optional

from systemcard.collection_plan import build_plan


class CollectionError(RuntimeError):
    """A Sysal snapshot could not be collected."""


def collect(scope: str = "default", sections: Optional[List[str]] = None) -> Dict[str, Any]:
    """Collect a JSON-compatible snapshot through the native adapter."""
    try:
        from systemcard import _native
    except ImportError as error:
        raise CollectionError(
            "The SystemCard native extension could not be loaded. "
            "Reinstall SystemCard in an environment with its Sysal build dependencies."
        ) from error

    try:
        plan = build_plan(scope, sections)
        snapshot = _native.collect(plan.domains, plan.filesystems, plan.sensors)
    except (ImportError, RuntimeError, ValueError) as error:
        raise CollectionError(str(error)) from error

    if not isinstance(snapshot, Mapping):
        raise CollectionError("Sysal returned an invalid snapshot.")
    return dict(snapshot)
