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
from django.core.management.base import CommandError
from django.utils._os import safe_join

from .platform import platform

__all__: list[str] = ["Sass", "SassCompilerError", "SassFinder"]

# Module-level alias: inside `SassFinder`, the name `list` is its `list` method.
type _Messages = list[Any]


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

    # Where the Bootstrap SCSS sources live, relative to the resources root.
    SCSS_RESOURCES_DIR: ClassVar[str] = "vendor/bootstrap/scss"

    # Where compiled CSS lives, relative to `STATIC_ROOT` and the static URL.
    CSS_STATIC_DIR: ClassVar[str] = "vendor/bootstrap/css"

    # Name of the compiled CSS file.
    CSS_FILE: ClassVar[str] = "custom.css"

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

    @classmethod
    def install_sass(cls, nodeenv_dir: Path) -> str:
        """Install `sass-embedded` into the Node.js environment; return the `sass` path.

        Examples::

            Sass.install_sass(Path(sys.prefix))  # ".../.venv/bin/sass"
        """
        nodeenv_dir = Path(nodeenv_dir)
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
    def _resolve_sass(
        cls, nodeenv_dir: Path, *, executable: str | Path | None, auto_install: bool
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
        `load_paths` becomes `--load-path`; `source_map` defaults to off.

        Examples::

            Sass.compile_scss("a { b: c }", Path("out.css"), {"style": "compressed"}, nodeenv_dir=Path(sys.prefix))
        """
        executable = cls._resolve_sass(
            Path(nodeenv_dir), executable=sass_executable, auto_install=auto_install
        )

        merged: dict[str, Any] = {"source_map": False, **(options or {})}
        load_paths: list[str] = list(merged.pop("load_paths", ()))

        command = [executable, "--stdin", *(f"--load-path={p}" for p in load_paths)]
        for name, value in merged.items():
            flag = name.replace("_", "-")
            if isinstance(value, bool):
                command.append(f"--{'' if value else 'no-'}{flag}")
            elif isinstance(value, (list, tuple)):
                command.extend(f"--{flag}={item}" for item in value)
            elif value is not None:
                command.append(f"--{flag}={value}")

        output.parent.mkdir(parents=True, exist_ok=True)
        cls._run([*command, str(output)], stdin=source)


class SassFinder(BaseFinder):
    """Let `runserver` serve the compiled Sass that lives in `STATIC_ROOT`.

    Only files under `Sass.CSS_STATIC_DIR` are found, and nothing is listed, so
    `collectstatic` ignores this finder.

    Examples::

        finders.find("vendor/bootstrap/css/custom.css")  # ".../public/static/vendor/bootstrap/css/custom.css"
        finders.find("admin/css/base.css")  # None (left to the other finders)
    """

    @property
    def root(self) -> Path | None:
        """Return the folder holding the compiled CSS, or `None` without `STATIC_ROOT`."""
        if not settings.STATIC_ROOT:
            return None
        return Path(settings.STATIC_ROOT) / Sass.CSS_STATIC_DIR

    def find(self, path: str, find_all: bool = False, **kwargs: Any) -> Any:
        """Return the file for `path` under `root` (a list if `find_all`), else nothing.

        `Any` because django-stubs types `BaseFinder.find` as `str | None`.
        """
        path = path.replace("\\", "/")
        prefix = f"{Sass.CSS_STATIC_DIR}/"
        match: str | None = None
        if self.root and path.startswith(prefix):
            try:
                file = Path(safe_join(self.root, path.removeprefix(prefix)))
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
