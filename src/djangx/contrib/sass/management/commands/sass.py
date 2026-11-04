# ramani: src/djangx/contrib/sass/management/commands/sass.py
import shutil
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from .....core.utils.commands import Verbosity
from .....core.utils.console import Style, cprint
from .....core.utils.djangx_dir import DjangxDir
from .....core.utils.string import fingerprint
from .....core.utils.version import Version
from ...utils import Sass, SassBootstrap, SassGitignore, SassStatic


class Command(BaseCommand):
    help: str = (
        "Manage Sass: --build compiles Bootstrap (if BOOTSTRAP_INCLUDES is set) "
        "and the .scss/.sass files in app static folders"
    )

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
        parser.add_argument(
            "--sass-executable",
            metavar="PATH",
            help="Use this Sass executable instead of the `sass` command on PATH.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["build"]:
            raise CommandError("Nothing to do. Pass --build (-b).")
        self.build(
            if_changed=options["if_changed"],
            sass_executable=options["sass_executable"],
            verbosity=Verbosity(options["verbosity"]),
        )

    def build(
        self,
        *,
        if_changed: bool = False,
        sass_executable: str | Path | None = None,
        verbosity: Verbosity = Verbosity.NORMAL,
    ) -> None:
        """Compile Bootstrap (optional) and the project's Sass files.

        Without `if_changed`, everything is rebuilt. With it, Bootstrap is rebuilt only
        when the watched settings changed (or its output is missing), and the project's
        Sass files are rebuilt through Dart Sass's incremental `--update`, unless the
        watched settings changed, in which case they are all rebuilt. The watched
        settings include the installed Sass version, so upgrading Sass rebuilds both.

        Unless `SASS_GITIGNORE` is `False`, each Sass static folder's `.gitignore` is
        kept up to date with the CSS files generated there.

        Examples::

            self.build(if_changed=True)  # cheap: only stale files are compiled
        """
        DjangxDir.ensure()
        sass_executable = sass_executable or getattr(settings, "SASS_EXECUTABLE", None)
        includes = getattr(settings, "BOOTSTRAP_INCLUDES", None)
        options = dict(getattr(settings, "SASS_DART_OPTIONS", None) or {})
        manage_gitignore = bool(getattr(settings, "SASS_GITIGNORE", True))
        extra_load_paths = list(options.pop("load_paths", []))
        sass_dirs = SassStatic.sass_dirs()

        # Find Sass first so its version can be part of the fingerprints. Skipped when
        # there is nothing to compile.
        resolved_executable: str | None = None
        sass_version: str | None = None
        if includes is not None or sass_dirs:
            resolved_executable = Sass.resolve(sass_executable)
            sass_version = Sass.version(resolved_executable)

        shared_fingerprint_data = {
            "SASS_DART_OPTIONS": getattr(settings, "SASS_DART_OPTIONS", None),
            "sass_executable": sass_executable,
            "sass_version": sass_version,
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
            and SassStatic.stamp_file().exists()
            and SassStatic.stamp_file().read_text() == sass_fingerprint
        )
        bootstrap_unchanged = (
            if_changed
            and SassBootstrap.stamp_file().exists()
            and SassBootstrap.stamp_file().read_text() == bootstrap_fingerprint
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
            shutil.rmtree(SassBootstrap.output_dir(), ignore_errors=True)
        elif not (bootstrap_unchanged and SassBootstrap.output_file().exists()):
            SassBootstrap.compile_css(
                includes,
                compile_options,
                sass_executable=resolved_executable,
            )
            built.append(SassBootstrap.output_file())

        if sass_dirs:
            SassStatic.compile_dirs(
                {folder: folder for folder in sass_dirs},  # CSS goes next to its source
                compile_options,
                sass_executable=resolved_executable,
                update=bool(sass_unchanged),
            )
            built.extend(sass_dirs)
            if manage_gitignore:
                for folder in sass_dirs:
                    SassGitignore.sync(folder)

        if includes is None and not sass_dirs:
            cprint(
                "Nothing to compile: BOOTSTRAP_INCLUDES is None and no Sass files were found.",
                Style.WARNING,
                verbosity=verbosity,
                min_verbosity=Verbosity.VERBOSE,
            )
            return

        SassBootstrap.stamp_file().parent.mkdir(parents=True, exist_ok=True)
        SassBootstrap.stamp_file().write_text(bootstrap_fingerprint)
        SassStatic.stamp_file().parent.mkdir(parents=True, exist_ok=True)
        SassStatic.stamp_file().write_text(sass_fingerprint)
        if built:
            cprint(
                "Compiled SCSS.",
                Style.SUCCESS,
                verbosity=verbosity,
            )
