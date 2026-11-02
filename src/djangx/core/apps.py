from pathlib import Path

from django.apps import AppConfig

from .. import CORE_APP, CORE_DIR


class CoreConfig(AppConfig):
    name: str = CORE_APP
    base: Path = CORE_DIR
    static: Path = base / "static"
    resources: Path = base / "resources"
    vendor: Path = resources / "vendor"

    def ready(self) -> None:
        """In development, recompile Sass files when they change."""
        from django.conf import settings

        if settings.DEBUG:
            from .utils.sass import SassReloader

            SassReloader.connect()
