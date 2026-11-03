import shutil
import sys
from pathlib import Path
from typing import Any, ClassVar

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from .....core.utils.commands import Verbosity
from .....core.utils.console import Style, cprint
from .....core.utils.string import fingerprint
from .....core.utils.version import Version
from ...utils import Sass, SassBootstrap, SassStatic


class Command(BaseCommand):
    help: str = (
        "Manage Sass: --build compiles Bootstrap (if BOOTSTRAP_INCLUDES is set) "
        "and the .scss/.sass files in app static folders"
    )

    VENV_DIR: ClassVar[Path] = Path(sys.prefix)

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
        """Compile Bootstrap (optional) and the project's Sass files.

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
        sass_dirs = SassStatic.sass_dirs()

        shared_fingerprint_data = {
            "SASS_DART_OPTIONS": getattr(settings, "SASS_DART_OPTIONS", None),
            "sass_executable": sass_executable,
            "djangx_version": Version.get("djangx").output,
        }
        sass_fingerprint = fingerprint(shared_fingerprint_data)
        bootstrap_fingerprint = fingerprint(
            {
                "BOOTSTRAP_INCLUDES": includes,
                **shared_fingerprint_data,
            }
        )
        sass_unchanged = (
            if_changed
            and SassStatic.STAMP_FILE.exists()
            and SassStatic.STAMP_FILE.read_text() == sass_fingerprint
        )
        bootstrap_unchanged = (
            if_changed
            and SassBootstrap.STAMP_FILE.exists()
            and SassBootstrap.STAMP_FILE.read_text() == bootstrap_fingerprint
        )

        load_paths = [
            str(SassBootstrap.SOURCE_DIR),
            *(str(folder) for folder in sass_dirs),
            *extra_load_paths,
        ]
        compile_options = {**options, "load_paths": load_paths}
        built: list[Path] = []

        if includes is None:
            # Bootstrap is off: drop everything left over from an earlier configuration
            # (the CSS and its source map); the folder holds nothing else.
            shutil.rmtree(SassBootstrap.OUTPUT_DIR, ignore_errors=True)
        elif not (bootstrap_unchanged and SassBootstrap.OUTPUT_FILE.exists()):
            SassBootstrap.compile_css(
                includes,
                compile_options,
                nodeenv_dir=self.VENV_DIR,
                sass_executable=sass_executable,
                auto_install=auto_install,
            )
            built.append(SassBootstrap.OUTPUT_FILE)

        if sass_dirs:
            SassStatic.compile_dirs(
                {folder: folder for folder in sass_dirs},  # CSS goes next to its source
                compile_options,
                nodeenv_dir=self.VENV_DIR,
                sass_executable=sass_executable,
                auto_install=auto_install,
                update=bool(sass_unchanged),
            )
            built.extend(sass_dirs)

        if includes is None and not sass_dirs:
            cprint(
                "Nothing to compile: BOOTSTRAP_INCLUDES is None and no Sass files were found.",
                Style.WARNING,
                verbosity=verbosity,
                min_verbosity=Verbosity.VERBOSE,
            )
            return

        SassBootstrap.STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SassBootstrap.STAMP_FILE.write_text(bootstrap_fingerprint)
        SassStatic.STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
        SassStatic.STAMP_FILE.write_text(sass_fingerprint)
        if built:
            cprint(
                "Compiled SCSS.",
                Style.SUCCESS,
                verbosity=verbosity,
            )
