import ast
from pathlib import Path

from django.core.management.base import BaseCommand

from ..apps import CoreConfig

__all__: list[str] = [
    "HELP_COMMANDS",
    "PROJECT_COMMANDS",
    "SCRIPT_COMMANDS",
    "NonSystemCheckedCommand",
]


class NonSystemCheckedCommand(BaseCommand):
    requires_system_checks = ()


def _is_script(file: Path) -> bool:
    """Return whether `file` defines a `Command` that subclasses `NonSystemCheckedCommand`.

    Parsed with `ast`, not imported, so no command module loads (or imports this one back).

    Examples::

        _is_script(Path("rm.py"))  # True
        _is_script(Path("sass.py"))  # False
    """
    tree = ast.parse(file.read_text(encoding="utf-8"))
    return any(
        isinstance(node, ast.ClassDef)
        and node.name == "Command"
        and any(
            isinstance(base, ast.Name) and base.id == "NonSystemCheckedCommand"
            for base in node.bases
        )
        for node in tree.body
    )


_FILES: list[Path] = sorted(
    file
    for file in (CoreConfig.base / "management" / "commands").glob("*.py")
    if not file.stem.startswith("_")
)

HELP_COMMANDS: set[str] = {"help", "-h"}

SCRIPT_COMMANDS: set[str] = {file.stem for file in _FILES if _is_script(file)}
"""Commands that subclass `NonSystemCheckedCommand`: {"copy", "platform", "random", "rm"}."""

PROJECT_COMMANDS: set[str] = {file.stem for file in _FILES} - SCRIPT_COMMANDS
"""Every other command: {"createfile", "runserver", "sass", "startapp"}."""
