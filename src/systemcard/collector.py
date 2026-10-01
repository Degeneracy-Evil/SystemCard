"""Native Sysal collection boundary."""

from typing import Any, Dict, Mapping


class CollectionError(RuntimeError):
    """A Sysal snapshot could not be collected."""


def collect(scope: str = "default") -> Dict[str, Any]:
    """Collect a JSON-compatible snapshot through the native adapter."""
    try:
        from systemcard import _native
    except ImportError as error:
        raise CollectionError(
            "The SystemCard native extension could not be loaded. "
            "Reinstall SystemCard in an environment with its Sysal build dependencies."
        ) from error

    try:
        snapshot = _native.collect(scope)
    except (RuntimeError, ValueError) as error:
        raise CollectionError(str(error)) from error

    if not isinstance(snapshot, Mapping):
        raise CollectionError("Sysal returned an invalid snapshot.")
    return dict(snapshot)
