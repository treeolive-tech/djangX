from typing import Any

from django.contrib.staticfiles.management.commands.runserver import (
    Command as RunserverCommand,
)
from django.core.management import call_command

from ...utils.enum import Verbosity


class Command(RunserverCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        """Recompile SCSS only if the watched settings changed, then run the server."""
        call_command(
            "sass",
            build=True,
            if_changed=True,
            verbosity=Verbosity(options["verbosity"]),
        )
        super().handle(*args, **options)
