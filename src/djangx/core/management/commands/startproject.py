"""``djx startproject``: create a djangX project layout."""

from argparse import ArgumentParser
from pathlib import Path
from typing import Any

from django.core.management import call_command
from django.core.management.commands.startproject import Command as StartProjectCommand
from django.test import override_settings

from ...apps import CoreConfig
from ...utils.commands import NonSystemCheckedCommand, Verbosity
from ...utils.console import Style, cprint


class Command(StartProjectCommand, NonSystemCheckedCommand):
    help = "Create a djangX project with settings in app/."
    rewrite_template_suffixes = (
        *StartProjectCommand.rewrite_template_suffixes,
        (".md-tpl", ".md"),
        (".toml-tpl", ".toml"),
    )

    def handle(self, **options: Any) -> None:
        platform = options.pop("platform")
        target = (
            Path(options["directory"]).expanduser().resolve()
            if options["directory"]
            else Path.cwd() / options["name"]
        )
        if options["template"] is None:
            options["template"] = str(CoreConfig.resources / "project_template")
        options["extensions"] = [*options["extensions"], "md", "toml"]
        options["vercel"] = platform == "vercel"
        super().handle(**options)
        with override_settings(APP_DIR=target / "app"):
            call_command("startapp", "main", verbosity=Verbosity.QUIET)
        if platform == "vercel":
            with override_settings(BASE_DIR=target):
                call_command("createdeploy", verbosity=Verbosity.QUIET)
        cprint(
            [
                ("✓ Created project ", Style.SUCCESS),
                (options["name"], Style.HIGHLIGHT),
                (" in ", Style.SUCCESS),
                (str(target), Style.HIGHLIGHT),
            ],
            verbosity=Verbosity(options["verbosity"]),
        )

    def add_arguments(self, parser: ArgumentParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--platform",
            choices=("vercel",),
            help="Deployment platform (default: none).",
        )
