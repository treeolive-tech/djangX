from pathlib import Path

from django.apps import AppConfig

from ... import PKG_NAME


class SassConfig(AppConfig):
    base: Path = Path(__file__).resolve().parent
    resources: Path = base / "resources"
    static: Path = base / "static"

    def ready(self) -> None:
        from .utils import SassWatcher

        SassWatcher.connect_browser_reload()

    name: str = f"{PKG_NAME}.contrib.{base.name}"
