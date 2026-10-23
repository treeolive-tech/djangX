"""Command-line entry point."""

from sys import argv

from ... import Package
from ..utils import DJANGO_SETTINGS_MODULE, ExitCode, print_version
from .commands import HELP_COMMANDS, SCRIPT_COMMANDS


def _run_builtin() -> None:
    """Run a built-in command with a minimal Django setup and no Django core commands."""
    from django import setup
    from django.conf import settings
    from django.core.management import execute_from_command_line, get_commands

    from ..apps import CoreConfig

    if not settings.configured:
        settings.configure(INSTALLED_APPS=[CoreConfig.name])
        setup()

    commands = get_commands()
    for name, app in list(commands.items()):
        if app == "django.core":
            del commands[name]

    execute_from_command_line(argv)


def _run_project_or_help(command: str) -> None:
    """Run a command against the project's settings, or show help if none is found."""

    if DJANGO_SETTINGS_MODULE:
        from os import environ
        from pathlib import Path
        from sys import path

        from django.core.management import execute_from_command_line
        from dotenv import load_dotenv

        base_dir = Path.cwd()
        path.insert(0, str(base_dir))
        environ.setdefault("DJANGO_SETTINGS_MODULE", DJANGO_SETTINGS_MODULE)
        dotenv = base_dir / ".env.local"

        if dotenv.is_file():
            load_dotenv(dotenv)

        execute_from_command_line(argv)
    else:
        match argv[1]:
            case cmd if cmd in HELP_COMMANDS:
                print(
                    "No pyproject.toml found (or it's missing a [project] `settings` key).\n\n"
                    "To see project-specific commands, run this from the root of a "
                    f"{Package.verbose_name} project, or add to your pyproject.toml:\n\n"
                    "    [project]\n"
                    '    settings = "app.settings"'
                )

            case _:
                print(
                    f"Unknown command: '{argv[1]}'\nType '{Package.name} help' for usage."
                )
                raise SystemExit(ExitCode.ERROR)

        if command in HELP_COMMANDS:
            _run_builtin()


def main() -> None:
    """Dispatch the CLI command."""
    command: str | None = argv[1] if len(argv) > 1 else None

    match command:
        case None:
            print(
                "...but the people who know their God shall be strong and do exploits. — Daniel 11:32"
            )

        case "-v" | "--version" | "version":
            raise SystemExit(print_version(Package.name))

        case _ if command in SCRIPT_COMMANDS:
            _run_builtin()

        case _:
            _run_project_or_help(command)


if __name__ == "__main__":
    main()
