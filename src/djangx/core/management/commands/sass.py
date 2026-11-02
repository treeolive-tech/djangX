import shutil
import sys
from pathlib import Path
from typing import Any, ClassVar, Literal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...apps import CoreConfig
from ...utils.commands import Verbosity
from ...utils.console import Style, cprint
from ...utils.sass import Sass
from ...utils.string import fingerprint
from ...utils.version import Version


class Command(BaseCommand):
    help: str = (
        "Manage Sass: --build compiles Bootstrap (if BOOTSTRAP_INCLUDES is set) "
        "and the .scss/.sass files in your static folders"
    )

    BOOTSTRAP_DIR: ClassVar[Path] = CoreConfig.vendor / Sass.BOOTSTRAP_RELATIVE_DIR
    VENV_DIR: ClassVar[Path] = Path(sys.prefix)
    WATCHED_SETTINGS: ClassVar[tuple[str, ...]] = (
        "BOOTSTRAP_INCLUDES",
        "SASS_DART_OPTIONS",
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

    @property
    def out(self) -> Path:
        """Return the compiled Bootstrap CSS file."""
        return Sass.bootstrap_root() / Sass.CSS_OUTPUT_FILE

    @property
    def stamp(self) -> Path:
        """Return the settings-hash file, stored in the parent output folder."""
        return Sass.output_root() / Sass.STAMP_FILE

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "-b",
            "--build",
            action="store_true",
            help="Compile Bootstrap (if enabled) and the Sass files in your static folders.",
        )
        parser.add_argument(
            "--if-changed",
            action="store_true",
            help=(
                "With --build, skip work that is already up to date: Bootstrap is "
                "rebuilt only when its settings change, and your Sass files only when stale."
            ),
        )
        install_group = parser.add_mutually_exclusive_group()
        install_group.add_argument(
            "-i",
            "--install",
            action="store_true",
            help="Install Sass in the current Python virtual environment.",
        )
        install_group.add_argument(
            "--no-install",
            dest="auto_install",
            action="store_false",
            default=True,
            help="Do not automatically install Sass when building.",
        )
        parser.add_argument(
            "--sass-executable",
            metavar="PATH",
            help="Use this installed Sass executable instead of PATH or nodeenv.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        verbosity = Verbosity(options["verbosity"])

        if options["install"]:
            Sass.install_sass(self.VENV_DIR)
            cprint(
                [
                    ("Installed Sass in ", Style.SUCCESS),
                    (str(self.VENV_DIR), Style.HIGHLIGHT),
                ],
                verbosity=verbosity,
            )

        if options["build"]:
            self.build(
                if_changed=options["if_changed"],
                auto_install=options["auto_install"],
                sass_executable=options["sass_executable"],
                verbosity=verbosity,
            )
        elif not options["install"]:
            raise CommandError("Nothing to do. Pass --build (-b).")

    def build(
        self,
        *,
        if_changed: bool = False,
        auto_install: bool = True,
        sass_executable: str | Path | None = None,
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        """Compile Bootstrap (optional) and the project's Sass files under `Sass.output_root()`.

        Without `if_changed`, everything is rebuilt. With it, Bootstrap is rebuilt only
        when the watched settings changed (or its output is missing), and the project's
        Sass files are rebuilt through Dart Sass's incremental `--update`, unless the
        watched settings changed, in which case they are all rebuilt.

        Examples::

            self.build(if_changed=True)  # cheap: only stale files are compiled
        """
        sass_executable = sass_executable or getattr(settings, "SASS_EXECUTABLE", None)
        includes = getattr(settings, "BOOTSTRAP_INCLUDES", None)
        options = dict(getattr(settings, "SASS_DART_OPTIONS", None) or {})
        extra_load_paths = list(options.pop("load_paths", []))
        scss_dirs = Sass.scss_dirs()

        build_fingerprint = fingerprint(
            {
                **{
                    name: getattr(settings, name, None)
                    for name in self.WATCHED_SETTINGS
                },
                "sass_executable": sass_executable,
                "djangx_version": Version.get("djangx").output,
            }
        )
        unchanged = (
            if_changed
            and self.stamp.exists()
            and self.stamp.read_text() == build_fingerprint
        )

        load_paths = [
            *([str(self.BOOTSTRAP_DIR)] if includes is not None else []),
            *(str(folder) for folder in scss_dirs),
            *extra_load_paths,
        ]
        compile_options = {**options, "load_paths": load_paths}
        built: list[Path] = []

        if includes is None:
            # Bootstrap is off: drop everything left over from an earlier configuration
            # (the CSS and its source map); the folder holds nothing else.
            shutil.rmtree(Sass.bootstrap_root(), ignore_errors=True)
        elif not (unchanged and self.out.exists()):
            Sass.compile_scss(
                self.build_source(includes),
                self.out,
                compile_options,
                nodeenv_dir=self.VENV_DIR,
                sass_executable=sass_executable,
                auto_install=auto_install,
            )
            built.append(self.out)

        if scss_dirs:
            Sass.compile_dirs(
                {
                    folder: Sass.scss_root() / prefix
                    for folder, prefix in scss_dirs.items()
                },
                compile_options,
                nodeenv_dir=self.VENV_DIR,
                sass_executable=sass_executable,
                auto_install=auto_install,
                update=bool(unchanged),
            )
            built.extend(scss_dirs)

        if includes is None and not scss_dirs:
            cprint(
                "Nothing to compile: BOOTSTRAP_INCLUDES is None and no Sass files were found.",
                Style.WARNING,
                verbosity=verbosity,
                min_verbosity=Verbosity.VERBOSE,
            )
            return

        self.stamp.parent.mkdir(parents=True, exist_ok=True)
        self.stamp.write_text(build_fingerprint)
        if built:
            cprint(
                [
                    ("Compiled SCSS to ", Style.SUCCESS),
                    (str(Sass.output_root()), Style.HIGHLIGHT),
                ],
                verbosity=verbosity,
            )

    def build_source(self, includes: list[str] | Literal["__all__"] | None) -> str:
        """Return the SCSS entry file that imports the chosen Bootstrap parts.

        Examples::

            self.build_source("__all__")  # "@use 'bootstrap';"
            self.build_source(["buttons"])  # "@use 'root';\\n@use 'buttons';\\n@use 'helpers';\\n@use 'utilities/api';"
            self.build_source(None)  # ""
        """
        match includes:
            case None:
                return ""
            case "__all__":
                lines = ["@use 'bootstrap';"]
            case _:
                unknown = sorted(set(includes) - set(self.COMPONENTS))
                if unknown:
                    raise CommandError(
                        f"Unknown BOOTSTRAP_INCLUDES: {', '.join(unknown)}"
                    )

                chosen = sorted(set(includes), key=self.COMPONENTS.index)
                names = ["root", *chosen, "helpers", "utilities/api"]
                lines = [f"@use '{name}';" for name in names]

        return "\n".join(lines)
