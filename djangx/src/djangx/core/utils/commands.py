"""Command base classes, command discovery and helpers for generated files."""

import ast
import re
from pathlib import Path
from typing import Any, ClassVar, Literal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from ..apps import CoreConfig
from .console import Style, cprint

__all__: list[str] = [
    "HELP_COMMANDS",
    "PROJECT_COMMANDS",
    "SCRIPT_COMMANDS",
    "FileCommand",
    "NonSystemCheckedCommand",
    "ServerFileCommand",
]

Result = Literal["wrote", "same", "differs"]

ENTRYPOINT: str = """\
from os import environ

from django.core.{kind} import get_{kind}_application
from djangx.core.utils.conf import settings_module

environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module())
application = get_{kind}_application()
"""


class NonSystemCheckedCommand(BaseCommand):
    """Base for commands that skip Django system checks."""

    requires_system_checks = ()


class FileCommand(BaseCommand):
    """Base for commands that create (default) or remove one generated file.

    Subclasses set `filename` and `template`, and may override `default_dir`.

    Examples::

        djx createmanage
        djx createdeploy --overwrite
        djx createdeploy --remove
    """

    filename: ClassVar[str]
    template: ClassVar[str] = ""

    @staticmethod
    def _write(file: Path, text: str, *, overwrite: bool = False) -> Result:
        """Write `text` to `file`; an existing file is kept unless `overwrite`.

        Examples::

            FileCommand._write(APP_DIR / "wsgi.py", text)  # "wrote"
            FileCommand._write(APP_DIR / "wsgi.py", text)  # "same" (matches `text`)
            FileCommand._write(BASE_DIR / "manage.py", text)  # "differs" (left alone)
        """
        if file.exists() and not overwrite:
            return "same" if file.read_text() == text else "differs"
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        return "wrote"

    @staticmethod
    def _remove(file: Path) -> bool:
        """Delete `file`; return whether it existed.

        Examples::

            FileCommand._remove(APP_DIR / "wsgi.py")  # True
            FileCommand._remove(APP_DIR / "wsgi.py")  # False
        """
        if not file.is_file():
            return False
        file.unlink()
        return True

    def default_dir(self) -> Path:
        """Return the default folder for the generated file."""
        return settings.APP_DIR

    def content(self) -> str:
        """Return the text written when creating the file."""
        return self.template

    def target_dir(self, options: dict[str, Any]) -> Path:
        """Return `--dir`, or the default folder."""
        return options["dir"] or self.default_dir()

    def add_arguments(self, parser: CommandParser) -> None:
        """Add `--remove`, `--overwrite` and `--dir`."""
        parser.add_argument(
            "-r", "--remove", action="store_true", help=f"Delete {self.filename}."
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace the file if it exists.",
        )
        parser.add_argument(
            "--dir", type=Path, help="Folder of the file (default depends on the file)."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Remove the file, or create it unless an existing file is preserved."""
        file = self.target_dir(options) / self.filename

        if options["remove"]:
            if self._remove(file):
                cprint(f"Removed {file}", Style.SUCCESS)
            else:
                cprint(f"{file} does not exist.", Style.WARNING)
            return

        match self._write(file, self.content(), overwrite=options["overwrite"]):
            case "wrote":
                cprint(f"Wrote {file}", Style.SUCCESS)
            case "same":
                cprint(f"{file} is already up to date.")
            case "differs":
                cprint(
                    f"{file} differs from the template; use --overwrite to replace it.",
                    Style.WARNING,
                )


class ServerFileCommand(FileCommand):
    """Base for `createasgi`/`createwsgi`; also sets or resets the application setting.

    `--set` cannot be combined with `--remove`. `--reset` requires `--remove`, and
    `--set` and `--reset` are mutually exclusive.

    Examples::

        djx createasgi --set  # write app/asgi.py, set ASGI_APPLICATION to app.asgi.application
        djx createasgi --remove --reset  # delete it, set ASGI_APPLICATION to djangx.core.management.asgi.application
        djx createwsgi --set
    """

    @staticmethod
    def _set_setting(name: str, value: str) -> bool:
        """Point `name` in `APP_DIR/settings.py` at `value`; return whether the file changed.

        Examples::

            ServerFileCommand._set_setting("WSGI_APPLICATION", "app.wsgi.application")  # True
            ServerFileCommand._set_setting("WSGI_APPLICATION", "app.wsgi.application")  # False (already set)
        """
        from django.core.management.base import CommandError

        file = settings.APP_DIR / "settings.py"
        text = file.read_text()
        new, count = re.subn(
            rf"^{name}[ :=].*$",
            f'{name}: str = "{value}"',
            text,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise CommandError(f"Expected one {name} line in {file}, found {count}.")
        if new == text:
            return False
        file.write_text(new)
        return True

    @property
    def kind(self) -> str:
        """Return `"asgi"` or `"wsgi"`."""
        return self.filename.removesuffix(".py")

    @property
    def setting(self) -> str:
        """Return the settings variable, e.g. `"ASGI_APPLICATION"`."""
        return f"{self.kind.upper()}_APPLICATION"

    def content(self) -> str:
        """Return the entry-point template for this command."""
        return ENTRYPOINT.format(kind=self.kind)

    def add_arguments(self, parser: CommandParser) -> None:
        """Add file options and mutually exclusive `--set`/`--reset` options."""
        super().add_arguments(parser)
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--set",
            action="store_true",
            help=f"Point {self.setting} at the project's {self.filename}.",
        )
        group.add_argument(
            "--reset",
            action="store_true",
            help=f"Point {self.setting} back at djangX's built-in {self.filename}.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Validate options, create or remove the file, and update its setting if requested."""
        from django.core.management.base import CommandError

        if options["set"] and options["remove"]:
            raise CommandError("--set cannot be used with --remove.")
        if options["reset"] and not options["remove"]:
            raise CommandError("--reset can only be used with --remove.")

        super().handle(*args, **options)

        if options["set"]:
            value = f"{self.target_dir(options).name}.{self.kind}.application"
        elif options["reset"]:
            value = f"djangx.core.management.{self.kind}.application"
        else:
            return

        if self._set_setting(self.setting, value):
            cprint(f"Set {self.setting} to {value}", Style.SUCCESS)
        else:
            cprint(f"{self.setting} is already {value}.")


def _is_script(file: Path) -> bool:
    """Return whether `file` has a top-level `Command` with the direct base `NonSystemCheckedCommand`.

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
"""Every other command: {"createasgi", "createdeploy", "createmanage", "createwsgi", "runserver", "sass", "startapp"}."""
