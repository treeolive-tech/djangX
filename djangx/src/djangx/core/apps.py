from pathlib import Path

from django.apps import AppConfig

from .. import CORE_APP, CORE_DIR


class CoreConfig(AppConfig):
    name: str = CORE_APP
    base: Path = CORE_DIR
    static: Path = base / "static"
    resources: Path = base / "resources"
