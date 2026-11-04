# ramani: src/djangx/core/apps.py
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
        from .utils.djangx_dir import DjangxDir

        try:
            DjangxDir.ensure()
        except OSError:
            pass  # A read-only deployment doesn't need `.djangx` while running.
