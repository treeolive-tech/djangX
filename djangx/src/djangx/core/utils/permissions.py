"""Cross-platform permission diagnostics and safe deletion retries."""

import stat
from collections.abc import Callable
from enum import StrEnum
from os import name as os_name
from pathlib import Path

from .platform import Platform

__all__: list[str] = [
    "PermissionAction",
    "make_writable_for_delete",
    "permission_message",
    "retry_readonly_delete",
]


class PermissionAction(StrEnum):
    """Filesystem access required by a file operation."""

    READ_SOURCE = "read from source"
    WRITE_DESTINATION = "write to destination"
    DELETE = "delete"
    MOVE = "move"


def permission_message(action: PermissionAction, path: str | Path) -> str:
    """Describe a permission failure with platform-appropriate guidance."""
    if _platform_name() == "windows":
        hint = "Check access control and close programs that may be using the path."
    elif action is PermissionAction.READ_SOURCE:
        hint = "Check read access to the source and traversal access to its parent folders."
    elif action is PermissionAction.WRITE_DESTINATION:
        hint = "Check write access to the destination and its parent folders."
    elif action is PermissionAction.MOVE:
        hint = "Check write and execute access to the source and destination parent folders."
    else:
        hint = "Check write and execute access to the containing folder."

    return f"Permission denied while trying to {action.value} '{path}'. {hint}"


def make_writable_for_delete(path: Path) -> bool:
    """Clear a Windows read-only attribute; never alter POSIX mode bits."""
    if _platform_name() != "windows" or path.is_symlink():
        return False

    try:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
    except OSError:
        return False
    return True


def retry_readonly_delete(
    function: Callable[[str], object], path: str, error: BaseException
) -> None:
    """Retry shutil deletion callbacks after clearing a Windows read-only flag."""
    target = Path(path)
    if not isinstance(error, PermissionError) or not make_writable_for_delete(target):
        raise error
    function(path)


def _platform_name() -> str:
    try:
        return Platform().os_name
    except (OSError, ValueError):
        return "windows" if os_name == "nt" else "unknown"
