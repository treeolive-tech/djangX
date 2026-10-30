"""``djx startproject``: create a djangX project layout."""

from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.commands.startproject import Command as StartProjectCommand
from django.test import override_settings

from ...utils.commands import NonSystemCheckedCommand


class Command(StartProjectCommand, NonSystemCheckedCommand):
    help = "Create a djangX project with settings in app/."
    rewrite_template_suffixes = (
        *StartProjectCommand.rewrite_template_suffixes,
        (".md-tpl", ".md"),
        (".toml-tpl", ".toml"),
    )

    def handle(self, **options: Any) -> None:
        target = (
            Path(options["directory"]).expanduser().resolve()
            if options["directory"]
            else Path.cwd() / options["name"]
        )
        if options["template"] is None:
            options["template"] = str(
                Path(__file__).resolve().parents[2] / "resources" / "project_template"
            )
        options["extensions"] = [*options["extensions"], "md", "toml"]
        super().handle(**options)
        with override_settings(APP_DIR=target / "app"):
            call_command("startapp", "main", verbosity=0)
