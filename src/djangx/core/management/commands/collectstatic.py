"""``djx collectstatic``: Django's `collectstatic`, without Sass sources, plus a Sass build.

The raw `.scss`/`.sass` files are not copied to `STATIC_ROOT`. Instead, once the
files are collected, `djx sass --build` compiles them into `STATIC_ROOT`. The build
runs after `--clear` has emptied the folder, so the compiled CSS is never wiped.

Examples::

    djx collectstatic  # never asks for confirmation
    djx collectstatic --interactive  # ask before overwriting, like Django
    djx collectstatic --install-sass  # install Sass first if it is missing
    djx collectstatic --no-sass  # skip the Sass build

Sass is not installed automatically (unlike `djx runserver`), so a deploy never
downloads Node mid-build. Install it beforehand with `djx sass --install`, set
`SASS_EXECUTABLE`, or pass `--install-sass`.
"""

from typing import Any

from django.contrib.staticfiles.management.commands.collectstatic import (
    Command as CollectStaticCommand,
)
from django.core.management import call_command

from ...utils.sass import Sass


class Command(CollectStaticCommand):
    def add_arguments(self, parser: Any) -> None:
        """Add Django's options and `--no-sass`."""
        super().add_arguments(parser)
        # `STATIC_ROOT` is generated output, so do not ask for confirmation by default.
        parser.set_defaults(interactive=False)
        parser.add_argument(
            "--interactive",
            action="store_true",
            dest="interactive",
            help="Ask for confirmation before overwriting or clearing STATIC_ROOT.",
        )
        parser.add_argument(
            "--no-sass",
            action="store_true",
            help="Do not build Sass after collecting static files.",
        )
        parser.add_argument(
            "--install-sass",
            action="store_true",
            help="Install Sass in the virtual environment if it is not found.",
        )

    def set_options(self, **options: Any) -> None:
        """Apply Django's options, then also ignore `*.scss` and `*.sass`.

        These patterns are added even with `--no-default-ignore`, which only turns
        off Django's own defaults (`CVS`, `.*`, `*~`).
        """
        super().set_options(**options)
        self.ignore_patterns = [*self.ignore_patterns, *Sass.SASS_PATTERNS]
        self.build_sass: bool = not options["no_sass"]
        self.install_sass: bool = options["install_sass"]

    def collect(self) -> dict[str, list[str]]:
        """Collect static files, then build Sass (skipped for `--dry-run` and `--no-sass`)."""
        collected = super().collect()
        if self.build_sass and not self.dry_run:
            call_command(
                "sass",
                build=True,
                auto_install=self.install_sass,
                verbosity=self.verbosity,
            )
        return collected
