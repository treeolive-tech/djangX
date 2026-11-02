"""Locate, install and run Dart Sass, and serve its compiled output in development."""

import shutil
import subprocess
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any, ClassVar, final

from django.conf import settings
from django.contrib.staticfiles.finders import BaseFinder
from django.core.exceptions import SuspiciousFileOperation
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils._os import safe_join
from django.utils.autoreload import autoreload_started, file_changed

from .platform import platform

__all__: list[str] = ["Sass", "SassCompilerError", "SassFinder", "SassReloader"]


class SassCompilerError(CommandError):
    """Raised when Sass cannot be found, installed or run."""


@final
class Sass:
    """Namespace for Sass executable resolution, installation and compilation.

    Examples::

        Sass.install_sass(Path(sys.prefix))  # ".../.venv/bin/sass"
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    BOOTSTRAP_RELATIVE_DIR: ClassVar[str] = "bootstrap/scss"

    # Everything Sass builds lives under one parent folder in `STATIC_ROOT`:
    #   compiled_sass/.settings-hash
    #   compiled_sass/bootstrap/output.css
    #   compiled_sass/scss/<path mirroring your static folders>.css
    OUTPUT_DIR: ClassVar[str] = "compiled_sass"

    BOOTSTRAP_OUTPUT_DIR: ClassVar[str] = "bootstrap"

    SCSS_OUTPUT_DIR: ClassVar[str] = "scss"

    CSS_OUTPUT_FILE: ClassVar[str] = "output.css"

    STAMP_FILE: ClassVar[str] = ".settings-hash"

    SASS_PATTERNS: ClassVar[tuple[str, ...]] = ("*.scss", "*.sass")

    @classmethod
    def install_sass(cls, nodeenv_dir: Path) -> str:
        """Install `sass-embedded` into the Node.js environment; return the `sass` path.

        Examples::

            Sass.install_sass(Path(sys.prefix))  # ".../.venv/bin/sass"
        """

        if sass := cls._find_in_nodeenv("sass", nodeenv_dir):
            return sass

        if cls._find_in_nodeenv("node", nodeenv_dir) is None:
            if sys.prefix == sys.base_prefix:
                raise SassCompilerError(
                    "Installing Sass needs an active virtual environment."
                )
            cls._run(
                [
                    sys.executable,
                    "-m",
                    "nodeenv",
                    "--node=lts",
                    "--python-virtualenv",
                    str(nodeenv_dir),
                ]
            )

        npm = cls._find_in_nodeenv("npm", nodeenv_dir)
        if npm is None:
            raise SassCompilerError("npm was not found in the Node.js environment.")

        # On Windows, npm puts global executables directly in the prefix.
        prefix = (
            cls._bin_dir(nodeenv_dir) if platform.os_name == "windows" else nodeenv_dir
        )
        cls._run([npm, "install", "--global", f"--prefix={prefix}", "sass-embedded"])

        sass = cls._find_in_nodeenv("sass", nodeenv_dir)
        if sass is None:
            raise SassCompilerError(
                "sass-embedded was installed, but its `sass` command was not found."
            )
        return sass

    @classmethod
    def output_root(cls) -> Path:
        """Return the parent folder inside `STATIC_ROOT` that holds everything Sass builds.

        Examples::

            Sass.output_root()  # Path(".../public/static/compiled_sass")
        """
        return Path(settings.STATIC_ROOT) / cls.OUTPUT_DIR

    @classmethod
    def bootstrap_root(cls) -> Path:
        """Return the folder that holds the compiled Bootstrap CSS.

        Examples::

            Sass.bootstrap_root()  # Path(".../public/static/compiled_sass/bootstrap")
        """
        return cls.output_root() / cls.BOOTSTRAP_OUTPUT_DIR

    @classmethod
    def scss_root(cls) -> Path:
        """Return the folder that holds the CSS compiled from your own Sass files.

        Examples::

            Sass.scss_root()  # Path(".../public/static/compiled_sass/scss")
        """
        return cls.output_root() / cls.SCSS_OUTPUT_DIR

    @classmethod
    def scss_dirs(cls) -> dict[Path, str]:
        """Return the static folders that contain Sass files, mapped to their URL prefix.

        Looks at `static/` in every installed `app.*` app and at `STATICFILES_DIRS`
        (a `(prefix, path)` entry keeps its prefix, otherwise the prefix is `""`).
        Folders that do not exist or hold no `.scss`/`.sass` file are left out.

        Examples::

            Sass.scss_dirs()  # {Path(".../app/blog/static"): "", Path(".../assets"): "site"}
        """
        from django.apps import apps

        candidates: list[tuple[Path, str]] = [
            (Path(config.path) / "static", "")
            for config in apps.get_app_configs()
            if config.name.startswith("app.")
        ]
        for entry in getattr(settings, "STATICFILES_DIRS", ()):
            if isinstance(entry, (list, tuple)):
                prefix, folder = entry
                candidates.append((Path(folder), str(prefix).strip("/")))
            else:
                candidates.append((Path(entry), ""))

        found: dict[Path, str] = {}
        for folder, prefix in candidates:
            folder = folder.resolve()
            if folder in found or not folder.is_dir():
                continue
            if any(next(folder.rglob(p), None) is not None for p in cls.SASS_PATTERNS):
                found[folder] = prefix
        return found

    @classmethod
    def compile_scss(
        cls,
        source: str,
        output: Path,
        options: Mapping[str, Any] | None = None,
        *,
        nodeenv_dir: Path,
        sass_executable: str | Path | None = None,
        auto_install: bool = False,
    ) -> None:
        """Compile SCSS `source` (read from stdin) into the `output` file.

        `options` maps to Dart Sass flags (`style="compressed"` -> `--style=compressed`).
        `source_map` defaults to off.

        Examples::

            Sass.compile_scss("a { b: c }", Path("out.css"), {"style": "compressed"}, nodeenv_dir=Path(sys.prefix))
        """
        executable = cls._resolve_sass(
            Path(nodeenv_dir), executable=sass_executable, auto_install=auto_install
        )
        command = [executable, "--stdin", *cls._flags(options)]
        output.parent.mkdir(parents=True, exist_ok=True)
        cls._run([*command, str(output)], stdin=source)

    @classmethod
    def compile_dirs(
        cls,
        mappings: Mapping[Path, Path],
        options: Mapping[str, Any] | None = None,
        *,
        nodeenv_dir: Path,
        sass_executable: str | Path | None = None,
        auto_install: bool = False,
        update: bool = True,
    ) -> None:
        """Compile every non-partial Sass file of each source folder into its output folder.

        Files starting with `_` are partials and are only compiled when imported.
        With `update`, Dart Sass rebuilds only stale files (`--update`); without it,
        every file is rebuilt.

        Examples::

            Sass.compile_dirs({Path("app/blog/static"): Path("public/static/compiled_sass/scss")}, nodeenv_dir=Path(sys.prefix))
        """
        if not mappings:
            return
        executable = cls._resolve_sass(
            Path(nodeenv_dir), executable=sass_executable, auto_install=auto_install
        )
        command = [executable, *cls._flags(options)]
        if update:
            command.append("--update")
        for source, destination in mappings.items():
            destination.mkdir(parents=True, exist_ok=True)
            command.append(f"{source}:{destination}")
        cls._run(command)

    @staticmethod
    def _flags(options: Mapping[str, Any] | None) -> list[str]:
        """Translate `options` into Dart Sass command-line flags.

        Examples::

            Sass._flags({"style": "compressed", "load_paths": ["a", "b"]})
            # ["--no-source-map", "--style=compressed", "--load-path=a", "--load-path=b"]
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
    def _resolve_sass(
        cls,
        nodeenv_dir: Path,
        *,
        executable: str | Path | None,
        auto_install: bool,
    ) -> str:
        """Find Sass: explicit path, then nodeenv, then PATH, then install if allowed."""
        if executable is not None:
            found = shutil.which(str(Path(executable).expanduser()))
            if found is None:
                raise SassCompilerError(
                    f"Configured Sass executable was not found: {executable}"
                )
            return found

        if found := cls._find_in_nodeenv("sass", nodeenv_dir) or shutil.which("sass"):
            return found

        if auto_install:
            return cls.install_sass(nodeenv_dir)

        raise SassCompilerError(
            "Dart Sass was not found. Set SASS_EXECUTABLE, pass `--sass-executable`, "
            "or run `djx sass --install`."
        )

    @staticmethod
    def _bin_dir(nodeenv_dir: Path) -> Path:
        """Return the folder holding executables in the Node.js environment."""
        return nodeenv_dir / ("Scripts" if platform.os_name == "windows" else "bin")

    @classmethod
    def _find_in_nodeenv(cls, name: str, nodeenv_dir: Path) -> str | None:
        """Return the executable `name` from the Node.js environment, if present."""
        return shutil.which(name, path=str(cls._bin_dir(nodeenv_dir)))

    @staticmethod
    def _run(command: list[str], *, stdin: str | None = None) -> str:
        """Run `command` and return its stdout; raise `SassCompilerError` on failure."""
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
class SassReloader:
    """Namespace for recompiling Sass files in development without restarting the server.

    Django's autoreloader watches Python files and restarts the server. Sass files are
    not Python, so this adds them to the watch list and, when one changes, recompiles
    and tells the autoreloader the change was handled (so it does not restart).

    `django_browser_reload` also listens to `file_changed`. Receivers run in the order
    they were connected, so `djangx.core` must come before it in `INSTALLED_APPS` (see
    `Conf.installed_apps`); then the CSS is rebuilt before the browser is told to reload.

    Examples::

        SassReloader.connect()  # called from `CoreConfig.ready()` when `DEBUG` is on
    """

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    @staticmethod
    def watch(sender: Any, **kwargs: Any) -> None:
        """Add every Sass folder to the autoreloader's watch list."""
        for folder in Sass.scss_dirs():
            for pattern in Sass.SASS_PATTERNS:
                sender.watch_dir(folder, f"**/{pattern}")

    @staticmethod
    def recompile(sender: Any, file_path: Path, **kwargs: Any) -> bool | None:
        """Recompile after a Sass file changed; return `True` so Django does not restart.

        Other files return `None`, which leaves Django's normal behaviour untouched.
        """
        if file_path.suffix not in {".scss", ".sass"}:
            return None

        from .console import Style, cprint

        try:
            call_command("sass", build=True, if_changed=True, verbosity=0)
        except CommandError as error:
            cprint(f"Sass compile failed: {error}", Style.ERROR)
        return True

    @classmethod
    def connect(cls) -> None:
        """Connect `watch` and `recompile` to Django's autoreload signals."""
        autoreload_started.connect(cls.watch, dispatch_uid="djangx_sass_watch")
        file_changed.connect(cls.recompile, dispatch_uid="djangx_sass_recompile")


type _Messages = list[Any]


class SassFinder(BaseFinder):
    """Let `runserver` serve the compiled Sass that lives in `STATIC_ROOT`.

    Everything under the `Sass.OUTPUT_DIR` folder is found (Bootstrap and your own
    files), and nothing is listed, so `collectstatic` ignores this finder.

    Examples::

        finders.find("compiled_sass/bootstrap/output.css")  # ".../public/static/compiled_sass/bootstrap/output.css"
        finders.find("compiled_sass/scss/blog/css/site.css")  # ".../public/static/compiled_sass/scss/blog/css/site.css"
        finders.find("admin/css/base.css")  # None (left to the other finders)
    """

    @property
    def root(self) -> Path | None:
        """Return the folder holding all compiled CSS, or `None` without `STATIC_ROOT`."""
        if not settings.STATIC_ROOT:
            return None
        return Sass.output_root()

    def find(self, path: str, find_all: bool = False, **kwargs: Any) -> Any:
        """Return the file for `path` under `root` (a list if `find_all`), else nothing.

        `Any` because django-stubs types `BaseFinder.find` as `str | None`.
        """
        path = path.replace("\\", "/")
        prefix = f"{Sass.OUTPUT_DIR}/"
        match: str | None = None
        root = self.root
        if root and path.startswith(prefix):
            try:
                file = Path(safe_join(root, path.removeprefix(prefix)))
            except SuspiciousFileOperation:
                file = None
            if file and file.is_file():
                match = str(file)
        if find_all:
            return [match] if match else []
        return match

    def list(self, ignore_patterns: Any) -> Iterator[Any]:
        """Yield nothing, so `collectstatic` does not copy the file onto itself."""
        return iter(())

    def check(self, **kwargs: Any) -> _Messages:
        """Return no system-check errors."""
        return []
