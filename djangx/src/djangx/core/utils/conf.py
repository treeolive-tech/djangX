"""Project settings: reads `pyproject.toml` and builds djangX's settings entries."""

from pathlib import Path
from tomllib import load
from typing import Any, ClassVar
from warnings import warn

from .files import write_file

__all__: list[str] = ["DJANGO_SETTINGS_MODULE", "Conf"]


class Conf:
    # `djangx.core` must come before `django.contrib.staticfiles` so its `runserver` wins.
    _REQUIRED_APPS: ClassVar[list[str]] = [
        "django_minify_html",
        "django_http_compression",
        "djangx.core",
        "rest_framework",
        "django_dart_sass",
        "django.contrib.staticfiles",
    ]
    _RELOAD_APP: ClassVar[str] = "django_browser_reload"

    # Request order: compression, then minify, then other HTML modifiers (reload last).
    _HTML_MIDDLEWARE: ClassVar[list[str]] = [
        "django_http_compression.middleware.HttpCompressionMiddleware",
        "django_minify_html.middleware.MinifyHtmlMiddleware",
    ]
    _RELOAD_MIDDLEWARE: ClassVar[str] = (
        "django_browser_reload.middleware.BrowserReloadMiddleware"
    )

    def __init__(self) -> None:
        """Load `pyproject.toml` from the working directory, or use empty data.

        Examples::

            Conf().path  # Path("/home/kevin/olyv/pyproject.toml")
        """
        self.path: Path = Path.cwd() / "pyproject.toml"
        self._data: dict[str, Any] = {}

        if self.path.is_file():
            with open(file=self.path, mode="rb") as f:
                self._data = load(f)

    def _get_str(self, *keys: str) -> str | None:
        """Return the string at *keys*, or ``None`` if missing or not a string.

        Examples::

            Conf()._get_str("project", "name")  # "olyv"
            Conf()._get_str("project", "version")  # None (not set)
        """
        value: Any = self._data
        for key in keys:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value if isinstance(value, str) else None

    @staticmethod
    def _discover_apps(app_dir: Path) -> list[str]:
        """Return dotted paths of folders in `app_dir` that have an `apps.py`.

        Examples::

            Conf._discover_apps(Path("/srv/site/app"))  # ["app.blog", "app.main"]
            Conf._discover_apps(Path("/srv/empty"))  # []
        """
        if not app_dir.is_dir():
            return []
        return [
            f"{app_dir.name}.{folder.name}"
            for folder in sorted(app_dir.iterdir())
            if (folder / "apps.py").is_file()
        ]

    @property
    def module(self) -> str | None:
        """The ``[project] settings`` value, or ``None`` if not a string.

        Examples::

            Conf().module  # "app.settings"
        """
        return self._get_str("project", "settings")

    @classmethod
    def installed_apps(
        cls, defaults: list[str], *, dir: Path, debug: bool = False
    ) -> list[str]:
        """Return auto-discovered `app.*` apps, then `defaults`, then djangX's apps.

        Examples::

            Conf.installed_apps(["django.contrib.auth"], dir=BASE_DIR / "app")  # ["app.blog", "django.contrib.auth", "django_minify_html", ..., "django.contrib.staticfiles"]
        """
        ours: list[str] = (
            [cls._RELOAD_APP, *cls._REQUIRED_APPS] if debug else cls._REQUIRED_APPS
        )
        found: list[str] = cls._discover_apps(dir)
        return [*(app for app in [*found, *defaults] if app not in ours), *ours]

    @classmethod
    def middleware(cls, middlewares: list[str], *, debug: bool = False) -> list[str]:
        """Return `middlewares` with djangX's HTML middleware appended in order.

        Examples::

            Conf.middleware(["django.middleware.security.SecurityMiddleware"])  # [..., "...HttpCompressionMiddleware", "...MinifyHtmlMiddleware"]
        """
        ours = [*cls._HTML_MIDDLEWARE, *([cls._RELOAD_MIDDLEWARE] if debug else [])]
        return [*(m for m in middlewares if m not in ours), *ours]

    @classmethod
    def _application(cls, kind: str, *, dir: Path, project: bool) -> str:
        """Return the `kind` ("asgi" or "wsgi") application path, creating `dir/<kind>.py` if missing.

        Examples::

            Conf._application("wsgi", dir=APP_DIR, project=False)  # "djangx.core.wsgi.application"
            Conf._application("wsgi", dir=APP_DIR, project=True)  # "app.wsgi.application"
        """
        if not project:
            return f"djangx.core.{kind}.application"

        if write_file(kind, dir) == "differs":
            warn(
                f"{dir / f'{kind}.py'} differs from djangX's template; leaving it as is.",
                stacklevel=3,
            )
        return f"{dir.name}.{kind}.application"

    @classmethod
    def asgi_application(cls, *, dir: Path, project: bool = False) -> str:
        """Return the `ASGI_APPLICATION` path: `dir/asgi.py` if `project`, else djangX's own.

        Examples::

            Conf.asgi_application(dir=APP_DIR)  # "djangx.core.asgi.application"
            Conf.asgi_application(dir=APP_DIR, project=True)  # "app.asgi.application"
        """
        return cls._application("asgi", dir=dir, project=project)

    @classmethod
    def wsgi_application(cls, *, dir: Path, project: bool = False) -> str:
        """Return the `WSGI_APPLICATION` path: `dir/wsgi.py` if `project`, else djangX's own.

        Examples::

            Conf.wsgi_application(dir=APP_DIR)  # "djangx.core.wsgi.application"
            Conf.wsgi_application(dir=APP_DIR, project=True)  # "app.wsgi.application"
        """
        return cls._application("wsgi", dir=dir, project=project)


DJANGO_SETTINGS_MODULE: str | None = Conf().module
