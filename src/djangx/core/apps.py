from pathlib import Path

from django.apps import AppConfig

from .. import PKG_NAME


class CoreConfig(AppConfig):
    base: Path = Path(__file__).resolve().parent
    resources: Path = base / "resources"
    static: Path = base / "static"
    name: str = f"{PKG_NAME}.{base.name}"

    def ready(self) -> None:
        from . import checks  # noqa: F401
