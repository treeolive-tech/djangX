"""Project settings: finds the project's settings module and builds djangX's settings entries."""

from functools import cache
from importlib.util import find_spec
from pathlib import Path
from typing import ClassVar

__all__: list[str] = ["Conf", "SettingsNotFound", "settings_module"]


class SettingsNotFound(Exception):
    """Raised when `app/settings.py` is missing from the working directory."""


@cache
def settings_module() -> str:
    """Return "app.settings"; raise `SettingsNotFound` if `app/settings.py` is missing.

    Examples::

        settings_module()  # "app.settings" (checks the disk once, then is cached)
        settings_module()  # SettingsNotFound: No app/settings.py found in /home/kevin
    """
    if not (Path.cwd() / "app" / "settings.py").is_file():
        raise SettingsNotFound(f"No app/settings.py found in {Path.cwd()}")
    return "app.settings"


class Conf:
    # `djangx.core` must come before `django.contrib.staticfiles` so its `runserver` wins.
    _REQUIRED_APPS: ClassVar[list[str]] = [
        "djangx.core",
        "rest_framework",
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

    @staticmethod
    def _is_installed(module_name: str) -> bool:
        """Return whether an optional package is importable."""
        return find_spec(module_name) is not None

    @classmethod
    def _optional_apps(cls, *, debug: bool = False) -> list[str]:
        """Return the optional apps that are available to the current environment."""
        apps: list[str] = []
        if debug and cls._is_installed(cls._RELOAD_APP):
            apps.append(cls._RELOAD_APP)
        if cls._is_installed("django_minify_html"):
            apps.append("django_minify_html")
        if cls._is_installed("django_http_compression"):
            apps.append("django_http_compression")
        return apps

    @classmethod
    def _optional_middleware(cls, *, debug: bool = False) -> list[str]:
        """Return optional HTML/request middleware that is currently available."""
        middleware: list[str] = []
        if cls._is_installed("django_http_compression"):
            middleware.append(cls._HTML_MIDDLEWARE[0])
        if cls._is_installed("django_minify_html"):
            middleware.append(cls._HTML_MIDDLEWARE[1])
        if debug and cls._is_installed(cls._RELOAD_APP):
            middleware.append(cls._RELOAD_MIDDLEWARE)
        return middleware

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

    @classmethod
    def installed_apps(
        cls, defaults: list[str], *, dir: Path, debug: bool = False
    ) -> list[str]:
        """Return auto-discovered `app.*` apps, then `defaults`, then djangX's apps.

        Examples::

            Conf.installed_apps(["django.contrib.auth"], dir=BASE_DIR / "app")  # ["app.blog", "django.contrib.auth", "django_minify_html", ..., "django.contrib.staticfiles"]
        """
        ours: list[str] = [*cls._optional_apps(debug=debug), *cls._REQUIRED_APPS]
        found: list[str] = cls._discover_apps(dir)
        return [*(app for app in [*found, *defaults] if app not in ours), *ours]

    @classmethod
    def middleware(cls, middlewares: list[str], *, debug: bool = False) -> list[str]:
        """Return `middlewares` with djangX's HTML middleware appended in order.

        Examples::

            Conf.middleware(["django.middleware.security.SecurityMiddleware"])  # [..., "...HttpCompressionMiddleware", "...MinifyHtmlMiddleware"]
        """
        ours = cls._optional_middleware(debug=debug)
        return [*(m for m in middlewares if m not in ours), *ours]
