"""Locate, install and run Dart Sass."""

import platform
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, Literal, final

from django.core.management import call_command
from django.core.management.base import CommandError

from ...core.utils.conf import Conf, project_app_configs
from ...core.utils.console import Style, cprint
from .apps import SassConfig

__all__: list[str] = [
    "Sass",
    "SassBootstrap",
    "SassCompilerError",
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
    def install_sass(cls, nodeenv_dir: Path) -> str:
        """Install Sass in the project's Node.js folder and return its command path."""
        if sass := cls._find_in_nodeenv("sass", nodeenv_dir):
            return sass

        if cls._find_in_nodeenv("node", nodeenv_dir) is None:
            if sys.prefix == sys.base_prefix:
                raise SassCompilerError(
                    "Installing Sass needs an active virtual environment."
                )
            cls.run(
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

        # npm uses a different folder for global commands on Windows.
        prefix = (
            cls._bin_dir(nodeenv_dir)
            if platform.system().lower() == "windows"
            else nodeenv_dir
        )
        cls.run([npm, "install", "--global", f"--prefix={prefix}", "sass-embedded"])

        sass = cls._find_in_nodeenv("sass", nodeenv_dir)
        if sass is None:
            raise SassCompilerError(
                "sass-embedded was installed, but its `sass` command was not found."
            )
        return sass

    @classmethod
    def compile_source(
        cls,
        source: str,
        output: Path,
        options: Mapping[str, Any] | None = None,
        *,
        nodeenv_dir: Path,
        sass_executable: str | Path | None = None,
        auto_install: bool = False,
    ) -> None:
        """Compile SCSS text into a CSS file.

        The SCSS text is sent to Sass through standard input. `options` become Sass
        command-line flags; source maps are off unless requested.
        """
        executable = cls.resolve(
            Path(nodeenv_dir), executable=sass_executable, auto_install=auto_install
        )
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
    def resolve(
        cls,
        nodeenv_dir: Path,
        *,
        executable: str | Path | None,
        auto_install: bool,
    ) -> str:
        """Choose which Sass command to run, or explain how to get one."""
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
        """Return the Node.js environment folder where commands are stored."""
        return nodeenv_dir / (
            "Scripts" if platform.system().lower() == "windows" else "bin"
        )

    @classmethod
    def _find_in_nodeenv(cls, name: str, nodeenv_dir: Path) -> str | None:
        """Find a command such as `sass` or `node` inside the Node.js environment."""
        return shutil.which(name, path=str(cls._bin_dir(nodeenv_dir)))

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

    STAMP_FILE: ClassVar[Path] = SassConfig.static / ".sass-settings-hash"

    @classmethod
    def sass_dirs(cls) -> list[Path]:
        """Find app `static` folders that contain `.scss` or `.sass` files."""
        sass_folders: list[Path] = []
        for app_config in project_app_configs():
            folder = (Path(app_config.path) / "static").resolve()
            if (
                folder.is_dir()
                and folder not in sass_folders
                and any(
                    file.is_file()
                    for pattern in cls.SASS_PATTERNS
                    for file in folder.rglob(pattern)
                )
            ):
                sass_folders.append(folder)
        return sass_folders

    @classmethod
    def source_for(cls, css_path: str) -> tuple[Path, Path] | None:
        """Find the Sass source for a static CSS path, or return `None`."""
        css_without_extension = css_path.lstrip("/").removesuffix(".css")
        for folder in cls.sass_dirs():
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
        nodeenv_dir: Path,
        sass_executable: str | Path | None = None,
        auto_install: bool = False,
        update: bool = True,
    ) -> None:
        """Compile Sass folders, optionally updating only stale files.

        Partials (files whose names start with `_`) are imported but not emitted as
        standalone CSS. Use the same source and destination folder to compile beside
        each source file.
        """
        if not mappings:
            return
        executable = Sass.resolve(
            Path(nodeenv_dir), executable=sass_executable, auto_install=auto_install
        )
        command = [executable, *Sass._flags(options)]
        if update:
            command.append("--update")
        for source, destination in mappings.items():
            destination.mkdir(parents=True, exist_ok=True)
            command.append(f"{source}:{destination}")
        Sass.run(command)


@final
class SassBootstrap:
    """Bootstrap-specific source paths, component selection, and compilation."""

    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    SOURCE_DIR: ClassVar[Path] = SassConfig.resources / "vendor" / "bootstrap" / "scss"

    OUTPUT_DIR: ClassVar[Path] = SassConfig.static / "vendor" / "bootstrap" / "css"

    OUTPUT_FILE: ClassVar[Path] = OUTPUT_DIR / "compiled.css"

    STATIC_PATH: ClassVar[str] = OUTPUT_FILE.relative_to(SassConfig.static).as_posix()

    STAMP_FILE: ClassVar[Path] = OUTPUT_DIR / ".settings-hash"

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
        nodeenv_dir: Path,
        sass_executable: str | Path | None = None,
        auto_install: bool = False,
    ) -> None:
        """Compile the configured Bootstrap components to `OUTPUT_FILE`."""
        Sass.compile_source(
            cls.build_source(includes),
            cls.OUTPUT_FILE,
            options,
            nodeenv_dir=nodeenv_dir,
            sass_executable=sass_executable,
            auto_install=auto_install,
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
        if file_path.suffix in {
            Path(pattern).suffix for pattern in SassStatic.SASS_PATTERNS
        }:
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
        for pattern in SassStatic.SASS_PATTERNS:
            for file in root.rglob(pattern):
                try:
                    files[file] = file.stat().st_mtime_ns
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
