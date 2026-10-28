"""Project settings: reads `pyproject.toml` and builds djangX's settings entries."""

from pathlib import Path
from tomllib import load
from typing import Any, ClassVar

from django.conf import settings

__all__: list[str] = ["DJANGO_SETTINGS_MODULE", "Settings"]


class Settings:
    _USED_HOME_URL: ClassVar[bool] = False

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

            Settings().path  # Path("/home/kevin/olyv/pyproject.toml")
        """
        self.path: Path = Path.cwd() / "pyproject.toml"
        self._data: dict[str, Any] = {}

        if self.path.is_file():
            with open(file=self.path, mode="rb") as f:
                self._data = load(f)

    def _get_str(self, *keys: str) -> str | None:
        """Return the string at *keys*, or ``None`` if missing or not a string.

        Examples::

            Settings()._get_str("project", "name")  # "olyv"
            Settings()._get_str("project", "version")  # None (not set)
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

            Settings._discover_apps(Path("/srv/site/app"))  # ["app.blog", "app.main"]
            Settings._discover_apps(Path("/srv/empty"))  # []
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

            Settings().module  # "app.settings"
        """
        return self._get_str("project", "settings")

    @classmethod
    def installed_apps(
        cls, defaults: list[str], *, app_dir: Path, debug: bool = False
    ) -> list[str]:
        """Return auto-discovered `app.*` apps, then `defaults`, then djangX's apps.

        Examples::

            Settings.installed_apps(["django.contrib.auth"], app_dir=BASE_DIR / "app")  # ["app.blog", "django.contrib.auth", "django_minify_html", ..., "django.contrib.staticfiles"]
        """
        ours: list[str] = (
            [cls._RELOAD_APP, *cls._REQUIRED_APPS] if debug else cls._REQUIRED_APPS
        )
        found: list[str] = cls._discover_apps(app_dir)
        return [*(app for app in [*found, *defaults] if app not in ours), *ours]

    @classmethod
    def middleware(cls, middlewares: list[str], *, debug: bool = False) -> list[str]:
        """Return `middlewares` with djangX's HTML middleware appended in order.

        Examples::

            Settings.middleware(["django.middleware.security.SecurityMiddleware"])  # [..., "...HttpCompressionMiddleware", "...MinifyHtmlMiddleware"]
        """
        ours = [*cls._HTML_MIDDLEWARE, *([cls._RELOAD_MIDDLEWARE] if debug else [])]
        return [*(m for m in middlewares if m not in ours), *ours]

    @classmethod
    def home_url(cls) -> str:
        """Return the `HOME_URL` prefix with a trailing slash, or `""` if unset."""
        cls._USED_HOME_URL = True
        url = str(getattr(settings, "HOME_URL", None) or "").strip("/")
        return f"{url}/" if url else ""

    @classmethod
    def home_url_was_used(cls) -> bool:
        """Return whether `home_url()` has been called."""
        return cls._USED_HOME_URL

    @classmethod
    def _configured_url(cls, setting_name: str, default: str) -> str:
        """Return a configured URL prefix (or `default`) with a trailing slash."""
        url = str(getattr(settings, setting_name, None) or default).strip("/")
        return f"{url}/"

    @classmethod
    def admin_url(cls) -> str:
        """Return the admin URL prefix."""
        return cls._configured_url("ADMIN_URL", "admin")

    @classmethod
    def rest_auth_url(cls) -> str:
        """Return the DRF login/logout URL prefix."""
        return cls._configured_url("REST_AUTH_URL", "__api-auth__")

    @classmethod
    def reload_url(cls) -> str:
        """Return the browser-reload URL prefix."""
        return cls._configured_url("RELOAD_URL", "__reload__")


DJANGO_SETTINGS_MODULE: str | None = Settings().module
