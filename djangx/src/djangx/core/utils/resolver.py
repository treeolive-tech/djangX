"""Helpers that coerce values into booleans, string lists and paths."""

from collections.abc import Callable
from os.path import expandvars
from pathlib import Path
from typing import Any

__all__: list[str] = ["to_bool", "to_list_of_str", "to_path"]


def to_bool(value: str | bool) -> bool:
    """Return ``True`` for a ``True`` bool or ``"true"``, ``"1"``, ``"yes"``, ``"on"`` (any case).

    Examples::

        to_bool(True)  # True
        to_bool("YES")  # True
        to_bool("0")  # False
        to_bool("maybe")  # False
    """
    if isinstance(value, bool):
        return value
    return value.lower() in ("true", "1", "yes", "on")


def to_list_of_str(
    value: Any, transform: Callable[[str], str] | None = None
) -> list[str]:
    """Turn a list or comma-separated string into a list of strings; anything else is ``[]``.

    Examples::

        to_list_of_str("a, b, c")  # ["a", "b", "c"]
        to_list_of_str("a,,b")  # ["a", "b"]
        to_list_of_str([1, 2, 3])  # ["1", "2", "3"]
        to_list_of_str("A,B", str.lower)  # ["a", "b"]
        to_list_of_str(None)  # []
    """
    if isinstance(value, list):
        items = [str(item) for item in value]
    elif isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    else:
        items = []
    return [transform(item) for item in items] if transform else items


def to_path(value: str | Path, resolve: bool = True) -> Path:
    """Expand ``$VAR`` and ``~`` in `value` and return a ``Path``, made absolute if `resolve`.

    Examples::

        to_path("~/projects")  # Path("/home/user/projects")
        to_path("$HOME/data")  # Path("/home/user/data")
        to_path("/tmp/../etc", resolve=False)  # Path("/tmp/../etc")
    """
    path = Path(expandvars(str(value))).expanduser()
    return path.resolve() if resolve else path
