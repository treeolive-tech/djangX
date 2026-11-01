"""``djx createmanage``: create or remove `manage.py`.

Examples::

    djx createmanage
    djx createmanage --remove
"""

from pathlib import Path

from django.conf import settings

from ...apps import CoreConfig
from ...utils.commands import FileCommand


class Command(FileCommand):
    help = "Create or remove manage.py."

    filename = "manage.py"
    template_file = CoreConfig.resources / "createfile_templates" / "manage.py-tpl"

    def default_dir(self) -> Path:
        return settings.BASE_DIR
