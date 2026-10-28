"""`createmanage`: write the project's `manage.py`, which Vercel reads for the settings module."""

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

MANAGE_PY: str = '''\
"""Vercel reads this for the settings module. For development, run `djangx` or `djx` instead."""

from os import environ

from djangx.core.utils import DJANGO_SETTINGS_MODULE

assert DJANGO_SETTINGS_MODULE is not None
environ.setdefault(key="DJANGO_SETTINGS_MODULE", value=DJANGO_SETTINGS_MODULE)

if __name__ == "__main__":
    from sys import argv

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
'''


class Command(BaseCommand):
    help = "Write `manage.py` to `BASE_DIR`, skipping it if it exists unless `--overwrite` is given."

    def add_arguments(self, parser: CommandParser) -> None:
        """Add the `--overwrite` flag.

        Examples::

            djx createmanage --overwrite
        """
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace `manage.py` if it already exists.",
        )

    def handle(self, *args: Any, overwrite: bool, **options: Any) -> None:
        """Write `BASE_DIR/manage.py`; an existing file is only replaced with `overwrite`.

        Examples::

            djx createmanage  # "Wrote /home/kevin/olyv/manage.py"
            djx createmanage  # "/home/kevin/olyv/manage.py already exists; use --overwrite to replace it."
        """
        file = settings.BASE_DIR / "manage.py"
        if file.exists() and not overwrite:
            self.stdout.write(
                self.style.WARNING(
                    f"{file} already exists; use --overwrite to replace it."
                )
            )
            return
        file.write_text(MANAGE_PY)
        self.stdout.write(self.style.SUCCESS(f"Wrote {file}"))
