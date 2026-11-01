"""``djx createdeploy``: create or remove the `deploy.yml` GitHub workflow.

Examples::

    djx createdeploy
    djx createdeploy --remove
"""

from pathlib import Path

from django.conf import settings

from ...apps import CoreConfig
from ...utils.commands import FileCommand


class Command(FileCommand):
    help = "Create or remove the deploy.yml GitHub workflow."

    filename = "deploy.yml"
    template_file = CoreConfig.resources / "createfile_templates" / "deploy.yml-tpl"

    def default_dir(self) -> Path:
        return settings.BASE_DIR / ".github" / "workflows"
