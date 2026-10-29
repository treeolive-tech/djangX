from pathlib import Path
from typing import Any, Literal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

Result = Literal["wrote", "same", "differs"]

MANAGE_PY: str = '''\
"""Vercel reads this for the settings module. For development, run `djangx` or `djx` instead."""

from os import environ

from djangx.core.utils import settings_module

environ.setdefault(key="DJANGO_SETTINGS_MODULE", value=settings_module())

if __name__ == "__main__":
    from sys import argv

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
'''

ENTRYPOINT: str = """\
from os import environ

from django.core.{kind} import get_{kind}_application
from djangx.core.utils import settings_module

environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module())
application = get_{kind}_application()
"""

DEPLOY_YML: str = '''\
name: Build deploy branch

on:
  push:
    branches: [main]

permissions:
  contents: write

jobs:
  deploy-branch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - uses: astral-sh/setup-uv@v10.0.1

      - name: Generate manage.py, asgi.py and wsgi.py
        run: uv run djx createfile manage asgi wsgi --overwrite

      - name: Point settings at the generated files
        run: |
          python3 - <<'PY'
          import re
          from pathlib import Path

          settings_file = Path("app/settings.py")
          text = settings_file.read_text()
          for name in ("ASGI", "WSGI"):
              text, count = re.subn(
                  rf"^{name}_APPLICATION[ :=].*$",
                  f'{name}_APPLICATION: str = "app.{name.lower()}.application"',
                  text,
                  flags=re.MULTILINE,
              )
              assert count == 1, f"expected one {name}_APPLICATION line in {settings_file}"
          settings_file.write_text(text)
          PY

      - name: Push to the deploy branch
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git switch -C deploy
          git add -f manage.py app/asgi.py app/wsgi.py app/settings.py
          git commit --allow-empty -m "Deploy build of ${GITHUB_SHA::7}"
          git push --force origin deploy
'''

FILES: dict[str, tuple[str, str]] = {
    "manage": ("manage.py", MANAGE_PY),
    "asgi": ("asgi.py", ENTRYPOINT.format(kind="asgi")),
    "wsgi": ("wsgi.py", ENTRYPOINT.format(kind="wsgi")),
    "deploy": ("deploy.yml", DEPLOY_YML),
}


class Command(BaseCommand):
    help = "Write `manage.py`, `asgi.py`, `wsgi.py` and/or `deploy.yml`; existing files are kept unless `--overwrite`."

    @staticmethod
    def _default_dir(kind: str) -> Path:
        """Return the folder `kind` is written to unless `--dir` is given.

        Examples::

            Command._default_dir("manage")  # Path("/home/kevin/olyv")
            Command._default_dir("wsgi")  # Path("/home/kevin/olyv/app")
            Command._default_dir("deploy")  # Path("/home/kevin/olyv/.github/workflows")
        """
        match kind:
            case "manage":
                return settings.BASE_DIR
            case "deploy":
                return settings.BASE_DIR / ".github" / "workflows"
            case _:
                return settings.APP_DIR

    @staticmethod
    def _write(kind: str, dir: Path, *, overwrite: bool = False) -> Result:
        """Write the `kind` file into `dir`; an existing file is kept unless `overwrite`.

        Examples::

            Command._write("wsgi", APP_DIR)  # "wrote"
            Command._write("wsgi", APP_DIR)  # "same" (already there, matches the template)
            Command._write("manage", BASE_DIR)  # "differs" (user edited it; left alone)
            Command._write("manage", BASE_DIR, overwrite=True)  # "wrote"
        """
        filename, text = FILES[kind]
        file = dir / filename
        if file.exists() and not overwrite:
            return "same" if file.read_text() == text else "differs"
        dir.mkdir(parents=True, exist_ok=True)
        file.write_text(text)
        return "wrote"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add `kinds`, `--dir` and `--overwrite`.

        Examples::

            djx createfile manage asgi wsgi
            djx createfile deploy --overwrite
            djx createfile asgi --dir app
        """
        parser.add_argument(
            "kinds", nargs="+", choices=list(FILES), help="Which files to write."
        )
        parser.add_argument(
            "--dir", type=Path,
            help="Parent folder for every file given (default: BASE_DIR for manage, APP_DIR for asgi/wsgi, .github/workflows for deploy).",
        )  # fmt: skip
        parser.add_argument(
            "--overwrite", action="store_true", help="Replace files that already exist."
        )

    def handle(
        self,
        *args: Any,
        kinds: list[str],
        dir: Path | None,
        overwrite: bool,
        **options: Any,
    ) -> None:
        """Write each kind and report whether it was written, unchanged or edited.

        Examples::

            djx createfile manage asgi  # "Wrote .../manage.py", "Wrote .../app/asgi.py"
        """
        for kind in kinds:
            parent = dir or self._default_dir(kind)
            file = parent / FILES[kind][0]
            match self._write(kind, parent, overwrite=overwrite):
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
