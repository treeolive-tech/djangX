"""Project settings: finds the project's settings module and builds djangX's settings entries."""

from functools import cache
from pathlib import Path
from typing import ClassVar, final

from django.apps import AppConfig, apps

__all__: list[str] = [
    "Conf",
    "SettingsNotFound",
    "project_app_configs",
    "settings_module",
]


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


def project_app_configs() -> list[AppConfig]:
    """Return installed app configs whose names start with `app.`."""
    return [
        app_config
        for app_config in apps.get_app_configs()
        if app_config.name.startswith("app.")
    ]


@final
class Conf:
    __slots__ = ()

    def __new__(cls):
        raise TypeError(f"{cls.__name__} cannot be instantiated.")

    _HTTP_COMPRESSION_APP: ClassVar[str] = "django_http_compression"
    _RELOAD_APP: ClassVar[str] = "django_browser_reload"
    _DEBUG_APPS: ClassVar[frozenset[str]] = frozenset({_RELOAD_APP})

    @classmethod
    def debug_app_enabled(cls, app_name: str, *, debug: bool) -> bool:
        """Return whether djangX enables an optional app in debug mode."""
        return debug and app_name in cls._DEBUG_APPS

    @classmethod
    def _framework_apps(cls, *, debug: bool = False) -> list[str]:
        """Return djangX's framework apps, including reload support in debug mode."""
        return [
            *(
                [cls._RELOAD_APP]
                if cls.debug_app_enabled(cls._RELOAD_APP, debug=debug)
                else []
            ),
            cls._HTTP_COMPRESSION_APP,
        ]

    @classmethod
    def _framework_middleware(cls, *, debug: bool = False) -> list[str]:
        """Return framework middleware in request order, with reload support last."""
        return [
            "django_http_compression.middleware.HttpCompressionMiddleware",
            *(
                ["django_browser_reload.middleware.BrowserReloadMiddleware"]
                if cls.debug_app_enabled(cls._RELOAD_APP, debug=debug)
                else []
            ),
        ]

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

        `djangx.core` comes first among djangX's apps and before the reload app.

        Examples::

            Conf.installed_apps(["django.contrib.auth"], dir=BASE_DIR / "app")  # ["app.blog", "django.contrib.auth", "djangx.core", "django_http_compression", "django.contrib.staticfiles"]
        """
        ours: list[str] = [
            "djangx.core",
            *cls._framework_apps(debug=debug),
            "rest_framework",
            "django.contrib.staticfiles",
        ]
        found: list[str] = cls._discover_apps(dir)
        return [*(app for app in [*found, *defaults] if app not in ours), *ours]

    @classmethod
    def middleware(cls, middlewares: list[str], *, debug: bool = False) -> list[str]:
        """Return `middlewares` with djangX's HTML middleware appended in order.

        Examples::

            Conf.middleware(["django.middleware.security.SecurityMiddleware"])  # [..., "...HttpCompressionMiddleware"]
        """
        ours = cls._framework_middleware(debug=debug)
        return [*(m for m in middlewares if m not in ours), *ours]
