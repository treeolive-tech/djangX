"""``djx createmanage``: create or remove `manage.py`.

Examples::

    djx createmanage
    djx createmanage --remove
"""

from pathlib import Path

from django.conf import settings

from ...utils.commands import FileCommand

MANAGE_PY: str = '''\
"""Vercel reads this for the settings module. For development, run `djangx` or `djx` instead."""

from os import environ

from djangx.core.utils.conf import settings_module

environ.setdefault(key="DJANGO_SETTINGS_MODULE", value=settings_module())

if __name__ == "__main__":
    from sys import argv

    from django.core.management import execute_from_command_line

    execute_from_command_line(argv)
'''


class Command(FileCommand):
    help = "Create or remove manage.py."

    filename = "manage.py"
    template = MANAGE_PY

    def default_dir(self) -> Path:
        return settings.BASE_DIR
