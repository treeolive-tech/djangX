"""Command-line entry point."""

from sys import argv

from ... import PKG_NAME, PKG_VERBOSE_NAME
from ..utils.commands import HELP_COMMANDS, PROJECT_COMMANDS, SCRIPT_COMMANDS
from ..utils.console import Style, cprint


def _run_builtin(*, scripts_only: bool = False) -> None:
    """Run a built-in command with a minimal Django setup and no Django core commands.

    Examples::

        _run_builtin()  # every djangX command
        _run_builtin(scripts_only=True)  # hides PROJECT_COMMANDS, for help outside a project
    """
    from django import setup
    from django.conf import settings
    from django.core.management import execute_from_command_line, get_commands

    from ..apps import CoreConfig

    if not settings.configured:
        settings.configure(INSTALLED_APPS=[CoreConfig.name])
        setup()

    hidden = PROJECT_COMMANDS if scripts_only else set()
    commands = get_commands()
    for name, app in list(commands.items()):
        if app == "django.core" or name in hidden:
            del commands[name]

    execute_from_command_line(argv)


def _run_project_or_help(command: str) -> None:
    """Run a command against the project's settings, or show help if none is found."""
    from ..utils.conf import SettingsNotFound, settings_module

    try:
        module = settings_module()
    except SettingsNotFound:
        match argv[1]:
            case cmd if cmd in HELP_COMMANDS:
                cprint(
                    [
                        ("No app/settings.py found.", Style.WARNING),
                        (
                            "\n\nTo see project-specific commands, run this from the root of a ",
                            "",
                        ),
                        (PKG_VERBOSE_NAME, Style.HIGHLIGHT),
                        (" project (the folder that contains `app/settings.py`).", ""),
                    ]
                )

            case _:
                from ..utils.exit import ExitCode

                cprint(
                    [
                        ("Unknown command: ", Style.ERROR),
                        (f"'{argv[1]}'", Style.HIGHLIGHT),
                        ("\nType ", ""),
                        (f"'{PKG_NAME} help'", Style.HIGHLIGHT),
                        (" for usage.", ""),
                    ]
                )
                raise SystemExit(ExitCode.ERROR)

        if command in HELP_COMMANDS:
            _run_builtin(scripts_only=True)
    else:
        from os import environ
        from pathlib import Path
        from sys import path

        from django.core.management import execute_from_command_line
        from dotenv import load_dotenv

        base_dir = Path.cwd()
        path.insert(0, str(base_dir))
        environ.setdefault("DJANGO_SETTINGS_MODULE", module)
        dotenv = base_dir / ".env.local"

        if dotenv.is_file():
            load_dotenv(dotenv)

        execute_from_command_line(argv)


def main() -> None:
    """Dispatch the CLI command."""
    command: str | None = argv[1] if len(argv) > 1 else None

    match command:
        case None:
            cprint(
                "...but the people who know their God shall be strong and do exploits. — Daniel 11:32",
                Style.INFO,
            )

        case "-v" | "--version" | "version":
            from ..utils.version import print_version

            raise SystemExit(print_version(PKG_NAME))

        case _ if command in SCRIPT_COMMANDS:
            _run_builtin()

        case _:
            _run_project_or_help(command)


if __name__ == "__main__":
    main()
