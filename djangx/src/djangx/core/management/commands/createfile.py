from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from ...utils.files import TEMPLATES, write_file


class Command(BaseCommand):
    help = "Write `manage.py` (to BASE_DIR) and/or `asgi.py` / `wsgi.py` (to APP_DIR); existing files are kept unless `--overwrite`."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add `kind`, `--all`, `--dir` and `--overwrite`.

        Examples::

            djx createfile manage
            djx createfile asgi --dir app --overwrite
            djx createfile --all
        """
        parser.add_argument("kind", nargs="?", choices=list(TEMPLATES))
        parser.add_argument(
            "-a", "--all", dest="all_kinds", action="store_true",
            help="Write manage.py, asgi.py and wsgi.py to their default folders.",
        )  # fmt: skip
        parser.add_argument(
            "--dir", type=Path,
            help="Parent folder (default: BASE_DIR for manage, APP_DIR otherwise).",
        )  # fmt: skip
        parser.add_argument(
            "--overwrite", action="store_true", help="Replace files that already exist."
        )

    def handle(
        self,
        *args: Any,
        kind: str | None,
        all_kinds: bool,
        dir: Path | None,
        overwrite: bool,
        **options: Any,
    ) -> None:
        """Write the chosen file, or all three with `--all`.

        Examples::

            djx createfile --all  # "Wrote .../manage.py", "Wrote .../app/asgi.py", ...
        """
        if all_kinds == (kind is not None):
            raise CommandError("Pass either a kind or --all.")
        if all_kinds and dir:
            raise CommandError("--dir can't be used with --all.")

        for name in TEMPLATES if all_kinds else [kind]:
            assert name is not None
            parent = dir or (settings.BASE_DIR if name == "manage" else settings.APP_DIR)
            file = parent / f"{name}.py"
            match write_file(name, parent, overwrite=overwrite):
                case "wrote":
                    self.stdout.write(self.style.SUCCESS(f"Wrote {file}"))
                case "same":
                    self.stdout.write(f"{file} is already up to date.")
                case "differs":
                    self.stdout.write(
                        self.style.WARNING(
                            f"{file} differs from the template; use --overwrite to replace it."
                        )
                    )
