from django.apps import AppConfig

from .. import CORE_APP, CORE_DIR


class CoreConfig(AppConfig):
    name = CORE_APP
    dir = CORE_DIR
