# ramani: src/djangx/contrib/sass/utils.py
"""Locate and run Dart Sass."""

import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, ClassVar, Literal, final

from django.core.management import call_command
from django.core.management.base import CommandError

from ...core.utils.conf import Conf, project_app_configs
from ...core.utils.console import Style, cprint
from ...core.utils.djangx_dir import DjangxDir
from .apps import SassConfig

__all__: list[str] = [
    "Sass",
    "SassBootstrap",
    "SassCompilerError",
    "SassGitignore",
    "SassStatic",
    "SassWatcher",
]


class SassCompilerError(CommandError):
    """An error that explains why Sass could not be used."""


@final
class Sass:
    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    @classmethod
    def compile_source(
        cls,
        source: str,
        output: Path,
        options: Mapping[str, Any] | None = None,
        *,
        sass_executable: str | Path | None = None,
    ) -> None:
        """Compile SCSS text into a CSS file.

        The SCSS text is sent to Sass through standard input. `options` become Sass
        command-line flags; source maps are off unless requested.
        """
        executable = cls.resolve(sass_executable)
        command = [executable, "--stdin", *cls._flags(options)]
        output.parent.mkdir(parents=True, exist_ok=True)
        cls.run([*command, str(output)], stdin=source)

    @staticmethod
    def _flags(options: Mapping[str, Any] | None) -> list[str]:
        """Turn an options dictionary into command-line flags for Sass.

        Names use underscores in Python and hyphens in Sass. Lists make one flag
        per item, and `load_paths` becomes one `--load-path` flag per folder.
        """
        merged: dict[str, Any] = {"source_map": False, **(options or {})}
        flags: list[str] = []
        for name, value in merged.items():
            flag = name.replace("_", "-")
            if name == "load_paths":
                flags.extend(f"--load-path={path}" for path in value if path)
            elif isinstance(value, bool):
                flags.append(f"--{'' if value else 'no-'}{flag}")
            elif isinstance(value, (list, tuple)):
                flags.extend(f"--{flag}={item}" for item in value)
            elif value is not None:
                flags.append(f"--{flag}={value}")
        return flags

    @classmethod
    def resolve(cls, executable: str | Path | None = None) -> str:
        """Return the Sass command to run, or explain how to get one.

        Uses `executable` if given, otherwise the `sass` command on `PATH`.
        """
        if executable is not None:
            found = shutil.which(str(Path(executable).expanduser()))
            if found is None:
                raise SassCompilerError(
                    f"Configured Sass executable was not found: {executable}"
                )
            return found

        if found := shutil.which("sass"):
            return found

        raise SassCompilerError(
            "Dart Sass was not found. Install it so the `sass` command is on your PATH "
            "(see https://sass-lang.com/install), or set SASS_EXECUTABLE / pass "
            "`--sass-executable`."
        )

    _versions: ClassVar[dict[str, str]] = {}

    @classmethod
    def version(cls, executable: str) -> str:
        """Return what `sass --version` prints, remembered for this process.

        Used in the build fingerprints so upgrading Sass rebuilds the CSS. Returns
        `"unknown"` (not remembered) if the command fails; the build itself will
        then report the real problem.
        """
        if executable not in cls._versions:
            try:
                cls._versions[executable] = cls.run([executable, "--version"]).strip()
            except SassCompilerError:
                return "unknown"
        return cls._versions[executable]

    @staticmethod
    def run(command: list[str], *, stdin: str | None = None) -> str:
        """Run a command and return its printed output, or raise a clear error."""
        try:
            result = subprocess.run(
                command, input=stdin, text=True, capture_output=True, check=False
            )
        except OSError as error:
            raise SassCompilerError(f"Could not run {command[0]}: {error}") from error
        if result.returncode:
            message = result.stderr.strip() or result.stdout.strip()
            raise SassCompilerError(message or f"Command failed: {command[0]}")
        return result.stdout


@final
class SassStatic:
    """Discover and compile Sass sources in project app static folders."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    SASS_PATTERNS: ClassVar[tuple[str, ...]] = ("*.scss", "*.sass")

    SASS_SUFFIXES: ClassVar[tuple[str, ...]] = tuple(
        pattern.removeprefix("*") for pattern in SASS_PATTERNS
    )

    @staticmethod
    def stamp_file() -> Path:
        """Return where the project Sass build fingerprint is stored."""
        return DjangxDir.path() / "sass" / "project.hash"

    @staticmethod
    def static_dirs() -> list[Path]:
        """Return each project app's `static` folder, without looking inside them."""
        folders: list[Path] = []
        for app_config in project_app_configs():
            folder = (Path(app_config.path) / "static").resolve()
            if folder.is_dir() and folder not in folders:
                folders.append(folder)
        return folders

    @classmethod
    def iter_sources(cls, folder: Path) -> Iterator[os.DirEntry[str]]:
        """Yield every `.scss` / `.sass` file under `folder` in a single walk.

        Symbolic links to folders are not followed. Folders that disappear or can't
        be read while walking are skipped.
        """
        pending = [str(folder)]
        while pending:
            try:
                with os.scandir(pending.pop()) as scanner:
                    entries = list(scanner)
            except OSError:
                continue
            for entry in entries:
                if entry.is_dir(follow_symlinks=False):
                    pending.append(entry.path)
                elif entry.name.endswith(cls.SASS_SUFFIXES) and entry.is_file():
                    yield entry

    @classmethod
    def sass_dirs(cls) -> list[Path]:
        """Find app `static` folders that contain `.scss` or `.sass` files."""
        return [
            folder
            for folder in cls.static_dirs()
            if next(cls.iter_sources(folder), None) is not None
        ]

    @classmethod
    def source_for(cls, css_path: str) -> tuple[Path, Path] | None:
        """Find the Sass source for a static CSS path, or return `None`.

        Only the exact candidate files are checked, so a path with no Sass source
        costs a few file checks instead of a scan of every static folder.
        """
        css_without_extension = css_path.lstrip("/").removesuffix(".css")
        for folder in cls.static_dirs():
            for suffix in (".scss", ".sass"):
                source_file = (folder / f"{css_without_extension}{suffix}").resolve()
                if source_file.is_relative_to(folder) and source_file.is_file():
                    return source_file, folder
        return None

    @classmethod
    def compile_dirs(
        cls,
        mappings: Mapping[Path, Path],
        options: Mapping[str, Any] | None = None,
        *,
        sass_executable: str | Path | None = None,
        update: bool = True,
    ) -> None:
        """Compile Sass folders, optionally updating only stale files.

        Partials (files whose names start with `_`) are imported but not emitted as
        standalone CSS. Use the same source and destination folder to compile beside
        each source file.
        """
        if not mappings:
            return
        executable = Sass.resolve(sass_executable)
        command = [executable, *Sass._flags(options)]
        if update:
            command.append("--update")
        for source, destination in mappings.items():
            destination.mkdir(parents=True, exist_ok=True)
            command.append(f"{source}:{destination}")
        Sass.run(command)


@final
class SassGitignore:
    """Keep generated CSS out of git with a managed block in `.gitignore`.

    Compiled CSS is written beside its Sass source, so each Sass static folder gets a
    `.gitignore` listing exactly the files Sass generates there (`site.css` and
    `site.css.map` for `site.scss`). Hand-written CSS is never listed. Everything
    between the start and end markers belongs to djangX and is rewritten on every
    build; any other line in the file is left alone.
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    FILE_NAME: ClassVar[str] = ".gitignore"

    START: ClassVar[str] = (
        "# >>> djangx sass: generated CSS (managed automatically, do not edit) >>>"
    )

    END: ClassVar[str] = "# <<< djangx sass <<<"

    @staticmethod
    def _escape(path: str) -> str:
        """Escape characters that `.gitignore` treats as pattern syntax."""
        escaped = re.sub(r"([\\*?\[\]])", r"\\\1", path)
        return escaped[:-1] + "\\ " if escaped.endswith(" ") else escaped

    @classmethod
    def entries(cls, folder: Path) -> list[str]:
        """Return anchored ignore patterns for the CSS built from sources in `folder`.

        Partials (names starting with `_`) produce no CSS, so they are skipped.

        Examples::

            SassGitignore.entries(Path("app/blog/static"))
            # ["/blog/css/site.css", "/blog/css/site.css.map"]
        """
        outputs: set[str] = set()
        for entry in SassStatic.iter_sources(folder):
            if entry.name.startswith("_"):
                continue
            css = Path(entry.path).relative_to(folder).with_suffix(".css").as_posix()
            outputs.update({css, f"{css}.map"})
        return [f"/{cls._escape(path)}" for path in sorted(outputs)]

    @classmethod
    def sync(cls, folder: Path) -> bool:
        """Create or update the managed block in `folder/.gitignore`.

        Returns `True` if the file was written. Nothing is written when the file is
        already correct, when there is nothing to ignore, when the file can't be read
        or written, or when it has a start marker without an end marker (it is left
        exactly as the user has it rather than guessing what to overwrite).
        """
        path = folder / cls.FILE_NAME
        entries = cls.entries(folder)
        managed = [cls.START, *entries, cls.END]

        existing: str | None = None
        try:
            if path.is_file():
                existing = path.read_bytes().decode("utf-8")
        except OSError, UnicodeDecodeError:
            return False

        newline = "\r\n" if existing and "\r\n" in existing else "\n"
        lines = existing.replace("\r\n", "\n").split("\n") if existing else []
        if lines and lines[-1] == "":
            lines.pop()  # the file's final newline

        starts = [i for i, line in enumerate(lines) if line.strip() == cls.START]
        if starts:
            start = starts[0]
            end = next(
                (
                    i
                    for i in range(start + 1, len(lines))
                    if lines[i].strip() == cls.END
                ),
                None,
            )
            if end is None:
                return False
            updated = [*lines[:start], *managed, *lines[end + 1 :]]
        elif not entries:
            return False
        else:
            separator = [""] if lines and lines[-1].strip() else []
            updated = [*lines, *separator, *managed]

        text = newline.join(updated) + newline
        if text == existing:
            return False
        try:
            path.write_bytes(text.encode("utf-8"))
        except OSError:
            return False
        return True


@final
class SassBootstrap:
    """Bootstrap-specific source paths, component selection, and compilation."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    SOURCE_DIR: ClassVar[Path] = SassConfig.resources / "vendor" / "bootstrap" / "scss"

    STATIC_PATH: ClassVar[str] = "vendor/bootstrap/css/compiled.css"

    @classmethod
    def output_file(cls) -> Path:
        """Return the compiled CSS file, inside the project's `.djangx/static`."""
        return DjangxDir.static_dir() / cls.STATIC_PATH

    @classmethod
    def output_dir(cls) -> Path:
        """Return the folder holding the compiled CSS and its source map."""
        return cls.output_file().parent

    @staticmethod
    def stamp_file() -> Path:
        """Return where the Bootstrap build fingerprint is stored."""
        return DjangxDir.path() / "sass" / "bootstrap.hash"

    # `root` and the trailing `helpers` / `utilities/api` are always included.
    COMPONENTS: ClassVar[list[str]] = [
        "content", "layout", "forms", "buttons", "accordion", "alert", "avatar",
        "badge", "breadcrumb", "chip", "card", "carousel", "datepicker", "dialog",
        "menu", "list-group", "nav", "nav-overflow", "navbar", "drawer",
        "pagination", "placeholder", "popover", "progress", "spinner", "stepper",
        "toasts", "tooltip", "transitions",
    ]  # fmt: skip

    @classmethod
    def build_source(cls, includes: list[str] | Literal["__all__"] | None) -> str:
        """Return the entry SCSS that imports the requested Bootstrap components."""
        match includes:
            case None:
                return ""
            case "__all__":
                lines = ["@use 'bootstrap';"]
            case _:
                unknown = sorted(set(includes) - set(cls.COMPONENTS))
                if unknown:
                    raise CommandError(
                        f"Unknown BOOTSTRAP_INCLUDES: {', '.join(unknown)}"
                    )

                chosen = sorted(set(includes), key=cls.COMPONENTS.index)
                names = ["root", *chosen, "helpers", "utilities/api"]
                lines = [f"@use '{name}';" for name in names]

        return "\n".join(lines)

    @classmethod
    def compile_css(
        cls,
        includes: list[str] | Literal["__all__"] | None,
        options: Mapping[str, Any] | None = None,
        *,
        sass_executable: str | Path | None = None,
    ) -> None:
        """Compile the configured Bootstrap components to `output_file()`."""
        Sass.compile_source(
            cls.build_source(includes),
            cls.output_file(),
            options,
            sass_executable=sass_executable,
        )


@final
class SassWatcher:
    """Watch Sass folders during development and rebuild CSS after edits.

    The first time a template asks for CSS made from a Sass file, `watch()` starts
    one background thread. It checks registered folders every half second, including
    partial files. When a file changes, `build()` recompiles out-of-date CSS beside
    the Sass source. The browser-reload package can then refresh the page.
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    INTERVAL: ClassVar[float] = 0.5

    _roots: ClassVar[dict[Path, dict[Path, int]]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()
    _build_lock: ClassVar[threading.Lock] = threading.Lock()
    _thread: ClassVar[threading.Thread | None] = None

    @classmethod
    def connect_browser_reload(cls) -> None:
        """Make browser reload ignore Sass sources but handle compiled CSS changes."""
        from django.apps import apps
        from django.conf import settings
        from django.utils.autoreload import file_changed

        if not Conf.debug_app_enabled("django_browser_reload", debug=settings.DEBUG):
            return
        if not apps.is_installed("django_browser_reload"):
            return

        # Importing views connects django-browser-reload's signal receivers.
        from importlib import import_module

        import_module("django_browser_reload.views")
        file_changed.disconnect(dispatch_uid="browser_reload")
        file_changed.connect(
            cls._browser_reload_file_changed,
            dispatch_uid="djangx_sass_browser_reload",
        )

    @staticmethod
    def _browser_reload_file_changed(*, file_path: Path, **kwargs: Any) -> bool | None:
        """Ignore Sass source events and forward other changes to browser reload."""
        if file_path.suffix in SassStatic.SASS_SUFFIXES:
            return True

        from django_browser_reload.views import on_file_changed

        return on_file_changed(file_path=file_path, **kwargs)

    @staticmethod
    def build() -> bool:
        """Rebuild changed Sass files; return `False` and print an error if it fails."""
        with SassWatcher._build_lock:
            try:
                call_command("sass", build=True, if_changed=True, verbosity=0)
            except CommandError as error:
                cprint(f"Sass compile failed: {error}", Style.ERROR)
                return False
        return True

    @staticmethod
    def _snapshot(root: Path) -> dict[Path, int]:
        """Remember when each Sass file under this folder was last changed."""
        files: dict[Path, int] = {}
        for entry in SassStatic.iter_sources(root):
            try:
                files[Path(entry.path)] = entry.stat().st_mtime_ns
            except OSError:
                continue  # removed while scanning
        return files

    @classmethod
    def watch(cls, root: Path) -> None:
        """Add a folder to the watcher; adding the same folder again does nothing."""
        root = root.resolve()
        with cls._lock:
            if root in cls._roots:
                return
            cls._roots[root] = cls._snapshot(root)
            if cls._thread is None:
                cls._thread = threading.Thread(
                    target=cls._run, name="djangx-sass-watcher", daemon=True
                )
                cls._thread.start()

    @classmethod
    def _run(cls) -> None:
        """Check watched folders repeatedly and build once when files have changed."""
        while True:
            time.sleep(cls.INTERVAL)
            with cls._lock:
                roots = list(cls._roots)
            changed = False
            for root in roots:
                current = cls._snapshot(root)
                with cls._lock:
                    if current != cls._roots[root]:
                        # Stored even if the build fails, so a broken file is retried
                        # only after the next edit instead of on every poll.
                        cls._roots[root] = current
                        changed = True
            if changed:
                cls.build()
