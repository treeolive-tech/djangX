from django.apps import AppConfig

from .. import CORE_APP, CORE_DIR


class CoreConfig(AppConfig):
    name = CORE_APP
    base_dir = CORE_DIR
    static_dir = base_dir / "static"
    res_dir = base_dir / "resources"
