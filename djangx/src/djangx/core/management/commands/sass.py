import hashlib
import json
from pathlib import Path
from typing import Any, ClassVar

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django_dart_sass.registry import compile_string

from ...apps import CoreConfig
from ...utils.commands import Verbosity
from ...utils.console import Style, cprint


class Command(BaseCommand):
    help: str = "Manage Sass: --build compiles Bootstrap (chosen via SASS_INCLUDES) into custom.css."

    SCSS_DIR: ClassVar[Path] = CoreConfig.resources / "vendor" / "bootstrap" / "scss"
    OUT: ClassVar[Path] = (
        CoreConfig.static / "vendor" / "bootstrap" / "css" / "custom.css"
    )
    STAMP: ClassVar[Path] = OUT.with_name(".settings-hash")

    # Settings whose change should trigger a recompile.
    WATCHED_SETTINGS: ClassVar[tuple[str, ...]] = (
        "SASS_INCLUDES",
        "SASS_DART_OPTIONS",
        "SASS_CUSTOM_CODE",
    )

    # Bootstrap 6 partials in `bootstrap.scss` order. `root` and the trailing
    # `helpers` / `utilities/api` are always included, so they are not listed here.
    COMPONENTS: ClassVar[list[str]] = [
        "content", "layout", "forms", "buttons", "accordion", "alert", "avatar",
        "badge", "breadcrumb", "chip", "card", "carousel", "datepicker", "dialog",
        "menu", "list-group", "nav", "nav-overflow", "navbar", "drawer",
        "pagination", "placeholder", "popover", "progress", "spinner", "stepper",
        "toasts", "tooltip", "transitions",
    ]  # fmt: skip

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "-b",
            "--build",
            action="store_true",
            help="Compile Bootstrap into custom.css.",
        )
        parser.add_argument(
            "--if-changed",
            action="store_true",
            help="With --build, skip compiling when the watched settings are unchanged.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["build"]:
            raise CommandError("Nothing to do. Pass --build (-b).")
        self.build(
            if_changed=options["if_changed"],
            verbosity=Verbosity(options["verbosity"]),
        )

    def build(
        self,
        *,
        if_changed: bool = False,
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        """Compile SCSS into `OUT`, optionally skipping when settings are unchanged.

        Examples::

            self.build(if_changed=True)  # no output if nothing changed
        """
        fingerprint = self.fingerprint()
        if (
            if_changed
            and self.OUT.exists()
            and self.STAMP.exists()
            and self.STAMP.read_text() == fingerprint
        ):
            return

        result = compile_string(
            self.build_source(
                getattr(settings, "SASS_INCLUDES", None),
                getattr(settings, "SASS_CUSTOM_CODE", None),
            ),
            dict(getattr(settings, "SASS_DART_OPTIONS", None) or {}),
        )
        self.OUT.parent.mkdir(parents=True, exist_ok=True)
        self.OUT.write_text(data=result["css"], encoding="utf-8")
        self.STAMP.write_text(fingerprint)
        cprint(
            [
                ("Compiled SCSS to ", Style.SUCCESS),
                (str(self.OUT), Style.HIGHLIGHT),
            ],
            verbosity=verbosity,
        )

    def build_source(
        self, includes: list[str] | None, custom_code: str | None = None
    ) -> str:
        """Return the SCSS entry source for the chosen Bootstrap parts.

        `None` includes all of Bootstrap (option A). Any `custom_code` is appended
        after the Bootstrap imports.

        Examples::

            self.build_source(["buttons"])  # "@use 'file:///.../root';\\n@use 'file:///.../buttons';\\n..."
            self.build_source(["buttons"], ".x { color: red; }")  # same, plus the custom rule at the end
        """
        if includes is None:
            lines = [f"@use '{(self.SCSS_DIR / 'bootstrap').as_uri()}';"]
        else:
            unknown = sorted(set(includes) - set(self.COMPONENTS))
            if unknown:
                raise CommandError(f"Unknown SASS_INCLUDES: {', '.join(unknown)}")

            chosen = sorted(set(includes), key=self.COMPONENTS.index)
            names = ["root", *chosen, "helpers", "utilities/api"]
            lines = [f"@use '{(self.SCSS_DIR / n).as_uri()}';" for n in names]

        if custom_code and custom_code.strip():
            lines.append(custom_code.strip())

        return "\n".join(lines)

    def fingerprint(self) -> str:
        """Return a hash of the watched settings.

        Examples::

            self.fingerprint()  # "9f2c...e1"
        """
        data = {name: getattr(settings, name, None) for name in self.WATCHED_SETTINGS}
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()
