import os
import shutil
from os.path import expandvars
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

from ...utils.commands import NonSystemCheckedCommand, Verbosity
from ...utils.console import Style, cprint
from ...utils.exit import Exit
from ...utils.permissions import PermissionAction, permission_message


class Command(NonSystemCheckedCommand):
    help = "Move or rename a file or folder."

    def add_arguments(self, parser) -> None:
        parser.add_argument("source", help="File or folder to move.")
        parser.add_argument("destination", help="Destination path or directory.")

    def handle(self, *args, **options) -> None:
        source = self._absolute_path(options["source"])
        destination = self._absolute_path(options["destination"])
        verbosity = Verbosity(options["verbosity"])

        if not source.exists() and not source.is_symlink():
            raise CommandError(f"Source does not exist: {source}")
        if not (source.is_file() or source.is_dir() or source.is_symlink()):
            raise CommandError(f"Source is not a file or folder: {source}")

        target = destination / source.name if destination.is_dir() else destination
        if os.path.normcase(os.path.abspath(source)) == os.path.normcase(
            os.path.abspath(target)
        ):
            raise CommandError("Source and destination are the same path.")
        if (
            source.is_dir()
            and not source.is_symlink()
            and target.is_relative_to(source)
        ):
            raise CommandError("A folder cannot be moved into itself.")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                shutil.move(source, target)
            else:
                call_command(
                    "copy",
                    str(source),
                    str(target),
                    verbosity=Verbosity.QUIET,
                )
                self._remove_source(source)
        except PermissionError as error:
            cprint(
                permission_message(PermissionAction.MOVE, target),
                Style.ERROR,
            )
            raise SystemExit(Exit.ERROR) from error

        cprint(
            [
                ("Moved ", Style.SUCCESS),
                (str(source), Style.HIGHLIGHT),
                (" to ", Style.SUCCESS),
                (str(target), Style.HIGHLIGHT),
            ],
            verbosity=verbosity,
        )

    @staticmethod
    def _absolute_path(value: str) -> Path:
        return Path(expandvars(value)).expanduser().absolute()

    @staticmethod
    def _remove_source(source: Path) -> None:
        options = {
            "base_dir": str(source.parent),
            "verbosity": Verbosity.QUIET,
        }
        if source.is_dir():
            options["folder_name"] = source.name
        else:
            options["file_name"] = source.name

        try:
            call_command("rm", **options)
        except SystemExit as error:
            cprint(
                f"Copied to the destination, but could not remove {source}; both paths may remain.",
                Style.ERROR,
            )
            raise SystemExit(Exit.ERROR) from error
